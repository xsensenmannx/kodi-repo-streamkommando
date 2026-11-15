<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stream Kommando – Kodi Repository</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0; min-height: 100vh; font-family: "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #dbe9f5; background: radial-gradient(1200px 700px at 50% -10%, #173d5c 0%, #0b1a2a 45%, #060d16 100%);
  }
  .wrap { max-width: 980px; margin: 0 auto; padding: 48px 24px 64px; }
  header { display: flex; gap: 24px; align-items: center; flex-wrap: wrap; margin-bottom: 40px; }
  header img { width: 128px; height: 128px; border-radius: 24px; box-shadow: 0 0 40px rgba(60,180,240,.35); }
  h1 { margin: 0 0 6px; font-size: clamp(28px, 5vw, 46px); letter-spacing: 3px; font-weight: 600; color: #eaf7ff; }
  .sub { margin: 0; color: #8fb6cf; letter-spacing: 2px; text-transform: uppercase; font-size: 13px; }
  .lead { color: #b6cddd; line-height: 1.6; max-width: 70ch; }
  h2 { font-size: 15px; letter-spacing: 2px; text-transform: uppercase; color: #7fd4f5; margin: 40px 0 12px; }
  .buttons { display: flex; gap: 14px; flex-wrap: wrap; margin: 26px 0 6px; }
  a.btn {
    display: inline-block; padding: 14px 22px; border-radius: 10px; text-decoration: none;
    font-weight: 600; letter-spacing: .4px; border: 1px solid rgba(120,210,255,.5);
    color: #04121d; background: linear-gradient(180deg, #9fe6ff, #43b6e8); transition: transform .15s ease;
  }
  a.btn.secondary { background: rgba(20,45,68,.75); color: #cfe9f9; border-color: rgba(120,190,230,.35); }
  a.btn:hover { transform: translateY(-2px); }
  ol { padding-left: 22px; line-height: 1.8; color: #c3d7e5; }
  code, pre { background: rgba(8,22,35,.8); border: 1px solid rgba(90,150,190,.25); border-radius: 8px; }
  code { padding: 2px 7px; font-size: 13px; color: #a9e6ff; }
  pre { padding: 14px 16px; overflow: auto; font-size: 13px; color: #a9e6ff; }
  ul { line-height: 1.8; color: #c3d7e5; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }
  .card { background: rgba(13,33,50,.7); border: 1px solid rgba(90,150,190,.22); border-radius: 12px; padding: 16px 18px; }
  .card h3 { margin: 0 0 6px; font-size: 15px; color: #d7efff; }
  .card p { margin: 0; font-size: 14px; color: #9db8ca; line-height: 1.5; }
  footer { margin-top: 48px; padding-top: 20px; border-top: 1px solid rgba(90,150,190,.2); color: #7d97a9; font-size: 13px; }
  footer a { color: #8fd6f5; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <img src="plugin.video.streamkommando/icon.png" alt="Stream Kommando">
    <div>
      <h1>STREAM KOMMANDO</h1>
      <p class="sub">Kodi Repository · Version {{ADDON_VERSION}}</p>
    </div>
  </header>

  <p class="lead">
    Eigenes Kodi-Repository für gemeinfreie Filme aus dem Internet Archive:
    kuratierte Sammlungen, Titelsuche, Zufallsfilm, Qualitätsauswahl und eigene
    <code>.strm</code>-/.m3u</code>-Quellen. Keine fremden Portale, keine Bezahlschranken.
  </p>

  <div class="buttons">
    <a class="btn" href="{{REPO_ZIP}}">Repository installieren ({{REPO_VERSION}})</a>
    <a class="btn secondary" href="{{ADDON_ZIP}}">Add-on direkt als ZIP</a>
  </div>

  <h2>Installation in Kodi</h2>
  <ol>
    <li>Diese Seite als Quelle hinzufügen: <strong>Einstellungen → Dateimanager → Quelle hinzufügen</strong>, URL
      <code>{{BASE_URL}}</code>.</li>
    <li><strong>Add-ons → Aus ZIP-Datei installieren</strong> → Quelle öffnen →
      <code>{{REPO_ZIP}}</code>.</li>
    <li><strong>Aus Repository installieren → Stream Kommando Repository → Video-Add-ons → Stream Kommando</strong>.</li>
  </ol>

  <h2>Was drin ist</h2>
  <div class="grid">
    <div class="card"><h3>Filmarchiv</h3><p>Acht Sammlungen mit über 60.000 Filmen, sortierbar nach Downloads, Titel oder Jahr.</p></div>
    <div class="card"><h3>Qualitätsauswahl</h3><p>Auflösung, Format und Dateigröße zur Auswahl – oder automatisch das Beste.</p></div>
    <div class="card"><h3>Zufallsfilm</h3><p>Ein Klick, ein zufälliger Film aus dem Archiv.</p></div>
    <div class="card"><h3>Eigene Streams</h3><p>Ein Ordner mit <code>.strm</code>- und <code>.m3u</code>-Dateien, auch aus Unterordnern.</p></div>
  </div>

  <h2>Repository-Dateien</h2>
  <ul>
    <li><a href="addons.xml">addons.xml</a> (Addon-Index)</li>
    <li><a href="addons.xml.md5">addons.xml.md5</a> (Änderungs-Token für Kodi)</li>
    <li><a href="zips/">zips/</a> – Installationspakete</li>
  </ul>

  <footer>
    Quellcode: <a href="https://github.com/xsensenmannx/kodi-repo-streamkommando">github.com/xsensenmannx/kodi-repo-streamkommando</a><br>
    Inhalte: Internet Archive, gemeinfrei oder frei lizenziert. Gesperrte Items werden nicht abgespielt.
  </footer>
</div>
</body>
</html>
