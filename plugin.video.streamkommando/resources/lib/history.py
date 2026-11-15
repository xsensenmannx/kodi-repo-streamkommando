# -*- coding: utf-8 -*-
"""Lokaler Verlauf mit Wiedergabeposition für Treffer aller Quellen."""

import json
import os
import time

import xbmcaddon
import xbmcvfs

MAX_ENTRIES = 100


def format_position(seconds):
    """Sekunden als m:ss bzw. h:mm:ss."""
    try:
        total = int(seconds or 0)
    except (TypeError, ValueError):
        return '0:00'
    if total < 0:
        total = 0
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return '%d:%02d:%02d' % (hours, minutes, secs)
    return '%d:%02d' % (minutes, secs)


class History(object):
    """JSON-Datei im Addon-Profil; ein Eintrag je Quelle + ID."""

    def __init__(self, folder=None):
        self.addon = xbmcaddon.Addon()
        if folder is None:
            folder = xbmcvfs.translatePath(self.addon.getAddonInfo('profile'))
        self.path = os.path.join(folder, 'history.json')
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
            entry.setdefault('position', 0)
            entry.setdefault('total', 0)
            entry.setdefault('updated', 0)
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
        return sorted(self._entries, key=lambda row: row.get('updated') or 0, reverse=True)

    def get(self, provider, identifier):
        for row in self._entries:
            if row.get('provider') == (provider or '') and row.get('id') == identifier:
                return dict(row)
        return {}

    def position(self, provider, identifier):
        try:
            return int(self.get(provider, identifier).get('position') or 0)
        except (TypeError, ValueError):
            return 0

    def touch(self, entry):
        """Legt einen Eintrag an oder aktualisiert seine Metadaten."""
        provider = entry.get('provider') or ''
        identifier = entry.get('id') or ''
        if not identifier:
            return
        existing = None
        for row in self._entries:
            if row.get('provider') == provider and row.get('id') == identifier:
                existing = row
                break
        if existing is None:
            existing = {
                'provider': provider,
                'id': identifier,
                'position': 0,
                'total': 0,
            }
            self._entries.append(existing)
        for field in ('src', 'title', 'plot', 'thumb'):
            if entry.get(field):
                existing[field] = entry[field]
        if entry.get('year'):
            existing['year'] = entry['year']
        existing['updated'] = time.time()
        if len(self._entries) > MAX_ENTRIES:
            self._entries = self.entries()[:MAX_ENTRIES]
        self._save()

    def update_position(self, provider, identifier, position, total=0):
        entry = self.get(provider, identifier)
        if not entry:
            return
        try:
            position = int(position or 0)
        except (TypeError, ValueError):
            position = 0
        try:
            total = int(total or 0)
        except (TypeError, ValueError):
            total = 0
        for row in self._entries:
            if row.get('provider') == (provider or '') and row.get('id') == identifier:
                row['position'] = max(0, position)
                row['total'] = max(0, total)
                row['updated'] = time.time()
                break
        self._save()

    def reset_position(self, provider, identifier):
        self.update_position(provider, identifier, 0, self.get(provider, identifier).get('total') or 0)

    def remove(self, provider, identifier):
        before = len(self._entries)
        self._entries = [row for row in self._entries
                         if not (row.get('provider') == (provider or '') and row.get('id') == identifier)]
        if len(self._entries) != before:
            self._save()
            return True
        return False

    def clear(self):
        self._entries = []
        self._save()
