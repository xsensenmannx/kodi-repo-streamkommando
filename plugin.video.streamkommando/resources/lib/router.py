# -*- coding: utf-8 -*-
"""Alle Ansichten des Plugins."""

import sys
import urllib.parse

import xbmcaddon
import xbmcgui
import xbmcplugin

from . import kodigui
from .archive import COLLECTIONS, IMG_URL, SORTS, Archive, clean_text, to_year
from .cache import Cache
from .streams import Streams


class Router(object):
    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self.handle = int(sys.argv[1])
        self.base = sys.argv[0]
        raw = sys.argv[2][1:] if len(sys.argv) > 2 else ''
        self.params = dict(urllib.parse.parse_qsl(raw))
        self.mode = self.params.get('mode') or 'root'
        self.cache = Cache()
        self.archive = Archive(self.cache)
        self.settings_url = '%s?mode=settings' % self.base

    # -- Helfer -----------------------------------------------------
    def url(self, mode='root', **params):
        params['mode'] = mode
        return '%s?%s' % (self.base, urllib.parse.urlencode(params))

    def _int_setting(self, key, default):
        try:
            return int(self.addon.getSetting(key) or default)
        except (TypeError, ValueError):
            return default

    def rows(self):
        return min(200, max(10, self._int_setting('items_per_page', 50)))

    def sort(self):
        index = self._int_setting('sort_order', 0)
        return SORTS[index] if 0 <= index < len(SORTS) else SORTS[0]

    def page(self):
        try:
            return max(1, int(self.params.get('page') or 1))
        except (TypeError, ValueError):
            return 1

    # -- Ansichten --------------------------------------------------
    def run(self):
        view = getattr(self, 'view_' + self.mode, None)
        if callable(view):
            view()
        else:
            self.view_root()

    def view_root(self):
        handle = self.handle
        kodigui.add_folder(handle, self.url('archive'), kodigui.tr(30001), plot=kodigui.tr(30014))
        kodigui.add_folder(handle, self.url('search'), kodigui.tr(30002))
        kodigui.add_link(handle, self.url('random'), kodigui.tr(30005), plot=kodigui.tr(30015))
        kodigui.add_folder(handle, self.url('streams'), kodigui.tr(30003))
        kodigui.add_folder(handle, self.settings_url, kodigui.tr(30004), folder=False)
        kodigui.add_folder(handle, self.url('clear'), kodigui.tr(30010), folder=False)
        kodigui.end(handle, content='files', cache=False)

    def view_settings(self):
        self.addon.openSettings()
        kodigui.end(self.handle, succeeded=False, cache=False)

    def view_clear(self):
        self.cache.clear()
        kodigui.notify(kodigui.tr(30011))
        kodigui.end(self.handle, content='files', succeeded=False, cache=False)

    def view_archive(self):
        handle = self.handle
        for string_id, collection_id in COLLECTIONS:
            kodigui.add_folder(handle, self.url('collection', id=collection_id, page=1), kodigui.tr(string_id))
        kodigui.end(handle, content='files', cache=False)

    def view_collection(self):
        collection_id = self.params.get('id') or ''
        docs, total = self.archive.collection(collection_id, self.page(), self.rows(), self.sort())
        self.list_movies(docs, total, 'collection', id=collection_id)

    def view_search(self):
        term = (self.params.get('q') or '').strip()
        if not term:
            term = (xbmcgui.Dialog().input(kodigui.tr(30008), type=xbmcgui.INPUT_ALPHANUM) or '').strip()
            if not term:
                kodigui.end(self.handle, succeeded=False, cache=False)
                return
        docs, total = self.archive.find(term, self.page(), self.rows(), self.sort())
        self.list_movies(docs, total, 'search', q=term)

    def list_movies(self, docs, total, mode, **params):
        handle = self.handle
        for doc in docs:
            identifier = doc.get('identifier')
            if not identifier:
                continue
            title = clean_text(doc.get('title'), 200) or identifier
            kodigui.add_link(
                handle,
                self.url('play', id=identifier),
                title,
                IMG_URL + urllib.parse.quote(identifier),
                title=title,
                year=to_year(doc.get('year')),
                plot=clean_text(doc.get('description'), 500),
                mediatype='movie',
            )
        if not docs:
            kodigui.notify(kodigui.tr(30007))
        if total > self.page() * self.rows():
            page_params = dict(params, page=self.page() + 1)
            kodigui.add_folder(handle, self.url(mode, **page_params), kodigui.tr(30006))
        kodigui.end(handle, content='videos')

    def view_play(self):
        identifier = self.params.get('id') or ''
        item = self.archive.item(identifier) if identifier else None
        if not item or not item.get('url'):
            kodigui.notify(kodigui.tr(30009), icon=xbmcgui.NOTIFICATION_ERROR)
            xbmcplugin.setResolvedUrl(self.handle, False, xbmcgui.ListItem(offscreen=True))
            return
        play_item = xbmcgui.ListItem(label=item['title'], offscreen=True)
        play_item.setPath(item['url'])
        play_item.setArt(kodigui.art(IMG_URL + urllib.parse.quote(identifier)))
        info = {
            'title': item['title'],
            'plot': item.get('plot', ''),
            'year': item.get('year') or 0,
            'mediatype': 'movie',
        }
        if item.get('creator'):
            info['studio'] = item['creator']
        if item.get('duration'):
            info['duration'] = item['duration']
        play_item.setInfo('video', info)
        xbmcplugin.setResolvedUrl(self.handle, True, play_item)

    def view_random(self):
        doc = self.archive.random_movie(self.rows())
        if not doc or not doc.get('identifier'):
            kodigui.notify(kodigui.tr(30007))
            xbmcplugin.setResolvedUrl(self.handle, False, xbmcgui.ListItem(offscreen=True))
            return
        self.params['id'] = doc['identifier']
        self.view_play()

    def view_streams(self):
        handle = self.handle
        folder = (self.addon.getSetting('own_streams_path') or '').strip()
        if not folder:
            kodigui.notify(kodigui.tr(30012))
            kodigui.add_folder(handle, self.settings_url, kodigui.tr(30013), folder=False)
            kodigui.end(handle, content='files', succeeded=False, cache=False)
            return
        files = Streams(folder).files()
        if not files:
            kodigui.notify(kodigui.tr(30007))
        for path, label in files:
            kodigui.add_file(handle, path, label)
        kodigui.end(handle, content='files', cache=False)
