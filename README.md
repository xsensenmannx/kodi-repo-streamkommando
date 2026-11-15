# Stream Kommando – eigenes Kodi-Repository

Ein selbst gebautes Kodi-Repository mit drei Video-Add-ons unter einem
Repository-Add-on:

| Add-on | Inhalt |
| --- | --- |
| Stream Kommando | **Globale Suche** über Internet Archive, NASA und Wikimedia Commons, **Blender Open Movies** (7 CC-BY-Filme), 8 IA-Sammlungen, Zufallsfilm, Qualitätsauswahl, Download-Manager für alle Quellen, eigene `.strm`/`.m3u`-Quellen |
| Stream Kommando: NASA | **images.nasa.gov**: Apollo, Artemis, Mars, ISS, Space Shuttle, Erde aus dem All, Raketenstarts + Suche |
| Stream Kommando: Commons | **Wikimedia Commons**: freie Videos (WebM/VP9) mit Lizenz- und Autorangabe + Suche |

## Aufbau

```
repo.json                              Basis-URL des Repositories (vor dem Hosten anpassen)
build.py                               baut Zips + addons.xml + addons.xml.md5, legt die ZIPs in dist/ ab + index.html
web/index.html.tpl                     Vorlage der Landingpage
addons.xml / addons.xml.md5            Addon-Index (generiert)
zips/<addon-id>/<addon-id>-<version>.zip   Installationspakete (generiert)
repository.streamkommando/             Repository-Add-on
plugin.video.streamkommando/           Internet-Archive-Add-on
plugin.video.streamkommando.nasa/      NASA-Add-on
plugin.video.streamkommando.commons/   Wikimedia-Commons-Add-on
```

Jedes Add-on ist eigenständig (eigene `resources/lib`, eigene Sprachen), damit es
auch einzeln per ZIP installierbar bleibt.

## 1. Basis-URL eintragen

In `repo.json` steht die Adresse, unter der das Repository erreichbar ist – für dieses
Projekt bereits gesetzt:

```json
{
  "base_url": "https://xsensenmannx.github.io/kodi-repo-streamkommando"
}
```

Bei einem Fork oder anderer Domain hier anpassen und neu bauen – `build.py` ersetzt
`{{BASE_URL}}` in der `addon.xml` des Repository-Add-ons, in der Landingpage und
schreibt alle Dateien neu:

```
python build.py
```

## 2. Hosten (GitHub Pages)

Alles, was Kodi braucht, liegt danach im Projektordner:

```
index.html                                       Landingpage + klickbare ZIP-Links
addons.xml / addons.xml.md5                      Addon-Index + Änderungs-Token
zips/repository.streamkommando/…-1.1.0.zip
zips/plugin.video.streamkommando/…-1.1.0.zip
```

Für Kodi ist **GitHub Pages** der richtige Host: `raw.githubusercontent.com` liefert
keine Verzeichnisliste, dort kann man im Kodi-Dateimanager keine ZIP-Datei anklicken.
Einmalig einschalten unter **Settings → Pages → Deploy from a branch → `main` → `/ (root)`**.
Die Seite liegt danach unter der `base_url`; `index.html` verlinkt beide ZIPs relativ,
damit Kodi sie im Dateimanager anzeigt.

Nach jeder Änderung an einem Add-on: Version in der `addon.xml` erhöhen und
`python build.py` erneut ausführen, dann committen und pushen.

Hinweis: Pages cacht ca. 10 Minuten. Wenn Kodi ein Update nicht sofort sieht, ist das
der Grund – nicht ein fehlerhafter Build.

## 3. In Kodi installieren

1. **Einstellungen → Dateimanager → Quelle hinzufügen**, die Basis-URL eintragen.
2. **Add-ons → Aus ZIP-Datei installieren** → Quelle öffnen →
   `repository.streamkommando/repository.streamkommando-1.0.0.zip`.
