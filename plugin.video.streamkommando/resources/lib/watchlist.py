# -*- coding: utf-8 -*-
"""Lokal gespeicherte Merkliste für Treffer aller Quellen."""

import json
import os
import time

import xbmcaddon
import xbmcvfs


class Watchlist(object):
    """JSON-Datei im Addon-Profil; Einträge werden über Quelle + ID dedupliziert."""

    def __init__(self, folder=None):
        self.addon = xbmcaddon.Addon()
        if folder is None:
            profile = xbmcvfs.translatePath(self.addon.getAddonInfo('profile'))
            folder = profile
        self.path = os.path.join(folder, 'watchlist.json')
        self._entries = self._load()

    @staticmethod
    def key(provider, identifier):
        return '%s:%s' % (provider or '', identifier or '')

    def _load(self):
        try:
            with open(self.path, encoding='utf-8') as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            return []
        if not isinstance(data, list):
            return []
        entries = []
        for entry in data:
            if not isinstance(entry, dict) or not entry.get('id'):
                continue
            entry.setdefault('provider', '')
            entry.setdefault('src', '')
            entry.setdefault('title', '')
            entry.setdefault('plot', '')
            entry.setdefault('thumb', '')
            entry.setdefault('year', 0)
            entry.setdefault('added', 0)
            entries.append(entry)
        return entries

    def _save(self):
        try:
            folder = os.path.dirname(self.path)
            if folder and not os.path.isdir(folder):
                os.makedirs(folder)
            with open(self.path, 'w', encoding='utf-8') as handle:
                json.dump(self._entries, handle, ensure_ascii=False, indent=2)
        except (OSError, TypeError):
            pass

    def entries(self):
        return sorted(self._entries, key=lambda row: row.get('added') or 0, reverse=True)

    def keys(self):
        return {self.key(row.get('provider'), row.get('id')) for row in self._entries}

    def contains(self, provider, identifier):
        return any(row.get('provider') == (provider or '') and row.get('id') == identifier
                   for row in self._entries)

    def toggle(self, entry):
        """Fügt hinzu oder entfernt. Rückgabe: True, wenn jetzt enthalten."""
        provider = entry.get('provider') or ''
        identifier = entry.get('id') or ''
        if not identifier:
            return False
        if self.contains(provider, identifier):
            self._entries = [row for row in self._entries
                             if not (row.get('provider') == provider and row.get('id') == identifier)]
            self._save()
            return False
        self._entries.append({
            'provider': provider,
            'id': identifier,
            'src': entry.get('src') or '',
            'title': entry.get('title') or identifier,
            'plot': entry.get('plot') or '',
            'thumb': entry.get('thumb') or '',
            'year': entry.get('year') or 0,
            'added': int(time.time()),
        })
        self._save()
        return True

    def remove(self, provider, identifier):
        before = len(self._entries)
        self._entries = [row for row in self._entries
                         if not (row.get('provider') == (provider or '') and row.get('id') == identifier)]
        if len(self._entries) != before:
            self._save()
            return True
        return False
