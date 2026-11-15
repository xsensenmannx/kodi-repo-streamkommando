# -*- coding: utf-8 -*-
"""Untertitel aus dem Internet Archive und Wikimedia Commons.

Kodi kann Untertitel bei Plugin-Wiedergabe nur als lokale Dateien sicher laden,
deshalb werden die Spuren vor dem Start heruntergeladen und über
``ListItem.setSubtitles`` angehängt.
"""

import hashlib
import os
import re
import urllib.parse
import urllib.request

import xbmc
import xbmcaddon
import xbmcvfs

USER_AGENT = 'StreamKommando/1.9 (Kodi Add-on; +https://github.com/xsensenmannx/kodi-repo-streamkommando)'
COMMONS_API = 'https://commons.wikimedia.org/w/api.php'
FILE_SUFFIXES = ('.srt', '.vtt', '.ass', '.ssa')
MAX_TRACKS = 3
MAX_SIZE = 5 * 1024 * 1024
TIMEOUT = 15

# ISO 639-1 plus gängige 639-2-Codes; verhindert, dass Wörter wie "is" als Sprache gelten.
LANGUAGES = set('''
af am ar as az ba be bg bn bo br bs ca co cs cy da de el en eo es et eu fa fi fil fo fr fy ga gd gl gu ha he hi hr hu hy id is it
ja jv ka kk km kn ko ku ky la lb lo lt lv mg mi mk ml mn mr ms mt my nb ne nl nn no oc pa pl ps pt ro ru sa sco sd si sk sl so sq sr
su sv sw ta te tg th tk tl tr tt ug uk ur uz vi wo xh yi yo zh zu
'''.split())
ALIASES = {
    'eng': 'en', 'deu': 'de', 'ger': 'de', 'fra': 'fr', 'fre': 'fr', 'spa': 'es', 'ita': 'it',
    'nld': 'nl', 'dut': 'nl', 'por': 'pt', 'rus': 'ru', 'pol': 'pl', 'tur': 'tr', 'jpn': 'ja',
    'zho': 'zh', 'chi': 'zh', 'kor': 'ko', 'ara': 'ar', 'hin': 'hi', 'swe': 'sv', 'dan': 'da',
    'nor': 'no', 'fin': 'fi', 'ces': 'cs', 'cze': 'cs', 'ell': 'el', 'gre': 'el', 'heb': 'he',
    'hun': 'hu', 'ukr': 'uk', 'ron': 'ro', 'rum': 'ro', 'bul': 'bg', 'hrv': 'hr', 'srp': 'sr',
    'slk': 'sk', 'slo': 'sk', 'slv': 'sl', 'lit': 'lt', 'lav': 'lv', 'est': 'et', 'cat': 'ca',
    'glg': 'gl', 'eus': 'eu', 'baq': 'eu', 'isl': 'is', 'ice': 'is', 'ind': 'id', 'vie': 'vi',
    'tha': 'th', 'fas': 'fa', 'per': 'fa', 'urd': 'ur', 'ben': 'bn', 'tam': 'ta', 'tel': 'te',
    'mal': 'ml', 'kan': 'kn', 'mar': 'mr', 'guj': 'gu', 'pan': 'pa', 'nep': 'ne', 'sin': 'si',
    'khm': 'km', 'lao': 'lo', 'mya': 'my', 'bur': 'my', 'kat': 'ka', 'geo': 'ka', 'hye': 'hy',
    'arm': 'hy', 'aze': 'az', 'kaz': 'kk', 'uzb': 'uz', 'mon': 'mn', 'amh': 'am', 'swa': 'sw',
    'zul': 'zu', 'afr': 'af', 'msa': 'ms', 'may': 'ms', 'und': 'und', 'mul': 'mul',
}
LANGUAGE_NAMES = {
    'english': 'en', 'eng': 'en', 'german': 'de', 'deutsch': 'de', 'ger': 'de', 'deu': 'de',
    'french': 'fr', 'francais': 'fr', 'français': 'fr', 'spanish': 'es', 'espanol': 'es',
    'español': 'es', 'italian': 'it', 'portuguese': 'pt', 'russian': 'ru', 'dutch': 'nl',
    'polish': 'pl', 'turkish': 'tr', 'japanese': 'ja', 'chinese': 'zh', 'korean': 'ko',
    'arabic': 'ar', 'hindi': 'hi', 'swedish': 'sv', 'danish': 'da', 'norwegian': 'no',
    'finnish': 'fi', 'czech': 'cs', 'greek': 'el', 'hebrew': 'he', 'hungarian': 'hu',
    'ukrainian': 'uk', 'romanian': 'ro', 'bulgarian': 'bg', 'croatian': 'hr', 'serbian': 'sr',
}


