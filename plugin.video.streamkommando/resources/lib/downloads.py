# -*- coding: utf-8 -*-
"""Downloads aus dem Archiv in einen lokalen Ordner."""

import json
import os
import re
import time
import urllib.parse
import urllib.request

import xbmcaddon
import xbmcgui
import xbmcvfs

from .archive import USER_AGENT, format_size

CHUNK = 256 * 1024
VIDEO_SUFFIXES = ('.mp4', '.m4v', '.mkv', '.webm', '.ogv', '.mpg', '.mpeg', '.avi', '.mov')
INVALID_CHARS = re.compile(r'[\\/:*?"<>|]')


def safe_name(value, limit=120):
    name = INVALID_CHARS.sub(' ', str(value or ''))
    name = re.sub(r'\s+', ' ', name).strip(' .')
    return name[:limit].strip(' .') or 'Film'


def _join(base, name):
    return base.rstrip('/\\') + '/' + name


def _write_text(path, text):
    handle = xbmcvfs.File(path, 'w')
    try:
        handle.write(text.encode('utf-8'))
    except TypeError:
        handle.write(text)
    finally:
        handle.close()


class Downloads(object):
    def __init__(self, folder=None):
        self.addon = xbmcaddon.Addon()
        self.folder = (self.addon.getSetting('download_path') or '').strip() if folder is None else folder

    # -- Pfade ------------------------------------------------------
    def path_for(self, item, source):
        title = item.get('title') or 'Film'
        if item.get('year'):
            title = '%s (%s)' % (title, item['year'])
        suffix = os.path.splitext(str(source.get('name') or ''))[1].lower()
        if not suffix:
            suffix = os.path.splitext(urllib.parse.urlparse(str(source.get('url') or '')).path)[1].lower()
        if suffix not in VIDEO_SUFFIXES:
            suffix = '.mp4'
        name = safe_name(title)
        target = _join(self.folder, name + suffix)
        counter = 2
        while xbmcvfs.exists(target):
            target = _join(self.folder, '%s (%d)%s' % (name, counter, suffix))
            counter += 1
        return target

    def _sidecar(self, target):
        return target + '.json'

    def _ensure_folder(self):
        if not self.folder or xbmcvfs.exists(self.folder):
            return
        try:
            xbmcvfs.mkdirs(self.folder)
        except Exception:
            pass

    # -- Herunterladen ---------------------------------------------
    def save(self, item, source, target):
        """Lädt eine Quelle mit Fortschrittsdialog. Rückgabe: (ok, string_id)."""
        self._ensure_folder()
        dialog = xbmcgui.DialogProgress()
        dialog.create(self.addon.getLocalizedString(30034), os.path.basename(target))
        handle = xbmcvfs.File(target, 'wb')
        total = int(source.get('size') or 0)
        done = 0
        last_percent = -1
        cancelled = False
        request = urllib.request.Request(source['url'], headers={'User-Agent': USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                total = int(response.headers.get('Content-Length') or total)
                while True:
                    if dialog.iscanceled():
                        cancelled = True
                        break
                    chunk = response.read(CHUNK)
                    if not chunk:
                        break
                    handle.write(chunk)
                    done += len(chunk)
                    percent = int(done * 100 / total) if total else 0
                    if percent != last_percent:
                        dialog.update(percent, '%s / %s' % (format_size(done), format_size(total)))
                        last_percent = percent
        except Exception:
            try:
                handle.close()
            except Exception:
                pass
            xbmcvfs.delete(target)
            dialog.close()
            return False, 30036
        try:
            handle.close()
        except Exception:
            pass
        dialog.close()

        if cancelled or done == 0:
            xbmcvfs.delete(target)
            return False, 30040

        meta = {
            'title': item.get('title'),
            'year': item.get('year'),
            'plot': item.get('plot'),
            'creator': item.get('creator'),
            'duration': item.get('duration'),
            'source': source.get('url'),
            'format': source.get('format'),
            'size': done,
            'added': int(time.time()),
        }
        try:
            _write_text(self._sidecar(target), json.dumps(meta, ensure_ascii=False))
        except Exception:
            pass
        return True, 30035

    # -- Bibliothek -------------------------------------------------
    def items(self):
        if not self.folder or not xbmcvfs.exists(self.folder):
            return []
        try:
            _dirs, files = xbmcvfs.listdir(self.folder)
        except Exception:
            return []
        entries = []
        for raw in files:
            name = raw.decode('utf-8', 'replace') if isinstance(raw, bytes) else str(raw)
            if not name.lower().endswith(VIDEO_SUFFIXES):
                continue
            path = _join(self.folder, name)
            meta = self._read_meta(path)
            entries.append({
                'path': path,
                'label': meta.get('title') or os.path.splitext(name)[0],
                'plot': meta.get('plot') or '',
                'year': meta.get('year') or 0,
                'duration': meta.get('duration') or 0,
                'size': meta.get('size') or 0,
            })
        entries.sort(key=lambda row: row['label'].lower())
        return entries

    def _read_meta(self, path):
        try:
            handle = xbmcvfs.File(self._sidecar(path))
            data = handle.read()
            handle.close()
            if isinstance(data, bytes):
                data = data.decode('utf-8', 'replace')
            return json.loads(data or '{}')
        except Exception:
            return {}

    def delete(self, path):
        removed = False
        for target in (path, self._sidecar(path)):
            try:
                if xbmcvfs.exists(target):
                    removed = xbmcvfs.delete(target) or removed
            except Exception:
                pass
        return removed
