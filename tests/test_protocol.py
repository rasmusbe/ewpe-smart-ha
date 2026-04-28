"""Unit tests for the AES wire-format helpers."""
from __future__ import annotations

import pytest

from custom_components.ewpe_smart.protocol import (
    EwpeAuthError,
    decrypt,
    encrypt,
)


def test_encrypt_decrypt_roundtrip_default_key() -> None:
    payload = {"t": "scan"}
    cipher = encrypt(payload)
    assert decrypt(cipher) == payload


def test_encrypt_decrypt_roundtrip_device_key() -> None:
    key = b"abcdefghijklmnop"
    payload = {
        "cols": ["Pow", "Mod", "SetTem"],
        "mac": "AA:BB:CC:DD:EE:FF",
        "t": "status",
    }
    cipher = encrypt(payload, key)
    assert decrypt(cipher, key) == payload


def test_decrypt_with_wrong_key_raises_auth_error() -> None:
    payload = {"t": "bind", "uid": 0}
    cipher = encrypt(payload, b"abcdefghijklmnop")
    with pytest.raises(EwpeAuthError):
        decrypt(cipher, b"ponmlkjihgfedcba")


def test_encrypt_produces_ascii_base64() -> None:
    payload = {"t": "scan"}
    cipher = encrypt(payload)
    cipher.encode("ascii")  # would raise UnicodeEncodeError on non-ASCII
    assert len(cipher) % 4 == 0
