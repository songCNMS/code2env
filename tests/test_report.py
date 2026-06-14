from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from code2env.jsonio import write_json, write_jsonl
from code2env.report import (
    FAILURE_TAGS,
    build_report,
    classify_reason,
    load_rollouts,
    render_markdown,
    write_report,
)


def _manifest() -> dict:
    return {
        "generated_at": "2026-06-14T00:00:00Z",
        "summary": {
            "candidates_scanned": 10,
            "draft_ok": 8,
            "build_ok": 6,
            "smoke_ok": 4,
            "skipped_no_fixture": 2,
            "by_repo": {"repoA": {"build_ok": 4, "smoke_ok": 3}, "repoB": {"build_ok": 2, "smoke_ok": 1}},
        },
        "envs": [
            # repoA: 4 built (3 smoke ok, 1 smoke fail -> weak_oracle via golden_error)
            {"env_id": "a1", "repo": "repoA", "symbol": "m:f1", "draft_ok": True, "build_ok": True, "smoke_ok": True, "smoke_fail_reason": None},
            {"env_id": "a2", "repo": "repoA", "symbol": "m:f2", "draft_ok": True, "build_ok": True, "smoke_ok": True, "smoke_fail_reason": None},
            {"env_id": "a3", "repo": "repoA", "symbol": "m:f3", "draft_ok": True, "build_ok": True, "smoke_ok": True, "smoke_fail_reason": None},
            {"env_id": "a4", "repo": "repoA", "symbol": "m:f4", "draft_ok": True, "build_ok": True, "smoke_ok": False, "smoke_fail_reason": "golden_error:golden computation raised"},
            # repoB: 2 built (1 smoke ok, 1 smoke fail -> weak_oracle via answer_mismatch)
            {"env_id": "b1", "repo": "repoB", "symbol": "m:g1", "draft_ok": True, "build_ok": True, "smoke_ok": True, "smoke_fail_reason": None},
            {"env_id": "b2", "repo": "repoB", "symbol": "m:g2", "draft_ok": True, "build_ok": True, "smoke_ok": False, "smoke_fail_reason": "answer_mismatch"},
            # build failure (dependency, canonical build_error:ModuleNotFound*)
            {"env_id": "b3", "repo": "repoB", "symbol": "m:g3", "draft_ok": True, "build_ok": False, "smoke_ok": False, "smoke_fail_reason": "build_error:ModuleNotFoundError: No module named 'lxml'"},
            # draft failure (fixture, canonical token)
            {"env_id": "c1", "repo": "repoC", "symbol": "m:h1", "draft_ok": False, "build_ok": False, "smoke_ok": False, "fixture": {"ok": False, "reason": "unsupported_param_type:numpy.ndarray"}},
        ],
        "skipped": [
            {"symbol": "m:s1", "repo": "repoC", "reason": "untyped_required_param"},
            {"symbol": "m:s2", "repo": "repoC", "reason": "requires_instance"},
        ],
    }


def _conv(env_id, *, model="gpt-5.5", rounds=3, qualified=True, correct=True, score=0.8, termination="submitted", submit=True):
    steps = []
    if submit:
        steps.append({"step": rounds, "action": {"type": "tool_call", "tool": "submit_answer", "arguments": {}}, "tool_result": {}, "reward": 0.0})
    return {
        "env_id": env_id,
        "model": model,
        "endpoint_source": "endpoint",
        "messages": [],
        "steps": steps,
        "final": {"submitted_answer": {}, "correct": correct, "score": score, "score_breakdown": {}, "steps": rounds},
        "num_tool_call_rounds": rounds,
        "qualified": qualified,
        "termination_reason": termination,
        "retries": 0,
        "errors": [],
    }


