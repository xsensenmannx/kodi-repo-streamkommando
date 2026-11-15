# -*- coding: utf-8 -*-
"""Zugriff auf das Internet Archive (advancedsearch + metadata)."""

import html
import json
import random
import re
import urllib.parse
import urllib.request

import xbmc

from .cache import Cache

SEARCH_URL = 'https://archive.org/advancedsearch.php'
META_URL = 'https://archive.org/metadata/'
IMG_URL = 'https://archive.org/services/img/'
FILE_URL = 'https://archive.org/download/'
USER_AGENT = 'StreamKommando/1.0 (Kodi Add-on)'

FIELDS = ('identifier', 'title', 'year', 'description', 'downloads', 'runtime', 'creator')

# (String-ID, Sammlungs-ID) – Reihenfolge bestimmt die Anzeige im Archiv.
COLLECTIONS = (
    (30108, 'feature_films'),
    (30101, 'SciFi_Horror'),
    (30102, 'Comedy_Films'),
    (30103, 'silent_films'),
    (30104, 'animationandcartoons'),
    (30105, 'classic_tv'),
    (30106, 'prelinger'),
    (30107, 'short_films'),
)

SORTS = ('downloads desc', 'title asc', 'year desc')

# Formatname (klein) -> Rang; höher ist besser.
VIDEO_FORMATS = (
    ('hires mpeg4', 6),
    ('h.264', 6),
    ('mpeg4', 5),
    ('512kb mpeg4', 4),
    ('matroska', 3),
    ('webm', 3),
    ('ogg video', 2),
    ('mpeg2', 1),
    ('quicktime', 1),
)
VIDEO_SUFFIXES = ('.mp4', '.m4v', '.mkv', '.webm', '.ogv', '.mpg', '.mpeg', '.avi', '.mov')


def clean_text(value, limit=1200):
    """Entfernt HTML aus den Archive-Beschreibungen und kürzt den Text."""
    if isinstance(value, (list, tuple)):
        value = ' '.join(str(part) for part in value if part)
    if not value:
        return ''
    text = re.sub(r'<br\s*/?>', '\n', str(value), flags=re.I)
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(' ', 1)[0].rstrip(',.;:') + '…'
    return text


def to_year(value):
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ''
    match = re.search(r'(1[89]\d\d|20\d\d)', str(value or ''))
    return int(match.group(1)) if match else 0


def to_seconds(value):
    """Wandelt '1:33:12' oder '93 min' in Sekunden für Kodi-InfoLabels."""
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ''
    text = str(value or '').strip()
    if not text:
        return 0
    clock = re.findall(r'\d+', text)
    if ':' in text and clock:
        seconds = 0
        for part in clock:
            seconds = seconds * 60 + int(part)
        return seconds
    if clock:
        return int(clock[0]) * 60
    return 0


def _open_json(url, timeout=20):
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8', 'replace'))
    except (OSError, ValueError) as error:
        xbmc.log('Stream Kommando: Anfrage fehlgeschlagen (%s): %s' % (url, error), xbmc.LOGWARNING)
        return {}


class Archive(object):
    def __init__(self, cache=None):
        self.cache = cache if cache is not None else Cache()

    # -- Suche ------------------------------------------------------
    def search(self, query, page=1, rows=50, sort='downloads desc'):
        params = [('q', query), ('rows', rows), ('page', page), ('output', 'json'), ('sort[]', sort)]
        params.extend(('fl[]', field) for field in FIELDS)
        url = SEARCH_URL + '?' + urllib.parse.urlencode(params)
        data = self.cache.get(url)
        if data is None:
            data = _open_json(url).get('response') or {}
            if data:
                self.cache.set(url, data)
        return data.get('docs') or [], int(data.get('numFound') or 0)

    def _collections_query(self):
        return ' OR '.join('collection:%s' % collection_id for _, collection_id in COLLECTIONS)

    def collection(self, collection_id, page=1, rows=50, sort='downloads desc'):
        return self.search('collection:%s AND mediatype:movies' % collection_id, page, rows, sort)

    def find(self, term, page=1, rows=50, sort='downloads desc'):
        term = re.sub(r'[\\:()\[\]{}"^~+]', ' ', term or '').strip()
        if not term:
            return [], 0
        query = 'mediatype:movies AND (%s) AND title:(%s)' % (self._collections_query(), term)
        return self.search(query, page, rows, sort)

    def random_movie(self, rows=50):
        """Zufallsfilm: zufällige Sammlung, zufällige flache Seite.

        Tiefe Seiten (page > ~600) beantwortet das Archive mit HTTP 507,
        deshalb bleibt die Auswahl bewusst im flachen Bereich.
        """
        collection_id = random.choice(COLLECTIONS)[1]
        for page in (random.randint(1, 12), 1):
            docs, _ = self.collection(collection_id, page, rows, 'downloads desc')
            if docs:
                return random.choice(docs)
        return None

    # -- Details ----------------------------------------------------
    def item(self, identifier):
        if not identifier:
            return None
        key = 'item:' + identifier
        data = self.cache.get(key)
        if data is None:
            payload = _open_json(META_URL + urllib.parse.quote(identifier))
            if not payload:
                return None
            data = self._digest(identifier, payload)
            self.cache.set(key, data)
        return data

    def _digest(self, identifier, payload):
        meta = payload.get('metadata') or {}
        return {
            'identifier': identifier,
            'title': clean_text(meta.get('title'), 200) or identifier,
            'year': to_year(meta.get('year') or meta.get('date')),
            'plot': clean_text(meta.get('description')),
            'creator': clean_text(meta.get('creator'), 200),
            'duration': to_seconds(meta.get('runtime')),
            'url': self._playback_url(identifier, payload.get('files') or []),
        }

    @staticmethod
    def _playback_url(identifier, files):
        ranked = []
        for entry in files:
            name = str(entry.get('name') or '')
            lower = name.lower()
            if not lower.endswith(VIDEO_SUFFIXES) or '/thumbs/' in lower:
                continue
            if lower.startswith('__ia_thumb') or 'thumb' in lower:
                continue
            fmt = str(entry.get('format') or '').lower()
            rank = 0
            for label, weight in VIDEO_FORMATS:
                if label in fmt:
                    rank = weight
                    break
            if rank == 0:
                rank = 1 if lower.endswith(('.mp4', '.m4v', '.mkv', '.webm')) else 0
            try:
                size = int(entry.get('size') or 0)
            except (TypeError, ValueError):
                size = 0
            ranked.append((rank, size, name))
        if not ranked:
            return ''
        ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
        return FILE_URL + urllib.parse.quote(identifier) + '/' + urllib.parse.quote(ranked[0][2])
