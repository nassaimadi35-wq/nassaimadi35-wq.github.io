#!/usr/bin/env bash
# Lance le serveur de contrôle à distance sur macOS / Linux.
cd "$(dirname "$0")"
python3 -m pip install -r requirements.txt
python3 server.py "$@"