class ClassifyReasonTest(unittest.TestCase):
    def test_canonical_d1_vocabulary(self) -> None:
        # fixture_unsynthesizable: every canonical D1 token from the lead's contract.
        for token in (
            "untyped_required_param",
            "unsupported_param_type",
            "requires_instance",
            "possible_side_effect",
            "not_module_level",
            "function_node_not_found",
            "no_fixture",
        ):
            self.assertEqual(classify_reason(token), "fixture_unsynthesizable", token)
            self.assertEqual(classify_reason(f"{token}:some detail"), "fixture_unsynthesizable", token)

    def test_dependency_canonical(self) -> None:
        self.assertEqual(classify_reason("build_error:ModuleNotFoundError: No module named 'lxml'"), "dependency_failure")
        self.assertEqual(classify_reason("build_error:ImportError: cannot import name x"), "dependency_failure")
        self.assertEqual(classify_reason("draft_error:failed to import numpy"), "dependency_failure")
        # build_error without an import signal is not a dependency failure.
        self.assertEqual(classify_reason("build_error:SyntaxError"), "other")

    def test_weak_oracle_and_format_canonical(self) -> None:
        self.assertEqual(classify_reason("golden_error:golden computation raised"), "weak_oracle")
        self.assertEqual(classify_reason("answer_mismatch"), "weak_oracle")
        self.assertEqual(classify_reason("parse_error"), "format_error")
        self.assertEqual(classify_reason("schema:invalid action"), "format_error")

    def test_other_and_empty(self) -> None:
        self.assertEqual(classify_reason("something weird"), "other")
        self.assertEqual(classify_reason(None), "other")
        self.assertEqual(classify_reason(""), "other")

    def test_all_tags_known(self) -> None:
        self.assertIn("other", FAILURE_TAGS)


