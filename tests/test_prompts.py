from collections import Counter
import hashlib
import json
import os
import re
from string import Formatter
import unittest
from unittest.mock import patch

from prompts import LANGUAGES, prompt_directory, read_prompt


class PromptTests(unittest.TestCase):
    def test_catalog_hashes_and_rendering(self):
        manifest = json.loads((prompt_directory / 'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(len(manifest['zh-CN']), 23)
        self.assertEqual(set(manifest['zh-CN']), set(manifest['en-US']))
        for name in manifest['zh-CN']:
            fields = []
            for language in LANGUAGES:
                with self.subTest(name=name, language=language):
                    text = read_prompt(name, language)
                    self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), manifest[language][name])
                    self.assertNotIn('[[include:', text)
                    self.assertNotRegex(text, r'ZXQ\d{4}QXZ')
                    names = [field for _, field, _, _ in Formatter().parse(text) if field is not None]
                    fields.append(Counter(names))
                    text.format(**dict.fromkeys(names, 'example'))
                    self.assertEqual(text, read_prompt(f'{name}.{language}'))
            self.assertEqual(fields[0], fields[1], name)
            self.assertEqual(Counter(re.findall(r'\d+(?:\.\d+)?', read_prompt(name, 'zh-CN'))), Counter(re.findall(r'\d+(?:\.\d+)?', read_prompt(name, 'en-US'))), name)
            for tag in ('reply', 'thought', 'action', 'verify', 'objective'):
                pattern = rf'</?{tag}>'
                self.assertEqual(re.findall(pattern, read_prompt(name, 'zh-CN')), re.findall(pattern, read_prompt(name, 'en-US')), name)

    def test_default_and_environment(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(read_prompt('summary'), read_prompt('summary.en-US'))
        with patch.dict(os.environ, {'PROMPT_LANGUAGE': 'en-US'}):
            self.assertEqual(read_prompt('summary'), read_prompt('summary.en-US'))
            self.assertEqual(read_prompt('summary.zh-CN'), read_prompt('summary', 'zh-CN'))

    def test_invalid_selection(self):
        with self.assertRaises(FileNotFoundError):
            read_prompt('missing', 'zh-CN')
        with self.assertRaises(ValueError):
            read_prompt('summary', 'fr')
        with self.assertRaises(ValueError):
            read_prompt('summary.en-US', 'zh-CN')

    def test_existing_english_prompt_is_identical(self):
        self.assertEqual(read_prompt('entity_extraction_distill', 'zh-CN'), read_prompt('entity_extraction_distill', 'en-US'))
