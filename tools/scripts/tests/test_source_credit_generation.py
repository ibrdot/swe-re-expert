import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sync_source_credits import load_ledger, render_sections, update_readme
from check_readme_credits import extract_credit_repos
class SourceCreditTest(unittest.TestCase):
    def setUp(self):
        self.ledger={"schemaVersion":1,"sections":{"official":"- [Legacy](https://github.com/Owner/Legacy): Original detail.","community":"- [Old](https://github.com/Owner/Old): Original detail."}}
    def test_preserves_legacy_and_adds_reviewed_metadata(self):
        metadata={"source_repo":"New/Source","source_type":"official"}
        sections=render_sections(self.ledger,[("example",metadata),("second",metadata)])
        self.assertIn(self.ledger["sections"]["official"],sections["official"])
        self.assertEqual(sections["official"].count("https://github.com/new/source"),1)
        self.assertIn("`example`, `second`",sections["official"])
        self.assertEqual(render_sections(self.ledger,[("second",metadata),("example",metadata)]),sections)
    def test_self_not_credited_as_external(self):
        self.assertEqual(render_sections(self.ledger,[("self",{"source":"self","source_repo":"owner/self"})]),self.ledger["sections"])
    def test_invalid_metadata_fails_closed(self):
        for metadata in [{"source_repo":"javascript:evil"},{"source_repo":"owner/repo","source_type":"invalid"}]:
            with self.assertRaises(ValueError):render_sections(self.ledger,[("example",metadata)])
        with self.assertRaises(ValueError):render_sections(self.ledger,[("bad`",{"source_repo":"owner/repo"})])
        with self.assertRaises(ValueError):load_ledger('{"schemaVersion":2}')
    def test_idempotent_sections_only(self):
        text="Before\n### Official Sources\n\nold\n</details>\nMiddle\n### Community Contributors\n\nold\n</details>\nAfter"
        generated=update_readme(text,self.ledger["sections"])
        self.assertEqual(update_readme(generated,self.ledger["sections"]),generated)
        self.assertTrue(generated.startswith("Before\n"));self.assertTrue(generated.endswith("After"));self.assertIn("Middle",generated)
        with self.assertRaises(ValueError):update_readme("no heading",self.ledger["sections"])
    def test_migration_preserves_baseline_attributions(self):
        root=Path(__file__).resolve().parents[3]
        ledger=load_ledger((root/"data/source-credits.json").read_text())
        for bucket,section in ledger["sections"].items():self.assertGreater(len(section),1000)
        text="\n".join("### "+("Official Sources" if k=="official" else "Community Contributors")+"\n"+v for k,v in ledger["sections"].items())
        sets=extract_credit_repos(text)
        self.assertGreater(len(sets["official"]),50);self.assertGreater(len(sets["community"]),150)
if __name__=="__main__":unittest.main()
