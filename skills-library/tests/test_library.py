import hashlib,json,sys,unittest,subprocess,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from build_skills_index import frontmatter
class LibraryTests(unittest.TestCase):
 def test_frontmatter_scalars(self):
  meta=frontmatter('---\nname: "example"\ndescription: >\n  Multiple lines\n  stay readable.\nlicense: MIT\ncategory: Research\n---\n# Guide')
  self.assertEqual(meta['name'],'example');self.assertEqual(meta['description'],'Multiple lines stay readable.');self.assertEqual(meta['category'],'Research')
 def test_missing_frontmatter(self): self.assertEqual(frontmatter('# plain guide'),{})
 def test_api_matches_catalogue(self):
  data=json.loads((ROOT/'docs/data/skills.json').read_text());api=json.loads((ROOT/'docs/api/v1/skills.json').read_text())
  self.assertEqual(data['counts'],api['counts']);self.assertEqual(len(data['skills']),len(api['skills']))
  keys=set()
  for source,row in zip(data['skills'],api['skills']):
   self.assertTrue(all(row[k]==v for k,v in source.items()));self.assertNotIn(row['key'],keys);keys.add(row['key'])
   detail=json.loads((ROOT/f"docs/api/v1/skills/{row['key']}.json").read_text());self.assertEqual(row,detail)
   self.assertEqual(row['content_sha256'],hashlib.sha256((ROOT/row['skill_file']).read_bytes()).hexdigest())
  actual={x.stem for x in (ROOT/'docs/api/v1/skills').glob('*.json')};self.assertEqual(actual,keys)
 def test_revision(self):
  api=json.loads((ROOT/'docs/api/v1/skills.json').read_text())
  digest=hashlib.sha256(json.dumps(api['skills'],sort_keys=True).encode()).hexdigest();self.assertEqual(api['revision'],digest)
  stats=json.loads((ROOT/'docs/api/v1/stats.json').read_text());self.assertEqual(stats['revision'],digest)
 def test_auto_add_remove(self):
  # Isolated miniature checkout verifies a new guide and deletion need no hand edits.
  with tempfile.TemporaryDirectory() as folder:
   tmp=Path(folder);shutil.copytree(ROOT/'tools',tmp/'tools');(tmp/'docs').mkdir()
   (tmp/'demo').mkdir();(tmp/'demo/SKILL.md').write_text('---\nname: new-guide\ndescription: Useful demo\ncategory: Research\n---\nBody')
   for script in ['build_skills_index.py','build_skill_docs.py','build_api.py']:subprocess.run([sys.executable,str(tmp/'tools'/script)],check=True,capture_output=True)
   api=json.loads((tmp/'docs/api/v1/skills.json').read_text());self.assertEqual(api['counts']['total'],1)
   detail=tmp/f"docs/api/v1/skills/{api['skills'][0]['key']}.json";self.assertTrue(detail.exists());self.assertIn('demo/SKILL.md',(tmp/'SKILLS.md').read_text())
   shutil.rmtree(tmp/'demo')
   for script in ['build_skills_index.py','build_skill_docs.py','build_api.py']:subprocess.run([sys.executable,str(tmp/'tools'/script)],check=True,capture_output=True)
   self.assertFalse(detail.exists());self.assertEqual(json.loads((tmp/'docs/api/v1/skills.json').read_text())['counts']['total'],0)
if __name__=='__main__':unittest.main()
