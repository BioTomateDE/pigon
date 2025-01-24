[//]: <> (!!------------------------------------------------------------------!!)
[//]: <> (!! Bitte diese Datei in Github anschauen für mehr Verständlichkeit. !!)
[//]: <> (!!               https://github.com/BioTomateDE/pigon               !!)
[//]: <> (!!------------------------------------------------------------------!!)


# Pigon Messenger
Entwickelt von **Levent Taraszow** (10-3) für Informatik mPA 2024/25.


## Features
- **Sicherheit ihrer Daten durch Verschlüsslung**:
  - RSA-Verschlüsslung für die Speicherung von (symmetrischen) Channel-Schlüsseln
  - AES-Verschlüsslung für das Senden und Empfangen von Nachrichten
- **Text-Formatierung in Nachrichten**:
  - `*` oder `_` für *kursiven* Text
  - `**` für **fetten** Text
  - `__` für <ins>unterstrichenen</ins> Text
  - ``` ` ``` für einzeilige `Code-Blöcke`
  - ` `` ` für mehrzeilige <code>Code-Blöcke</code>
- **GDPR/DSGVO-konform**; alle gesammelten Daten werden auf Wunsch mit einem Knopfdruck sofort gelöscht!

## Technische Daten:
Getestet auf **Windows 11** 23H2 mit Python **3.12.6**.
- Backend: **Python**
  - Version: 3.12.6
  - Externe Libraries: `websockets` (Version 12.0)
- Frontend: **HTML, CSS, JavaScript**
  - Externe Libraries: `lodash`, `base64js`


## Installationsanleitung
1. Windows 10/11 benutzen (Linux könnte theoretisch klappen; ist allerdings ungetestet)
2. Python 3.12.6 installieren (Python 3.9 könnte ebenfalls funktionieren)
3. Libraries installieren: `pip install websockets==12` (bzw. `py -m pip install websockets==12` oder `python -m pip install websockets==12`; je nachdem, was auf dem System funktioniert)
4. Dieses Repository herunterladen: `<> Code` --> `Download ZIP`
5. Heruntergeladene ZIP-Datei zum gewünschten Server-Ordner extrahieren
6. Es sollten diese `README.md`-Datei und drei Ordner `src`, `backend_files` und `frontend_files` enthalten sein.
7. Im Ordner `backend_files` sollten zwei leere Ordner `accounts` und `channels` existieren. Wenn nicht, diese bitte erstellen. Diese sollten nur jeweils eine .gitkeep Datei enthalten. Falls das nicht der Fall ist, sollten alle Dateien in diesen Ordnern gelöscht werden (Die .gitkeep Dateien können ebenfalls gelöscht werden).
8. Um den Server auszuführen, in einem Command-Prompt zum `src`-Ordner navigieren
9. Dann `py server.py` ausführen (bzw. `python server.py`)
10. Es sollten zwei Nachrichten erscheinen: `Started server.` und `Started Websocket Server.`
11. Nun im Browser `http://localhost:8000/register.html` aufrufen.
12. Es sollte ein graues Fenster erscheinen, um sich beim Messenger zu registrieren.


## Problembehandlung
Der Server ist leider in Python geschrieben und ist daher nicht besonders schnell.
Außerdem schreibt und liest der Server bei Benutzung des Messengers oft/viele Dateien.
Da ich nicht den Fokus auf eine Datenbank, sondern auf Verschlüsselung gelegt habe, bestehen die gespeicherten Daten nur aus JSON-Dateien.

Durch diese intensive Auslastung des Dateisystems **kann der Server sich manchmal aufhängen**.
Das merkt man dadurch, das der Server für lange Zeit (mehr als 20 Sekunden) nicht reagiert.
Um dies zu beheben, **muss der Server in der Konsole durch Strg+Unterbrechen gestoppt und dann wieder gestartet werden**.
