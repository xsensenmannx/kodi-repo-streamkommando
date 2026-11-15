# -*- coding: utf-8 -*-
"""Eigene Streams aus einem Ordner mit .strm-/.m3u-Dateien."""

import xbmcvfs

PLAYABLE = ('.strm', '.m3u', '.m3u8', '.mp4', '.mkv', '.avi', '.mov', '.webm', '.ts')


def _text(value):
    if isinstance(value, bytes):
        return value.decode('utf-8', 'replace')
    return str(value)


def _join(base, name):
    return base.rstrip('/\\') + '/' + name


class Streams(object):
    def __init__(self, folder, depth=2):
        self.folder = folder
        self.depth = max(1, depth)

    def files(self):
        found = []
        self._scan(self.folder, '', 0, found)
        found.sort(key=lambda row: row[0].lower())
        return found

    def _scan(self, path, prefix, level, found):
        try:
            dirs, files = xbmcvfs.listdir(path)
        except Exception:
            return
        for raw in files:
            name = _text(raw)
            if name.lower().endswith(PLAYABLE):
                label = prefix + name.rsplit('.', 1)[0]
                found.append((_join(path, name), label))
        if level + 1 >= self.depth:
            return
        for raw in dirs:
            name = _text(raw)
            if not name or name.startswith('.'):
                continue
            self._scan(_join(path, name), prefix + name + ' / ', level + 1, found)
