# -*- coding: utf-8 -*-
"""Zugriff auf die MediaWiki-API von Wikimedia Commons (Videos)."""

import html
import json
import re
import urllib.parse
import urllib.request

import xbmc

from .cache import Cache

API = 'https://commons.wikimedia.org/w/api.php'
FILE_PATH = 'https://commons.wikimedia.org/wiki/Special:FilePath/'
USER_AGENT = 'StreamKommando-Commons/1.0 (Kodi Add-on; +https://github.com/xsensenmannx/kodi-repo-streamkommando)'
PER_PAGE = 24

TOPICS = (
    ('Städte', 'stadt'),
    ('Natur', 'natur'),
    ('Tiere', 'tiere'),
    ('Wissenschaft', 'wissenschaft'),
    ('Historische Filme', 'historischer film'),
)


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
        xbmc.log('Stream Kommando Commons: Anfrage fehlgeschlagen (%s): %s' % (url, error), xbmc.LOGWARNING)
        return {}


def pick_derivative(info):
    """Beste abspielbare Fassung: WebM bevorzugt, sonst Original."""
    derivatives = info.get('derivatives') or []
    ranked = []
    for entry in derivatives:
        src = entry.get('src') or ''
        if not src:
            continue
        height = int(entry.get('height') or 0)
        mime = str(entry.get('type') or '').lower()
        bonus = 2 if 'webm' in mime else (1 if 'mp4' in mime or 'quicktime' in mime else 0)
        ranked.append((height, bonus, src))
    if ranked:
        ranked.sort(reverse=True)
        return ranked[0][2]
    return info.get('url') or ''


class Commons(object):
    def __init__(self, cache=None):
        self.cache = cache if cache is not None else Cache()

    def search(self, term, offset=0, limit=PER_PAGE):
        params = [
            ('action', 'query'),
            ('format', 'json'),
            ('formatversion', '2'),
            ('generator', 'search'),
            ('gsrsearch', 'filetype:video %s' % term),
            ('gsrnamespace', 6),
            ('gsrlimit', limit),
            ('gsroffset', max(0, int(offset))),
            ('prop', 'videoinfo'),
            ('viprop', 'url|size|derivatives|extmetadata'),
        ]
        url = API + '?' + urllib.parse.urlencode(params)
        data = self.cache.get(url)
        if data is None:
            payload = _open_json(url)
            pages = (payload.get('query') or {}).get('pages') or []
            data = {
                'items': [self._normalize(page) for page in pages],
                'more': bool(payload.get('continue')),
            }
            if data['items']:
                self.cache.set(url, data)
        return data.get('items') or [], bool(data.get('more'))

    def _normalize(self, page):
        info = (page.get('videoinfo') or [{}])[0]
        meta = info.get('extmetadata') or {}
        title = str(page.get('title') or '').replace('File:', '')
        title = re.sub(r'\.[a-z0-9]{2,5}$', '', title, flags=re.I).replace('_', ' ')
        license_name = clean_text((meta.get('LicenseShortName') or {}).get('value'), 60)
        artist = clean_text((meta.get('Artist') or {}).get('value'), 120)
        plot_parts = ['Wikimedia Commons']
        if license_name:
            plot_parts.append('Lizenz: %s' % license_name)
        if artist:
            plot_parts.append('Autor: %s' % artist)
        raw_title = str(page.get('title') or '')
        thumb = ''
        if raw_title:
            file_name = raw_title[len('File:'):] if raw_title.startswith('File:') else raw_title
            thumb = FILE_PATH + urllib.parse.quote(file_name) + '?width=400'
        return {
            'title': title or raw_title,
            'url': pick_derivative(info),
            'plot': ' · '.join(plot_parts),
            'thumb': thumb,
            'license': license_name,
            'artist': artist,
        }
