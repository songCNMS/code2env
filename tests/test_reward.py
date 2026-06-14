from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from code2env.builder import build_env_package
from code2env.ingest import ingest_repo
from code2env.jsonio import write_json
from code2env.models import EnvSpec
from code2env.runtime import DEFAULT_REWARD_WEIGHTS, REWARD_DIMENSIONS, Code2Env
from code2env.spec import draft_env_spec


def _build_env(
    temp_dir: Path,
    body: str,
    *,
    symbol: str,
    fixture: dict | None = None,
    compute_golden: bool = True,
) -> Code2Env:
    repo = temp_dir / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "sample.py").write_text(body.lstrip(), encoding="utf-8")
    snapshot = ingest_repo(str(repo))
    spec = draft_env_spec(snapshot, symbol=symbol, fixture=fixture, compute_golden=compute_golden)
    spec_path = temp_dir / "env_spec.json"
    write_json(spec_path, spec.to_dict())
    package_root = build_env_package(spec_path, temp_dir / "generated")
    return Code2Env(package_root / "env_spec.json")


SAMPLE = """
def clean_text(value):
    return " ".join(value.strip().split())


def normalize_name(name, shout=False):
    \"\"\"Normalize a human name for display.\"\"\"
    cleaned = clean_text(name)
    if shout:
        return cleaned.upper()
    return cleaned.title()
"""

NET_SAMPLE = """
def tries_network():
    import socket
    socket.socket()
    return "unexpected"
"""


def _entrypoint_call(env: Code2Env) -> dict:
    return {"type": "tool_call", "tool": "call_entrypoint", "arguments": env.spec.fixture}


def _submit(answer: object) -> dict:
    return {"type": "tool_call", "tool": "submit_answer", "arguments": {"answer": answer}}