def _normalize(code):
    code = str(code or '').strip().lower().replace('_', '-')
    if not code:
        return ''
    base = code.split('-', 1)[0]
    if code in ALIASES:
        return ALIASES[code]
    if base in ALIASES:
        return ALIASES[base]
    if base in LANGUAGES:
        return base
    if code in LANGUAGES:
        return code
    return ''


def language_code(value):
    """Sprache aus IA-Metadaten ('English', 'eng', ['de']) als Kürzel."""
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ''
    text = str(value or '').strip().lower()
    if not text:
        return ''
    if text in LANGUAGE_NAMES:
        return LANGUAGE_NAMES[text]
    return _normalize(text)


def language_from_name(name, default='und'):
    """Sprache aus dem Dateinamen, z. B. film.de.srt oder film_en.vtt."""
    stem = os.path.splitext(os.path.basename(str(name or '')))[0]
    tokens = [token for token in re.split(r'[._\- ]+', stem.lower()) if token]
    # Nur die letzten beiden Teile prüfen: "this_is_the_army" enthält sonst "is" (Isländisch).
    for token in reversed(tokens[-2:]):
        code = _normalize(token)
        if code:
            return code
    return default or 'und'


def archive_tracks(files, identifier, default_language='und'):
    """Untertiteldateien eines Internet-Archive-Items."""
    tracks = []
    for entry in files or []:
        name = str(entry.get('name') or '')
        lower = name.lower()
        extension = os.path.splitext(lower)[1]
        if extension not in FILE_SUFFIXES or '/thumbs/' in lower:
            continue
        if lower.startswith('__ia_thumb') or 'thumb' in lower:
            continue
        if str(entry.get('private') or '').lower() in ('true', '1'):
            continue
        try:
            size = int(entry.get('size') or 0)
        except (TypeError, ValueError):
            size = 0
        if size > MAX_SIZE:
            continue
        tracks.append({
            'url': 'https://archive.org/download/%s/%s' % (
                urllib.parse.quote(identifier), urllib.parse.quote(name)),
            'language': language_from_name(name, default_language),
            'label': os.path.basename(name),
            'ext': extension,
        })
    return tracks


def commons_tracks(entries):
    """TimedText-Einträge der Commons-API in Untertitelspuren wandeln."""
    tracks = []
    for entry in entries or []:
        kind = str(entry.get('kind') or 'subtitles').lower()
        if kind not in ('subtitles', 'captions'):
            continue
        url = str(entry.get('src') or '')
        if not url.startswith('https://'):
            continue
        language = _normalize(entry.get('srclang')) or 'und'
        label = re.sub(r'[\u202a-\u202e\u2066-\u2069]', '', str(entry.get('label') or language)).strip()
        tracks.append({
            'url': url,
            'language': language,
            'label': label or language,
            'ext': '.vtt',
        })
    return tracks


def _open_json(url, timeout=TIMEOUT):
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        import json
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8', 'replace'))
    except (OSError, ValueError) as error:
        xbmc.log('Stream Kommando: Untertitel-Abfrage fehlgeschlagen (%s): %s' % (url, error),
                 xbmc.LOGWARNING)
        return None


