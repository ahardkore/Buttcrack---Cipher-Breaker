"""Bounded attacks on weak raw RSA parameters, not attacks on secure RSA/OAEP."""

from __future__ import annotations

import math
import time

from .common import byte_result, deadline, integer

MAX_INTEGER = (1 << 4096) - 1


def root(value: int, degree: int) -> tuple[int, bool]:
    if value == 0:
        return 0, True
    estimate = 1 << ((value.bit_length() + degree - 1) // degree)
    while True:
        next_estimate = ((degree - 1) * estimate + value // estimate ** (degree - 1)) // degree
        if next_estimate >= estimate:
            return estimate, estimate ** degree == value
        estimate = next_estimate



def wiener(n: int, e: int) -> tuple[int, int] | None:
    """Verify factors derived from convergents of e/n, not just a small d guess."""
    a, b = e, n
    h0, h1, k0, k1 = 0, 1, 1, 0
    while b:
        quotient, remainder = divmod(a, b)
        a, b = b, remainder
        h0, h1 = h1, quotient * h1 + h0
        k0, k1 = k1, quotient * k1 + k0
        k, d = h1, k1
        if not k or (e * d - 1) % k:
            continue
        phi = (e * d - 1) // k
        total = n - phi + 1
        discriminant = total * total - 4 * n
        if discriminant < 0:
            continue
        square = math.isqrt(discriminant)
        if square * square == discriminant and (total + square) % 2 == 0:
            p, q = (total + square) // 2, (total - square) // 2
            if p > 1 and q > 1 and p * q == n:
                return p, q
    return None


def probable_prime(n: int) -> bool:
    # Deterministic for n < 2**64; above that, these are probable-prime checks.
    if n < 2:
        return False
    for prime in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n % prime == 0:
            return n == prime
    odd, shift = n - 1, 0
    while odd % 2 == 0:
        odd //= 2
        shift += 1
    for base in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        base %= n
        if not base:
            continue
        x = pow(base, odd, n)
        if x in (1, n - 1):
            continue
        for _ in range(shift - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def plaintext(m: int) -> dict:
    return {"integer": str(m), **byte_result(m.to_bytes(max(1, (m.bit_length() + 7) // 8), "big"))}


def analyze(options: dict) -> dict:
    end = deadline(options)
    records = options.get("keys")
    if not isinstance(records, list) or not 1 <= len(records) <= 32:
        raise ValueError("keys must be a list of 1–32 objects containing n, e and optionally c")
    keys = []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Each RSA key must be an object")
        n = integer(record.get("n"), "n", 4, MAX_INTEGER)
        e = integer(record.get("e"), "e", 2, n - 1)
        c = integer(record["c"], "c", 0, n - 1) if "c" in record else None
        keys.append((n, e, c))
    steps = integer(options.get("fermat_steps", 1000), "fermat_steps", 0, 20000)
    findings, checks = [], []
    incomplete = False
    factored = set()

    def factors(index, p, q, attack):
        nonlocal incomplete
        if index in factored or p <= 1 or q <= 1 or p * q != keys[index][0]:
            return
        factored.add(index)
        n, e, c = keys[index]
        finding = {"key_index": index, "attack": attack, "p": str(p), "q": str(q), "factorization_verified": True}
        if time.monotonic() >= end:
            incomplete = True
            finding["private_key_recovery"] = "skipped: time budget exhausted"
            findings.append(finding)
            return
        if p != q and probable_prime(p) and probable_prime(q):
            finding["prime_check"] = "deterministic below 2^64; probable-prime checks for larger factors"
            phi = (p - 1) * (q - 1)
            if math.gcd(e, phi) == 1:
                d = pow(e, -1, phi)
                finding["d"] = str(d)
                if c is not None:
                    m = pow(c, d, n)
                    finding["reencryption_verified"] = pow(m, e, n) == c
                    if finding["reencryption_verified"]:
                        finding["raw_plaintext"] = plaintext(m)
        findings.append(finding)

    # Pairwise GCD also works for large moduli. Identical moduli are not factors.
    for i, (n, _, _) in enumerate(keys):
        for j in range(i):
            g = math.gcd(n, keys[j][0])
            if 1 < g < n:
                factors(i, g, n // g, "shared prime factor")
            if 1 < g < keys[j][0]:
                factors(j, g, keys[j][0] // g, "shared prime factor")
    checks.append("Pairwise GCD: all supplied moduli compared; identical moduli do not establish a factorization.")
    for index, (n, e, c) in enumerate(keys):
        if time.monotonic() >= end:
            incomplete = True
            break
        if n % 2 == 0:
            factors(index, 2, n // 2, "even modulus")
        if index not in factored:
            pair = wiener(n, e)
            if pair:
                factors(index, *pair, "Wiener small-private-exponent attack")
        if e <= 7 and c is not None:
            m, exact = root(c, e)
            if exact and pow(m, e, n) == c:
                findings.append({"key_index": index, "attack": "unwrapped low-exponent raw RSA", "raw_plaintext": plaintext(m), "reencryption_verified": True})
        if index in factored:
            continue
        a = math.isqrt(n)
        if a * a < n:
            a += 1
        examined = 0
        for _ in range(steps):
            if time.monotonic() >= end:
                incomplete = True
                break
            examined += 1
            b2 = a * a - n
            b = math.isqrt(b2)
            if b * b == b2 and a - b > 1:
                factors(index, a - b, a + b, "bounded Fermat close-factor search")
                break
            a += 1
        checks.append(f"Key {index}: {examined} Fermat candidates examined (configured limit {steps}).")
    # Broadcast: same unpadded message and exponent, enough coprime moduli.
    for e in (3, 5, 7):
        group = [(i, n, c) for i, (n, exponent, c) in enumerate(keys) if exponent == e and c is not None]
        if len(group) < e:
            continue
        if time.monotonic() >= end:
            incomplete = True
            break
        if any(math.gcd(left[1], right[1]) != 1 for i, left in enumerate(group) for right in group[:i]):
            checks.append(f"Broadcast e={e} skipped: supplied moduli are not pairwise coprime.")
            continue
        modulus = math.prod(n for _, n, _ in group)
        combined = sum(c * (modulus // n) * pow(modulus // n, -1, n) for _, n, c in group) % modulus
        m, exact = root(combined, e)
        if exact and all(m < n and pow(m, e, n) == c for _, n, c in group):
            findings.append({"key_indices": [i for i, _, _ in group], "attack": "low-exponent broadcast (same raw message)", "raw_plaintext": plaintext(m), "reencryption_verified": True})
    return {
        "lab": "rsa", "status": "weakness found" if findings else "no weakness found within these tests",
        "findings": findings, "checks": checks, "budget_exhausted": incomplete,
        "limitations": "Raw RSA only. No OAEP/PKCS#1 padding decoding. Re-encryption verifies arithmetic, not authenticity or intended meaning. No finding is not proof of security; these bounded checks do not factor secure arbitrary RSA moduli.",
    }
