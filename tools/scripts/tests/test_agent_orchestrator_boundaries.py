"""Local advisory orchestration must not disguise failure as a clean inventory."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]


def module(name, storage):
    source = ROOT / 'skills/agent-orchestrator/scripts' / (name + '.py')
    spec = importlib.util.spec_from_file_location('review_' + name, source)
    loaded = importlib.util.module_from_spec(spec)
    with patch.dict(os.environ, {'AGENT_ORCHESTRATOR_DATA_DIR': str(Path(storage).resolve())}):
        spec.loader.exec_module(loaded)
    return loaded


class AdvisoryBoundaries(unittest.TestCase):
    def test_missing_and_malformed_registry_are_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            matcher = module('match_skills', directory)
            with self.assertRaises(ValueError):
                matcher.load_registry()
            matcher.REGISTRY_PATH.write_text('{', encoding='utf-8')
            with self.assertRaises(json.JSONDecodeError):
                matcher.load_registry()

    def test_ambiguous_name_is_not_silently_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            planner = module('orchestrate', directory)
            planner.REGISTRY_PATH.write_text(json.dumps({'skills': [
                {'name': 'same', 'skill_md': '/first/SKILL.md'},
                {'name': 'same', 'skill_md': '/second/SKILL.md'},
            ]}), encoding='utf-8')
            with self.assertRaises(ValueError):
                planner.load_registry()

    def test_zero_scores_do_not_choose_arbitrary_primary(self):
        with tempfile.TemporaryDirectory() as directory:
            planner = module('orchestrate', directory)
            self.assertEqual(planner.classify_pattern([{'name': 'a'}, {'name': 'b'}], 'q'), 'parallel')
            for invalid in [-1, float('nan'), float('inf'), True, '10']:
                with self.assertRaises(ValueError):
                    planner.classify_pattern([{'score': invalid}, {'score': 1}], 'q')
            result = planner.generate_plan([{'name': 'low', 'score': 1}, {'name': 'high', 'score': 8}], 'q', 'primary_support')
            self.assertEqual(result['steps'][0]['skill'], 'high')
            with self.assertRaises(ValueError):
                planner.generate_plan([], 'q', 'single')

    def test_cache_rejects_corruption_and_preserves_link_target(self):
        with tempfile.TemporaryDirectory() as directory:
            scanner = module('scan_registry', directory)
            scanner.REGISTRY_PATH.write_text('[]', encoding='utf-8')
            with self.assertRaises(ValueError):
                scanner.load_registry()
            scanner.REGISTRY_PATH.unlink()
            target = Path(directory) / 'outside.json'
            target.write_text('original', encoding='utf-8')
            scanner.REGISTRY_PATH.symlink_to(target)
            with self.assertRaises(ValueError):
                scanner.save_registry({'skills': []})
            self.assertEqual(target.read_text(), 'original')
            scanner.REGISTRY_PATH.unlink()
            scanner.save_registry({'skills': []})
            self.assertEqual(scanner.load_registry()['skills'], [])
            self.assertEqual(list(Path(directory).glob('.registry-*')), [])

    def test_malformed_metadata_and_projects_do_not_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            scanner = module('scan_registry', directory)
            entry = Path(directory) / 'SKILL.md'
            entry.write_text('---\n- list\n---\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                scanner.parse_yaml_frontmatter(entry)
            matcher = module('match_skills', directory)
            matcher.PROJECTS_PATH.write_text('{', encoding='utf-8')
            with self.assertRaises(json.JSONDecodeError):
                matcher.load_projects()
            for candidate in [{'name': []}, {'description': {}}, {'triggers': 'text'}]:
                with self.assertRaises(ValueError):
                    matcher.score_skill(candidate, 'query')
            planner = module('orchestrate', directory)
            for candidates in [[], [{'name': ''}], [{'name': 'ok', 'capabilities': 'not-list'}]]:
                with self.assertRaises(ValueError):
                    planner.validate_skills(candidates)

    def test_empty_name_does_not_match_every_query(self):
        with tempfile.TemporaryDirectory() as directory:
            matcher = module('match_skills', directory)
            self.assertEqual(matcher.score_skill({'name': '', 'description': '', 'triggers': [], 'capabilities': []}, 'ordinary query')['score'], 0)


if __name__ == '__main__':
    unittest.main()
