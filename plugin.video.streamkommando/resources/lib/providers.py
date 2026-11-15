# -*- coding: utf-8 -*-
"""Provider-Registry: eine Suche über mehrere freie Quellen.

Jeder Provider liefert normalisierte Treffer und löst die Wiedergabe-URL auf.
Quellen: Internet Archive (kuratierte Sammlungen), images.nasa.gov, Wikimedia Commons.
"""

import json
import re
import urllib.parse
import urllib.request

import xbmc

from .archive import IMG_URL, Archive, clean_text, to_year
from .cache import Cache

USER_AGENT = 'StreamKommando/1.3 (Kodi Add-on; +https://github.com/xsensenmannx/kodi-repo-streamkommando)'
NASA_BASE = 'https://images-api.nasa.gov'
COMMONS_API = 'https://commons.wikimedia.org/w/api.php'
COMMONS_FILE = 'https://commons.wikimedia.org/wiki/Special:FilePath/'

NASA_SIZES = ('~orig.mp4', '~large.mp4', '~medium.mp4', '~small.mp4', '~mobile.mp4', '~preview.mp4')

# Kuratierte Open Movies der Blender Foundation (CC-BY), Fassungen auf Wikimedia Commons.
BLENDER_FILMS = (
    ('Big Buck Bunny', 2008,
     'Ein riesiger Hase rächt sich an drei Nagern – der erste Open Movie der Blender Foundation.',
     'File:Big Buck Bunny 4K.webm'),
    ('Sintel', 2010,
     'Ein Mädchen sucht ihren verletzten Drachen. Fantasy-Kurzfilm der Blender Foundation.',
     'File:Sintel movie 4K.webm'),
    ('Tears of Steel', 2012,
     'Science-Fiction in Amsterdam: Menschen gegen Roboter, gedreht mit realem Filmmaterial.',
     'File:Tears of Steel 1080p.webm'),
    ('Cosmos Laundromat', 2015,
     'Ein Schaf auf einer einsamen Insel trifft einen Händler mit einem ungewöhnlichen Angebot.',
     'File:Cosmos Laundromat - First Cycle - Official Blender Foundation release.webm'),
    ('Spring', 2019,
     'Ein Hirtenmädchen und ihr Hund stellen sich den Geistern des Frühlings.',
     'File:Spring - Blender Open Movie.webm'),
    ('Elephants Dream', 2006,
     'Der erste Open Movie: zwei Männer in einer surrealen Maschinenwelt.',
     'File:Elephants Dream (2006).webm'),
    ('Caminandes 3: Llamigos', 2016,
     'Koro das Lama und sein Freund Pico im Schnee – kurzer Animationsfilm.',
     'File:Caminandes 3 - Llamigos - Blender Animated Short.webm'),
)


def _open_json(url, timeout=20):
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8', 'replace'))
    except (OSError, ValueError) as error:
        xbmc.log('Stream Kommando: Provider-Anfrage fehlgeschlagen (%s): %s' % (url, error), xbmc.LOGWARNING)
        return None


def _secure(url):
    if url.startswith('http://'):
        url = 'https://' + url[len('http://'):]
    return urllib.parse.quote(url, safe=':/?&=%~,+')


def _to_year(value):
    match = re.search(r'(\d{4})', str(value or ''))
    return int(match.group(1)) if match else 0


class ArchiveProvider(object):
    key = 'archive'
    label_id = 30110

    def __init__(self, only_licensed=False):
        self.api = Archive(Cache('providers'), only_licensed=only_licensed)
        self.error = False

    def search(self, term, page=1, limit=12, sort=None):
        docs, total = self.api.find(term, page, limit, sort or 'downloads desc')
        self.error = self.api.error
        items = []
        for doc in docs:
            identifier = doc.get('identifier')
            if not identifier:
                continue
            items.append({
                'id': identifier,
                'title': clean_text(doc.get('title'), 200) or identifier,
                'plot': clean_text(doc.get('description'), 400),
                'thumb': IMG_URL + urllib.parse.quote(identifier),
                'year': to_year(doc.get('year')),
                'url': '',
            })
        return items, total, total > page * limit

    def play_url(self, params):
        item = self.api.item(params.get('id') or '')
        return (item or {}).get('url') or ''


