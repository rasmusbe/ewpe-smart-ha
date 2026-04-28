"""A tiny in-process UDP server that simulates an EWPE Smart device.

Used by the test suite to exercise the full client → server → client cycle
without touching the network.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from custom_components.ewpe_smart.const import GENERIC_KEY
from custom_components.ewpe_smart.protocol import decrypt, encrypt


class MockEwpeProtocol(asyncio.DatagramProtocol):
    """Simulates one device. Tracks received commands for test assertions."""

    def __init__(
        self,
        mac: str = "AA:BB:CC:DD:EE:FF",
        name: str = "MockAC",
        device_key: bytes = b"abcdefghijklmnop",
        status: dict[str, int] | None = None,
        misbehave: str | None = None,
    ) -> None:
        self.mac = mac
        self.name = name
        self.device_key = device_key
        self.status: dict[str, int] = status or {
            "Pow": 1,
            "Mod": 1,
            "SetTem": 22,
            "TemUn": 0,
            "WdSpd": 0,
            "TemSen": 65,  # raw value before -40 offset → 25 °C
        }
        self.misbehave = misbehave
        self.received_commands: list[dict[str, Any]] = []
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        if self.misbehave == "silent":
            return
        if self.misbehave == "garbage":
            assert self.transport is not None
            self.transport.sendto(b"not-json", addr)
            return

        envelope = json.loads(data.decode("utf-8"))
        if "pack" in envelope:
            key = GENERIC_KEY if envelope.get("i") == 1 else self.device_key
            inner = decrypt(envelope["pack"], key)
        else:
            # Unencrypted broadcast scan
            inner = envelope

        reply = self._build_reply(inner)
        if reply is None:
            return

        out_key = self.device_key if reply.get("t") in {"dat", "res"} else GENERIC_KEY
        out_envelope = {
            "cid": self.mac,
            "i": 0 if reply.get("t") in {"dat", "res"} else 1,
            "t": "pack",
            "uid": 0,
            "pack": encrypt(reply, out_key),
        }
        assert self.transport is not None
        self.transport.sendto(
            json.dumps(out_envelope, separators=(",", ":")).encode("utf-8"),
            addr,
        )

    def _build_reply(self, inner: dict[str, Any]) -> dict[str, Any] | None:
        t = inner.get("t")
        if t == "scan":
            return {
                "t": "dev",
                "cid": self.mac,
                "mac": self.mac,
                "name": self.name,
                "brand": "Daitsu",
                "model": "MockAC-1",
                "vender": "Gree",
                "ver": "V1.0.0",
            }
        if t == "bind":
            return {
                "t": "bindok",
                "mac": self.mac,
                "key": self.device_key.decode("utf-8"),
            }
        if t == "status":
            cols = inner.get("cols") or list(self.status.keys())
            return {
                "t": "dat",
                "mac": self.mac,
                "cols": cols,
                "dat": [self.status.get(c, 0) for c in cols],
            }
        if t == "cmd":
            opt = inner.get("opt") or []
            values = inner.get("p") or []
            self.received_commands.append({"opt": opt, "p": values})
            for k, v in zip(opt, values, strict=False):
                self.status[k] = v
            return {
                "t": "res",
                "mac": self.mac,
                "opt": opt,
                "val": values,
            }
        return None


async def start_mock_device(**kwargs: Any) -> tuple[MockEwpeProtocol, int]:
    """Spin up a mock device on localhost and return ``(protocol, port)``."""
    loop = asyncio.get_running_loop()
    protocol = MockEwpeProtocol(**kwargs)
    transport, _ = await loop.create_datagram_endpoint(
        lambda: protocol, local_addr=("127.0.0.1", 0)
    )
    sockname = transport.get_extra_info("sockname")
    return protocol, sockname[1]
