"""最小后端骨架：标准库 http.server，无第三方依赖。

接口（形状与 demo/js/adapters.js 的 5 个 Mock 对齐）：

  GET  /health                      → {ok, embedder, stats}
  GET  /search?q=..&corpus=..&k=5   → [{title, meta, hit, tag}]   ← 对齐 MockRAG.search
  POST /search  {query, corpus, k}  → 同上
  POST /ingest  {doc_id, text, ...} → {doc_id, chunks}
  GET  /stats                       → 各类计数

契约要点（第 1–2 轮修正）：
- `corpus` 可为 null / doc_id 字符串 / 数组（前端 mock 传的是数组），
  归一逻辑在 store.normalize_corpus；过滤为空时退化全库并标 `_corpus_fallback`。
- **空 query 不报错**（mock 的行为是返回全量），返回 200 + 前 k 块。
- 任何异常都返回结构化 JSON，不抛栈给前端（对应 A-W1-1 契约 v1.1「永不 reject」）。

刻意不做（留给 W3）：鉴权、并发优化、真 embedding、/structure。
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import rag
import store

HERE = os.path.dirname(os.path.abspath(__file__))
SEED_DIR = os.path.join(HERE, "seed")

SEED_META = {
    "cs_红黑树.md": dict(course="数据结构", chapter="平衡树", kp_name="红黑树旋转",
                        difficulty="难", source="课件", version="v1"),
    "zh_文心雕龙.md": dict(course="中国古代文学", chapter="文心雕龙", kp_name="神思与虚静",
                         difficulty="中", source="教材", version="v1"),
}


def _parse_k(raw, default: int = 5, lo: int = 1, hi: int = 50) -> int:
    """k 只接受 1..50 的整数；非法值直接夹到合法区间，不抛异常（第 2 轮修正：
    原来 k=xx 会导致 500，内部异常不该外泄）。"""
    try:
        k = int(str(raw).strip())
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, k))


def ensure_seeded() -> list[str]:
    store.init_db()
    if store.stats()["chunks"] > 0:
        return []
    ingested = []
    if not os.path.isdir(SEED_DIR):
        return ingested
    for fn in sorted(os.listdir(SEED_DIR)):
        if not fn.endswith(".md"):
            continue
        m = SEED_META.get(fn, dict(course="未分类", chapter="", kp_name="", source=fn, version="v1"))
        r = store.ingest_file(os.path.join(SEED_DIR, fn), **m)
        ingested.append(r["doc_id"])
    return ingested


class Handler(BaseHTTPRequestHandler):
    server_version = "StudyFlowBackend/0.3"

    def _send(self, code: int, payload) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _safe(self, fn) -> None:
        """统一异常出口：任何内部错误都变成 JSON，不把栈丢给前端。"""
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc(file=sys.stderr)
            self._send(500, {"error": type(exc).__name__, "message": str(exc)})

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("[backend] %s\n" % (fmt % args))

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send(204, {})

    def _do_search(self, query: str, corpus, k: int, min_score=None) -> None:
        self._send(200, store.search(query, corpus, k, min_score=min_score))

    def do_GET(self) -> None:  # noqa: N802
        u = urlparse(self.path)
        q = parse_qs(u.query)

        def run() -> None:
            if u.path == "/health":
                self._send(200, {"ok": True, "embedder": rag.HashingEmbedder().name, "stats": store.stats()})
                return
            if u.path == "/stats":
                self._send(200, store.stats())
                return
            if u.path == "/search":
                query = (q.get("q") or q.get("query") or [""])[0]
                corpus = (q.get("corpus") or [None])[0]
                k = _parse_k((q.get("k") or ["5"])[0])
                ms = (q.get("min_score") or [None])[0]
                self._do_search(query, corpus, k, ms)
                return
            self._send(404, {"error": "not_found", "path": u.path})

        self._safe(run)

    def do_POST(self) -> None:  # noqa: N802
        u = urlparse(self.path)

        def run() -> None:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                data = json.loads(raw or b"{}")
            except json.JSONDecodeError:
                self._send(400, {"error": "invalid_json"})
                return
            if not isinstance(data, dict):
                self._send(400, {"error": "body_must_be_object"})
                return

            if u.path == "/search":
                self._do_search(
                    data.get("query") or data.get("q") or "",
                    data.get("corpus"),
                    _parse_k(data.get("k", 5)),
                    data.get("min_score"),
                )
                return

            if u.path == "/ingest":
                if not data.get("text"):
                    self._send(400, {"error": "missing_text"})
                    return
                doc_id = data.get("doc_id") or "doc"
                meta = {k: data.get(k, "") for k in
                        ("course", "chapter", "kp_name", "difficulty", "source", "version")}
                self._send(200, store.ingest_document(doc_id, data["text"], **meta))
                return

            self._send(404, {"error": "not_found", "path": u.path})

        self._safe(run)


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    seeded = ensure_seeded()
    s = store.stats()
    print("=" * 62)
    print("StudyFlow 最小后端已启动")
    print(f"  地址     http://127.0.0.1:{port}")
    print(f"  数据库   {s['db']}")
    print(f"  资料块   {s['chunks']} 块 / {s['docs']} 份")
    print(f"  embedder {rag.HashingEmbedder().name}（零依赖，W3 可换真 embedding）")
    if seeded:
        print(f"  本次导入 {seeded}")
    print("=" * 62)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
