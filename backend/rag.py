"""最小 RAG 内核：分块 + 向量 + 检索。

设计约束（W2 环境真实条件）：
- **纯标准库**，零第三方依赖（这台机器 pip 连不上 PyPI）。
- 向量用「字符 n-gram 哈希」而不是神经网络 embedding：
  中文不需要分词、不需要模型文件、256 维、可复现。
  它在"术语/人名/公式符号"上的召回足够支撑 W2 的检索验证；
  W3 换成真 embedding 时，只要实现下面 Embedder 接口即可，存储与检索代码不用改。

替换点只有一处：`HashingEmbedder` → `ApiEmbedder`（调百炼 text-embedding）。
"""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata

DIM = 256


def normalize(text: str) -> str:
    """全角转半角 + 小写，避免「ＡＢＣ」和「abc」被当成两个词。"""
    return unicodedata.normalize("NFKC", text or "").lower()


def ngrams(text: str, sizes=(1, 2, 3)) -> list[str]:
    """字符 n-gram。中文按字切、英文按字符切，不依赖分词器。"""
    t = re.sub(r"\s+", "", normalize(text))
    out: list[str] = []
    for n in sizes:
        if len(t) < n:
            continue
        out.extend(t[i : i + n] for i in range(len(t) - n + 1))
    return out


class HashingEmbedder:
    """零依赖 embedder：n-gram 哈希到固定维度，带符号桶，L2 归一化。"""

    name = "hashing-ngram-256"

    def __init__(self, dim: int = DIM) -> None:
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for g in ngrams(text):
            h = int.from_bytes(hashlib.blake2b(g.encode("utf-8"), digest_size=8).digest(), "big")
            idx = h % self.dim
            sign = 1.0 if (h >> 63) & 1 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


def cosine(a: list[float], b: list[float]) -> float:
    """两个已归一化向量的余弦相似度 = 点积。"""
    return sum(x * y for x, y in zip(a, b))


# ---- 分块 -------------------------------------------------------------------
# 规则：按 markdown 标题切成小节，小节超过 MAX_CHARS 再按句子切。
# 每块保留页码与序号，供「点回原始位置」用（对应 A-W1-1 的 sections[].src 约定）。

MAX_CHARS = 320


def chunk_text(text: str, max_chars: int = MAX_CHARS) -> list[dict]:
    """返回 [{ord, heading, page, text}]。page 由 form feed (\\f) 或 [第N页] 标记推算。"""
    text = text.replace("\r\n", "\n")
    blocks: list[dict] = []
    page = 1
    heading = ""
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf
        if not buf:
            return
        body = "\n".join(buf).strip()
        if body:
            for piece in _split_long(body, max_chars):
                blocks.append({"ord": len(blocks), "heading": heading, "page": page, "text": piece})
        buf = []

    for line in text.split("\n"):
        m_page = re.match(r"^\s*\[第(\d+)页\]\s*$", line)
        if m_page:
            flush()
            page = int(m_page.group(1))
            continue
        if line.strip() == "\f":
            flush()
            page += 1
            continue
        if line.startswith("#"):
            flush()
            heading = line.lstrip("#").strip()
            continue
        buf.append(line)
    flush()
    return blocks


def _split_long(body: str, max_chars: int) -> list[str]:
    if len(body) <= max_chars:
        return [body]
    parts = re.split(r"(?<=[。！？；\.\!\?;])", body)
    out: list[str] = []
    cur = ""
    for p in parts:
        if len(cur) + len(p) > max_chars and cur:
            out.append(cur.strip())
            cur = p
        else:
            cur += p
    if cur.strip():
        out.append(cur.strip())
    # 极长单句再硬切
    final: list[str] = []
    for s in out:
        while len(s) > max_chars:
            final.append(s[:max_chars])
            s = s[max_chars:]
        if s.strip():
            final.append(s)
    return final
