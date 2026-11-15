# -*- coding: utf-8 -*-
"""Ansichten des NASA-Add-ons."""

import sys
import urllib.parse

import xbmcgui
import xbmcplugin

from . import ui
from .api import PER_PAGE, TOPICS, Nasa, clean_text


class Router(object):
    def __init__(self):
        self.handle = int(sys.argv[1])
        self.base = sys.argv[0]
        raw = sys.argv[2][1:] if len(sys.argv) > 2 else ''
        self.params = dict(urllib.parse.parse_qsl(raw))
        self.mode = self.params.get('mode') or 'root'
        self.api = Nasa()

    def url(self, mode='root', **params):
        params['mode'] = mode
        return '%s?%s' % (self.base, urllib.parse.urlencode(params))

    def page(self):
        try:
            return max(1, int(self.params.get('page') or 1))
        except (TypeError, ValueError):
            return 1

    def run(self):
        view = getattr(self, 'view_' + self.mode, None)
        if callable(view):
            view()
        else:
            self.view_root()

    def view_root(self):
        handle = self.handle
        ui.add_folder(handle, self.url('search'), ui.tr(30101))
        for index, (label, query) in enumerate(TOPICS):
            ui.add_folder(handle, self.url('topic', id=str(index), page=1), label)
        ui.end(handle, content='files', cache=False)

    def view_topic(self):
        try:
            index = int(self.params.get('id') or 0)
        except (TypeError, ValueError):
            index = 0
        index = min(max(index, 0), len(TOPICS) - 1)
        label, query = TOPICS[index]
        items, total = self.api.search(query, self.page())
        self.list_videos(items, total, 'topic', id=str(index))

    def view_search(self):
        term = (self.params.get('q') or '').strip()
        if not term:
            term = (xbmcgui.Dialog().input(ui.tr(30102), type=xbmcgui.INPUT_ALPHANUM) or '').strip()
            if not term:
                ui.end(self.handle, succeeded=False, cache=False)
                return
        items, total = self.api.search(term, self.page())
        self.list_videos(items, total, 'search', q=term)

    def list_videos(self, items, total, mode, **params):
        handle = self.handle
        for item in items:
            if not item.get('id'):
                continue
            ui.add_link(
                handle,
                self.url('play', id=item['id'], title=item['title'], thumb=item.get('thumb') or ''),
                item['title'] or item['id'],
                item.get('thumb'),
                title=item['title'],
                year=item.get('year') or 0,
                plot=item.get('plot', ''),
                mediatype='movie',
            )
        if not items:
            ui.notify(ui.tr(30103))
        if total > self.page() * PER_PAGE:
            page_params = dict(params, page=self.page() + 1)
            ui.add_folder(handle, self.url(mode, **page_params), ui.tr(30104))
        ui.end(handle, content='videos')

    def view_play(self):
        identifier = self.params.get('id') or ''
        url = self.api.playback_url(identifier)
        if not url:
            ui.notify(ui.tr(30105), icon=xbmcgui.NOTIFICATION_ERROR)
            xbmcplugin.setResolvedUrl(self.handle, False, xbmcgui.ListItem(offscreen=True))
            return
        title = clean_text(self.params.get('title'), 200) or identifier
        thumb = self.params.get('thumb') or ''
        item = xbmcgui.ListItem(label=title, offscreen=True)
        item.setPath(url)
        item.setArt(ui.art(thumb if thumb.startswith('https://') else None))
        ui.apply_info(item, {'title': title, 'mediatype': 'movie'})
        ui.allow_content_lookup(item)
        if hasattr(item, 'setMimeType'):
            item.setMimeType('video/mp4')
        xbmcplugin.setResolvedUrl(self.handle, True, item)
