import importlib.util,json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('audit',ROOT/'scripts/swe_audit.py');audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
class ScriptTests(unittest.TestCase):
 def test_external_root_all(self):
  with tempfile.TemporaryDirectory() as t:
   out=Path(t)/'result.json'
   subprocess.run([sys.executable,str(ROOT/'scripts/swe_audit.py'),'--root',str(ROOT/'examples/demo-project'),'--all','--out',str(out)],cwd=t,check=True,capture_output=True)
   data=json.loads(out.read_text());self.assertEqual(data['total_files'],1);self.assertTrue(data['complexity_hotspots']);self.assertIn('summary',data)
 def test_reference_counts(self):
  root=ROOT/'examples/demo-project';inv=audit.inventory(root);rows=audit.find_dead_code(inv['files_by_lang'],root)
  self.assertNotIn('called_helper',[r['symbol'] for r in rows]);self.assertIn('unused_candidate',[r['symbol'] for r in rows]);self.assertTrue(all(r['occurrences']>=1 for r in rows))
 def test_excluded_folders(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);(root/'vendor').mkdir();(root/'vendor/no.py').write_text('x=1');(root/'yes.py').write_text('x=1')
   self.assertEqual(audit.inventory(root)['total_files'],1)
 def test_missing_root(self):
  r=subprocess.run([sys.executable,str(ROOT/'scripts/swe_audit.py'),'--root','/nonexistent-repo-fixture'],capture_output=True,text=True);self.assertNotEqual(r.returncode,0);self.assertIn('error',json.loads(r.stdout))
 def test_documentation_links(self):
  import re
  for name in ['README.md','CONTRIBUTING.md','SECURITY.md','docs/GETTING_STARTED.md','docs/CAPABILITIES.md','docs/LAUNCH_KIT.md']:
   p=ROOT/name
   for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
    if link.startswith(('http:','https:','mailto:','#')):continue
    self.assertTrue((p.parent/link.split('#')[0]).exists(),f'{name}: {link}')
if __name__=='__main__':unittest.main()