class NasaProvider(object):
    key = 'nasa'
    label_id = 30111

    def __init__(self):
        self.cache = Cache('providers')
        self.error = False

    def search(self, term, page=1, limit=12, sort=None):
        self.error = False
        params = {
            'q': term,
            'media_type': 'video',
            'page': max(1, int(page)),
            'page_size': limit,
        }
        url = NASA_BASE + '/search?' + urllib.parse.urlencode(params)
        data = self.cache.get(url)
        if data is None:
            payload = _open_json(url)
            if payload is None:
                self.error = True
                return [], 0, False
            collection = (payload.get('collection') or {})
            total = int((collection.get('metadata') or {}).get('total_hits') or 0)
            items = []
            for entry in collection.get('items') or []:
                info = (entry.get('data') or [{}])[0]
                identifier = info.get('nasa_id') or ''
                if not identifier:
                    continue
                thumb = ''
                for link in entry.get('links') or []:
                    if link.get('rel') == 'preview' and link.get('href'):
                        thumb = link['href']
                        break
                items.append({
                    'id': identifier,
                    'title': clean_text(info.get('title'), 200) or identifier,
                    'plot': clean_text(info.get('description'), 400),
                    'thumb': thumb,
                    'year': _to_year(info.get('date_created')),
                    'url': '',
                })
            data = {'items': items, 'total': total}
            if items:
                self.cache.set(url, data)
        total = int(data.get('total') or 0)
        return data.get('items') or [], total, total > page * limit

    def play_url(self, params):
        identifier = params.get('id') or ''
        if not identifier:
            return ''
        key = 'asset:' + identifier
        url = self.cache.get(key)
        if url is None:
            payload = _open_json(NASA_BASE + '/asset/' + urllib.parse.quote(identifier))
            if not payload:
                self.error = True
                return ''
            files = [entry.get('href') or '' for entry in (payload.get('collection') or {}).get('items') or []]
            mp4 = [path for path in files if path.lower().endswith('.mp4')]
            url = ''
            for marker in NASA_SIZES:
                for path in mp4:
                    if marker in path:
                        url = path
                        break
                if url:
                    break
            if not url and mp4:
                url = mp4[0]
            if url:
                url = _secure(url)
                self.cache.set(key, url)
        return url or ''


