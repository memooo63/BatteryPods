# BatteryPods

Windows-Anwendung, die den Batteriestatus verbundener Apple AirPods anzeigt.
Die GUI wurde mit **PySide6** umgesetzt und kann per PyInstaller zu einer
portable `.exe` kompiliert werden.

## Features

- Fortschrittsbalken für den Ladezustand von Left, Right und Case (in %)
- Umschaltbarer Dark-/Light-Mode
- Option für Autostart mit Windows (Registry)
- Gerätauswahl für verbundene AirPods (erstes Gerät wird vorgeschlagen)
- Automatisches Speichern von Einstellungen (Theme, Autostart, Sprache, Gerät)
- Fehlerbehandlung, falls keine AirPods gefunden werden
- Mehrsprachige Oberfläche (Deutsch/Englisch)


## Installation

```bash
pip install -r requirements.txt
python app.py  # Start der Anwendung
```

## Build mit PyInstaller

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile app.py
```

Die erstellte ausführbare Datei befindet sich anschließend im Verzeichnis
`dist/`.

## Hinweise

Die Auslesung des Batteriestatus erfolgt über die Bluetooth-LE API des Pakets
`bleak`. Die AirPods müssen gekoppelt sein und sich in Reichweite befinden.
