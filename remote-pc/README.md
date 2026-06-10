# 🖥️📱 Contrôle PC à distance depuis votre téléphone

Voyez l'écran de votre PC, bougez la souris et tapez au clavier depuis le
navigateur de votre téléphone — où que vous soyez dans le monde.

## Comment ça marche

Deux parties :

1. **Le serveur** (`server.py`) tourne sur le PC à contrôler. Il capture
   l'écran et exécute les actions souris/clavier que vous envoyez.
2. **Le client** est une simple page web servie par le serveur. Sur votre
   téléphone, ouvrez l'adresse du serveur dans Chrome/Safari : aucune
   application à installer.

## Installation (sur le PC à contrôler)

1. Installez [Python 3.9+](https://www.python.org/downloads/)
   (sous Windows, cochez **« Add Python to PATH »**).
2. Copiez ce dossier `remote-pc/` sur le PC.
3. Démarrez le serveur :
   - **Windows** : double-cliquez sur `demarrer_windows.bat`
   - **macOS / Linux** : `bash demarrer_mac_linux.sh`
   - ou manuellement :
     ```bash
     pip install -r requirements.txt
     python server.py --password VotreMotDePasse
     ```

Le serveur affiche alors l'adresse à ouvrir et le mot de passe (généré
aléatoirement si vous n'en donnez pas un).

> **macOS** : autorisez le terminal dans Réglages → Confidentialité et
> sécurité → *Enregistrement de l'écran* et *Accessibilité*.

## Utilisation sur le téléphone

1. Ouvrez l'adresse affichée par le serveur (ex. `http://192.168.1.20:8765`).
2. Entrez le mot de passe.
3. Gestes :

| Geste | Action |
|---|---|
| Toucher l'écran | Clic gauche à cet endroit |
| Double-tap | Double-clic |
| Appui long | Clic droit |
| Glisser un doigt | Déplacer le curseur |
| Deux doigts haut/bas | Défilement (molette) |
| Bouton **✊ Glisser** | Le prochain toucher fait un glisser-déposer |
| Bouton **⌨️ Clavier** | Ouvre le clavier du téléphone |
| Ctrl / Alt / Maj / Win | Touches modificatrices (restent enfoncées tant qu'elles sont vertes) |

## Accès depuis n'importe où dans le monde 🌍

L'adresse `http://192.168.x.x:8765` ne fonctionne que sur votre réseau Wi-Fi
local. Pour y accéder depuis partout, la méthode **recommandée, gratuite et
sécurisée** est [Tailscale](https://tailscale.com) :

1. Créez un compte Tailscale (gratuit) et installez-le **sur le PC**.
2. Installez l'application **Tailscale sur votre téléphone** et connectez-vous
   au même compte.
3. Sur le téléphone, ouvrez `http://<ip-tailscale-du-pc>:8765`
   (l'IP commence par `100.`, visible dans l'application Tailscale).

Tailscale crée un tunnel chiffré privé entre vos appareils : rien n'est
exposé sur Internet, pas de configuration de box/routeur nécessaire, et ça
marche en 4G/5G comme en Wi-Fi.

Alternatives :
- **ngrok** : `ngrok http 8765` puis ouvrez l'URL `https://...ngrok...` fournie.
- **Redirection de port** sur votre box (déconseillé : le trafic n'est pas
  chiffré et votre PC devient accessible publiquement).

## Options du serveur

```
python server.py --password SECRET   # mot de passe de connexion
                 --port 8765         # port d'écoute
                 --fps 12            # images par seconde
                 --quality 60        # qualité JPEG (1-95)
                 --max-width 1280    # largeur max du flux vidéo
                 --monitor 1         # écran à diffuser (si plusieurs)
```

Connexion lente (4G) ? Essayez `--fps 8 --quality 40 --max-width 960`.

## Sécurité ⚠️

- Ce serveur donne le **contrôle total du PC** à quiconque connaît le mot de
  passe : choisissez-en un long, et ne lancez le serveur que quand vous en
  avez besoin.
- Utilisez **Tailscale** (trafic chiffré) plutôt qu'une redirection de port.
- En HTTP local, le mot de passe transite en clair sur le réseau : encore une
  raison de passer par le tunnel chiffré de Tailscale.
