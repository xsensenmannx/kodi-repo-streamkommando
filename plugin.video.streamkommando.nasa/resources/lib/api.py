# -*- coding: utf-8 -*-
"""Zugriff auf die offizielle NASA-Bild- und Video-API (images.nasa.gov)."""

import html
import json
import re
import urllib.parse
import urllib.request

import xbmc

from .cache import Cache

BASE = 'https://images-api.nasa.gov'
USER_AGENT = 'StreamKommando-NASA/1.0 (Kodi Add-on; +https://github.com/xsensenmannx/kodi-repo-streamkommando)'
PER_PAGE = 40

# (Label, Suchbegriff) – Labels bewusst sprachneutral bzw. deutsch.
TOPICS = (
    ('Apollo', 'apollo'),
    ('Artemis', 'artemis'),
    ('Mars', 'mars rover'),
    ('ISS', 'international space station'),
    ('Space Shuttle', 'space shuttle'),
    ('Erde aus dem All', 'earth from space'),
    ('Raketenstarts', 'rocket launch'),
)

SIZE_ORDER = ('~orig.mp4', '~large.mp4', '~medium.mp4', '~small.mp4', '~mobile.mp4', '~preview.mp4')


def clean_text(value, limit=900):
    if isinstance(value, (list, tuple)):
        value = ' '.join(str(part) for part in value if part)
    if not value:
        return ''
    text = re.sub(r'<[^>]+>', ' ', str(value))
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(' ', 1)[0].rstrip(',.;:') + '…'
    return text


def _open_json(url, timeout=25):
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8', 'replace'))
    except (OSError, ValueError) as error:
        xbmc.log('Stream Kommando NASA: Anfrage fehlgeschlagen (%s): %s' % (url, error), xbmc.LOGWARNING)
        return {}


def to_year(value):
    match = re.search(r'(\d{4})', str(value or ''))
    return int(match.group(1)) if match else 0


class Nasa(object):
    def __init__(self, cache=None):
        self.cache = cache if cache is not None else Cache()

    def search(self, term, page=1, per_page=PER_PAGE):
        params = {
            'q': term,
            'media_type': 'video',
            'page': max(1, int(page)),
            'page_size': per_page,
        }
        url = BASE + '/search?' + urllib.parse.urlencode(params)
        data = self.cache.get(url)
        if data is None:
            payload = _open_json(url)
            collection = payload.get('collection') or {}
            items = collection.get('items') or []
            total = int((collection.get('metadata') or {}).get('total_hits') or 0)
            data = {'items': [self._normalize(item) for item in items], 'total': total}
            if data['items']:
                self.cache.set(url, data)
        return data.get('items') or [], int(data.get('total') or 0)

    def _normalize(self, item):
        data = (item.get('data') or [{}])[0]
        links = item.get('links') or []
        thumb = ''
        for link in links:
            if link.get('rel') == 'preview' and link.get('href'):
                thumb = link['href']
                break
        return {
            'id': data.get('nasa_id') or '',
            'title': clean_text(data.get('title'), 200) or data.get('nasa_id') or '',
            'plot': clean_text(data.get('description')),
            'thumb': thumb,
            'year': to_year(data.get('date_created')),
        }

    @staticmethod
    def _secure(url):
        """NASA liefert Asset-URLs teils als http:// – unter Android blockiert."""
        if url.startswith('http://'):
            url = 'https://' + url[len('http://'):]
        return urllib.parse.quote(url, safe=':/?&=%~,+')

    def playback_url(self, nasa_id):
        if not nasa_id:
            return ''
        key = 'asset:' + nasa_id
        url = self.cache.get(key)
        if url is None:
            payload = _open_json(BASE + '/asset/' + urllib.parse.quote(nasa_id))
            files = [entry.get('href') or '' for entry in (payload.get('collection') or {}).get('items') or []]
            mp4 = [path for path in files if path.lower().endswith('.mp4')]
            url = ''
            for marker in SIZE_ORDER:
                for path in mp4:
                    if marker in path:
                        url = path
                        break
                if url:
                    break
            if not url and mp4:
                url = mp4[0]
            if url:
                url = self._secure(url)
                self.cache.set(key, url)
        return url or ''
