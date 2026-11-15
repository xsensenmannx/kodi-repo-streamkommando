# -*- coding: utf-8 -*-
"""Alle Ansichten des Plugins."""

import os
import sys
import urllib.parse

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from . import kodigui
from . import subtitles
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
from .downloads import VIDEO_SUFFIXES, Downloads
from .feeds import Feeds, normalize_commons, normalize_ia
from .history import History, format_position
from .library import LibraryExport
from .providers import Providers
from .streams import Streams
from .watchlist import Watchlist

SOURCE_LIMIT = 24


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
        self.providers = Providers(only_licensed=self.bool_setting('only_licensed'))
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
        """Hauptmenü: globale Suche, dann die Quellen direkt."""
        handle = self.handle
        kodigui.add_folder(handle, self.url('search'), kodigui.tr(30002), plot=kodigui.tr(30043))
        kodigui.add_link(handle, self.url('random'), kodigui.tr(30005), plot=kodigui.tr(30015))
        for string_id, collection_id in COLLECTIONS:
            kodigui.add_folder(handle, self.url('collection', id=collection_id, page=1), kodigui.tr(string_id))
        kodigui.add_folder(handle, self.url('source', key='blender', page=1), kodigui.tr(30044), plot=kodigui.tr(30045))
        kodigui.add_folder(handle, self.url('feeds'), kodigui.tr(30068), plot=kodigui.tr(30072))
        kodigui.add_folder(handle, self.url('watchlist'), kodigui.tr(30050), plot=kodigui.tr(30051))
        kodigui.add_folder(handle, self.url('history'), kodigui.tr(30054), plot=kodigui.tr(30058))
        kodigui.add_folder(handle, self.url('downloads'), kodigui.tr(30031))
        kodigui.add_folder(handle, self.url('libraryexport'), kodigui.tr(30063),
                            plot=kodigui.tr(30064), folder=False)
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

    # -- Eigene Sammlungen -----------------------------------------
    def view_feeds(self):
        handle = self.handle
        feeds = Feeds()
        entries = feeds.entries()
        if not entries:
            kodigui.notify(kodigui.tr(30071))
            self.addon.openSettings()
            kodigui.end(handle, succeeded=False, cache=False)
            return
        for entry in entries:
            kodigui.add_folder(
                handle,
                self.url('feed', kind=entry['kind'], id=entry['id']),
                entry['label'],
                plot=kodigui.tr(30072),
            )
        kodigui.end(handle, content='files', cache=False)

    def view_feed(self):
        kind = self.params.get('kind') or ''
        identifier = self.params.get('id') or ''
        if kind == 'ia':
            identifier = normalize_ia(identifier)
            if not identifier:
                kodigui.notify(kodigui.tr(30007), icon=xbmcgui.NOTIFICATION_ERROR)
                kodigui.end(self.handle, succeeded=False, cache=False)
                return
            docs, total = self.archive.collection(identifier, self.page(), self.rows(), self.sort())
            if self.archive.error and not docs:
                kodigui.notify(kodigui.tr(30046), icon=xbmcgui.NOTIFICATION_ERROR)
                kodigui.end(self.handle, succeeded=False, cache=False)
                return
            self.list_movies(docs, total, 'feed', kind='ia', id=identifier)
            return
        if kind == 'commons':
            name = normalize_commons(identifier)
            provider = self.providers.by_key('commons')
            if not name or provider is None:
                kodigui.notify(kodigui.tr(30007), icon=xbmcgui.NOTIFICATION_ERROR)
                kodigui.end(self.handle, succeeded=False, cache=False)
                return
            items, _more = provider.category(name, 50)
            if provider.error and not items:
                kodigui.notify(kodigui.tr(30046), icon=xbmcgui.NOTIFICATION_ERROR)
                kodigui.end(self.handle, succeeded=False, cache=False)
                return
            self.add_source_items(items, 'commons')
            if not items:
                kodigui.notify(kodigui.tr(30007))
            kodigui.end(self.handle, content='videos')
            return
        kodigui.notify(kodigui.tr(30007), icon=xbmcgui.NOTIFICATION_ERROR)
        kodigui.end(self.handle, succeeded=False, cache=False)

    # -- Globale Suche ---------------------------------------------
    def view_search(self):
        term = (self.params.get('q') or '').strip()
        if not term:
            term = (xbmcgui.Dialog().input(kodigui.tr(30008), type=xbmcgui.INPUT_ALPHANUM) or '').strip()
            if not term:
                kodigui.end(self.handle, succeeded=False, cache=False)
                return
        handle = self.handle
        for provider in self.providers.all():
            items, total, _more = provider.search(term, 1, 12, self.sort())
            count = total or len(items)
            if count == 0 and not getattr(provider, 'always_list', True):
                continue
            label = '%s · %d' % (kodigui.tr(provider.label_id), count)
            kodigui.add_folder(handle, self.url('source', key=provider.key, q=term, page=1), label)
        kodigui.end(handle, content='files', cache=False)

    def view_source(self):
        key = self.params.get('key') or ''
        term = (self.params.get('q') or '').strip()
        provider = self.providers.by_key(key)
        if provider is None or (not term and not getattr(provider, 'browse_all', False)):
            kodigui.notify(kodigui.tr(30007), icon=xbmcgui.NOTIFICATION_ERROR)
            kodigui.end(self.handle, succeeded=False, cache=False)
            return
        items, total, more = provider.search(term, self.page(), SOURCE_LIMIT, self.sort())
        handle = self.handle
        self.add_source_items(items, key)
        if not items:
            if getattr(provider, 'error', False):
                kodigui.notify(kodigui.tr(30046), icon=xbmcgui.NOTIFICATION_ERROR)
            else:
                kodigui.notify(kodigui.tr(30007))
        if more or total > self.page() * SOURCE_LIMIT:
            kodigui.add_folder(
                handle,
                self.url('source', key=key, q=term, page=self.page() + 1),
                kodigui.tr(30006),
            )
        kodigui.end(handle, content='videos')

    def add_source_items(self, items, key):
        """NASA-/Commons-Treffer mit Download- und Merklisten-Kontext anhängen."""
        saved_keys = Watchlist().keys()
        for item in items:
            identifier = item.get('id') or ''
            saved = Watchlist.key(key, identifier) in saved_keys
            context = [
                (
                    kodigui.tr(30033),
                    'RunPlugin(%s)' % self.url(
                        'sourcedownload',
                        key=key,
                        id=identifier,
                        src=item.get('url') or '',
                        title=item.get('title') or '',
                        year=item.get('year') or 0,
                        plot=item.get('plot') or '',
                    ),
                ),
                (
                    kodigui.tr(30049 if saved else 30048),
                    'RunPlugin(%s)' % self.url(
                        'watchlisttoggle',
                        provider=key,
                        id=identifier,
                        src=item.get('url') or '',
                        title=item.get('title') or '',
                        year=item.get('year') or 0,
                        plot=item.get('plot') or '',
                        thumb=item.get('thumb') or '',
                    ),
                ),
            ]
            kodigui.add_link(
                self.handle,
                self.url(
                    'sourceplay',
                    key=key,
                    id=item.get('id') or '',
                    src=item.get('url') or '',
                    title=item.get('title') or '',
                    plot=item.get('plot') or '',
                    thumb=item.get('thumb') or '',
                ),
                item.get('title') or item.get('id'),
                item.get('thumb'),
                context=context,
                title=item.get('title'),
                year=item.get('year') or 0,
                plot=item.get('plot') or '',
                mediatype='movie',
            )

    def view_sourcedownload(self):
        """Kontextmenü-Aktion: NASA- oder Commons-Treffer herunterladen."""
        key = self.params.get('key') or ''
        provider = self.providers.by_key(key)
        url = provider.play_url(self.params) if provider else ''
        if not url:
            kodigui.notify(kodigui.tr(30009), icon=xbmcgui.NOTIFICATION_ERROR)
            return
        downloads = Downloads()
        if not downloads.folder:
            kodigui.notify(kodigui.tr(30039))
            return
        title = clean_text(self.params.get('title'), 200) or 'Video'
        try:
            year = int(self.params.get('year') or 0)
        except (TypeError, ValueError):
            year = 0
        item = {
            'title': title,
            'year': year,
            'plot': clean_text(self.params.get('plot'), 600),
            'creator': '',
            'duration': 0,
        }
        suffix = os.path.splitext(urllib.parse.urlparse(url).path)[1].lower()
        if suffix not in VIDEO_SUFFIXES:
            suffix = '.mp4'
        source = {'url': url, 'size': 0, 'format': suffix.lstrip('.').upper()}
        target = downloads.path_for(item, source)
        ok, message_id = downloads.save(item, source, target)
        icon = xbmcgui.NOTIFICATION_INFO if ok else xbmcgui.NOTIFICATION_ERROR
        kodigui.notify(kodigui.tr(message_id), icon=icon)

    # -- Merkliste --------------------------------------------------
    def view_watchlist(self):
        handle = self.handle
        entries = Watchlist().entries()
        if not entries:
            kodigui.notify(kodigui.tr(30007))
        for entry in entries:
            context = [(
                kodigui.tr(30049),
                'RunPlugin(%s)' % self.url(
                    'watchlistremove',
                    provider=entry.get('provider') or '',
                    id=entry.get('id') or '',
                ),
            )]
            kodigui.add_link(
                handle,
                self.url(
                    'watchlistplay',
                    provider=entry.get('provider') or '',
                    id=entry.get('id') or '',
                    src=entry.get('src') or '',
                    title=entry.get('title') or '',
                    plot=entry.get('plot') or '',
                    thumb=entry.get('thumb') or '',
                ),
                entry.get('title') or entry.get('id'),
                entry.get('thumb'),
                context=context,
                title=entry.get('title') or entry.get('id'),
                year=entry.get('year') or 0,
                plot=entry.get('plot') or '',
                mediatype='movie',
            )
        kodigui.end(handle, content='videos', cache=False)

    def view_watchlistplay(self):
        provider = self.params.get('provider') or ''
        if provider in ('', 'archive'):
            self.view_play()
            return
        self.params['key'] = provider
        self.view_sourceplay()

    def view_history(self):
        handle = self.handle
        entries = History().entries()
        if not entries:
            kodigui.notify(kodigui.tr(30007))
        for entry in entries:
            position = entry.get('position') or 0
            plot = entry.get('plot') or ''
            resume = '%s %s' % (kodigui.tr(30056), format_position(position)) if position else kodigui.tr(30059)
            if plot:
                plot = '%s · %s' % (resume, plot)
            else:
                plot = resume
            context = [(
                kodigui.tr(30057),
                'RunPlugin(%s)' % self.url(
                    'historyremove',
                    provider=entry.get('provider') or '',
                    id=entry.get('id') or '',
                ),
            )]
            kodigui.add_link(
                handle,
                self.url(
                    'historyplay',
                    provider=entry.get('provider') or '',
                    id=entry.get('id') or '',
                    src=entry.get('src') or '',
                    title=entry.get('title') or '',
                    plot=entry.get('plot') or '',
                    thumb=entry.get('thumb') or '',
                    year=entry.get('year') or 0,
                ),
                entry.get('title') or entry.get('id'),
                entry.get('thumb'),
                context=context,
                title=entry.get('title') or entry.get('id'),
                year=entry.get('year') or 0,
                plot=plot,
                mediatype='movie',
            )
        kodigui.end(handle, content='videos', cache=False)

    def view_historyplay(self):
        provider = self.params.get('provider') or ''
        if provider in ('', 'archive'):
            self.view_play()
            return
        self.params['key'] = provider
        self.view_sourceplay()

    def view_historyremove(self):
        removed = History().remove(self.params.get('provider') or '', self.params.get('id') or '')
        if removed:
            kodigui.notify(kodigui.tr(30060))
        xbmc.executebuiltin('Container.Refresh')

    def view_watchlisttoggle(self):
        try:
            year = int(self.params.get('year') or 0)
        except (TypeError, ValueError):
            year = 0
        entry = {
            'provider': self.params.get('provider') or '',
            'id': self.params.get('id') or '',
            'src': self.params.get('src') or '',
            'title': clean_text(self.params.get('title'), 200),
            'plot': clean_text(self.params.get('plot'), 600),
            'thumb': self.params.get('thumb') or '',
            'year': year,
        }
        if not entry['id']:
            return
        added = Watchlist().toggle(entry)
        kodigui.notify(kodigui.tr(30052 if added else 30053))
        xbmc.executebuiltin('Container.Refresh')

    def view_watchlistremove(self):
        removed = Watchlist().remove(self.params.get('provider') or '', self.params.get('id') or '')
        if removed:
            kodigui.notify(kodigui.tr(30053))
        xbmc.executebuiltin('Container.Refresh')

    def view_sourceplay(self):
        key = self.params.get('key') or ''
        provider = self.providers.by_key(key)
        url = provider.play_url(self.params) if provider else ''
        if not url:
            self.fail_playback()
            return
        identifier = self.params.get('id') or self.params.get('src') or ''
        start_position = self.ask_resume(key, identifier)
        title = clean_text(self.params.get('title'), 200) or 'Stream Kommando'
        play_item = xbmcgui.ListItem(label=title, offscreen=True)
        play_item.setPath(url)
        thumb = self.params.get('thumb') or ''
        play_item.setArt(kodigui.art(thumb if thumb.startswith('https://') else None))
        kodigui.apply_info(play_item, {
            'title': title,
            'plot': clean_text(self.params.get('plot'), 600),
            'mediatype': 'movie',
        })
        kodigui.allow_content_lookup(play_item)
        mimetype = mime_type(url)
        if mimetype and hasattr(play_item, 'setMimeType'):
            play_item.setMimeType(mimetype)
        try:
            tracks = provider.subtitles(self.params) if hasattr(provider, 'subtitles') else []
        except Exception as error:
            xbmc.log('Stream Kommando: Untertitelquelle fehlgeschlagen: %s' % error, xbmc.LOGWARNING)
            tracks = []
        subtitles.attach(play_item, tracks)
        xbmcplugin.setResolvedUrl(self.handle, True, play_item)
        self.track_playback(key, identifier, url, {
            'title': title,
            'plot': clean_text(self.params.get('plot'), 600),
            'thumb': thumb if thumb.startswith('https://') else '',
            'year': self.params.get('year') or 0,
        }, start_position)

    # -- Filmarchiv -------------------------------------------------
    def list_movies(self, docs, total, mode, **params):
        handle = self.handle
        saved_ids = {row.get('id') for row in Watchlist().entries() if row.get('provider') == 'archive'}
        for doc in docs:
            identifier = doc.get('identifier')
            if not identifier:
                continue
            title = clean_text(doc.get('title'), 200) or identifier
            context = [
                (
                    kodigui.tr(30033),
                    'RunPlugin(%s)' % self.url('download', id=identifier),
                ),
                (
                    kodigui.tr(30049 if identifier in saved_ids else 30048),
                    'RunPlugin(%s)' % self.url(
                        'watchlisttoggle',
                        provider='archive',
                        id=identifier,
                        src='',
                        title=title,
                        plot=clean_text(doc.get('description'), 600),
                        thumb=IMG_URL + urllib.parse.quote(identifier),
                        year=to_year(doc.get('year')),
                    ),
                ),
            ]
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

    def ask_resume(self, provider, identifier):
        """Fragt nach dem Fortsetzen und liefert die Startposition in Sekunden."""
        position = History().position(provider, identifier)
        if position < 30:
            return 0
        question = '%s %s' % (kodigui.tr(30056), format_position(position))
        if xbmcgui.Dialog().yesno(kodigui.tr(30055), question):
            return position
        History().reset_position(provider, identifier)
        return 0

    def track_playback(self, provider, identifier, url, meta, start_position=0):
        """Hält die Wiedergabeposition im Verlauf fest, solange der Player läuft."""
        history = History()
        entry = dict(meta)
        entry.update({'provider': provider, 'id': identifier, 'src': url})
        history.touch(entry)
        player = xbmc.Player()
        for _step in range(10):
            try:
                if player.isPlaying():
                    break
            except Exception:
                return
            xbmc.sleep(200)
        if start_position:
            try:
                player.seekTime(start_position)
            except Exception:
                pass
        while True:
            try:
                if not player.isPlaying():
                    break
                position = player.getTime()
                total = player.getTotalTime()
            except Exception:
                break
            history.update_position(provider, identifier, position, total)
            xbmc.sleep(5000)

    def view_play(self):
        identifier = self.params.get('id') or ''
        item = self.archive.item(identifier) if identifier else None
        sources = (item or {}).get('sources') or []
        if not item or not sources:
            self.fail_playback()
            return

        start_position = self.ask_resume('archive', identifier)
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
        subtitles.attach(play_item, item.get('subtitles') or [])
        xbmcplugin.setResolvedUrl(self.handle, True, play_item)
        self.track_playback('archive', identifier, chosen['url'], {
            'title': item['title'],
            'plot': item.get('plot', ''),
            'thumb': IMG_URL + urllib.parse.quote(identifier),
            'year': item.get('year') or 0,
        }, start_position)

    def view_random(self):
        doc = self.archive.random_movie(self.rows())
        if not doc or not doc.get('identifier'):
            kodigui.notify(kodigui.tr(30007))
            xbmcplugin.setResolvedUrl(self.handle, False, xbmcgui.ListItem(offscreen=True))
            return
        self.params['id'] = doc['identifier']
        self.view_play()

    # -- Downloads --------------------------------------------------
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

    def view_libraryexport(self):
        """Merkliste und Downloads als .strm + .nfo exportieren und die Bibliothek aktualisieren."""
        exporter = LibraryExport()
        if not exporter.folder:
            # Ohne Ordner direkt die Einstellungen öffnen, damit er gleich gesetzt werden kann.
            self.addon.openSettings()
            kodigui.end(self.handle, succeeded=False, cache=False)
            return
        count = exporter.export()
        if count:
            kodigui.notify('%s: %d' % (kodigui.tr(30066), count))
            xbmc.executebuiltin('UpdateLibrary(video)')
        else:
            kodigui.notify(kodigui.tr(30067))
        kodigui.end(self.handle, succeeded=False, cache=False)

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
