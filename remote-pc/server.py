#!/usr/bin/env python3
"""Serveur de contrôle à distance.

À lancer sur le PC que l'on veut contrôler. Il diffuse l'écran en continu
et reçoit les mouvements de souris / frappes clavier envoyés depuis le
navigateur du téléphone (voir client.html, servi automatiquement).

Usage :
    python server.py --password MonMotDePasse
    python server.py                # un mot de passe aléatoire est généré
"""

import argparse
import asyncio
import hmac
import io
import json
import logging
import os
import secrets
import socket
import threading
from pathlib import Path

from aiohttp import WSMsgType, web
from PIL import Image
import mss
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Button, Controller as MouseController

LOG = logging.getLogger("remote-pc")
CLIENT_HTML = Path(__file__).parent / "client.html"

SPECIAL_KEYS = {
    "Enter": Key.enter,
    "Backspace": Key.backspace,
    "Tab": Key.tab,
    "Escape": Key.esc,
    "Delete": Key.delete,
    "Insert": Key.insert,
    "Home": Key.home,
    "End": Key.end,
    "PageUp": Key.page_up,
    "PageDown": Key.page_down,
    "ArrowUp": Key.up,
    "ArrowDown": Key.down,
    "ArrowLeft": Key.left,
    "ArrowRight": Key.right,
    "Control": Key.ctrl,
    "Alt": Key.alt,
    "AltGr": Key.alt_gr,
    "Shift": Key.shift,
    "Meta": Key.cmd,
    "CapsLock": Key.caps_lock,
    " ": Key.space,
    "Space": Key.space,
    **{f"F{i}": getattr(Key, f"f{i}") for i in range(1, 13)},
}

MOUSE_BUTTONS = {"left": Button.left, "right": Button.right, "middle": Button.middle}


class InputController:
    """Traduit les messages JSON du client en actions souris/clavier."""

    def __init__(self, screen_w: int, screen_h: int, offset_x: int, offset_y: int):
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        self.w, self.h = screen_w, screen_h
        self.ox, self.oy = offset_x, offset_y

    def _abs(self, nx: float, ny: float):
        x = self.ox + min(max(nx, 0.0), 1.0) * self.w
        y = self.oy + min(max(ny, 0.0), 1.0) * self.h
        return x, y

    def handle(self, msg: dict):
        t = msg.get("t")
        if t == "move":
            self.mouse.position = self._abs(msg["x"], msg["y"])
        elif t == "moverel":
            self.mouse.move(msg["dx"], msg["dy"])
        elif t == "click":
            if "x" in msg:
                self.mouse.position = self._abs(msg["x"], msg["y"])
            btn = MOUSE_BUTTONS.get(msg.get("button", "left"), Button.left)
            self.mouse.click(btn, int(msg.get("count", 1)))
        elif t == "mousedown":
            if "x" in msg:
                self.mouse.position = self._abs(msg["x"], msg["y"])
            self.mouse.press(MOUSE_BUTTONS.get(msg.get("button", "left"), Button.left))
        elif t == "mouseup":
            self.mouse.release(MOUSE_BUTTONS.get(msg.get("button", "left"), Button.left))
        elif t == "scroll":
            self.mouse.scroll(int(msg.get("dx", 0)), int(msg.get("dy", 0)))
        elif t == "text":
            self.keyboard.type(msg["text"])
        elif t == "key":
            key = SPECIAL_KEYS.get(msg["key"], msg["key"] if len(msg["key"]) == 1 else None)
            if key is None:
                LOG.debug("Touche inconnue ignorée : %r", msg["key"])
                return
            if msg.get("down", True):
                self.keyboard.press(key)
            else:
                self.keyboard.release(key)
        elif t == "press":
            key = SPECIAL_KEYS.get(msg["key"], msg["key"] if len(msg["key"]) == 1 else None)
            if key is not None:
                self.keyboard.press(key)
                self.keyboard.release(key)


