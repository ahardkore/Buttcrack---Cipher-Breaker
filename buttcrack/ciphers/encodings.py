"""Encoding layers: base64 and friends, hex, URL, binary, decimal.

These are not ciphers -- they are reversible *representations* -- but they are
the reason real-world puzzles feel "complex": the interesting payload is almost
never bare, it is ``base64(hex(rot13(...)))``.  Each layer here implements
:meth:`decodable`, a conservative test that says "stripping me is plausible",
which is what lets the engine peel a stack recursively without trying to
base64-decode English prose.

Every layer returns the *inner* payload as text so the next layer, or a
classical attack, can continue.
"""

from __future__ import annotations

import base64
import binascii
import re
import urllib.parse
from typing import Any, Iterator

from .base import CHEAP, CipherInfo, Family, LayerCipher

HEX_RE = re.compile(r"^[0-9a-fA-F]+$")
B64_RE = re.compile(r"^[A-Za-z0-9+/\-_]+={0,2}$")
B32_RE = re.compile(r"^[A-Z2-7]+={0,6}$")
B58_RE = re.compile(r"^[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]+$")
B85_RE = re.compile(r"^[\x21-\x75\s]+$")  # ASCII85 spans 0x21-0x75
BIN_RE = re.compile(r"^[01\s]+$")
DEC_RE = re.compile(r"^\d+([,\s;]+|$)")
URL_RE = re.compile(r"%[0-9A-Fa-f]{2}")
#: Everything that may appear in percent-encoded text (RFC 3986 unreserved plus
#: the characters ``quote(..., safe="")`` leaves alone in practice).
URL_SAFE_RE = re.compile(r"[A-Za-z0-9%_.~!*'()+,;:@/?\[\]=&$# -]+")


