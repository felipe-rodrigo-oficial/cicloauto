# CicloAuto 🚲

A modular navigation and signaling system for cyclists: a phone dashboard on the handlebar and a micro:bit rear light.

## Features
- **Motorcycle-style dashboard** (web app, runs in the phone's browser): speedometer, trip dial, map, elevation profile, battery and road grade.
- **Bike routes** with turn-by-turn directions (OpenStreetMap data).
- **Automatic turn signals**: on 50 m before each turn (and before your roundabout exit), off 10 m after it.
- **Brake light**: braking is detected from the phone's GPS speed.
- **Speed alerts** at 25, 30, 40 and 50 km/h.
- **Crash detection & SOS**: after a hard impact followed by a stop, a 30 s "Are you OK?" countdown; with no answer the phone app opens ready to call the emergency number or your contact.
- **micro:bit rear light** over Bluetooth: animated turn signals, brake light and hazard flashing. A virtual micro:bit is built in for testing without the device.

## Project layout
| Path | What it is |
|---|---|
| `index.html` | The whole web app (HTML, CSS and JavaScript) |
| `manifest.webmanifest`, `icon-*.png` | Lets you install it on the phone's home screen |
| `microbit/cicloauto-rear-v2/` | micro:bit V2 program (MakeCode project: `main.ts` + `pxt.json` with `bluetooth`, no pairing). Ready-to-flash `.hex` and download page at `/microbit/`. See `microbit/README.md` |
| `render.yaml` | Deploys the app as a static site on Render (free HTTPS) |
| `android/` | Early Kivy (Python) prototype, no longer used |

## Run it
- **Locally:** serve the folder, e.g. `python -m http.server 8744`, then open `http://localhost:8744`.
- **On a phone:** GPS and Bluetooth need HTTPS, so deploy it (Render reads `render.yaml`) and open the URL in Chrome on Android. Use "Install app" to add it to the home screen.

## Credits
Map © OpenStreetMap contributors · tiles by OpenFreeMap · routes by OSRM · elevation and weather by Open-Meteo · search by Photon.
