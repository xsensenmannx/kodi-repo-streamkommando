# -*- coding: utf-8 -*-
"""Merkliste und Downloads als .strm + .nfo für die Kodi-Filmbibliothek."""

import json
import os
import urllib.parse
from xml.sax.saxutils import escape

import xbmcaddon
import xbmcvfs

from .downloads import Downloads, safe_name

PLUGIN_BASE = 'plugin://plugin.video.streamkommando/'
FOLDERS = ('Merkliste', 'Downloads')
MANIFEST = 'streamkommando-export.json'


def plugin_url(entry):
    """Wiedergabe-URL für einen Merklisten-Eintrag."""
    params = [('mode', 'watchlistplay'), ('provider', entry.get('provider') or 'archive')]
    for key in ('id', 'src', 'title', 'year'):
        value = entry.get(key)
        if value:
            params.append((key, value))
    return PLUGIN_BASE + '?' + urllib.parse.urlencode(params)


def nfo_text(entry):
    """Kodi-Movie-NFO mit den Metadaten des Eintrags."""
    title = entry.get('title') or entry.get('label') or entry.get('id') or 'Film'
    lines = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<movie>',
        '  <title>%s</title>' % escape(str(title)),
    ]
    try:
        year = int(entry.get('year') or 0)
    except (TypeError, ValueError):
        year = 0
    if year:
        lines.append('  <year>%d</year>' % year)
    plot = entry.get('plot')
    if plot:
        lines.append('  <plot>%s</plot>' % escape(str(plot)))
    try:
        duration = int(entry.get('duration') or 0)
    except (TypeError, ValueError):
        duration = 0
    if duration > 0:
        lines.append('  <runtime>%d</runtime>' % max(1, duration // 60))
    thumb = entry.get('thumb')
    if thumb and str(thumb).startswith('https://'):
        lines.append('  <thumb>%s</thumb>' % escape(str(thumb)))
    unique = entry.get('uniqueid')
    if unique:
        lines.append('  <uniqueid type="streamkommando" default="true">%s</uniqueid>' % escape(str(unique)))
    lines.append('</movie>')
    return '\n'.join(lines) + '\n'


def _stem(entry):
    title = entry.get('title') or entry.get('label') or entry.get('id') or 'Film'
    try:
        year = int(entry.get('year') or 0)
    except (TypeError, ValueError):
        year = 0
    if year:
        title = '%s (%d)' % (title, year)
    return safe_name(title, 120)


def _unique(stem, used):
    candidate = stem
    counter = 2
    while candidate.lower() in used:
        candidate = safe_name('%s (%d)' % (stem, counter), 120)
        counter += 1
    used.add(candidate.lower())
    return candidate


def _write(path, text):
    try:
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(text)
        return True
    except OSError:
        return False


def _write_pair(folder, stem, target, entry):
    if not _write(os.path.join(folder, stem + '.strm'), target + '\n'):
        return False
    if not _write(os.path.join(folder, stem + '.nfo'), nfo_text(entry)):
        return False
    return True


def _read_manifest(folder):
    """Dateien, die der letzte Export geschrieben hat."""
    try:
        with open(os.path.join(folder, MANIFEST), encoding='utf-8') as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return []
    files = data.get('files') if isinstance(data, dict) else None
    if not isinstance(files, list):
        return []
    return [item for item in files if isinstance(item, str)]


def _write_manifest(folder, files):
    try:
        with open(os.path.join(folder, MANIFEST), 'w', encoding='utf-8') as handle:
            json.dump({'version': 1, 'files': sorted(files)}, handle, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _safe_path(folder, relative):
    """Nur eigene Exportdateien in Merkliste/ und Downloads/ zulassen."""
    parts = [part for part in str(relative or '').replace('\\', '/').split('/') if part not in ('', '.')]
    if not parts or parts[0] not in FOLDERS or '..' in parts:
        return ''
    if not parts[-1].lower().endswith(('.strm', '.nfo')):
        return ''
    path = os.path.join(folder, *parts)
    try:
        if os.path.commonpath([os.path.abspath(folder), os.path.abspath(path)]) != os.path.abspath(folder):
            return ''
    except ValueError:
        return ''
    return path


def _cleanup(folder, previous, current):
    """Löscht nur Dateien aus dem letzten Manifest, die jetzt nicht mehr entstehen."""
    removed = 0
    for relative in previous:
        if relative in current:
            continue
        path = _safe_path(folder, relative)
        if not path:
            continue
        try:
            if os.path.exists(path):
                os.remove(path)
                removed += 1
        except OSError:
            pass
    return removed


def export_entries(folder, watchlist_entries, download_entries):
    """Schreibt beide Quellen in Unterordner; Rückgabe: Anzahl exportierter Filme."""
    if not folder:
        return 0
    folder = xbmcvfs.translatePath(folder)
    watch_folder = os.path.join(folder, 'Merkliste')
    download_folder = os.path.join(folder, 'Downloads')
    # Unabhängig anlegen: ein bereits vorhandener Ordner darf den anderen nicht verhindern.
    for target in (watch_folder, download_folder):
        try:
            os.makedirs(target, exist_ok=True)
        except OSError:
            pass
    previous = _read_manifest(folder)
    current = set()
    count = 0
    used = set()
    for entry in watchlist_entries or []:
        if not entry.get('id'):
            continue
        stem = _unique(_stem(entry), used)
        data = dict(entry)
        data['uniqueid'] = '%s:%s' % (entry.get('provider') or 'archive', entry.get('id'))
        if _write_pair(watch_folder, stem, plugin_url(entry), data):
            current.add('Merkliste/%s.strm' % stem)
            current.add('Merkliste/%s.nfo' % stem)
            count += 1
    used = set()
    for entry in download_entries or []:
        path = entry.get('path') or ''
        if not path or not xbmcvfs.exists(path):
            continue
        stem = _unique(_stem(entry), used)
        data = dict(entry)
        data['uniqueid'] = 'download:%s' % os.path.basename(path)
        data.setdefault('thumb', '')
        if _write_pair(download_folder, stem, path, data):
            current.add('Downloads/%s.strm' % stem)
            current.add('Downloads/%s.nfo' % stem)
            count += 1
    _cleanup(folder, previous, current)
    _write_manifest(folder, current)
    return count


class LibraryExport(object):
    def __init__(self, folder=None):
        self.addon = xbmcaddon.Addon()
        if folder is None:
            folder = (self.addon.getSetting('library_path') or '').strip()
        self.folder = xbmcvfs.translatePath(folder) if folder else ''

    def export(self):
        if not self.folder:
            return 0
        from .watchlist import Watchlist
        return export_entries(self.folder, Watchlist().entries(), Downloads().items())