class MultiDimRewardTest(unittest.TestCase):
    def _normalize_env(self, temp_dir: Path) -> Code2Env:
        return _build_env(
            temp_dir,
            SAMPLE,
            symbol="sample:normalize_name",
            fixture={"args": ["  ada   lovelace "], "kwargs": {"shout": True}},
        )

    def test_full_correct_run_scores_every_dimension(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = self._normalize_env(Path(temp))
            env.reset()
            _, _, _, _ = env.step(_entrypoint_call(env))
            answer = env.state["last_tool_result"]
            _, _, done, info = env.step(_submit(answer))

            self.assertTrue(done)
            breakdown = env.evaluate()["score_breakdown"]
            dims = breakdown["dimensions"]
            # Every dimension present with raw/weight/weighted/detail.
            self.assertEqual(set(dims), set(REWARD_DIMENSIONS))
            for dim in REWARD_DIMENSIONS:
                self.assertEqual(set(dims[dim]), {"raw", "weight", "weighted", "detail"})
                self.assertAlmostEqual(dims[dim]["raw"], 1.0)
                self.assertAlmostEqual(dims[dim]["weighted"], dims[dim]["weight"])
            self.assertAlmostEqual(breakdown["total"], 1.0)
            self.assertTrue(0.0 <= breakdown["total"] <= 1.0)
            # step exposes the breakdown for online consumers too.
            self.assertIn("score_breakdown", info)

    def test_weighted_total_matches_reward_weights(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = self._normalize_env(Path(temp))
            env.reset()
            env.step(_entrypoint_call(env))
            answer = env.state["last_tool_result"]
            env.step(_submit(answer))
            dims = env.evaluate()["score_breakdown"]["dimensions"]
            for dim in REWARD_DIMENSIONS:
                self.assertAlmostEqual(dims[dim]["weight"], env.spec.reward["weights"][dim])

    def test_schema_validity_drops_on_invalid_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = self._normalize_env(Path(temp))
            env.reset()
            env.step({"type": "tool_call", "tool": "nonexistent_tool", "arguments": {}})
            dims = env.evaluate()["score_breakdown"]["dimensions"]
            self.assertEqual(dims["schema_validity"]["raw"], 0.0)
            # An invalid call is also wasted work -> efficiency penalised.
            self.assertLess(dims["efficiency"]["raw"], 1.0)

    def test_process_progress_is_partial_without_executing_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = self._normalize_env(Path(temp))
            env.reset()
            env.step({"type": "tool_call", "tool": "inspect_task", "arguments": {}})
            # Submit the known golden answer without ever executing the source.
            env.step(_submit(env.spec.golden_answer))
            dims = env.evaluate()["score_breakdown"]["dimensions"]
            # explored + submit_after_progress reached, execute_source not -> 2/3.
            self.assertAlmostEqual(dims["process_progress"]["raw"], 2 / 3, places=5)
            self.assertEqual(dims["final_correctness"]["raw"], 1.0)

    def test_efficiency_penalises_duplicate_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = self._normalize_env(Path(temp))
            env.reset()
            env.step(_entrypoint_call(env))
            env.step(_entrypoint_call(env))  # identical -> duplicate
            dims = env.evaluate()["score_breakdown"]["dimensions"]
            self.assertLess(dims["efficiency"]["raw"], 1.0)

    def test_efficiency_penalises_budget_exhaustion_without_submit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = self._normalize_env(Path(temp))
            env.max_steps = 2  # tighten budget for the test
            env.reset()
            env.step({"type": "tool_call", "tool": "inspect_task", "arguments": {}})
            _, _, done, _ = env.step({"type": "tool_call", "tool": "inspect_task", "arguments": {}})
            self.assertTrue(done)  # budget exhausted, never submitted
            dims = env.evaluate()["score_breakdown"]["dimensions"]
            self.assertLessEqual(dims["efficiency"]["raw"], 0.5)
            self.assertEqual(dims["final_correctness"]["raw"], 0.0)

    def test_safety_violation_zeroes_safety_dimension(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = _build_env(
                Path(temp),
                NET_SAMPLE,
                symbol="sample:tries_network",
                compute_golden=False,
            )
            env.reset()
            env.step({"type": "tool_call", "tool": "call_entrypoint", "arguments": {}})
            result = env.state["last_tool_result"]
            self.assertFalse(result["ok"])
            dims = env.evaluate()["score_breakdown"]["dimensions"]
            self.assertEqual(dims["safety"]["raw"], 0.0)

    def test_step_rewards_telescope_to_evaluation_total(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = self._normalize_env(Path(temp))
            obs = env.reset()
            initial_total = obs["state"]["score_breakdown"]["total"]
            _, r1, _, _ = env.step(_entrypoint_call(env))
            answer = env.state["last_tool_result"]
            _, r2, _, _ = env.step(_submit(answer))
            final_total = env.evaluate()["score_breakdown"]["total"]
            # Potential-based shaping: sum of dense step rewards == delta in total.
            self.assertAlmostEqual(r1 + r2, final_total - initial_total, places=6)

    def test_weights_fall_back_to_defaults_when_unspecified(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = self._normalize_env(Path(temp))
            # Strip declared weights to exercise the fallback path.
            spec_dict = env.spec.to_dict()
            spec_dict["reward"].pop("weights", None)
            env2 = Code2Env(EnvSpec.from_dict(spec_dict), package_root=env.package_root)
            self.assertEqual(env2.weights, DEFAULT_REWARD_WEIGHTS)

    def test_training_reward_and_evaluation_score_are_separate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = self._normalize_env(Path(temp))
            env.reset()
            _, reward, _, _ = env.step(_entrypoint_call(env))
            evaluation = env.evaluate()
            # step yields a scalar dense reward; evaluate yields the structured score.
            self.assertIsInstance(reward, float)
            self.assertIn("score_breakdown", evaluation)
            self.assertIsInstance(evaluation["score"], float)


if __name__ == "__main__":
    unittest.main()