def commons_tracks_for_title(title, cache=None):
    """Untertitelspuren für einen Commons-Dateititel ('File:...')."""
    title = str(title or '')
    if not title:
        return []
    key = 'timedtext:' + title
    if cache is not None:
        cached = cache.get(key)
        if isinstance(cached, list):
            return cached
    params = [
        ('action', 'query'),
        ('format', 'json'),
        ('formatversion', '2'),
        ('titles', title),
        ('prop', 'videoinfo'),
        ('viprop', 'timedtext'),
    ]
    payload = _open_json(COMMONS_API + '?' + urllib.parse.urlencode(params))
    if not payload:
        return []
    pages = (payload.get('query') or {}).get('pages') or []
    if not pages:
        return []
    info = (pages[0].get('videoinfo') or [{}])[0]
    tracks = commons_tracks(info.get('timedtext'))
    if cache is not None and tracks:
        cache.set(key, tracks)
    return tracks


def _fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        data = response.read(MAX_SIZE + 1)
    if len(data) > MAX_SIZE:
        raise ValueError('Untertiteldatei zu groß')
    return data


def _valid(data, extension):
    head = data[:4096].lower()
    if extension == '.vtt':
        return head.lstrip().startswith(b'webvtt')
    if extension == '.srt':
        return b'-->' in head
    if extension in ('.ass', '.ssa'):
        return b'[script info]' in head
    return False


def _folder():
    addon = xbmcaddon.Addon()
    folder = os.path.join(xbmcvfs.translatePath(addon.getAddonInfo('profile')), 'subtitles')
    if not os.path.isdir(folder):
        try:
            os.makedirs(folder)
        except OSError:
            return ''
    return folder


def _priority(track):
    language = track.get('language') or 'und'
    if language == 'de':
        return 0
    if language == 'en':
        return 1
    if language == 'und':
        return 2
    return 3


def prepare(tracks, limit=MAX_TRACKS):
    """Lädt die besten Spuren herunter und liefert lokale Dateipfade."""
    folder = _folder()
    if not folder:
        return []
    paths = []
    seen_languages = set()
    for track in sorted(tracks or [], key=_priority):
        url = track.get('url') or ''
        language = _normalize(track.get('language')) or 'und'
        extension = track.get('ext') or '.srt'
        if not url or language in seen_languages:
            continue
        seen_languages.add(language)
        name = 'sub-%s.%s%s' % (hashlib.md5(url.encode('utf-8')).hexdigest()[:12], language, extension)
        path = os.path.join(folder, name)
        if os.path.exists(path) and os.path.getsize(path) > 32:
            paths.append(path)
            if len(paths) >= limit:
                break
            continue
        try:
            data = _fetch(url)
            if not _valid(data, extension):
                raise ValueError('kein gültiges Untertitelformat')
            with open(path, 'wb') as handle:
                handle.write(data)
        except (OSError, ValueError) as error:
            xbmc.log('Stream Kommando: Untertitel nicht ladbar (%s): %s' % (url, error), xbmc.LOGWARNING)
            continue
        paths.append(path)
        if len(paths) >= limit:
            break
    return paths


def attach(item, tracks):
    """Hängt Untertitelspuren an ein Kodi-ListItem; Fehler blockieren die Wiedergabe nicht."""
    if not tracks:
        return 0
    try:
        paths = prepare(tracks)
    except Exception as error:
        xbmc.log('Stream Kommando: Untertitel Vorbereitung fehlgeschlagen: %s' % error, xbmc.LOGWARNING)
        return 0
    if not paths:
        return 0
    setter = getattr(item, 'setSubtitles', None)
    if not callable(setter):
        return 0
    try:
        setter(paths)
        return len(paths)
    except Exception as error:
        xbmc.log('Stream Kommando: Untertitel konnten nicht gesetzt werden: %s' % error, xbmc.LOGWARNING)
        return 0
