from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from code2env.indexer import build_test_link_index, index_repo, test_links_for_candidate
from code2env.ingest import ingest_repo
from code2env.spec import draft_env_spec


SOURCE = """
def add(a, b):
    return a + b


def normalize_values(values):
    \"\"\"Scale and sort a list of numbers.\"\"\"
    scaled = [value * 2 for value in values]
    return sorted(scaled)
""".lstrip()

TEST_SOURCE = """
import json

import pytest

from maths import add, normalize_values


@pytest.fixture
def sample_values():
    return [3, 1, 2]


def test_normalize_values(sample_values):
    expected = json.load(open("golden/normalize.json"))
    assert normalize_values(sample_values) == expected


def test_add():
    assert add(1, 2) == 3
""".lstrip()


class TestLinkIndexTest(unittest.TestCase):
    def _make_repo_with_tests(self, root: Path) -> Path:
        root.mkdir(parents=True)
        (root / "maths.py").write_text(SOURCE, encoding="utf-8")
        tests_dir = root / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_maths.py").write_text(TEST_SOURCE, encoding="utf-8")
        return root

    def test_ingest_separates_tests_without_polluting_python_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._make_repo_with_tests(Path(temp_dir) / "repo")
            snapshot = ingest_repo(str(repo))

            self.assertIn("maths.py", snapshot.python_files)
            # The test module must not leak into the ranked source corpus.
            self.assertNotIn("tests/test_maths.py", snapshot.python_files)
            self.assertIn("tests/test_maths.py", snapshot.test_files)

            # Candidates are still drawn from source only (no test functions).
            symbols = {candidate.symbol for candidate in index_repo(snapshot)}
            self.assertIn("maths:normalize_values", symbols)
            self.assertNotIn("test_maths:test_normalize_values", symbols)

    def test_test_link_index_associates_test_fixture_and_golden(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._make_repo_with_tests(Path(temp_dir) / "repo")
            snapshot = ingest_repo(str(repo))
            candidates = index_repo(snapshot)
            index = build_test_link_index(snapshot, candidates)

            links = index["maths:normalize_values"]
            kinds = {link.target_kind for link in links}
            self.assertIn("test", kinds)
            self.assertIn("fixture", kinds)
            self.assertIn("golden", kinds)

            test_link = next(link for link in links if link.target_kind == "test")
            self.assertEqual(test_link.target, "tests/test_maths.py::test_normalize_values")
            self.assertIn("name_match", test_link.evidence)
            self.assertIn("import_ref", test_link.evidence)
            self.assertGreater(test_link.confidence, 0.5)

            fixture_link = next(link for link in links if link.target_kind == "fixture")
            self.assertTrue(fixture_link.target.endswith("::sample_values"))

            golden_link = next(link for link in links if link.target_kind == "golden")
            self.assertEqual(golden_link.target, "golden/normalize.json")

    def test_unrelated_candidate_is_not_linked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._make_repo_with_tests(Path(temp_dir) / "repo")
            snapshot = ingest_repo(str(repo))
            candidate = next(
                c for c in index_repo(snapshot) if c.symbol == "maths:add"
            )
            links = test_links_for_candidate(snapshot, candidate)
            # `add` is referenced only by test_add, which must link by name.
            self.assertTrue(any(link.target.endswith("::test_add") for link in links))
            self.assertFalse(
                any(link.target.endswith("::test_normalize_values") for link in links)
            )

    def test_draft_provenance_has_two_diverse_sources_with_tests(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._make_repo_with_tests(Path(temp_dir) / "repo")
            snapshot = ingest_repo(str(repo))
            spec = draft_env_spec(
                snapshot,
                symbol="maths:normalize_values",
                fixture={"args": [[3, 1, 2]], "kwargs": {}},
                compute_golden=False,
            )
            sources = spec.provenance["task_sources"]
            kinds = [source["kind"] for source in sources]
            self.assertGreaterEqual(len(sources), 2)
            self.assertIn("source_span", kinds)
            self.assertIn("test_link", kinds)
            self.assertEqual(spec.provenance["test_link_status"], "linked")
            self.assertNotIn("degradation", spec.provenance)

    def test_draft_provenance_degrades_without_tests(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "maths.py").write_text(SOURCE, encoding="utf-8")
            snapshot = ingest_repo(str(repo))
            self.assertEqual(snapshot.test_files, [])

            spec = draft_env_spec(
                snapshot,
                symbol="maths:normalize_values",
                fixture={"args": [[3, 1, 2]], "kwargs": {}},
                compute_golden=False,
            )
            kinds = [source["kind"] for source in spec.provenance["task_sources"]]
            # Still >=2 sources, but no test artifacts and an explicit degradation note.
            self.assertGreaterEqual(len(spec.provenance["task_sources"]), 2)
            self.assertNotIn("test_link", kinds)
            self.assertEqual(spec.provenance["test_link_status"], "no_test_links_found")
            self.assertIn("degradation", spec.provenance)


if __name__ == "__main__":
    unittest.main()
