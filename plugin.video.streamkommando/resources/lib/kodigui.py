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


def add_folder(handle, url, label, image=None, plot='', folder=True):
    item = xbmcgui.ListItem(label=label, offscreen=True)
    item.setArt(art(image))
    if plot:
        item.setInfo('video', {'plot': plot})
    xbmcplugin.addDirectoryItem(handle, url, item, folder)


def add_link(handle, url, label, image=None, **info):
    item = xbmcgui.ListItem(label=label, offscreen=True)
    item.setArt(art(image))
    if info:
        item.setInfo('video', info)
    item.setProperty('IsPlayable', 'true')
    xbmcplugin.addDirectoryItem(handle, url, item, False)


def add_file(handle, path, label):
    item = xbmcgui.ListItem(label=label, offscreen=True)
    item.setArt(art())
    item.setInfo('video', {'title': label})
    item.setPath(path)
    xbmcplugin.addDirectoryItem(handle, path, item, False)


def end(handle, content='videos', succeeded=True, cache=True):
    xbmcplugin.setContent(handle, content)
    xbmcplugin.endOfDirectory(handle, succeeded=succeeded, cacheToDisc=cache)
