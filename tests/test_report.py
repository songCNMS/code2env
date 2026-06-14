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
            # repoA: 4 built (3 smoke ok, 1 smoke fail -> tool granularity)
            {"env_id": "a1", "repo": "repoA", "symbol": "m:f1", "draft_ok": True, "build_ok": True, "smoke_ok": True, "smoke_fail_reason": None},
            {"env_id": "a2", "repo": "repoA", "symbol": "m:f2", "draft_ok": True, "build_ok": True, "smoke_ok": True, "smoke_fail_reason": None},
            {"env_id": "a3", "repo": "repoA", "symbol": "m:f3", "draft_ok": True, "build_ok": True, "smoke_ok": True, "smoke_fail_reason": None},
            {"env_id": "a4", "repo": "repoA", "symbol": "m:f4", "draft_ok": True, "build_ok": True, "smoke_ok": False, "smoke_fail_reason": "agent exhausted step budget, no progress"},
            # repoB: 2 built (1 smoke ok, 1 smoke fail -> format error)
            {"env_id": "b1", "repo": "repoB", "symbol": "m:g1", "draft_ok": True, "build_ok": True, "smoke_ok": True, "smoke_fail_reason": None},
            {"env_id": "b2", "repo": "repoB", "symbol": "m:g2", "draft_ok": True, "build_ok": True, "smoke_ok": False, "smoke_fail_reason": "invalid json returned by tool"},
            # build failure (dependency)
            {"env_id": "b3", "repo": "repoB", "symbol": "m:g3", "draft_ok": True, "build_ok": False, "smoke_ok": False, "smoke_fail_reason": "ModuleNotFoundError: no module named lxml"},
            # draft failure (fixture)
            {"env_id": "c1", "repo": "repoC", "symbol": "m:h1", "draft_ok": False, "build_ok": False, "smoke_ok": False, "fixture": {"ok": False, "reason": "cannot synthesize fixture for required positional arg"}},
        ],
        "skipped": [
            {"symbol": "m:s1", "repo": "repoC", "reason": "fixture unsynthesizable: complex annotation"},
            {"symbol": "m:s2", "repo": "repoC", "reason": "no golden oracle available"},
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
    def test_keyword_routing(self) -> None:
        self.assertEqual(classify_reason("ModuleNotFoundError: no module named x"), "dependency_failure")
        self.assertEqual(classify_reason("cannot synthesize fixture"), "fixture_unsynthesizable")
        self.assertEqual(classify_reason("no golden oracle available"), "weak_oracle")
        self.assertEqual(classify_reason("agent exhausted step budget"), "tool_granularity")
        self.assertEqual(classify_reason("invalid json returned"), "format_error")
        self.assertEqual(classify_reason("something weird"), "other")
        self.assertEqual(classify_reason(None), "other")

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
            self.assertEqual(gen["counts"]["fixture_unsynthesizable"], 2)  # skip s1 + draft c1
            self.assertEqual(gen["counts"]["weak_oracle"], 1)              # skip s2
            self.assertEqual(gen["counts"]["dependency_failure"], 1)       # build b3
            self.assertEqual(gen["counts"]["tool_granularity"], 1)        # smoke a4
            self.assertEqual(gen["counts"]["format_error"], 1)           # smoke b2
            self.assertEqual(sum(gen["counts"].values()), 6)

    def test_rollout_stats_and_clustering(self) -> None:
        rollouts = [
            _conv("a1", score=0.9, correct=True, qualified=True),
            _conv("a2", score=0.7, correct=True, qualified=True),
            _conv("a4", score=0.1, correct=False, qualified=False, rounds=1, submit=False, termination="max_steps_exhausted"),
            _conv("b2", score=0.0, correct=False, qualified=True, termination="invalid json parse error"),
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


if __name__ == "__main__":
    unittest.main()
