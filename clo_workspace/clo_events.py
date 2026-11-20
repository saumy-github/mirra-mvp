"""Event-driven completion for the CLO REST plugin (stdlib only).

Replaces "queue a command, then poll /status until the queue is empty" with
waiting on the plugin's own completion events:

    GET  /wait?id=N         long-poll until command N finished
    GET  /events?since=S    long-poll for events newer than S
    WS   /ws?since=S        push stream, one JSON event per frame

Every async POST answers with an `X-Mirra-Command-Id` header; `post_and_wait`
uses it to block until exactly that command is done and returns the plugin's
own `elapsed_ms` for it. Plugins built before the event feed (no `has_events`
in /health) answer 404 on /wait; callers fall back to polling via
`wait_idle_or_poll`.
"""
from __future__ import annotations

import base64
import json
import os
import socket
import struct
import time
import urllib.error
import urllib.request
from typing import Iterator
from urllib.parse import urlparse


class EventsUnavailable(RuntimeError):
    """The plugin has no event feed (older build)."""


class EventClient:
    def __init__(self, base_url: str = "http://127.0.0.1:50505", http_timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.http_timeout = http_timeout

    # -- plain HTTP helpers -------------------------------------------------
    def _get(self, path: str, timeout: float | None = None) -> dict:
        req = urllib.request.Request(self.base_url + path)
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.http_timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise EventsUnavailable(f"{path} not found: plugin has no event feed") from exc
            raise

    def _post(self, path: str, payload: dict | None, timeout: float | None = None) -> tuple[dict, dict]:
        data = json.dumps(payload or {}).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + path, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout or self.http_timeout) as resp:
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return json.loads(resp.read().decode("utf-8")), headers

    # -- event reads --------------------------------------------------------
    def has_events(self) -> bool:
        try:
            return bool(self._get("/health").get("has_events"))
        except Exception:
            return False

    def latest_seq(self) -> int:
        return int(self._get("/events?since=0&limit=1").get("latest", 0))

    def events(self, since: int, timeout_ms: int = 0, limit: int = 200) -> dict:
        wait_s = timeout_ms / 1000.0 + self.http_timeout
        return self._get(f"/events?since={since}&timeout_ms={timeout_ms}&limit={limit}", timeout=wait_s)

    def wait_command(self, command_id: int, timeout: float = 30.0) -> dict:
        """Block until command `command_id` is done; return its command_done event."""
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"CLO command {command_id} not done within {timeout}s")
            chunk = min(remaining, 60.0)
            r = self._get(
                f"/wait?id={command_id}&timeout_ms={int(chunk * 1000)}", timeout=chunk + self.http_timeout
            )
            if r.get("done"):
                return r.get("event") or {"type": "command_done", "id": command_id}

    def wait_idle(self, since: int | None = None, timeout: float = 30.0) -> dict:
        """Block until a queue_idle event newer than `since` (default: now) arrives."""
        cursor = self.latest_seq() if since is None else since
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"CLO queue not idle within {timeout}s")
            chunk = min(remaining, 60.0)
            r = self.events(cursor, timeout_ms=int(chunk * 1000))
            for ev in r.get("events", []):
                if ev.get("type") == "queue_idle":
                    return ev
            cursor = max(cursor, int(r.get("latest", cursor)))

    # -- post and wait ------------------------------------------------------
    def post_and_wait(self, path: str, payload: dict | None = None, timeout: float = 120.0) -> dict:
        """POST a command and wait for exactly that command to finish.

        Returns {"response": <POST body>, "command_id": N, "event": <command_done>}.
        Raises EventsUnavailable if the plugin did not return a command id.
        """
        body, headers = self._post(path, payload)
        cid = headers.get("x-mirra-command-id")
        if not cid:
            raise EventsUnavailable(f"{path}: no X-Mirra-Command-Id header (older plugin build?)")
        event = self.wait_command(int(cid), timeout=timeout)
        return {"response": body, "command_id": int(cid), "event": event}

    # -- WebSocket stream ---------------------------------------------------
    def ws_events(self, since: int | None = None, idle_timeout: float = 60.0) -> Iterator[dict]:
        """Yield events pushed over /ws until the socket closes."""
        parsed = urlparse(self.base_url)
        host, port = parsed.hostname or "127.0.0.1", parsed.port or 80
        path = "/ws" + ("" if since is None else f"?since={since}")
        sock = socket.create_connection((host, port), timeout=10)
        try:
            key = base64.b64encode(os.urandom(16)).decode()
            sock.sendall(
                (
                    f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\n"
                    f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
                ).encode()
            )
            head = b""
            while b"\r\n\r\n" not in head:
                chunk = sock.recv(4096)
                if not chunk:
                    raise ConnectionError("websocket handshake closed")
                head += chunk
            header_blob, _, rest = head.partition(b"\r\n\r\n")
            if b" 101 " not in header_blob.split(b"\r\n", 1)[0]:
                raise EventsUnavailable("websocket upgrade refused: " + header_blob.split(b"\r\n", 1)[0].decode())
            sock.settimeout(idle_timeout)
            buf = bytearray(rest)
            while True:
                frame = _read_frame(sock, buf)
                if frame is None:
                    return
                opcode, payload = frame
                if opcode == 0x8:  # close
                    return
                if opcode == 0x9:  # ping -> pong
                    sock.sendall(_masked_frame(0xA, payload))
                    continue
                if opcode == 0x1:
                    yield json.loads(payload.decode("utf-8"))
        finally:
            try:
                sock.close()
            except OSError:
                pass


def _recv_exact(sock: socket.socket, buf: bytearray, n: int) -> bytes | None:
    while len(buf) < n:
        chunk = sock.recv(65536)
        if not chunk:
            return None
        buf.extend(chunk)
    out = bytes(buf[:n])
    del buf[:n]
    return out


def _read_frame(sock: socket.socket, buf: bytearray) -> tuple[int, bytes] | None:
    hdr = _recv_exact(sock, buf, 2)
    if hdr is None:
        return None
    opcode = hdr[0] & 0x0F
    masked = bool(hdr[1] & 0x80)
    length = hdr[1] & 0x7F
    if length == 126:
        ext = _recv_exact(sock, buf, 2)
        if ext is None:
            return None
        length = struct.unpack(">H", ext)[0]
    elif length == 127:
        ext = _recv_exact(sock, buf, 8)
        if ext is None:
            return None
        length = struct.unpack(">Q", ext)[0]
    mask = _recv_exact(sock, buf, 4) if masked else None
    payload = _recv_exact(sock, buf, length) if length else b""
    if payload is None:
        return None
    if mask:
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    return opcode, payload


def _masked_frame(opcode: int, payload: bytes) -> bytes:
    mask = os.urandom(4)
    n = len(payload)
    head = bytes([0x80 | opcode])
    if n < 126:
        head += bytes([0x80 | n])
    elif n < 65536:
        head += bytes([0x80 | 126]) + struct.pack(">H", n)
    else:
        head += bytes([0x80 | 127]) + struct.pack(">Q", n)
    return head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