def _squash(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _to_text(data: bytes) -> str:
    """Decode bytes for the next layer, preferring strict UTF-8."""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1", "replace")


class _Encoding(LayerCipher):
    """Common behaviour: cheap, keyless, layer-capable."""

    family = Family.ENCODING

    def encrypt(self, plaintext: str, key: Any = None) -> str:
        return self.encode(plaintext)

    def decrypt(self, ciphertext: str, key: Any = None) -> str:
        out = self.decode(ciphertext)
        return out if isinstance(out, str) else _to_text(out or b"")

    def encode(self, text: str) -> str:
        raise NotImplementedError

    def keys(self) -> Iterator[None]:
        yield None


class Base64(_Encoding):
    """Base64, including the URL-safe alphabet and missing padding."""

    info = CipherInfo(
        name="base64",
        title="Base64",
        family=Family.ENCODING,
        keyed=False,
        key_type="none",
        keyspace=1,
        min_length=4,
        cost=CHEAP,
        layer=True,
        aliases=("b64", "base_64"),
        description="6 bits per character over A-Za-z0-9+/ (or -_ for URLs), padded to a multiple of 4.",
    )

    def decodable(self, text: str) -> bool:
        s = _squash(text)
        if len(s) < 12 or not B64_RE.match(s):
            return False
        # Real base64 of ASCII text mixes cases and usually contains a digit or
        # a padding/+// character.  A bare A-Z stream (classical ciphertext)
        # would otherwise be "decoded" into noise on every single run.
        has_digit = any(c.isdigit() for c in s)
        has_symbol = any(c in "+/=" for c in s)
        mixed_case = any(c.isupper() for c in s) and any(c.islower() for c in s)
        if not (has_digit or has_symbol or mixed_case):
            return False
        body = s.rstrip("=")
        # Base64 of ASCII text almost always starts with a letter or digit run
        # and has a length that is 0, 2 or 3 mod 4 once padding is removed.
        if len(body) % 4 == 1:
            return False
        try:
            self.decode(text)
            return True
        except Exception:
            return False

    def encode(self, text: str) -> str:
        return base64.b64encode(text.encode()).decode()

    def decode(self, text: str) -> bytes:
        s = _squash(text).replace("-", "+").replace("_", "/")
        s += "=" * (-len(s) % 4)
        return base64.b64decode(s, validate=True)


class Base32(_Encoding):
    """Base32 (RFC 4648): A-Z and 2-7."""

    info = CipherInfo(
        name="base32",
        title="Base32",
        family=Family.ENCODING,
        keyed=False,
        key_type="none",
        keyspace=1,
        min_length=8,
        cost=CHEAP,
        layer=True,
        description="5 bits per character over A-Z2-7, padded to a multiple of 8.",
    )

    def decodable(self, text: str) -> bool:
        raw = _squash(text)
        s = raw.upper()
        if len(s) < 8 or not B32_RE.match(s):
            return False
        # Require a 2-7 digit or padding: an all-letter A-Z stream is classical
        # ciphertext far more often than it is base32.
        if not any(c in "234567=" for c in s):
            return False
        if len(s.rstrip("=")) % 8 in (1, 3, 6):
            return False
        try:
            base64.b32decode(s + "=" * (-len(s) % 8), casefold=False)
            return True
        except (binascii.Error, ValueError):
            return False

    def encode(self, text: str) -> str:
        return base64.b32encode(text.encode()).decode()

    def decode(self, text: str) -> bytes:
        s = _squash(text).upper()
        return base64.b32decode(s + "=" * (-len(s) % 8))


class Base16(_Encoding):
    """Hexadecimal (base16)."""

    info = CipherInfo(
        name="base16",
        title="Hex / base16",
        family=Family.ENCODING,
        keyed=False,
        key_type="none",
        keyspace=1,
        min_length=4,
        cost=CHEAP,
        layer=True,
        aliases=("hex", "base_16"),
        description="4 bits per hex digit. Requires an even number of digits and at least one a-f.",
    )

    def decodable(self, text: str) -> bool:
        s = _squash(text)
        return bool(len(s) >= 4 and len(s) % 2 == 0 and HEX_RE.match(s) and re.search(r"[a-fA-F]", s))

    def encode(self, text: str) -> str:
        return text.encode().hex()

    def decode(self, text: str) -> bytes:
        return bytes.fromhex(_squash(text))


class Base58(_Encoding):
    """Base58 (Bitcoin alphabet): no 0, O, I or l."""

    info = CipherInfo(
        name="base58",
        title="Base58",
        family=Family.ENCODING,
        keyed=False,
        key_type="none",
        keyspace=1,
        min_length=10,
        cost=CHEAP,
        layer=True,
        description="Big-integer base58 over the Bitcoin alphabet, leading '1's encode leading zero bytes.",
    )
    ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

    def decodable(self, text: str) -> bool:
        s = _squash(text)
        if len(s) < 16 or not B58_RE.match(s):
            return False
        mixed_case = any(c.isupper() for c in s) and any(c.islower() for c in s)
        return mixed_case and any(c.isdigit() for c in s)

    def encode(self, text: str) -> str:
        data = text.encode()
        n = int.from_bytes(data, "big")
        out = ""
        while n > 0:
            n, r = divmod(n, 58)
            out = self.ALPHABET[r] + out
        pad = len(data) - len(data.lstrip(b"\x00"))
        return self.ALPHABET[0] * pad + out

    def decode(self, text: str) -> bytes:
        s = _squash(text)
        n = 0
        for ch in s:
            idx = self.ALPHABET.index(ch)
            if idx < 0:
                raise ValueError(f"{ch!r} is not base58")
            n = n * 58 + idx
        pad = len(s) - len(s.lstrip(self.ALPHABET[0]))
        body = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
        return b"\x00" * pad + body


class Base85(_Encoding):
    """ASCII85 / base85."""

    info = CipherInfo(
        name="base85",
        title="ASCII85 / base85",
        family=Family.ENCODING,
        keyed=False,
        key_type="none",
        keyspace=1,
        min_length=6,
        cost=CHEAP,
        layer=True,
        aliases=("ascii85", "base_85"),
        description="5 bytes per 5 characters over the printable ASCII range; ``<~ ~>`` delimiters optional.",
    )

    def decodable(self, text: str) -> bool:
        s = text.strip()
        if s.startswith("<~") and s.endswith("~>"):
            return True
        s = _squash(s)
        if len(s) < 10 or not B85_RE.match(s):
            return False
        # ASCII85 packs 4 bytes into 5 printable characters, so its output is
        # *saturated* with punctuation (~25%) and its length can never leave a
        # remainder of 1 when divided by 5.  Prose squashed of whitespace has
        # almost no punctuation, which is what keeps an ordinary sentence from
        # being "decoded" as base85.
        punct = [c for c in s if not c.isalnum()]
        if len(punct) / len(s) < 0.10 or len(set(punct)) < 3:
            return False
        return len(s) % 5 != 1

    def encode(self, text: str) -> str:
        return base64.a85encode(text.encode()).decode()

    def decode(self, text: str) -> bytes:
        s = text.strip()
        if s.startswith("<~"):
            s = s[2:]
        if s.endswith("~>"):
            s = s[:-2]
        try:
            return base64.a85decode(_squash(s))
        except ValueError:
            return base64.b85decode(_squash(s))


class PercentEncoding(_Encoding):
    """URL percent-encoding."""

    info = CipherInfo(
        name="url",
        title="URL encoding",
        family=Family.ENCODING,
        keyed=False,
        key_type="none",
        keyspace=1,
        min_length=3,
        cost=CHEAP,
        layer=True,
        aliases=("percent", "url_encoding"),
        description="Bytes as %XX hex escapes.",
    )

    def decodable(self, text: str) -> bool:
        """Only for text that really is percent-encoded.

        A single stray ``%41`` turns up inside binary payloads -- an XOR message
        decoded from hex will contain one often enough -- and peeling it silently
        deletes characters from the middle of the stream.  So the whole text has
        to be URL-safe and carry more than one escape.
        """
        squashed = _squash(text)
        if squashed.count("%") < 2 or not URL_SAFE_RE.fullmatch(squashed):
            return False
        return len(URL_RE.findall(squashed)) >= 2

    def encode(self, text: str) -> str:
        return urllib.parse.quote(text, safe="")

    def decode(self, text: str) -> str:
        return urllib.parse.unquote(text)


class BinaryASCII(_Encoding):
    """Binary (base2) representation of ASCII bytes."""

    info = CipherInfo(
        name="binary",
        title="Binary ASCII",
        family=Family.ENCODING,
        keyed=False,
        key_type="none",
        keyspace=1,
        min_length=8,
        cost=CHEAP,
        layer=True,
        aliases=("base2", "bits"),
        description="Each byte as 8 bits, separated by spaces (or run together).",
    )

    def decodable(self, text: str) -> bool:
        s = _squash(text)
        return bool(len(s) >= 16 and len(s) % 8 == 0 and BIN_RE.match(s))

    def encode(self, text: str) -> str:
        return " ".join(f"{b:08b}" for b in text.encode())

    def decode(self, text: str) -> bytes:
        s = _squash(text)
        return bytes(int(s[i : i + 8], 2) for i in range(0, len(s), 8))


class DecimalASCII(_Encoding):
    """Decimal (or hex/octal) byte values separated by spaces."""

    info = CipherInfo(
        name="decimal_ascii",
        title="Decimal ASCII",
        family=Family.ENCODING,
        keyed=False,
        key_type="none",
        keyspace=1,
        min_length=4,
        cost=CHEAP,
        layer=True,
        aliases=("ascii_decimal", "byte_values"),
        description="Byte values in decimal, separated by spaces or commas (0x.. and octal are also accepted).",
    )

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return [t for t in re.split(r"[\s,;|]+", text.strip()) if t]

    def decodable(self, text: str) -> bool:
        tokens = self._tokens(text)
        if len(tokens) < 3:
            return False
        values = []
        for t in tokens:
            try:
                values.append(int(t, 0) if t.lower().startswith("0x") else int(t))
            except ValueError:
                return False
        return all(9 <= v <= 126 for v in values)

    def encode(self, text: str) -> str:
        return " ".join(str(b) for b in text.encode())

    def decode(self, text: str) -> str:
        out = []
        for t in self._tokens(text):
            out.append(chr(int(t, 0) if t.lower().startswith("0x") else int(t)))
        return "".join(out)
