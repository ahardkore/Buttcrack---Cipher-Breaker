"""Input limits and byte representations shared by the explicit crypto labs."""

from __future__ import annotations

import time

MAX_BYTES = 16384


def hex_bytes(value: object, name: str, *, limit: int = MAX_BYTES) -> bytes:
    if not isinstance(value, str) or len(value) > limit * 3:
        raise ValueError(f"{name} must be hex text (maximum {limit} bytes)")
    try:
        data = bytes.fromhex(value)
    except ValueError:
        raise ValueError(f"{name} must contain complete hexadecimal bytes") from None
    if len(data) > limit:
        raise ValueError(f"{name} exceeds {limit} bytes")
    return data


def integer(value: object, name: str, low: int, high: int) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    if isinstance(value, str):
        if len(value) > 1300:
            raise ValueError(f"{name} is too long")
        try:
            result = int(value, 16 if value.lower().startswith("0x") else 10)
        except ValueError:
            raise ValueError(f"{name} must be decimal or 0x-prefixed hex") from None
    elif isinstance(value, int):
        result = value
    else:
        raise ValueError(f"{name} must be an integer")
    if not low <= result <= high:
        raise ValueError(f"{name} must be between {low} and {high}")
    return result


def byte_result(data: bytes) -> dict:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = None
    return {"hex": data.hex(), "utf8": text, "bytes": len(data)}


def deadline(options: dict) -> float:
    budget = options.get("budget", 3)
    if isinstance(budget, bool) or not isinstance(budget, (int, float)) or not 0.1 <= budget <= 5:
        raise ValueError("budget must be between 0.1 and 5 seconds")
    return time.monotonic() + budget
