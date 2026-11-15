# -*- coding: utf-8 -*-
"""Kleiner JSON-Cache im Addon-Profil."""

import hashlib
import json
import os
import time

import xbmcaddon
import xbmcvfs

DEFAULT_HOURS = 12


class Cache(object):
    def __init__(self, folder='cache'):
        self.addon = xbmcaddon.Addon()
        profile = xbmcvfs.translatePath(self.addon.getAddonInfo('profile'))
        self.path = os.path.join(profile, folder)
        self._ensure_path()
        self.ttl = self._ttl()

    def _ensure_path(self):
        try:
            if not os.path.isdir(self.path):
                os.makedirs(self.path)
        except OSError:
            pass

    def _ttl(self):
        try:
            hours = int(self.addon.getSetting('cache_hours') or DEFAULT_HOURS)
        except (TypeError, ValueError):
            hours = DEFAULT_HOURS
        return max(1, min(168, hours)) * 3600

    def _file(self, key):
        name = hashlib.sha1(key.encode('utf-8')).hexdigest()
        return os.path.join(self.path, name + '.json')

    def get(self, key):
        path = self._file(key)
        try:
            if os.path.getmtime(path) + self.ttl < time.time():
                return None
            with open(path, encoding='utf-8') as handle:
                return json.load(handle)
        except (OSError, ValueError):
            return None

    def set(self, key, value):
        try:
            with open(self._file(key), 'w', encoding='utf-8') as handle:
                json.dump(value, handle)
        except (OSError, ValueError, TypeError):
            pass

    def clear(self):
        removed = 0
        try:
            for name in os.listdir(self.path):
                if not name.endswith('.json'):
                    continue
                try:
                    os.remove(os.path.join(self.path, name))
                    removed += 1
                except OSError:
                    pass
        except OSError:
            pass
        return removed
