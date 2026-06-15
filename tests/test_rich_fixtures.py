from __future__ import annotations

import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from code2env.batch import generate_batch
from code2env.executor import serialize_value
from code2env.rich_fixtures import (
    dataframe_descriptor,
    fixture_component_descriptor,
    hydrate_value,
    numpy_array_descriptor,
    path_descriptor,
    torch_tensor_descriptor,
)
from code2env.rollout import ScriptedTraceSolveChat, run_rollout
from code2env.rollout_export import write_conversation
from code2env.runtime import Code2Env


class RichFixtureHydrationTest(unittest.TestCase):
    def test_hydrates_pandas_dataframe_descriptor(self) -> None:
        if importlib.util.find_spec("pandas") is None:
            self.skipTest("pandas is not installed")
        import pandas as pd

        value = hydrate_value(
            dataframe_descriptor(
                [
                    {"instrument": "SH000001", "datetime": "2020-01-02", "value": 1.5},
                    {"instrument": "SH000002", "datetime": "2020-01-03", "value": 2.5},
                ],
                columns=["instrument", "datetime", "value"],
                index_columns=["instrument", "datetime"],
                parse_dates=["datetime"],
            )
        )

        self.assertEqual(value.index.names, ["instrument", "datetime"])
        self.assertIsInstance(value.index.get_level_values("datetime")[0], pd.Timestamp)
        self.assertEqual(value.loc[("SH000001", pd.Timestamp("2020-01-02")), "value"], 1.5)

    def test_hydrates_path_descriptor_relative_to_source_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = hydrate_value(
                path_descriptor("data/input.csv", base="source_root"),
                source_root=temp_dir,
            )

        self.assertIsInstance(path, Path)
        self.assertEqual(path, (Path(temp_dir).resolve() / "data/input.csv"))
        self.assertEqual(path.name, "input.csv")
        self.assertIn("data", path.parts)

    def test_rejects_source_root_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "escapes source root"):
                hydrate_value(
                    path_descriptor("../escape", base="source_root"),
                    source_root=temp_dir,
                )

    def test_rejects_absolute_source_root_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "must be relative"):
                hydrate_value(
                    path_descriptor(str(Path(temp_dir).parent / "escape"), base="source_root"),
                    source_root=temp_dir,
                )

    def test_rejected_source_root_path_mkdir_does_not_create_outside(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_root = root / "repo"
            source_root.mkdir()
            outside = root / "escape"

            with self.assertRaisesRegex(ValueError, "escapes source root"):
                hydrate_value(
                    path_descriptor("../escape", base="source_root", mkdir=True),
                    source_root=source_root,
                )

            self.assertFalse(outside.exists())

    def test_tmpdir_path_descriptor_still_hydrates(self) -> None:
        path = hydrate_value(path_descriptor("scratch/output.txt", base="tmpdir"))

        self.assertIsInstance(path, Path)
        self.assertEqual(path.name, "output.txt")
        self.assertIn("scratch", path.parts)


class RichSerializationTest(unittest.TestCase):
    def test_serializes_pandas_dataframe_canonically(self) -> None:
        if importlib.util.find_spec("pandas") is None:
            self.skipTest("pandas is not installed")
        import pandas as pd

        df = pd.DataFrame(
            {"value": [1.5], "when": [pd.Timestamp("2020-01-02")]},
            index=pd.Index(["row1"], name="id"),
        )
        payload = serialize_value(df)

        self.assertEqual(payload["kind"], "pandas.DataFrame")
        self.assertEqual(payload["columns"], ["value", "when"])
        self.assertEqual(payload["index"], ["row1"])
        self.assertEqual(payload["index_names"], ["id"])
        self.assertEqual(payload["data"][0][1]["kind"], "pandas.Timestamp")

    def test_serializes_numpy_array_and_scalar_canonically(self) -> None:
        if importlib.util.find_spec("numpy") is None:
            self.skipTest("numpy is not installed")
        import numpy as np

        array_payload = serialize_value(np.array([[1, 2], [3, 4]], dtype="int64"))
        scalar_payload = serialize_value(np.float32(1.25))

        self.assertEqual(array_payload["kind"], "numpy.ndarray")
        self.assertEqual(array_payload["shape"], [2, 2])
        self.assertEqual(array_payload["dtype"], "int64")
        self.assertEqual(array_payload["data"], [[1, 2], [3, 4]])
        self.assertEqual(scalar_payload["kind"], "numpy.scalar")
        self.assertEqual(scalar_payload["dtype"], "float32")

    def test_torch_tensor_descriptor_and_serialization_when_available(self) -> None:
        if importlib.util.find_spec("torch") is None:
            self.skipTest("torch is not installed")

        tensor = hydrate_value(torch_tensor_descriptor([[1.0, 2.0]], dtype="float32"))
        payload = serialize_value(tensor)

        self.assertEqual(payload["kind"], "torch.Tensor")
        self.assertEqual(payload["shape"], [1, 2])
        self.assertEqual(payload["dtype"], "float32")
        self.assertEqual(payload["data"], [[1.0, 2.0]])

    def test_torch_tensor_descriptor_hydrates_and_serializes_with_fake_torch(self) -> None:
        class FakeTensor:
            def __init__(self, data, dtype=None):
                self._data = data
                self.dtype = f"torch.{dtype or 'float32'}"
                self.shape = self._shape(data)

            def detach(self):
                return self

            def cpu(self):
                return self

            def tolist(self):
                return self._data

            @classmethod
            def _shape(cls, data):
                if isinstance(data, list):
                    if data and isinstance(data[0], list):
                        return (len(data), len(data[0]))
                    return (len(data),)
                return ()

        fake_torch = types.SimpleNamespace(
            Tensor=FakeTensor,
            float32="float32",
            tensor=lambda data, dtype=None: FakeTensor(data, dtype=dtype),
        )

        with patch.dict(sys.modules, {"torch": fake_torch}):
            tensor = hydrate_value(torch_tensor_descriptor(0.25, dtype="float32"))
            payload = serialize_value(tensor)

        self.assertIsInstance(tensor, FakeTensor)
        self.assertEqual(payload["kind"], "torch.Tensor")
        self.assertEqual(payload["shape"], [])
        self.assertEqual(payload["dtype"], "float32")
        self.assertEqual(payload["data"], 0.25)

    def test_fixture_component_descriptor_preserves_typed_tensor_component(self) -> None:
        found, component, path = fixture_component_descriptor(
            torch_tensor_descriptor([0.1, 0.2, 0.3], dtype="float32"),
            1,
        )

        self.assertTrue(found)
        self.assertEqual(component, torch_tensor_descriptor(0.2, dtype="float32"))
        self.assertEqual(path, "data[1]")


class RichFixtureBatchTraceTest(unittest.TestCase):
    def test_pandas_fixture_builds_smokes_and_exports_trace_rollout(self) -> None:
        if importlib.util.find_spec("pandas") is None:
            self.skipTest("pandas is not installed")
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "pipe.py").write_text(
                """
import pandas as pd


def normalize(df=None):
    if df is None:
        df = pd.DataFrame({"value": [1.0]})
    out = df.copy()
    out["value"] = out["value"].astype(float)
    return out


def enrich(df=None):
    out = normalize(df)
    out["plus_one"] = out["value"] + 1.0
    return out


def summarize(df=None):
    out = enrich(df)
    return float(out["plus_one"].sum())


def qlib_style_pipeline(df: pd.DataFrame):
    normalized = normalize(df)
    enriched = enrich(normalized)
    total = summarize(enriched)
    return {"rows": len(enriched), "total": total}
""".lstrip(),
                encoding="utf-8",
            )
            manifest = generate_batch(
                [str(repo)],
                output_dir=Path(temp_dir) / "out",
                target_count=1,
                min_semantic_helpers=3,
                generated_at="2026-06-14T00:00:00Z",
            )

            self.assertEqual(manifest["summary"]["build_ok"], 1)
            env_record = manifest["envs"][0]
            self.assertEqual(env_record["semantic_helper_count"], 3)
            self.assertEqual(env_record["golden_status"], "real_value")
            self.assertEqual(env_record["determinism"], "deterministic")
            self.assertTrue(env_record["smoke_ok"])
            self.assertEqual(
                env_record["fixture_rich_params"],
                [{"kind": "pandas.DataFrame", "path": "fixture.args[0]"}],
            )

            env = Code2Env(Path(env_record["package_path"]) / "env_spec.json")
            result = run_rollout(
                env,
                ScriptedTraceSolveChat(env),
                primary_source="mock",
                max_rounds=8,
                trace_mode="subfunctions",
            )
            self.assertTrue(result["qualified"])
            self.assertTrue(result["final"]["correct"])
            self.assertTrue(result["subfunction_trace"]["helper_trace_complete"])
            written = write_conversation(result, Path(temp_dir) / "rollouts", validate=True)
            self.assertTrue(written.exists())
