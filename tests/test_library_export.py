# -*- coding: utf-8 -*-
"""Tests für den Bibliotheksexport (ohne Kodi-Installation lauffähig)."""

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


if __name__ == '__main__':
    unittest.main()
