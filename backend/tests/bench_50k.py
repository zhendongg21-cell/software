"""50k 块暴力检索压测（W3 实验 3 的基线，验证 A-W2-1 §三 的 200ms 阈值差多少）

跑法： python backend/tests/bench_50k.py
"""
from __future__ import annotations

import json
import os
import sqlite3
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, BACKEND)

_DATA = os.path.join(BACKEND, "data")
os.makedirs(_DATA, exist_ok=True)
os.environ["STUDYFLOW_DB"] = os.path.join(_DATA, f"bench-{os.getpid()}.sqlite3")

import rag  # noqa: E402
import store  # noqa: E402

N = 50000
QUERIES = ["红黑树的旋转", "虚静的创作心理", "左旋右旋指针", "学习任务状态接续"]


def build(n: int) -> float:
    store.init_db()
    emb = rag.HashingEmbedder()
    conn = store._connect()
    t0 = time.time()
    # 直接批量写入，避免逐条 commit
    for i in range(n):
        text = f"第{i}块：数据结构与文学理论的混合样例文本，用于压测检索延迟。知识点{i % 997} 章节{i % 131}。"
        cur = conn.execute(
            """INSERT INTO chunk (doc_id,course,chapter,kp_id,kp_name,difficulty,source,version,page,ord,text)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (f"doc{i % 2000}", "压测", f"章{i % 131}", None, f"知识点{i % 997}", "", "bench", "v1", i % 500, i, text),
        )
        vec = emb.embed(text)
        conn.execute(
            "INSERT INTO chunk_vec (chunk_id,dim,vec) VALUES (?,?,?)",
            (cur.lastrowid, len(vec), json.dumps(vec, separators=(",", ":"))),
        )
        if i % 5000 == 0:
            conn.commit()
            print(f"  写入 {i}/{n}", flush=True)
    conn.commit()
    conn.close()
    return time.time() - t0


def measure(conn: sqlite3.Connection, n: int) -> list[float]:
    """模拟 store.search 的暴力路径：全表读入 + 逐条余弦。"""
    emb = rag.HashingEmbedder()
    rows = conn.execute("SELECT c.id, v.vec FROM chunk c JOIN chunk_vec v ON v.chunk_id=c.id").fetchall()
    vecs = [(r[0], json.loads(r[1])) for r in rows]
    times = []
    for q in QUERIES:
        qv = emb.embed(q)
        t0 = time.time()
        scored = [(rag.cosine(qv, v), cid) for cid, v in vecs]
        scored.sort(key=lambda x: x[0], reverse=True)
        _ = scored[:5]
        times.append((time.time() - t0) * 1000)
    return times


def main() -> None:
    db = os.environ["STUDYFLOW_DB"]
    for s in ("", "-wal", "-shm"):
        try:
            os.remove(db + s)
        except OSError:
            pass

    print(f"=== 50k 暴力检索压测 ===")
    print(f"  库: {db}")
    build_s = build(N)
    size_mb = os.path.getsize(db) / 1024 / 1024 if os.path.exists(db) else 0
    print(f"  写入 {N} 块耗时 {build_s:.1f}s，库大小 {size_mb:.0f} MB")

    conn = sqlite3.connect(db)
    # 预热
    measure(conn, 1)
    times = measure(conn, N)
    conn.close()

    print(f"  单次检索（{len(QUERIES)} 次）:")
    for q, ms in zip(QUERIES, times):
        print(f"    {q:16} {ms:8.1f} ms")
    p95 = sorted(times)[int(len(times) * 0.95) - 1] if len(times) > 1 else max(times)
    print(f"  中位数 {statistics.median(times):.0f} ms ｜ 最大 {max(times):.0f} ms ｜ P95 {p95:.0f} ms")
    print(f"  目标 200 ms → 差 {statistics.median(times) / 200:.1f} 倍")

    for s in ("", "-wal", "-shm"):
        try:
            os.remove(db + s)
        except OSError:
            pass


if __name__ == "__main__":
    main()
