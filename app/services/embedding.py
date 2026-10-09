import hashlib
import json
import math
import re

DIMENSIONS = 96


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]{2,}", text.lower())


def text_embedding(text: str) -> list[float]:
    vec = [0.0] * DIMENSIONS
    for token in tokenize(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:2], "big") % DIMENSIONS
        sign = 1.0 if digest[2] % 2 == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]


def text_embedding_json(text: str) -> str:
    return json.dumps(text_embedding(text))


def load_embedding(raw: str) -> list[float]:
    try:
        data = json.loads(raw or "[]")
        if isinstance(data, list):
            return [float(x) for x in data]
    except Exception:
        pass
    return [0.0] * DIMENSIONS


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    return sum(a[i] * b[i] for i in range(n))
