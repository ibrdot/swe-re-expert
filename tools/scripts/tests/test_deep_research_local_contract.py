"""Actual recovered helper contracts on synthetic local data; no HTTP client/provider call."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('reviewed_deep_research', ROOT/'skills/deep-research/scripts/research.py')
research = importlib.util.module_from_spec(spec)
spec.loader.exec_module(research)

class ContractTests(unittest.TestCase):
    def test_current_and_legacy_report_shapes(self):
        current={'steps':[{'type':'model_output','content':[{'type':'thought','text':'not report'},{'type':'text','text':'Part 1'},{'type':'text','text':'Part 2'}]}]}
        self.assertEqual(research.extract_report_text(current),'Part 1\nPart 2')
        self.assertEqual(research.extract_report_text({'outputs':[{'text':'Legacy'}]}),'Legacy')
        self.assertEqual(research.extract_report_text({'steps':[]}),'')

    def test_ids_cannot_traverse_or_add_queries(self):
        self.assertEqual(research.checked_interaction_id('v1_fixture-123'),'v1_fixture-123')
        for value in ('../escape','a/b','a?key=secret','','A'*257,None):
            with self.assertRaises(research.DeepResearchError):research.checked_interaction_id(value)

    def test_history_private_atomic_and_queries_not_stored(self):
        with tempfile.TemporaryDirectory() as directory:
            history=research.HistoryManager(directory)
            history.add_interaction('fixture','private synthetic query')
            data=history.history_file.read_text()
            self.assertNotIn('private synthetic query',data)
            self.assertEqual(history.get_recent()[0]['id'],'fixture')
            self.assertFalse(list(Path(directory).glob('tmp*')))
            if os.name!='nt':self.assertEqual(history.history_file.stat().st_mode & 0o777,0o600)
            history.history_file.write_text('invalid JSON')
            with self.assertRaises(research.DeepResearchError):history.get_recent()

    def test_link_and_oversize_history_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            history=research.HistoryManager(directory)
            outside=Path(directory)/'fixture';outside.write_text('{"interactions":[]}');outside.chmod(0o600)
            history.history_file.symlink_to(outside)
            with self.assertRaises(research.DeepResearchError):history.get_recent()
            history.history_file.unlink()
            history.history_file.write_bytes(b'x'*(512*1024+1));history.history_file.chmod(0o600)
            with self.assertRaises(research.DeepResearchError):history.get_recent()

    def test_explicit_cache_and_positive_wait_limits(self):
        with patch.dict(os.environ, {'DEEP_RESEARCH_CACHE_DIR':''}):
            with self.assertRaises(research.DeepResearchError):research.HistoryManager()
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'DEEP_RESEARCH_CACHE_DIR':directory,'DEEP_RESEARCH_TIMEOUT':'0'}):
            with self.assertRaises(research.DeepResearchError):research.DeepResearchClient('synthetic-key')

if __name__=='__main__':unittest.main()
