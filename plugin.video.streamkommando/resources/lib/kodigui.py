# -*- coding: utf-8 -*-
"""Dünne Hülle um xbmcgui/xbmcplugin."""

import os

import xbmcaddon
import xbmcgui
import xbmcplugin

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')


def tr(string_id):
    return ADDON.getLocalizedString(string_id)


def notify(message, icon=xbmcgui.NOTIFICATION_INFO, heading=None, time=4000):
    xbmcgui.Dialog().notification(heading or ADDON.getAddonInfo('name'), message, icon, time)


def art(image=None):
    data = {
        'icon': os.path.join(ADDON_PATH, 'icon.png'),
        'fanart': os.path.join(ADDON_PATH, 'fanart.jpg'),
    }
    if image:
        data.update({'poster': image, 'thumb': image, 'landscape': image})
    return data


def apply_info(item, info):
    """Setzt InfoLabels über InfoTagVideo (Kodi 20+) mit Fallback auf setInfo."""
    tag = getattr(item, 'getVideoInfoTag', None)
    if tag is None:
        item.setInfo('video', info)
        return
    vtag = item.getVideoInfoTag()
    values = (
        ('setTitle', info.get('title')),
        ('setPlot', info.get('plot')),
        ('setYear', info.get('year') or None),
        ('setMediaType', info.get('mediatype')),
        ('setDuration', info.get('duration') or None),
        ('setStudios', [info['studio']] if info.get('studio') else None),
    )
    applied = 0
    for name, value in values:
        if value in (None, ''):
            continue
        setter = getattr(vtag, name, None)
        if not callable(setter):
            continue
        try:
            setter(value)
            applied += 1
        except Exception:
            pass
    if applied == 0:
        item.setInfo('video', info)


def allow_content_lookup(item):
    """Verhindert HEAD-Abfragen beim Öffnen der Liste (schneller, kein Timeout)."""
    setter = getattr(item, 'setContentLookup', None)
    if callable(setter):
        try:
            setter(False)
        except Exception:
            pass


def add_folder(handle, url, label, image=None, plot='', folder=True):
    item = xbmcgui.ListItem(label=label, offscreen=True)
    item.setArt(art(image))
    if plot:
        apply_info(item, {'plot': plot, 'mediatype': 'video'})
    xbmcplugin.addDirectoryItem(handle, url, item, folder)


def add_link(handle, url, label, image=None, **info):
    item = xbmcgui.ListItem(label=label, offscreen=True)
    item.setArt(art(image))
    if info:
        apply_info(item, info)
    item.setProperty('IsPlayable', 'true')
    allow_content_lookup(item)
    xbmcplugin.addDirectoryItem(handle, url, item, False)


def add_file(handle, path, label):
    item = xbmcgui.ListItem(label=label, offscreen=True)
    item.setArt(art())
    apply_info(item, {'title': label, 'mediatype': 'movie'})
    item.setPath(path)
    xbmcplugin.addDirectoryItem(handle, path, item, False)


def end(handle, content='videos', succeeded=True, cache=True):
    xbmcplugin.setContent(handle, content)
    xbmcplugin.endOfDirectory(handle, succeeded=succeeded, cacheToDisc=cache)
