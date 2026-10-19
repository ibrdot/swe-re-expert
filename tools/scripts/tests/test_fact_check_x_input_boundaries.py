"""Synthetic local boundary checks for the reviewed orchestrator; no provider calls."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / 'skills/fact-check-x-unified/scripts'
sys.path.insert(0, str(SCRIPTS))
import fact_check_x as pipeline
import trusted_search_config as credentials

class BoundaryTests(unittest.TestCase):
    def test_request_ids_cannot_escape_or_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            requests = Path(directory) / 'requests'
            for value in ('../outside', '/absolute', 'a/b', 'a\\b', '.', '', 'A'*65):
                comparison = {'schemaVersion':'fact-check-x/comparison@1','knowledgePoints':[{'id':value}]}
                with self.assertRaises(pipeline.PipelineError):
                    pipeline.build_requests(comparison, requests)
                self.assertFalse(requests.exists())
            with self.assertRaises(pipeline.PipelineError):
                pipeline.build_requests({'schemaVersion':'fact-check-x/comparison@1','knowledgePoints':[{'id':'K1'},{'id':'K1'}]}, requests)
            self.assertFalse(requests.exists())

    def test_credential_transport_rejects_plaintext_and_redirects(self):
        for address in ('http://external.example/search','https://user:password@example.com/search','https://example.com/#fragment','file:///tmp/key'):
            with patch.dict(os.environ, {'FACTCHECK_TRUSTED_SEARCH_URL':address}), patch.object(credentials,'open_trusted_search') as transport:
                with self.assertRaises(credentials.ConfigurationError):
                    credentials.validate_trusted_search_key('synthetic_fixture_1234567890')
                transport.assert_not_called()
        handler = credentials.RejectCredentialRedirects()
        with self.assertRaises(credentials.ServiceUnavailableError):
            handler.redirect_request(None,None,302,'redirect',{},'https://other.example/')

    def test_linked_credential_file_is_not_read(self):
        with tempfile.TemporaryDirectory() as directory:
            real = Path(directory)/'real'
            real.write_text('synthetic_fixture_1234567890')
            real.chmod(0o600)
            linked = Path(directory)/'link'
            linked.symlink_to(real)
            with patch.dict(os.environ, {'FACT_CHECK_X_TRUSTED_SEARCH_KEY_FILE':str(linked)}):
                with self.assertRaises(credentials.ConfigurationError):
                    credentials.load_trusted_search_key()

    def test_capture_changes_cannot_be_regated_after_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            results = base/'results.json'
            results.write_text(json.dumps({'schemaVersion':'1','platforms':[{'platform':'fixture','status':'success','answerMarkdown':'Initial captured answer'}]}))
            pipeline.validate_and_gate_capture(base, results)
            results.write_text(results.read_text().replace('Initial','Changed'))
            with self.assertRaises(pipeline.PipelineError):
                pipeline.require_capture_gate(base, results)

if __name__ == '__main__':
    unittest.main()
