# -*- coding: utf-8 -*-
"""Stream Kommando – Einstiegspunkt des Kodi-Plugins."""

import os
import sys
import traceback

import xbmc
import xbmcaddon
import xbmcgui

ADDON_PATH = os.path.dirname(os.path.abspath(__file__))
if ADDON_PATH not in sys.path:
    sys.path.insert(0, ADDON_PATH)

from resources.lib.router import Router  # noqa: E402


def main():
    """Startet das Add-on und meldet Fehler nachvollziehbar statt stumm."""
    try:
        Router().run()
    except SystemExit:
        # Nutzer hat den Dialog abgebrochen (z. B. Back-Taste) – kein Fehler.
        return
    except Exception:
        report = traceback.format_exc()
        xbmc.log('Stream Kommando: unerwarteter Fehler\n%s' % report, xbmc.LOGERROR)
        summary = report.strip().splitlines()[-1]
        addon = xbmcaddon.Addon()
        xbmcgui.Dialog().ok(
            addon.getAddonInfo('name'),
            '%s\n\n%s' % (addon.getLocalizedString(30047), summary),
        )


if __name__ == '__main__':
    main()
