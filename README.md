# Stream Kommando – eigenes Kodi-Repository

Ein selbst gebautes Kodi-Repository mit dem Video-Add-on **Stream Kommando**.
Das Add-on durchsucht und spielt **gemeinfreie Filme aus dem Internet Archive**
(kuratierte Sammlungen, Titelsuche, Zufallsfilm) und listet zusätzlich einen
eigenen Ordner mit `.strm`- und `.m3u`-Dateien.

## Aufbau

```
repo.json                              Basis-URL des Repositories (vor dem Hosten anpassen)
build.py                               baut Zips + addons.xml + addons.xml.md5
addons.xml / addons.xml.md5            Addon-Index (generiert)
zips/<addon-id>/<addon-id>-<version>.zip   Installationspakete (generiert)
repository.streamkommando/             Repository-Add-on
plugin.video.streamkommando/           Stream Kommando Add-on
    default.py
    resources/lib/                     archive.py, router.py, streams.py, cache.py, kodigui.py
    resources/settings.xml
    resources/language/                de_de + en_gb
```

## 1. Basis-URL eintragen

In `repo.json` steht die Adresse, unter der das Repository erreichbar ist – für dieses
Projekt bereits gesetzt:

```json
{
  "base_url": "https://raw.githubusercontent.com/xsensenmannx/kodi-repo-streamkommando/main"
}
```

Bei einem Fork oder anderem Branch hier anpassen und neu bauen – `build.py` ersetzt
`{{BASE_URL}}` in der `addon.xml` des Repository-Add-ons und schreibt alle Dateien neu:

```
python build.py
```

## 2. Hosten

Alles, was Kodi braucht, liegt danach im Projektordner:

```
addons.xml
addons.xml.md5
zips/repository.streamkommando/repository.streamkommando-1.0.0.zip
zips/plugin.video.streamkommando/plugin.video.streamkommando-1.0.0.zip
```

Diese Pfade müssen unter der `base_url` genau so erreichbar sein. Geeignet sind
GitHub Pages, `raw.githubusercontent.com` (Branch `main`) oder jeder statische
Webspace. Nach jeder Änderung an einem Add-on: Version in der `addon.xml`
erhöhen und `python build.py` erneut ausführen.

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
| Filmarchiv | 8 Sammlungen (Spielfilme, Sci-Fi & Horror, Komödie, Stummfilm, Animation, Klassisches Fernsehen, Prelinger-Archiv, Kurzfilme), sortiert nach Downloads/Titel/Jahr, mit Blättern |
| Suche | Titelsuche im Filmarchiv |
| Zufallsfilm | startet direkt einen zufälligen Film |
| Eigene Streams | Ordner aus den Einstellungen (eine Ebene Unterordner), spielt `.strm`, `.m3u`, `.m3u8`, `.mp4`, `.mkv` usw. |
| Cache leeren | verwirft zwischengespeicherte Archive-Antworten |

Einstellungen: Einträge pro Seite, Sortierung, Cache-Dauer in Stunden und der
Ordner für eigene Streams.

## Rechtliches

Alle Inhalte kommen aus dem Internet Archive und sind dort gemeinfrei oder frei
lizenziert. Das Add-on liest keine fremden Streaming-Portale aus und umgeht keine
Bezahlscharanken oder Kopierschutzmaßnahmen. Für eigene Streams ist der Nutzer
selbst verantwortlich, dass er die nötigen Rechte besitzt.