class ScreenStreamer:
    """Capture l'écran dans un thread et encode des images JPEG."""

    def __init__(self, monitor_index: int, max_width: int, quality: int, fps: int):
        self.monitor_index = monitor_index
        self.max_width = max_width
        self.quality = quality
        self.interval = 1.0 / max(fps, 1)
        self._local = threading.local()

    def _sct(self):
        if not hasattr(self._local, "sct"):
            self._local.sct = mss.mss()
        return self._local.sct

    def monitor(self) -> dict:
        monitors = self._sct().monitors
        index = min(self.monitor_index, len(monitors) - 1)
        return monitors[index]

    def grab_jpeg(self) -> bytes:
        sct = self._sct()
        shot = sct.grab(self.monitor())
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        if img.width > self.max_width:
            ratio = self.max_width / img.width
            img = img.resize((self.max_width, int(img.height * ratio)), Image.BILINEAR)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=self.quality)
        return buf.getvalue()


async def stream_frames(ws: web.WebSocketResponse, streamer: ScreenStreamer):
    while not ws.closed:
        started = asyncio.get_event_loop().time()
        try:
            frame = await asyncio.to_thread(streamer.grab_jpeg)
            await ws.send_bytes(frame)
        except (ConnectionResetError, RuntimeError):
            break
        elapsed = asyncio.get_event_loop().time() - started
        await asyncio.sleep(max(streamer.interval - elapsed, 0.01))


async def ws_handler(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse(heartbeat=20, max_msg_size=2 * 1024 * 1024)
    await ws.prepare(request)
    app = request.app
    peer = request.remote

    # Premier message obligatoire : {"t": "auth", "password": "..."}
    try:
        first = await asyncio.wait_for(ws.receive_json(), timeout=10)
    except (asyncio.TimeoutError, TypeError, ValueError):
        await ws.close()
        return ws
    if first.get("t") != "auth" or not hmac.compare_digest(
        str(first.get("password", "")), app["password"]
    ):
        LOG.warning("Authentification refusée pour %s", peer)
        await ws.send_json({"t": "auth", "ok": False})
        await ws.close()
        return ws

    streamer: ScreenStreamer = app["streamer"]
    monitor = await asyncio.to_thread(streamer.monitor)
    controller = InputController(
        monitor["width"], monitor["height"], monitor["left"], monitor["top"]
    )
    await ws.send_json(
        {"t": "auth", "ok": True, "w": monitor["width"], "h": monitor["height"]}
    )
    LOG.info("Client connecté : %s", peer)

    sender = asyncio.create_task(stream_frames(ws, streamer))
    try:
        async for msg in ws:
            if msg.type != WSMsgType.TEXT:
                continue
            try:
                controller.handle(json.loads(msg.data))
            except Exception:
                LOG.exception("Message client invalide")
    finally:
        sender.cancel()
        LOG.info("Client déconnecté : %s", peer)
    return ws


async def index_handler(_request: web.Request) -> web.Response:
    return web.Response(text=CLIENT_HTML.read_text(encoding="utf-8"), content_type="text/html")


def local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def main():
    parser = argparse.ArgumentParser(description="Contrôle du PC depuis un téléphone")
    parser.add_argument("--password", default=os.environ.get("REMOTE_PC_PASSWORD"),
                        help="Mot de passe de connexion (sinon généré aléatoirement)")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--fps", type=int, default=12, help="Images par seconde")
    parser.add_argument("--quality", type=int, default=60, help="Qualité JPEG (1-95)")
    parser.add_argument("--max-width", type=int, default=1280,
                        help="Largeur max des images envoyées")
    parser.add_argument("--monitor", type=int, default=1,
                        help="Numéro de l'écran à diffuser (1 = principal)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    password = args.password or secrets.token_urlsafe(8)
    app = web.Application()
    app["password"] = password
    app["streamer"] = ScreenStreamer(args.monitor, args.max_width, args.quality, args.fps)
    app.router.add_get("/", index_handler)
    app.router.add_get("/ws", ws_handler)

    print("=" * 60)
    print("  Contrôle PC à distance — serveur démarré")
    print(f"  Sur ce réseau : http://{local_ip()}:{args.port}")
    print(f"  Mot de passe  : {password}")
    print("  (Pour un accès depuis n'importe où : voir README, Tailscale)")
    print("=" * 60)

    web.run_app(app, host=args.host, port=args.port, print=None)


if __name__ == "__main__":
    main()
