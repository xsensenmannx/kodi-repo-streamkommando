# -*- coding: utf-8 -*-
"""Alle Ansichten des Plugins."""

import sys
import urllib.parse

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from . import kodigui
from .archive import (
    COLLECTIONS,
    IMG_URL,
    SORTS,
    Archive,
    clean_text,
    mime_type,
    source_label,
    to_year,
)
from .cache import Cache
from .downloads import Downloads
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
        self.archive = Archive(self.cache, only_licensed=self.bool_setting('only_licensed'))
        self.settings_url = '%s?mode=settings' % self.base

    # -- Helfer -----------------------------------------------------
    def url(self, mode='root', **params):
        params['mode'] = mode
        return '%s?%s' % (self.base, urllib.parse.urlencode(params))

    def int_setting(self, key, default):
        try:
            return int(self.addon.getSetting(key) or default)
        except (TypeError, ValueError):
            return default

    def bool_setting(self, key, default=False):
        value = (self.addon.getSetting(key) or '').lower()
        if not value:
            return default
        return value in ('true', '1', 'yes', 'on')

    def rows(self):
        return min(200, max(10, self.int_setting('items_per_page', 50)))

    def sort(self):
        index = self.int_setting('sort_order', 0)
        return SORTS[index] if 0 <= index < len(SORTS) else SORTS[0]

    def page(self):
        try:
            return max(1, int(self.params.get('page') or 1))
        except (TypeError, ValueError):
            return 1

    def fail_playback(self):
        kodigui.notify(kodigui.tr(30009), icon=xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.setResolvedUrl(self.handle, False, xbmcgui.ListItem(offscreen=True))

    # -- Ansichten --------------------------------------------------
    def run(self):
        view = getattr(self, 'view_' + self.mode, None)
        if callable(view):
            view()
        else:
            self.view_root()

    def view_root(self):
        """Hauptmenü wie beim Original: Suche oben, dann die Quellen direkt."""
        handle = self.handle
        kodigui.add_folder(handle, self.url('search'), kodigui.tr(30002), plot=kodigui.tr(30014))
        kodigui.add_link(handle, self.url('random'), kodigui.tr(30005), plot=kodigui.tr(30015))
        for string_id, collection_id in COLLECTIONS:
            kodigui.add_folder(handle, self.url('collection', id=collection_id, page=1), kodigui.tr(string_id))
        kodigui.add_folder(handle, self.url('downloads'), kodigui.tr(30031))
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
            context = [(
                kodigui.tr(30033),
                'RunPlugin(%s)' % self.url('download', id=identifier),
            )]
            kodigui.add_link(
                handle,
                self.url('play', id=identifier),
                title,
                IMG_URL + urllib.parse.quote(identifier),
                context=context,
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
        if hasattr(xbmcplugin, 'addSortMethod'):
            xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_VIDEO_TITLE)
            xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
        kodigui.end(handle, content='videos')

    def view_play(self):
        identifier = self.params.get('id') or ''
        item = self.archive.item(identifier) if identifier else None
        sources = (item or {}).get('sources') or []
        if not item or not sources:
            self.fail_playback()
            return

        chosen = sources[0]
        if len(sources) > 1 and self.int_setting('quality_mode', 0) == 1:
            labels = [source_label(source) for source in sources]
            index = xbmcgui.Dialog().select(kodigui.tr(30030), labels)
            if index < 0:
                self.fail_playback()
                return
            chosen = sources[index]

        play_item = xbmcgui.ListItem(label=item['title'], offscreen=True)
        play_item.setPath(chosen['url'])
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
        kodigui.apply_info(play_item, info)
        kodigui.allow_content_lookup(play_item)
        mimetype = mime_type(chosen['url'])
        if mimetype and hasattr(play_item, 'setMimeType'):
            play_item.setMimeType(mimetype)
        xbmcplugin.setResolvedUrl(self.handle, True, play_item)

    def view_random(self):
        doc = self.archive.random_movie(self.rows())
        if not doc or not doc.get('identifier'):
            kodigui.notify(kodigui.tr(30007))
            xbmcplugin.setResolvedUrl(self.handle, False, xbmcgui.ListItem(offscreen=True))
            return
        self.params['id'] = doc['identifier']
        self.view_play()

    def view_download(self):
        """Kontextmenü-Aktion: Film in den Download-Ordner laden."""
        identifier = self.params.get('id') or ''
        item = self.archive.item(identifier) if identifier else None
        sources = (item or {}).get('sources') or []
        if not item or not sources:
            kodigui.notify(kodigui.tr(30009), icon=xbmcgui.NOTIFICATION_ERROR)
            return
        downloads = Downloads()
        if not downloads.folder:
            kodigui.notify(kodigui.tr(30039))
            return
        index = 0
        if len(sources) > 1:
            index = xbmcgui.Dialog().select(kodigui.tr(30030), [source_label(s) for s in sources])
            if index < 0:
                return
        target = downloads.path_for(item, sources[index])
        ok, message_id = downloads.save(item, sources[index], target)
        kodigui.notify(
            kodigui.tr(message_id),
            icon=xbmcgui.NOTIFICATION_INFO if ok else xbmcgui.NOTIFICATION_ERROR,
        )

    def view_downloads(self):
        handle = self.handle
        downloads = Downloads()
        if not downloads.folder:
            kodigui.notify(kodigui.tr(30039))
            kodigui.add_folder(handle, self.settings_url, kodigui.tr(30013), folder=False)
            kodigui.end(handle, content='files', succeeded=False, cache=False)
            return
        entries = downloads.items()
        if not entries:
            kodigui.notify(kodigui.tr(30007))
        for entry in entries:
            context = [(
                kodigui.tr(30037),
                'RunPlugin(%s)' % self.url('delete', path=entry['path']),
            )]
            kodigui.add_file(
                handle,
                entry['path'],
                entry['label'],
                context=context,
                plot=entry['plot'],
                year=entry['year'],
                duration=entry['duration'],
            )
        kodigui.end(handle, content='movies', cache=False)

    def view_delete(self):
        path = self.params.get('path') or ''
        if not path:
            return
        if xbmcgui.Dialog().yesno(kodigui.tr(30037), kodigui.tr(30038), path):
            Downloads().delete(path)
            kodigui.notify(kodigui.tr(30041))
            xbmc.executebuiltin('Container.Refresh')

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
