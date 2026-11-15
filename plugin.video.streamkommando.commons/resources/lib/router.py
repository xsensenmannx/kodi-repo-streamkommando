# -*- coding: utf-8 -*-
"""Ansichten des Commons-Add-ons."""

import sys
import urllib.parse

import xbmcgui
import xbmcplugin

from . import ui
from .api import PER_PAGE, TOPICS, Commons, clean_text


class Router(object):
    def __init__(self):
        self.handle = int(sys.argv[1])
        self.base = sys.argv[0]
        raw = sys.argv[2][1:] if len(sys.argv) > 2 else ''
        self.params = dict(urllib.parse.parse_qsl(raw))
        self.mode = self.params.get('mode') or 'root'
        self.api = Commons()

    def url(self, mode='root', **params):
        params['mode'] = mode
        return '%s?%s' % (self.base, urllib.parse.urlencode(params))

    def offset(self):
        try:
            return max(0, int(self.params.get('offset') or 0))
        except (TypeError, ValueError):
            return 0

    def run(self):
        view = getattr(self, 'view_' + self.mode, None)
        if callable(view):
            view()
        else:
            self.view_root()

    def view_root(self):
        handle = self.handle
        ui.add_folder(handle, self.url('search'), ui.tr(30201))
        for index, (label, query) in enumerate(TOPICS):
            ui.add_folder(handle, self.url('topic', id=str(index)), label)
        ui.end(handle, content='files', cache=False)

    def view_topic(self):
        try:
            index = int(self.params.get('id') or 0)
        except (TypeError, ValueError):
            index = 0
        index = min(max(index, 0), len(TOPICS) - 1)
        label, query = TOPICS[index]
        items, more = self.api.search(query, self.offset())
        self.list_videos(items, more, 'topic', id=str(index))

    def view_search(self):
        term = (self.params.get('q') or '').strip()
        if not term:
            term = (xbmcgui.Dialog().input(ui.tr(30202), type=xbmcgui.INPUT_ALPHANUM) or '').strip()
            if not term:
                ui.end(self.handle, succeeded=False, cache=False)
                return
        items, more = self.api.search(term, self.offset())
        self.list_videos(items, more, 'search', q=term)

    def list_videos(self, items, more, mode, **params):
        handle = self.handle
        for item in items:
            if not item.get('url'):
                continue
            ui.add_link(
                handle,
                self.url('play', src=item['url'], title=item['title'], plot=item['plot']),
                item['title'],
                item.get('thumb'),
                title=item['title'],
                plot=item.get('plot', ''),
                mediatype='movie',
            )
        if not items:
            ui.notify(ui.tr(30203))
        if more:
            page_params = dict(params, offset=self.offset() + PER_PAGE)
            ui.add_folder(handle, self.url(mode, **page_params), ui.tr(30204))
        ui.end(handle, content='videos')

    def view_play(self):
        src = self.params.get('src') or ''
        if not src.startswith('https://'):
            ui.notify(ui.tr(30205), icon=xbmcgui.NOTIFICATION_ERROR)
            xbmcplugin.setResolvedUrl(self.handle, False, xbmcgui.ListItem(offscreen=True))
            return
        title = clean_text(self.params.get('title'), 200) or 'Wikimedia Commons'
        item = xbmcgui.ListItem(label=title, offscreen=True)
        item.setPath(src)
        item.setArt(ui.art())
        ui.apply_info(item, {'title': title, 'plot': clean_text(self.params.get('plot')), 'mediatype': 'movie'})
        ui.allow_content_lookup(item)
        if hasattr(item, 'setMimeType'):
            item.setMimeType('video/webm' if src.lower().endswith('.webm') else 'video/mp4')
        xbmcplugin.setResolvedUrl(self.handle, True, item)
