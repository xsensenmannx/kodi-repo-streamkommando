#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Baut das Stream-Kommando-Kodi-Repository.

Packt jeden Addon-Ordner nach zips/<id>/<id>-<version>.zip, ersetzt
{{BASE_URL}} in der addon.xml des Repository-Addons und schreibt
addons.xml sowie addons.xml.md5 neu.
"""

import hashlib
import json
import os
import xml.etree.ElementTree as ElementTree
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(ROOT, 'repo.json')
BASE_URL_TOKEN = '{{BASE_URL}}'
SKIP_DIRS = {'.git', '.freebuff', '.idea', '.vscode', '__pycache__'}
SKIP_FILES = {'.DS_Store', 'Thumbs.db', 'desktop.ini'}
SKIP_SUFFIXES = ('.pyc', '.pyo', '.zip')


def load_config():
    with open(CONFIG_FILE, encoding='utf-8') as handle:
        config = json.load(handle)
    base_url = str(config.get('base_url', '')).strip().rstrip('/')
    if not base_url.startswith(('http://', 'https://')):
        raise SystemExit('repo.json: "base_url" muss eine http(s)-URL sein')
    config['base_url'] = base_url
    config['zip_dir'] = config.get('zip_dir') or 'zips'
    return config


def find_addons():
    addons = []
    for name in sorted(os.listdir(ROOT)):
        path = os.path.join(ROOT, name)
        if not os.path.isdir(path) or name.startswith('.') or name == 'zips':
            continue
        if os.path.isfile(os.path.join(path, 'addon.xml')):
            addons.append(path)
    return addons


def render_addon_xml(addon_dir, config):
    with open(os.path.join(addon_dir, 'addon.xml'), encoding='utf-8') as handle:
        return handle.read().replace(BASE_URL_TOKEN, config['base_url'])


def addon_info(text, source):
    root = ElementTree.fromstring(text)
    info = {key: root.get(key) for key in ('id', 'name', 'version', 'provider-name')}
    for key in ('id', 'version'):
        if not info.get(key):
            raise SystemExit('%s: addon.xml ohne "%s"' % (source, key))
    return info


def addon_files(addon_dir):
    for current, dirs, files in os.walk(addon_dir):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith('.'))
        for name in sorted(files):
            if name in SKIP_FILES or name.lower().endswith(SKIP_SUFFIXES):
                continue
            full = os.path.join(current, name)
            yield full, os.path.relpath(full, addon_dir).replace(os.sep, '/')


def build_zip(addon_dir, addon, addon_xml, zip_dir):
    target_dir = os.path.join(zip_dir, addon['id'])
    os.makedirs(target_dir, exist_ok=True)
    zip_name = '%s-%s.zip' % (addon['id'], addon['version'])
    zip_path = os.path.join(target_dir, zip_name)
    for existing in os.listdir(target_dir):
        if existing.lower().endswith('.zip') and existing != zip_name:
            os.remove(os.path.join(target_dir, existing))
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for full, relative in addon_files(addon_dir):
            if relative == 'addon.xml':
                archive.writestr('%s/addon.xml' % addon['id'], addon_xml.encode('utf-8'))
            else:
                archive.write(full, '%s/%s' % (addon['id'], relative))
    return zip_path


def write_addons_xml(entries, target):
    parts = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', '<addons>']
    for addon_xml in entries:
        parts.append(addon_xml.split('?>', 1)[-1].strip())
    parts.append('</addons>')
    content = '\n'.join(parts) + '\n'
    with open(target, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(content)
    return content.encode('utf-8')


def main():
    config = load_config()
    zip_dir = os.path.join(ROOT, config['zip_dir'])
    addons = find_addons()
    if not addons:
        raise SystemExit('Keine Addon-Ordner mit addon.xml gefunden')

    print('Repository: %s' % config['base_url'])
    entries = []
    for addon_dir in addons:
        addon_xml = render_addon_xml(addon_dir, config)
        info = addon_info(addon_xml, addon_dir)
        zip_path = build_zip(addon_dir, info, addon_xml, zip_dir)
        entries.append(addon_xml)
        print('  %-32s %-8s %s' % (info['id'], info['version'], os.path.relpath(zip_path, ROOT)))

    data = write_addons_xml(entries, os.path.join(ROOT, 'addons.xml'))
    digest = hashlib.md5(data).hexdigest()
    with open(os.path.join(ROOT, 'addons.xml.md5'), 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(digest)
    print('addons.xml + addons.xml.md5 (%s)' % digest)


if __name__ == '__main__':
    main()
