# -*- coding: utf-8 -*-
"""Stream Kommando: NASA – Einstiegspunkt."""

import os
import sys

ADDON_PATH = os.path.dirname(os.path.abspath(__file__))
if ADDON_PATH not in sys.path:
    sys.path.insert(0, ADDON_PATH)

from resources.lib.router import Router  # noqa: E402


if __name__ == '__main__':
    Router().run()