class ReportStatsTest(unittest.TestCase):
    def test_env_generation_stats(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mpath = Path(tmp) / "manifest.json"
            write_json(mpath, _manifest())
            report = build_report(mpath, None)
            env = report["env_generation"]
            self.assertEqual(env["candidates_scanned"], 10)
            self.assertEqual(env["draft_ok"], 8)
            self.assertEqual(env["build_ok"], 6)
            self.assertEqual(env["smoke_ok"], 4)
            self.assertEqual(env["draft_rate"], 0.8)
            self.assertEqual(env["build_rate"], 0.6)
            self.assertAlmostEqual(env["smoke_rate_of_built"], round(4 / 6, 4))

    def test_by_repo_distribution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mpath = Path(tmp) / "manifest.json"
            write_json(mpath, _manifest())
            by_repo = build_report(mpath, None)["env_generation"]["by_repo"]
            self.assertEqual(by_repo["repoA"], {"total": 4, "build_ok": 4, "smoke_ok": 3, "skipped": 0})
            self.assertEqual(by_repo["repoB"]["build_ok"], 2)
            self.assertEqual(by_repo["repoC"]["skipped"], 2)
            self.assertEqual(by_repo["repoC"]["total"], 1)  # the draft-failed c1 env

    def test_generation_failure_clustering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mpath = Path(tmp) / "manifest.json"
            write_json(mpath, _manifest())
            gen = build_report(mpath, None)["failure_clusters"]["generation"]
            # 2 skipped + draft fail(c1) + build fail(b3) + 2 smoke fails(a4,b2) = 6
            self.assertEqual(gen["total"], 6)
            # skip s1(untyped_required_param) + skip s2(requires_instance) + draft c1(unsupported_param_type)
            self.assertEqual(gen["counts"]["fixture_unsynthesizable"], 3)
            self.assertEqual(gen["counts"]["dependency_failure"], 1)       # build b3 build_error:ModuleNotFound
            self.assertEqual(gen["counts"]["weak_oracle"], 2)             # smoke a4 golden_error + b2 answer_mismatch
            self.assertEqual(gen["counts"]["tool_granularity"], 0)        # generation never tool_granularity
            self.assertEqual(gen["counts"]["format_error"], 0)
            self.assertEqual(gen["counts"]["other"], 0)
            self.assertEqual(sum(gen["counts"].values()), 6)

    def test_rollout_stats_and_clustering(self) -> None:
        rollouts = [
            _conv("a1", score=0.9, correct=True, qualified=True),
            _conv("a2", score=0.7, correct=True, qualified=True),
            _conv("a4", score=0.1, correct=False, qualified=False, rounds=1, submit=False, termination="max_steps_exhausted"),
            _conv("b2", score=0.0, correct=False, qualified=True, termination="parse_error"),
            _conv("b1", score=0.4, correct=True, qualified=True, termination="submitted"),  # low score
        ]
        with tempfile.TemporaryDirectory() as tmp:
            mpath = Path(tmp) / "manifest.json"
            write_json(mpath, _manifest())
            jsonl = Path(tmp) / "rollouts.jsonl"
            write_jsonl(jsonl, rollouts)
            report = build_report(mpath, jsonl)
            r = report["rollouts"]
            self.assertEqual(r["total"], 5)
            self.assertEqual(r["qualified"], 4)
            self.assertEqual(r["qualified_rate"], 0.8)
            self.assertEqual(r["correct"], 3)
            self.assertAlmostEqual(r["mean_score"], round((0.9 + 0.7 + 0.1 + 0.0 + 0.4) / 5, 4))
            self.assertEqual(r["low_score_count"], 3)  # 0.1, 0.0, 0.4 < 0.5
            self.assertEqual(r["by_model"]["gpt-5.5"]["total"], 5)

            rc = report["failure_clusters"]["rollout"]
            # unhealthy: a4 (unqualified), b2 (incorrect), b1 (low score) = 3
            self.assertEqual(rc["total"], 3)
            self.assertEqual(rc["counts"]["tool_granularity"], 1)  # a4 max_steps
            self.assertEqual(rc["counts"]["format_error"], 1)      # b2 parse error
            # b1: qualified+correct but low score, no failure keyword -> other
            self.assertEqual(rc["counts"]["other"], 1)

    def test_qualified_derived_when_flag_missing(self) -> None:
        conv = _conv("x", rounds=2, submit=True)
        del conv["qualified"]
        rollouts = [conv]
        with tempfile.TemporaryDirectory() as tmp:
            mpath = Path(tmp) / "manifest.json"
            write_json(mpath, _manifest())
            jsonl = Path(tmp) / "r.jsonl"
            write_jsonl(jsonl, rollouts)
            r = build_report(mpath, jsonl)["rollouts"]
            self.assertEqual(r["qualified"], 1)

        conv2 = _conv("y", rounds=1, submit=False)
        del conv2["qualified"]
        with tempfile.TemporaryDirectory() as tmp:
            mpath = Path(tmp) / "manifest.json"
            write_json(mpath, _manifest())
            jsonl = Path(tmp) / "r.jsonl"
            write_jsonl(jsonl, [conv2])
            r = build_report(mpath, jsonl)["rollouts"]
            self.assertEqual(r["qualified"], 0)


class LoaderAndOutputTest(unittest.TestCase):
    def test_load_rollouts_prefers_per_env_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "rollouts"
            d.mkdir()
            write_json(d / "a1.json", _conv("a1"))
            write_json(d / "a2.json", _conv("a2"))
            # a stray merged jsonl should be ignored when per-env files exist
            write_jsonl(d / "rollouts.jsonl", [_conv("a1"), _conv("a2"), _conv("a3")])
            loaded = load_rollouts(d)
            self.assertEqual(len(loaded), 2)
            self.assertEqual({c["env_id"] for c in loaded}, {"a1", "a2"})

    def test_load_rollouts_falls_back_to_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "rollouts"
            d.mkdir()
            write_jsonl(d / "rollouts.jsonl", [_conv("a1"), _conv("a2")])
            loaded = load_rollouts(d)
            self.assertEqual(len(loaded), 2)

    def test_write_report_emits_md_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mpath = Path(tmp) / "manifest.json"
            write_json(mpath, _manifest())
            jsonl = Path(tmp) / "rollouts.jsonl"
            write_jsonl(jsonl, [_conv("a1"), _conv("a2", score=0.2, correct=False, qualified=False, rounds=1, submit=False, termination="max_steps_exhausted")])
            out = Path(tmp) / "outputs"
            paths = write_report(mpath, jsonl, out)
            self.assertTrue(Path(paths["json"]).exists())
            self.assertTrue(Path(paths["md"]).exists())
            data = json.loads(Path(paths["json"]).read_text())
            self.assertIn("env_generation", data)
            md = Path(paths["md"]).read_text()
            self.assertIn("# code2env Rollout Summary Report", md)
            self.assertIn("Qualified", md)
            self.assertIn("Failure Clusters", md)

    def test_render_markdown_handles_no_rollouts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mpath = Path(tmp) / "manifest.json"
            write_json(mpath, _manifest())
            report = build_report(mpath, None)
            md = render_markdown(report)
            self.assertIn("0 records", md)
            self.assertEqual(report["rollouts"]["total"], 0)


def _golden_manifest() -> dict:
    """Post-dependency-install manifest carrying golden_status per env."""
    return {
        "generated_at": "2026-06-14T03:00:00Z",
        "summary": {"candidates_scanned": 4, "draft_ok": 4, "build_ok": 4, "smoke_ok": 3},
        "envs": [
            {"env_id": "a1", "repo": "requests", "draft_ok": True, "build_ok": True, "smoke_ok": True, "golden_status": "real_value"},
            {"env_id": "a2", "repo": "requests", "draft_ok": True, "build_ok": True, "smoke_ok": True, "golden_status": "real_value"},
            {"env_id": "f1", "repo": "flask", "draft_ok": True, "build_ok": True, "smoke_ok": True, "golden_status": "weak_oracle:no test assertions"},
            {"env_id": "f2", "repo": "flask", "draft_ok": True, "build_ok": True, "smoke_ok": False, "golden_status": "real_value"},
        ],
        "skipped": [],
    }


class GoldenStatusTrueCorrectTest(unittest.TestCase):
    def test_true_correct_rate_excludes_weak_oracle(self) -> None:
        rollouts = [
            _conv("a1", correct=True, score=0.9),   # real_value, correct
            _conv("a2", correct=False, score=0.2),  # real_value, incorrect
            _conv("f1", correct=True, score=0.9),   # weak_oracle -> excluded (false positive)
            _conv("f2", correct=True, score=0.8),   # real_value, correct
        ]
        with tempfile.TemporaryDirectory() as tmp:
            mpath = Path(tmp) / "m.json"
            write_json(mpath, _golden_manifest())
            jsonl = Path(tmp) / "r.jsonl"
            write_jsonl(jsonl, rollouts)
            r = build_report(mpath, jsonl)["rollouts"]
            self.assertEqual(r["total"], 4)
            self.assertEqual(r["correct"], 3)            # raw includes the f1 false positive
            self.assertEqual(r["weak_oracle_excluded"], 1)
            self.assertEqual(r["usable_total"], 3)       # 4 - 1 weak
            self.assertEqual(r["true_correct"], 2)       # a1 + f2 (f1 excluded)
            self.assertAlmostEqual(r["true_correct_rate"], round(2 / 3, 4))
            self.assertEqual(r["golden_unknown"], 0)

    def test_missing_golden_status_degrades_to_unknown_kept_in_denominator(self) -> None:
        manifest = _golden_manifest()
        # Drop golden_status from a2 -> rollout should count as unknown, still usable.
        for env in manifest["envs"]:
            if env["env_id"] == "a2":
                del env["golden_status"]
        rollouts = [_conv("a1", correct=True), _conv("a2", correct=False), _conv("f1", correct=True)]
        with tempfile.TemporaryDirectory() as tmp:
            mpath = Path(tmp) / "m.json"
            write_json(mpath, manifest)
            jsonl = Path(tmp) / "r.jsonl"
            write_jsonl(jsonl, rollouts)
            r = build_report(mpath, jsonl)["rollouts"]
            self.assertEqual(r["weak_oracle_excluded"], 1)   # f1
            self.assertEqual(r["golden_unknown"], 1)         # a2
            self.assertEqual(r["usable_total"], 2)           # a1 + a2
            self.assertEqual(r["true_correct"], 1)           # a1


class DependencyComparisonTest(unittest.TestCase):
    def _baseline(self) -> dict:
        # Pre-install: golden was error (no real_value), flask smoke all failing.
        return {
            "generated_at": "2026-06-14T01:00:00Z",
            "summary": {"candidates_scanned": 4, "draft_ok": 4, "build_ok": 4, "smoke_ok": 1},
            "envs": [
                {"env_id": "a1", "repo": "requests", "smoke_ok": True, "golden_status": "real_value"},
                {"env_id": "a2", "repo": "requests", "smoke_ok": False, "golden_status": "weak_oracle:error"},
                {"env_id": "f1", "repo": "flask", "smoke_ok": False, "golden_status": "weak_oracle:no deps"},
                {"env_id": "f2", "repo": "flask", "smoke_ok": False, "golden_status": "weak_oracle:no deps"},
            ],
            "skipped": [],
        }

    def test_before_after_with_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cur = Path(tmp) / "cur.json"
            base = Path(tmp) / "base.json"
            write_json(cur, _golden_manifest())
            write_json(base, self._baseline())
            comp = build_report(cur, None, baseline_manifest_path=base)["dependency_comparison"]
            self.assertTrue(comp["baseline_provided"])
            # a2 (weak->real) and f2 (weak->real) became real_value; a1 already real.
            self.assertEqual(comp["golden_error_to_real_value"], 2)
            # flask smoke_ok: before 0 -> after 1 (f1 ok in current manifest)
            self.assertEqual(comp["smoke_ok_by_repo"]["flask"], {"before": 0, "after": 1, "delta": 1})
            self.assertEqual(comp["smoke_ok_by_repo"]["requests"], {"before": 1, "after": 2, "delta": 1})

    def test_without_baseline_degrades(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cur = Path(tmp) / "cur.json"
            write_json(cur, _golden_manifest())
            report = build_report(cur, None)
            comp = report["dependency_comparison"]
            self.assertFalse(comp["baseline_provided"])
            self.assertEqual(comp["current_golden"]["counts"], {"real_value": 3, "weak_oracle": 1, "unknown": 0})
            md = render_markdown(report)
            self.assertIn("Dependency-install Before/After", md)
            self.assertIn("True correct", md)

    def test_markdown_shows_smoke_before_after(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cur = Path(tmp) / "cur.json"
            base = Path(tmp) / "base.json"
            write_json(cur, _golden_manifest())
            write_json(base, self._baseline())
            report = build_report(cur, None, baseline_manifest_path=base)
            md = render_markdown(report)
            self.assertIn("error → real_value", md)
            self.assertIn("smoke_ok by repo", md)


def _v3_manifest() -> dict:
    """Manifest with golden_status + determinism (task038 / w1 contract)."""
    return {
        "generated_at": "2026-06-14T06:00:00Z",
        "summary": {"candidates_scanned": 4, "draft_ok": 4, "build_ok": 4, "smoke_ok": 4},
        "envs": [
            {"env_id": "a1", "repo": "requests", "smoke_ok": True, "golden_status": "real_value", "determinism": "deterministic"},
            {"env_id": "a2", "repo": "requests", "smoke_ok": True, "golden_status": "real_value", "determinism": "deterministic"},
            {"env_id": "n1", "repo": "flask", "smoke_ok": True, "golden_status": "real_value", "determinism": "nondeterministic:uses time.time"},
            {"env_id": "w1", "repo": "flask", "smoke_ok": True, "golden_status": "weak_oracle:no deps", "determinism": "deterministic"},
        ],
        "skipped": [],
    }


class CategoriesAndDeterminismTest(unittest.TestCase):
    def test_categories_partition_and_true_nonzero_rate(self) -> None:
        rollouts = [
            _conv("a1", correct=True),    # deterministic_usable, correct
            _conv("a2", correct=False),   # deterministic_usable, still_wrong
            _conv("n1", correct=True),    # nondeterministic -> excluded
            _conv("w1", correct=True),    # weak_oracle -> excluded
        ]
        with tempfile.TemporaryDirectory() as tmp:
            mpath = Path(tmp) / "m.json"
            write_json(mpath, _v3_manifest())
            jsonl = Path(tmp) / "v3.jsonl"
            write_jsonl(jsonl, rollouts)
            r = build_report(mpath, jsonl)["rollouts"]
            cats = r["categories"]
            self.assertEqual(cats["deterministic_usable"], 2)
            self.assertEqual(cats["nondeterministic_excluded"], 1)
            self.assertEqual(cats["weak_oracle_excluded"], 1)
            self.assertEqual(cats["still_wrong"], 1)
            self.assertEqual(cats["golden_unknown"], 0)
            self.assertEqual(cats["envelope_flipped_to_correct"], 0)  # no prev run
            # partition sums to total
            self.assertEqual(
                cats["deterministic_usable"] + cats["nondeterministic_excluded"]
                + cats["weak_oracle_excluded"] + cats["golden_unknown"],
                r["total"],
            )
            # true non-zero: 1 correct (a1) / 2 deterministic usable
            self.assertEqual(r["true_nonzero_correct"], 1)
            self.assertEqual(r["true_nonzero_correct_rate"], 0.5)
            # task033 weak-only true_correct still present (a1+n1 correct over non-weak {a1,a2,n1})
            self.assertEqual(r["true_correct"], 2)
            self.assertEqual(r["usable_total"], 3)

    def test_missing_determinism_degrades_to_usable(self) -> None:
        manifest = _v3_manifest()
        for env in manifest["envs"]:
            if env["env_id"] == "n1":
                del env["determinism"]  # missing -> not excluded
        rollouts = [_conv("a1", correct=True), _conv("n1", correct=True)]
        with tempfile.TemporaryDirectory() as tmp:
            mpath = Path(tmp) / "m.json"
            write_json(mpath, manifest)
            jsonl = Path(tmp) / "v3.jsonl"
            write_jsonl(jsonl, rollouts)
            cats = build_report(mpath, jsonl)["rollouts"]["categories"]
            self.assertEqual(cats["nondeterministic_excluded"], 0)
            self.assertEqual(cats["deterministic_usable"], 2)  # n1 now usable


class EvolutionAndEnvelopeFlipTest(unittest.TestCase):
    def test_envelope_flipped_and_evolution(self) -> None:
        v2 = [
            _conv("a1", correct=False),  # was wrong in v2
            _conv("a2", correct=True),
            _conv("n1", correct=True),
            _conv("w1", correct=True),
        ]
        v3 = [
            _conv("a1", correct=True),   # flipped to correct in v3
            _conv("a2", correct=True),
            _conv("n1", correct=True),
            _conv("w1", correct=True),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            mpath = Path(tmp) / "m.json"
            write_json(mpath, _v3_manifest())
            v2p = Path(tmp) / "v2.jsonl"
            v3p = Path(tmp) / "v3.jsonl"
            write_jsonl(v2p, v2)
            write_jsonl(v3p, v3)
            report = build_report(mpath, v3p, prev_rollouts_paths=[v2p])
            r = report["rollouts"]
            self.assertEqual(r["categories"]["envelope_flipped_to_correct"], 1)  # a1
            evo = report["evolution"]
            self.assertEqual([e["label"] for e in evo], ["v1", "v2"])
            # v1 == prev run: true_nonzero 1/2 (a2 correct, a1 wrong among det-usable)
            self.assertEqual((evo[0]["true_nonzero_correct"], evo[0]["deterministic_usable"]), (1, 2))
            # v2 == current: true_nonzero 2/2
            self.assertEqual((evo[1]["true_nonzero_correct"], evo[1]["deterministic_usable"]), (2, 2))
            md = render_markdown(report)
            self.assertIn("Categories", md)
            self.assertIn("evolution", md)
            self.assertIn("True non-zero correct", md)

    def test_three_run_evolution_labels(self) -> None:
        runs = [[_conv("a1", correct=False)], [_conv("a1", correct=False)], [_conv("a1", correct=True)]]
        with tempfile.TemporaryDirectory() as tmp:
            mpath = Path(tmp) / "m.json"
            write_json(mpath, _v3_manifest())
            paths = []
            for i, run in enumerate(runs):
                p = Path(tmp) / f"r{i}.jsonl"
                write_jsonl(p, run)
                paths.append(p)
            report = build_report(mpath, paths[-1], prev_rollouts_paths=paths[:-1])
            self.assertEqual([e["label"] for e in report["evolution"]], ["v1", "v2", "v3"])


if __name__ == "__main__":
    unittest.main()