3. **Add-ons → Aus Repository installieren → Stream Kommando Repository →
   Video-Add-ons → Stream Kommando**.

Ab dann laufen Aktualisierungen über das Repository. Ohne Hosting lässt sich das
Add-on auch direkt testen: `zips/plugin.video.streamkommando/…zip` per
**Aus ZIP-Datei installieren** einspielen.

## Bedienung

| Menüpunkt | Funktion |
| --- | --- |
| Sammlungen | Acht Quellen direkt im Hauptmenü (Spielfilme, Sci-Fi & Horror, Komödie, Stummfilm, Animation, Klassisches Fernsehen, Prelinger-Archiv, Kurzfilme), sortiert nach Downloads/Titel/Jahr, mit Blättern |
| Suche | Globale Suche über Internet Archive, NASA und Wikimedia Commons – Treffer je Quelle gruppiert, Wiedergabe in der besten verfügbaren Qualität |
| Blender Open Movies | Sieben freie Filme der Blender Foundation (CC-BY) als eigene Sammlung, mit Wiedergabe und Download |
| Meine Merkliste | Treffer aller Quellen lokal merken (Kontextmenü), direkt aus der Liste abspielen oder entfernen |
| Verlauf | Zuletzt gesehen mit Wiedergabeposition, Fortsetzen-Dialog und Entfernen per Kontextmenü |
| Untertitel | SRT aus dem Internet Archive und TimedText (VTT) von Commons als Kodi-Untertitelspuren |
| Bibliothek | Merkliste und Downloads als `.strm` + `.nfo` exportieren, veraltete Exporte über ein Manifest aufräumen und die Kodi-Filmbibliothek aktualisieren |
| Downloads | heruntergeladene Filme abspielen oder löschen |
| Zufallsfilm | startet direkt einen zufälligen Film |
| Eigene Streams | Ordner aus den Einstellungen (eine Ebene Unterordner), spielt `.strm`, `.m3u`, `.m3u8`, `.mp4`, `.mkv` usw. |
| Cache leeren | verwirft zwischengespeicherte Archive-Antworten |

Einstellungen: Einträge pro Seite, Sortierung, **Wiedergabequalität** (immer beste
Qualität oder bei mehreren Dateien fragen), optionaler **Lizenzfilter** (nur Items mit
`licenseurl`), **Download-Ordner**, Cache-Dauer und der Ordner für eigene Streams.

Abspielbare Dateien listen Auflösung, Format und Größe; gesperrte Archive-Items
(`is_dark`) werden nicht wiedergegeben.

## Downloads

Im Kontextmenü eines Films (`C` auf der Tastatur, lange OK-Taste auf der Fernbedienung)
startet **Herunterladen** den Download in den eingestellten Ordner: mit Fortschrittsdialog,
Abbrechen, Qualitätsauswahl bei mehreren Dateien und einer `.json`-Begleitdatei für Titel,
Handlung, Jahr und Dauer. Das gilt für Internet-Archive-Filme genauso wie für NASA- und
Commons-Treffer der globalen Suche; die Endung folgt der Quelle (`.mp4` bei der NASA,
`.webm` bei Commons). Unter **Downloads** im Hauptmenü liegen die fertigen Filme
zum Abspielen; **Löschen** im Kontextmenü entfernt Datei und Begleitdatei.
Falls der Download-Ordner noch nicht gesetzt ist, verweist das Add-on auf die Einstellungen.
Der Download läuft im Vordergrund mit Fortschrittsdialog – Kodi bleibt bedienbar,
aber der Vorgang endet, wenn du das Add-on schließt.

## Rechtliches

Alle Inhalte kommen aus dem Internet Archive und sind dort gemeinfrei oder frei
lizenziert. Das Add-on liest keine fremden Streaming-Portale aus und umgeht keine
Bezahlscharanken oder Kopierschutzmaßnahmen. Für eigene Streams ist der Nutzer
selbst verantwortlich, dass er die nötigen Rechte besitzt.
