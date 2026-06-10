#!/usr/bin/env bash
# Installateur automatique — Contrôle PC à distance (macOS / Linux)
# Usage :
#   curl -fsSL https://raw.githubusercontent.com/nassaimadi35-wq/nassaimadi35-wq.github.io/claude/remote-pc-control-app-rgbmo9/remote-pc/installer.sh | bash
set -e

REPO="nassaimadi35-wq/nassaimadi35-wq.github.io"
BRANCH="claude/remote-pc-control-app-rgbmo9"
DEST="$HOME/RemotePC"

echo ""
echo "=== Installation du Contrôle PC à distance ==="

if ! command -v python3 >/dev/null; then
  echo "Python 3 est requis. Installez-le puis relancez :"
  echo "  - macOS  : brew install python  (ou https://www.python.org/downloads/)"
  echo "  - Debian/Ubuntu : sudo apt install python3 python3-pip"
  exit 1
fi
echo "[1/3] Python présent : $(python3 --version)"

echo "[2/3] Téléchargement de l'application..."
TMP=$(mktemp -d)
curl -fsSL "https://github.com/$REPO/archive/refs/heads/$BRANCH.tar.gz" | tar -xz -C "$TMP"
mkdir -p "$DEST"
cp -r "$TMP"/*/remote-pc/. "$DEST/"
rm -rf "$TMP"
echo "      Installé dans $DEST"

echo "[3/3] Installation des dépendances Python..."
python3 -m pip install --quiet -r "$DEST/requirements.txt" \
  || python3 -m pip install --quiet --user -r "$DEST/requirements.txt"

echo ""
echo "=== Installation terminée ! ==="
if [ "$(uname)" = "Darwin" ]; then
  echo "macOS : autorisez votre Terminal dans Réglages → Confidentialité et sécurité"
  echo "        → 'Enregistrement de l'écran' ET 'Accessibilité'."
fi
echo ""
echo "Démarrage du serveur..."
cd "$DEST"
exec python3 server.py
