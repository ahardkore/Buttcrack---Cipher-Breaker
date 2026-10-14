"""AES known-key operations through a maintained provider, plus block analysis."""

from __future__ import annotations

from .common import byte_result, hex_bytes


def analyze(options: dict) -> dict:
    data = hex_bytes(options.get("data", ""), "data")
    operation = options.get("operation", "analyze")
    if operation == "analyze":
        blocks = [data[i:i + 16] for i in range(0, len(data) - 15, 16)]
        locations = {}
        for index, block in enumerate(blocks):
            locations.setdefault(block.hex(), []).append(index)
        repeats = [{"block_hex": block, "indices": indices} for block, indices in locations.items() if len(indices) > 1]
        return {"lab": "aes", "status": "block analysis only", "complete_blocks": len(blocks), "trailing_bytes": len(data) % 16, "repeated_blocks": repeats, "limitations": "Repeated aligned blocks are consistent with ECB, but do not prove AES or ECB. No repeated blocks does not rule out ECB. This does not recover any key."}
    if operation not in ("encrypt", "decrypt"):
        raise ValueError("operation must be analyze, encrypt or decrypt")
    try:
        from cryptography.exceptions import InvalidTag
        from cryptography.hazmat.primitives import padding
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    except ImportError:
        raise ValueError('AES operations require the optional provider: pip install "buttcrack[modern]". The Windows build bundles it.') from None
    key = hex_bytes(options.get("key", ""), "key", limit=32)
    if len(key) not in (16, 24, 32):
        raise ValueError("AES key must be 16, 24 or 32 bytes")
    mode = options.get("mode", "GCM")
    iv = hex_bytes(options.get("iv", ""), "iv/nonce", limit=16)
    tag = hex_bytes(options.get("tag", ""), "tag", limit=16)
    aad = hex_bytes(options.get("aad", ""), "aad")
    use_padding = options.get("padding", False)
    if not isinstance(use_padding, bool):
        raise ValueError("padding must be true or false")
    if mode in ("ECB", "CBC"):
        if mode == "ECB" and iv:
            raise ValueError("ECB does not use an IV")
        if mode == "CBC" and len(iv) != 16:
            raise ValueError("CBC IV must be 16 bytes")
        mode_object = modes.ECB() if mode == "ECB" else modes.CBC(iv)
    elif mode == "CTR":
        if len(iv) != 16 or use_padding:
            raise ValueError("CTR requires a 16-byte initial counter block and no padding")
        mode_object = modes.CTR(iv)
    elif mode == "GCM":
        if len(iv) != 12 or use_padding:
            raise ValueError("GCM requires a 12-byte nonce and no padding")
        if operation == "decrypt" and len(tag) != 16:
            raise ValueError("GCM decryption requires a separate 16-byte authentication tag")
        if operation == "encrypt" and tag:
            raise ValueError("Do not supply a tag when encrypting")
        mode_object = modes.GCM(iv, tag if operation == "decrypt" else None)
    else:
        raise ValueError("mode must be ECB, CBC, CTR or GCM")
    if mode != "GCM" and (tag or aad):
        raise ValueError("Tag and AAD are only used for GCM")
    original = data
    if operation == "encrypt" and use_padding:
        padder = padding.PKCS7(128).padder()
        data = padder.update(data) + padder.finalize()
    if mode in ("ECB", "CBC") and len(data) % 16:
        raise ValueError("ECB/CBC input must contain whole blocks; use PKCS#7 padding when encrypting")
    cipher = Cipher(algorithms.AES(key), mode_object)
    worker = cipher.encryptor() if operation == "encrypt" else cipher.decryptor()
    if mode == "GCM":
        worker.authenticate_additional_data(aad)
    try:
        output = worker.update(data) + worker.finalize()
    except InvalidTag:
        # No unauthenticated plaintext is ever returned.
        raise ValueError("GCM authentication failed: key, nonce, tag, AAD or ciphertext is incorrect") from None
    if operation == "decrypt" and use_padding:
        unpadder = padding.PKCS7(128).unpadder()
        try:
            output = unpadder.update(output) + unpadder.finalize()
        except ValueError:
            raise ValueError("Invalid PKCS#7 padding; check the key, IV, ciphertext and padding choice") from None
    result = {"lab": "aes", "status": f"known-key {operation}", "mode": mode, "output": byte_result(output), "authenticated": mode == "GCM" and operation == "decrypt", "limitations": "Uses a supplied key, not key recovery. ECB/CBC/CTR do not authenticate output; readable text or valid padding does not prove the key is correct. Use a unique nonce for every encryption under a GCM or CTR key. Keys and inputs are not persisted by this lab."}
    if mode == "GCM" and operation == "encrypt":
        result["tag"] = worker.tag.hex()
    if operation == "decrypt" and mode != "GCM":
        # Reproduction with a supplied key is evidence of implementation only.
        check = output
        if use_padding:
            padder = padding.PKCS7(128).padder()
            check = padder.update(check) + padder.finalize()
        encryptor = cipher.encryptor()
        result["round_trip_verified"] = encryptor.update(check) + encryptor.finalize() == original
    return result
