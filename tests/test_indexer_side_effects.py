from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from code2env.indexer import find_candidate, index_repo
from code2env.ingest import ingest_repo


SOURCE = """
import subprocess

import requests


def dict_lookup(payload):
    return payload.get("answer", 0)


def object_lookup(cache):
    return cache.get("answer")


def fetch_url(url):
    return requests.get(url).status_code


def post_session(session, url, payload):
    return session.post(url, json=payload).status_code


def read_file(path):
    return open(path).read()


def run_command(cmd):
    return subprocess.run(cmd).returncode
""".lstrip()


class IndexerSideEffectTest(unittest.TestCase):
    def test_generic_get_calls_do_not_mark_possible_side_effect(self) -> None:
        candidates = self._index_source()

        for symbol in ("side_effects:dict_lookup", "side_effects:object_lookup"):
            with self.subTest(symbol=symbol):
                candidate = find_candidate(candidates, symbol)
                self.assertNotIn("possible_side_effect", candidate.risk_flags)

    def test_qualified_http_filesystem_and_subprocess_calls_mark_side_effect(self) -> None:
        candidates = self._index_source()

        for symbol in (
            "side_effects:fetch_url",
            "side_effects:post_session",
            "side_effects:read_file",
            "side_effects:run_command",
        ):
            with self.subTest(symbol=symbol):
                candidate = find_candidate(candidates, symbol)
                self.assertIn("possible_side_effect", candidate.risk_flags)

    def _index_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "side_effects.py").write_text(SOURCE, encoding="utf-8")
            return index_repo(ingest_repo(str(repo)))


if __name__ == "__main__":
    unittest.main()
