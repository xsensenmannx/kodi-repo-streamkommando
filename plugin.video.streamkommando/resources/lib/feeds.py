# -*- coding: utf-8 -*-
"""Eigene Sammlungen: IA-Collections und Commons-Kategorien aus den Einstellungen."""

import re

import xbmcaddon

IA_PATTERN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$')
COMMONS_PATTERN = re.compile(r'^[^<>\[\]{}|\x00-\x1f]{1,120}$')


def _split(value):
    return [part.strip() for part in re.split(r'[,\n;]+', str(value or '')) if part.strip()]


def normalize_ia(value):
    candidate = str(value or '').strip()
    if candidate.lower().startswith('collection:'):
        candidate = candidate[len('collection:'):].strip()
    return candidate if IA_PATTERN.match(candidate) else ''


def normalize_commons(value):
    candidate = str(value or '').strip()
    if candidate.lower().startswith('category:'):
        candidate = candidate[len('category:'):].strip()
    candidate = re.sub(r'\s+', ' ', candidate.replace('_', ' ')).strip()
    return candidate if COMMONS_PATTERN.match(candidate) else ''


def _unique(values):
    seen = set()
    result = []
    for value in values:
        key = value.lower()
        if value and key not in seen:
            seen.add(key)
            result.append(value)
    return result


def parse_ia(value):
    return _unique([normalize_ia(item) for item in _split(value)])


def parse_commons(value):
    return _unique([normalize_commons(item) for item in _split(value)])


class Feeds(object):
    """Konfigurierte Sammlungen aus den Add-on-Einstellungen."""

    def __init__(self):
        addon = xbmcaddon.Addon()
        self.ia = parse_ia(addon.getSetting('custom_ia_collections'))
        self.commons = parse_commons(addon.getSetting('custom_commons_categories'))

    def entries(self):
        rows = [{'kind': 'ia', 'id': identifier,
                 'label': 'Internet Archive: %s' % identifier} for identifier in self.ia]
        rows.extend({'kind': 'commons', 'id': name,
                     'label': 'Commons: %s' % name} for name in self.commons)
        return rows

    def __len__(self):
        return len(self.ia) + len(self.commons)
