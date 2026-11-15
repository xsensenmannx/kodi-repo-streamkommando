# -*- coding: utf-8 -*-
"""Kleiner JSON-Cache im Addon-Profil."""

import hashlib
import json
import os
import time

import xbmcaddon
import xbmcvfs

TTL_HOURS = 6


class Cache(object):
    def __init__(self, folder='cache'):
        self.addon = xbmcaddon.Addon()
        profile = xbmcvfs.translatePath(self.addon.getAddonInfo('profile'))
        self.path = os.path.join(profile, folder)
        try:
            if not os.path.isdir(self.path):
                os.makedirs(self.path)
        except OSError:
            pass

    def _file(self, key):
        return os.path.join(self.path, hashlib.sha1(key.encode('utf-8')).hexdigest() + '.json')

    def get(self, key):
        path = self._file(key)
        try:
            if os.path.getmtime(path) + TTL_HOURS * 3600 < time.time():
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
        try:
            for name in os.listdir(self.path):
                if name.endswith('.json'):
                    os.remove(os.path.join(self.path, name))
        except OSError:
            pass
