# -*- coding: utf-8 -*-
"""Tests für den Bibliotheksexport (ohne Kodi-Installation lauffähig)."""

import json
import os
import shutil
import sys
import tempfile
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON_DIR = os.path.join(ROOT, 'plugin.video.streamkommando')
PROFILE = tempfile.mkdtemp(prefix='sk-test-profile-')

# Minimale Kodi-Stubs, damit resources.lib.library importierbar ist.
xbmc = types.ModuleType('xbmc')
xbmc.LOGDEBUG = 0
xbmc.LOGINFO = 1
xbmc.LOGWARNING = 2
xbmc.LOGERROR = 3
xbmc.log = lambda *args, **kwargs: None
xbmc.sleep = lambda ms: None
xbmc.executebuiltin = lambda command: None


class _Player(object):
    def isPlaying(self):
        return False

    def getTime(self):
        return 0

    def getTotalTime(self):
        return 0


xbmc.Player = _Player
sys.modules['xbmc'] = xbmc

xbmcaddon = types.ModuleType('xbmcaddon')


class _Addon(object):
    SETTINGS = {}

    def getAddonInfo(self, key):
        return {
            'id': 'plugin.video.streamkommando',
            'name': 'Stream Kommando',
            'path': ADDON_DIR,
            'profile': PROFILE,
            'version': '1.10.1',
        }.get(key, '')

    def getSetting(self, key):
        return self.SETTINGS.get(key, '')

    def getLocalizedString(self, string_id):
        return 'str%d' % string_id


xbmcaddon.Addon = _Addon
sys.modules['xbmcaddon'] = xbmcaddon

xbmcgui = types.ModuleType('xbmcgui')
xbmcgui.NOTIFICATION_INFO = 'info'
xbmcgui.NOTIFICATION_ERROR = 'error'


class _Dialog(object):
    def notification(self, *args, **kwargs):
        pass


class _DialogProgress(object):
    def create(self, *args, **kwargs):
        pass

    def update(self, *args, **kwargs):
        pass

    def iscanceled(self):
        return False

    def close(self):
        pass


xbmcgui.Dialog = _Dialog
xbmcgui.DialogProgress = _DialogProgress
sys.modules['xbmcgui'] = xbmcgui

xbmcvfs = types.ModuleType('xbmcvfs')
xbmcvfs.translatePath = lambda path: path
xbmcvfs.exists = os.path.exists
xbmcvfs.mkdirs = lambda path: os.makedirs(path, exist_ok=True) or True
xbmcvfs.delete = lambda path: os.remove(path) or True
xbmcvfs.listdir = lambda path: ([], sorted(os.listdir(path)) if os.path.isdir(path) else [])
sys.modules['xbmcvfs'] = xbmcvfs

sys.path.insert(0, ADDON_DIR)
from resources.lib.library import export_entries  # noqa: E402


class LibraryExportTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='sk-test-export-')
        self.video = os.path.join(self.root, 'Quelle', 'Film.mp4')
        os.makedirs(os.path.dirname(self.video))
        with open(self.video, 'wb') as handle:
            handle.write(b'video')
        self.download = {
            'path': self.video,
            'title': 'Film',
            'year': 2020,
            'plot': 'Plot',
            'duration': 120,
        }
        self.second_video = os.path.join(self.root, 'Quelle', 'Zweiter.mp4')
        with open(self.second_video, 'wb') as handle:
            handle.write(b'video2')
        self.second_download = {
            'path': self.second_video,
            'title': 'Zweiter',
            'year': 2021,
            'plot': 'Plot 2',
            'duration': 90,
        }

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_downloads_folder_created_when_watchlist_exists(self):
        library = os.path.join(self.root, 'Bibliothek')
        os.makedirs(os.path.join(library, 'Merkliste'))

        count = export_entries(library, [], [self.download])

        downloads = os.path.join(library, 'Downloads')
        self.assertEqual(count, 1)
        self.assertTrue(os.path.isdir(downloads))
        self.assertTrue(os.path.isfile(os.path.join(downloads, 'Film (2020).strm')))
        self.assertTrue(os.path.isfile(os.path.join(downloads, 'Film (2020).nfo')))

    def test_watchlist_folder_created_when_downloads_exists(self):
        library = os.path.join(self.root, 'Bibliothek')
        os.makedirs(os.path.join(library, 'Downloads'))

        count = export_entries(library, [], [])

        self.assertEqual(count, 0)
        self.assertTrue(os.path.isdir(os.path.join(library, 'Merkliste')))

    def test_export_is_idempotent(self):
        library = os.path.join(self.root, 'Bibliothek')
        os.makedirs(os.path.join(library, 'Merkliste'))
        os.makedirs(os.path.join(library, 'Downloads'))

        self.assertEqual(export_entries(library, [], [self.download]), 1)
        self.assertEqual(export_entries(library, [], [self.download]), 1)

        files = sorted(os.listdir(os.path.join(library, 'Downloads')))
        self.assertEqual(files, ['Film (2020).nfo', 'Film (2020).strm'])


    def test_stale_exports_removed_on_next_export(self):
        library = os.path.join(self.root, 'Bibliothek')
        self.assertEqual(export_entries(library, [], [self.download, self.second_download]), 2)

        downloads = os.path.join(library, 'Downloads')
        self.assertTrue(os.path.isfile(os.path.join(downloads, 'Zweiter (2021).strm')))

        self.assertEqual(export_entries(library, [], [self.download]), 1)

        self.assertTrue(os.path.isfile(os.path.join(downloads, 'Film (2020).strm')))
        self.assertTrue(os.path.isfile(os.path.join(downloads, 'Film (2020).nfo')))
        self.assertFalse(os.path.exists(os.path.join(downloads, 'Zweiter (2021).strm')))
        self.assertFalse(os.path.exists(os.path.join(downloads, 'Zweiter (2021).nfo')))
        with open(os.path.join(library, 'streamkommando-export.json'), encoding='utf-8') as handle:
            manifest = json.load(handle)
        self.assertEqual(sorted(manifest['files']),
                         ['Downloads/Film (2020).nfo', 'Downloads/Film (2020).strm'])

    def test_empty_export_removes_all_previous_exports(self):
        library = os.path.join(self.root, 'Bibliothek')
        export_entries(library, [], [self.download])

        self.assertEqual(export_entries(library, [], []), 0)

        downloads = os.path.join(library, 'Downloads')
        self.assertEqual(os.listdir(downloads), [])

    def test_cleanup_leaves_files_without_manifest(self):
        library = os.path.join(self.root, 'Bibliothek')
        downloads = os.path.join(library, 'Downloads')
        os.makedirs(downloads)
        manual = os.path.join(downloads, 'Manuell.strm')
        with open(manual, 'w', encoding='utf-8') as handle:
            handle.write('plugin://manuell\n')

        export_entries(library, [], [])

        self.assertTrue(os.path.isfile(manual))

    def test_manifest_with_outside_paths_is_ignored(self):
        library = os.path.join(self.root, 'Bibliothek')
        os.makedirs(os.path.join(library, 'Merkliste'))
        outside = os.path.join(self.root, 'aussen.strm')
        with open(outside, 'w', encoding='utf-8') as handle:
            handle.write('plugin://aussen\n')
        with open(os.path.join(library, 'streamkommando-export.json'), 'w', encoding='utf-8') as handle:
            json.dump({'version': 1, 'files': [
                '../aussen.strm', outside, 'Merkliste/../../aussen.strm', 'Merkliste/ok.txt',
            ]}, handle)

        export_entries(library, [], [])

        self.assertTrue(os.path.isfile(outside))

    def test_corrupt_manifest_is_ignored(self):
        library = os.path.join(self.root, 'Bibliothek')
        downloads = os.path.join(library, 'Downloads')
        os.makedirs(downloads)
        keep = os.path.join(downloads, 'Bleibt.strm')
        with open(keep, 'w', encoding='utf-8') as handle:
            handle.write('plugin://bleibt\n')
        with open(os.path.join(library, 'streamkommando-export.json'), 'w', encoding='utf-8') as handle:
            handle.write('{kaputt')

        export_entries(library, [], [])

        self.assertTrue(os.path.isfile(keep))


if __name__ == '__main__':
    unittest.main()
