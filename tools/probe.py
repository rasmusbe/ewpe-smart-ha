#!/usr/bin/env python3
"""Standalone probe for an EWPE Smart / Gree device.

Sends a raw scan packet to ``<ip>:7000`` and prints what comes back. Tells
you whether the device speaks the original V1 protocol (AES-ECB) or the
newer V2 protocol (AES-GCM, used by commercial U-Match controllers like the
XE7A series), or whether it's unreachable from this host.

Run this on the same host that runs Home Assistant — only that machine's
view of the network matters for the integration.

Usage:
    python3 tools/probe.py <device-ip> [<device-ip> ...]

Optional ``--decrypt`` flag tries the matching generic key on the encrypted
``pack`` field and prints the dev info (brand/model/MAC/name).
"""

from __future__ import annotations

import argparse
import base64
import json
import socket
import sys

PORT = 7000
TIMEOUT = 5.0

# V1 generic key — AES-128 ECB
V1_KEY = b"a3K8Bx%2r8Y7#xDh"
# V2 generic key + GCM nonce + AAD — AES-128 GCM
V2_KEY = b"{yxAHAY_Lm6pbC/<"
V2_NONCE = b"\x54\x40\x78\x44\x49\x67\x5a\x51\x6c\x5e\x63\x13"
V2_AAD = b"qualcomm-test"


def _decrypt_v1(pack_b64: str) -> dict:
    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    raw = base64.b64decode(pack_b64)
    cipher = Cipher(algorithms.AES(V1_KEY), modes.ECB())  # nosec B305
    decryptor = cipher.decryptor()
    padded = decryptor.update(raw) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    plain = unpadder.update(padded) + unpadder.finalize()
    return json.loads(plain.decode("utf-8"))


def _decrypt_v2(pack_b64: str, tag_b64: str) -> dict:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    ciphertext = base64.b64decode(pack_b64)
    tag = base64.b64decode(tag_b64)
    aesgcm = AESGCM(V2_KEY)
    plain = aesgcm.decrypt(V2_NONCE, ciphertext + tag, V2_AAD)
    text = plain.decode("utf-8", errors="replace")
    last = text.rfind("}")
    if last >= 0:
        text = text[: last + 1]
    return json.loads(text)


def probe(ip: str, decrypt: bool) -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(TIMEOUT)
    sock.bind(("", 0))
    try:
        packet = json.dumps({"t": "scan"}).encode()
        print(f"[{ip}] → sending raw scan ({len(packet)} B) to {ip}:{PORT}")
        try:
            sock.sendto(packet, (ip, PORT))
        except OSError as err:
            print(f"[{ip}]   sendto failed: {err}")
            return 2
        try:
            data, addr = sock.recvfrom(4096)
        except socket.timeout:
            print(f"[{ip}]   ✗ no reply within {TIMEOUT}s")
            print(
                f"[{ip}]     → device unreachable from this host. "
                "Check VLAN/firewall, or Docker bridge networking on HA."
            )
            return 1

        print(f"[{ip}] ← reply from {addr[0]}:{addr[1]} ({len(data)} B)")
        try:
            envelope = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as err:
            print(f"[{ip}]   ✗ reply is not JSON: {err}")
            print(f"[{ip}]     raw: {data!r}")
            return 3

        keys = sorted(envelope.keys())
        print(f"[{ip}]   envelope keys: {keys}")
        if "tag" in envelope:
            print(
                f"[{ip}]   → V2 protocol detected (AES-GCM). "
                "Integration ≥ 0.1.2 supports this."
            )
            if decrypt and "pack" in envelope:
                try:
                    info = _decrypt_v2(envelope["pack"], envelope["tag"])
                except Exception as err:
                    print(f"[{ip}]   ✗ V2 decrypt failed: {err}")
                    return 4
                print(f"[{ip}]   info: {info}")
            return 0
        if "pack" in envelope:
            print(f"[{ip}]   → V1 protocol detected (AES-ECB).")
            if decrypt:
                try:
                    info = _decrypt_v1(envelope["pack"])
                except Exception as err:
                    print(f"[{ip}]   ✗ V1 decrypt failed: {err}")
                    return 4
                print(f"[{ip}]   info: {info}")
            return 0
        print(f"[{ip}]   ?? unknown envelope: {envelope}")
        return 5
    finally:
        sock.close()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ips", nargs="+", help="Device IP addresses")
    parser.add_argument(
        "--decrypt",
        action="store_true",
        help="Also decrypt the dev info using the matching generic key.",
    )
    args = parser.parse_args(argv)
    rc = 0
    for ip in args.ips:
        rc = max(rc, probe(ip, args.decrypt))
        print()
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
