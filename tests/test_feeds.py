# -*- coding: utf-8 -*-
"""Tests für die eigenen Sammlungen (Parsing und Einstellungen)."""

import os
import sys
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON_DIR = os.path.join(ROOT, 'plugin.video.streamkommando')

xbmcaddon = types.ModuleType('xbmcaddon')


class _Addon(object):
    SETTINGS = {'custom_ia_collections': '', 'custom_commons_categories': ''}

    def getSetting(self, key):
        return self.SETTINGS.get(key, '')

    def getAddonInfo(self, key):
        return {'id': 'plugin.video.streamkommando', 'name': 'Stream Kommando',
                'profile': os.path.join(ROOT, '.test-profile'), 'path': ADDON_DIR}.get(key, '')


xbmcaddon.Addon = _Addon
sys.modules['xbmcaddon'] = xbmcaddon

sys.path.insert(0, ADDON_DIR)
from resources.lib.feeds import (  # noqa: E402
    Feeds,
    normalize_commons,
    normalize_ia,
    parse_commons,
    parse_ia,
)


class FeedParsingTest(unittest.TestCase):
    def tearDown(self):
        _Addon.SETTINGS = {'custom_ia_collections': '', 'custom_commons_categories': ''}

    def test_ia_prefix_and_valid_id(self):
        self.assertEqual(normalize_ia('collection:feature_films'), 'feature_films')
        self.assertEqual(normalize_ia('prelinger'), 'prelinger')

    def test_ia_rejects_paths_and_spaces(self):
        self.assertEqual(normalize_ia('../etc'), '')
        self.assertEqual(normalize_ia('feature films'), '')
        self.assertEqual(normalize_ia(''), '')

    def test_commons_prefix_underscores_and_spaces(self):
        self.assertEqual(normalize_commons('Category:Videos_by_NASA'), 'Videos by NASA')
        self.assertEqual(normalize_commons('Category:Big Buck Bunny'), 'Big Buck Bunny')
        self.assertEqual(normalize_commons('Category:  Videos  by  NASA  '), 'Videos by NASA')

    def test_commons_rejects_unsafe_names(self):
        self.assertEqual(normalize_commons('<script>alert(1)</script>'), '')
        self.assertEqual(normalize_commons('Category:'), '')

    def test_parse_ia_splits_and_deduplicates(self):
        value = 'feature_films, classic_tv; collection:prelinger\nfeature_films'
        self.assertEqual(parse_ia(value), ['feature_films', 'classic_tv', 'prelinger'])

    def test_parse_commons_splits_and_deduplicates(self):
        value = 'Category:Videos by NASA, Category:Big_Buck_Bunny; videos by nasa'
        self.assertEqual(parse_commons(value), ['Videos by NASA', 'Big Buck Bunny'])

    def test_feeds_entries_and_emptiness(self):
        _Addon.SETTINGS = {
            'custom_ia_collections': 'feature_films,prelinger',
            'custom_commons_categories': 'Category:Videos by NASA',
        }
        feeds = Feeds()
        self.assertEqual(len(feeds), 3)
        self.assertEqual([entry['label'] for entry in feeds.entries()], [
            'Internet Archive: feature_films',
            'Internet Archive: prelinger',
            'Commons: Videos by NASA',
        ])
        self.assertEqual([entry['kind'] for entry in feeds.entries()], ['ia', 'ia', 'commons'])

    def test_empty_settings(self):
        feeds = Feeds()
        self.assertEqual(len(feeds), 0)
        self.assertEqual(feeds.entries(), [])


if __name__ == '__main__':
    unittest.main()