class CommonsProvider(object):
    key = 'commons'
    label_id = 30112

    def __init__(self):
        self.cache = Cache('providers')
        self.error = False

    def search(self, term, page=1, limit=12, sort=None):
        self.error = False
        offset = max(0, (max(1, int(page)) - 1) * limit)
        params = [
            ('action', 'query'),
            ('format', 'json'),
            ('formatversion', '2'),
            ('generator', 'search'),
            ('gsrsearch', 'filetype:video %s' % term),
            ('gsrnamespace', 6),
            ('gsrlimit', limit),
            ('gsroffset', offset),
            ('prop', 'videoinfo'),
            ('viprop', 'url|size|derivatives|extmetadata'),
        ]
        url = COMMONS_API + '?' + urllib.parse.urlencode(params)
        data = self.cache.get(url)
        if data is None:
            payload = _open_json(url)
            if payload is None:
                self.error = True
                return [], 0, False
            items = []
            for entry in (payload.get('query') or {}).get('pages') or []:
                info = (entry.get('videoinfo') or [{}])[0]
                src = self._derivative(info)
                if not src:
                    continue
                title = str(entry.get('title') or '').replace('File:', '')
                title = re.sub(r'\.[a-z0-9]{2,5}$', '', title, flags=re.I).replace('_', ' ')
                meta = info.get('extmetadata') or {}
                license_name = clean_text((meta.get('LicenseShortName') or {}).get('value'), 60)
                artist = clean_text((meta.get('Artist') or {}).get('value'), 120)
                plot = ['Wikimedia Commons']
                if license_name:
                    plot.append('Lizenz: %s' % license_name)
                if artist:
                    plot.append('Autor: %s' % artist)
                raw_title = str(entry.get('title') or '')
                file_name = raw_title[len('File:'):] if raw_title.startswith('File:') else raw_title
                items.append({
                    'id': raw_title,
                    'title': title or raw_title,
                    'plot': ' · '.join(plot),
                    'thumb': COMMONS_FILE + urllib.parse.quote(file_name) + '?width=400',
                    'year': 0,
                    'url': src,
                })
            data = {'items': items, 'more': bool(payload.get('continue'))}
            if items:
                self.cache.set(url, data)
        items = data.get('items') or []
        more = bool(data.get('more'))
        total = ((offset + len(items) + limit) if more else offset + len(items))
        return items, total, more

    @staticmethod
    def _derivative(info):
        ranked = []
        for entry in info.get('derivatives') or []:
            src = entry.get('src') or ''
            if not src:
                continue
            mime = str(entry.get('type') or '').lower()
            bonus = 2 if 'webm' in mime else (1 if 'mp4' in mime or 'quicktime' in mime else 0)
            ranked.append((int(entry.get('height') or 0), bonus, src))
        if ranked:
            ranked.sort(reverse=True)
            return ranked[0][2]
        return info.get('url') or ''

    def play_url(self, params):
        src = params.get('src') or ''
        return src if src.startswith('https://') else ''


class BlenderProvider(object):
    """Kuratierte Blender-Open-Movies-Sammlung, aufgelöst über Wikimedia Commons."""

    key = 'blender'
    label_id = 30113
    browse_all = True
    always_list = False

    def __init__(self):
        self.cache = Cache('providers')
        self.error = False

    def search(self, term, page=1, limit=12, sort=None):
        self.error = False
        term = (term or '').strip().lower()
        items = []
        for title, year, plot, commons_title in BLENDER_FILMS:
            if term and term not in title.lower():
                continue
            items.append({
                'id': commons_title,
                'title': title,
                'plot': '%s · Blender Foundation, CC-BY' % plot,
                'thumb': COMMONS_FILE + urllib.parse.quote(commons_title[len('File:'):]) + '?width=400',
                'year': year,
                'url': '',
            })
        return items, len(items), False

    def play_url(self, params):
        src = params.get('src') or ''
        if src.startswith('https://'):
            return src
        return self._resolve(params.get('id') or '')

    def _resolve(self, commons_title):
        if not commons_title:
            return ''
        key = 'blender:' + commons_title
        url = self.cache.get(key)
        if url:
            return url
        payload = _open_json(COMMONS_API + '?' + urllib.parse.urlencode([
            ('action', 'query'),
            ('format', 'json'),
            ('formatversion', '2'),
            ('titles', commons_title),
            ('prop', 'videoinfo'),
            ('viprop', 'url|derivatives'),
        ]))
        if not payload:
            self.error = True
            return ''
        pages = (payload.get('query') or {}).get('pages') or []
        if not pages:
            return ''
        info = (pages[0].get('videoinfo') or [{}])[0]
        url = CommonsProvider._derivative(info)
        if url.startswith('https://'):
            self.cache.set(key, url)
            return url
        return ''


class Providers(object):
    def __init__(self, only_licensed=False):
        self._items = [
            ArchiveProvider(only_licensed),
            NasaProvider(),
            CommonsProvider(),
        ]
        self.blender = BlenderProvider()

    def all(self):
        return list(self._items) + [self.blender]

    def by_key(self, key):
        for provider in self.all():
            if provider.key == key:
                return provider
        return None
