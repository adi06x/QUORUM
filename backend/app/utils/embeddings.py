from __future__ import annotations

import hashlib
import math
import re


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9']+")


def embed_text(text: str, dimensions: int = 192) -> list[float]:
    vector = [0.0] * dimensions
    tokens = TOKEN_PATTERN.findall(text.lower())
    if not tokens:
        return vector

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        weight = 1.0 + (digest[5] / 255.0)
        vector[bucket] += sign * weight

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def embed_texts(texts: list[str], dimensions: int = 192) -> list[list[float]]:
    return [embed_text(text, dimensions=dimensions) for text in texts]

