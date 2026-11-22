"""第 1 轮修复：接口语义对齐前端 MockRAG

发现的问题：
1. 前端 `MockRAG.search(query, corpus)` 的 corpus 是**数组**（scene().kb，内存过滤）；
   我原来把 corpus 当 doc_id 字符串用 → B 切换后会失效。
   修复：corpus 接受 null / 字符串 / 数组，数组时提取 doc_id 或 id 字段做过滤。
2. 前端空查询时 mock 返回整个 corpus；我原来返回 400。
   修复：空查询返回 200 + 库里前 k 块（不报错）。
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid

import rag

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(HERE, "schema.sql")


def db_path() -> str:
    """惰性解析数据库路径（第 3 轮修正：原来在 import 时固化，
    测试或换库时必须重开进程才生效）。"""
    return os.environ.get("STUDYFLOW_DB") or os.path.join(HERE, "data", "kb.sqlite3")


def _connect() -> sqlite3.Connection:
    path = db_path()
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# 当前 schema 里「后加的列」清单：旧库缺哪个就 ALTER 补哪个。
# CREATE TABLE IF NOT EXISTS 不会给已存在的表加列，所以必须显式补齐。
_ADDED_COLUMNS = {
    "chunk": {"kp_id": "TEXT"},
    "knowledge_point": {"related_courses": "TEXT DEFAULT ''"},
    "mastery_record": {
        "wrong_answer": "TEXT DEFAULT ''",
        "error_type": "TEXT DEFAULT ''",
        "first_cause": "TEXT DEFAULT ''",
        "review_count": "INTEGER DEFAULT 0",
        "mastery_status": "TEXT DEFAULT '未掌握'",
    },
}


def _migrate(conn: sqlite3.Connection) -> list[str]:
    """把旧库补齐到当前 schema（第 4 轮加，第 12 轮改为通用补列）。"""
    applied: list[str] = []
    for table, cols in _ADDED_COLUMNS.items():
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type=? AND name=?", ("table", table)
        ).fetchone()
        if not exists:
            continue
        have = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        for col, ddl in cols.items():
            if col not in have:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
                applied.append(f"{table}.{col}")
    conn.commit()
    return applied


def init_db(conn: sqlite3.Connection | None = None) -> list[str]:
    """建库/升级。顺序很关键：schema.sql 里有 `CREATE INDEX ON chunk(kp_id)`，
    若旧库缺 kp_id 而先跑 schema 就会报 no such column —— 所以**先补列再建索引**
    （第 5 轮修正）。"""
    own = conn is None
    conn = conn or _connect()
    applied = _migrate(conn)          # ① 旧库先补列
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())  # ② 再建表/索引（新库一步到位）
    conn.commit()
    if own:
        conn.close()
    return applied


def normalize_corpus(corpus) -> list[str] | None:
    """把前端传来的 corpus 归一成 doc_id 列表。

    兼容三种：
    - None / "" → None（全库）
    - "doc_id"  → ["doc_id"]
    - [{doc_id|id|title...}] 或 ["doc_id"] → 提取可用标识
    """
    if corpus in (None, "", [], {}):
        return None
    if isinstance(corpus, str):
        return [corpus]
    if isinstance(corpus, (list, tuple)):
        out: list[str] = []
        for it in corpus:
            if isinstance(it, str):
                out.append(it)
            elif isinstance(it, dict):
                for k in ("doc_id", "id", "title"):
                    v = it.get(k)
                    if isinstance(v, str) and v:
                        out.append(v)
                        break
        return out or None
    return None


def ingest_document(
    doc_id: str,
    text: str,
    *,
    course: str = "",
    chapter: str = "",
    kp_name: str = "",
    kp_id: str = "",
    difficulty: str = "",
    source: str = "",
    version: str = "v1",
    conn: sqlite3.Connection | None = None,
) -> dict:
    own = conn is None
    conn = conn or _connect()
    emb = rag.HashingEmbedder()

    conn.execute("DELETE FROM chunk_vec WHERE chunk_id IN (SELECT id FROM chunk WHERE doc_id=?)", (doc_id,))
    conn.execute("DELETE FROM chunk WHERE doc_id=?", (doc_id,))

    pieces = rag.chunk_text(text)
    n = 0
    for p in pieces:
        cur = conn.execute(
            """INSERT INTO chunk (doc_id,course,chapter,kp_id,kp_name,difficulty,source,version,page,ord,text)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (doc_id, course, chapter, kp_id or None, kp_name, difficulty, source, version, p["page"], p["ord"], p["text"]),
        )
        cid = cur.lastrowid
        vec = emb.embed(f"{kp_name} {chapter} {p['text']}")
        conn.execute(
            "INSERT INTO chunk_vec (chunk_id,dim,vec) VALUES (?,?,?)",
            (cid, len(vec), json.dumps(vec, separators=(",", ":"))),
        )
        n += 1
    conn.commit()
    result = {"doc_id": doc_id, "chunks": n, "embedder": emb.name}
    if own:
        conn.close()
    return result


def ingest_file(path: str, **meta) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    doc_id = meta.pop("doc_id", None) or os.path.splitext(os.path.basename(path))[0]
    return ingest_document(doc_id, text, **meta)


def _row_to_item(r: sqlite3.Row, score: float | None = None) -> dict:
    meta_bits = [r["source"] or r["doc_id"]]
    if r["page"]:
        meta_bits.append(f"第 {r['page']} 页")
    if score is not None:
        meta_bits.append(f"相似度 {score:.3f}")
    return {
        "title": r["kp_name"] or r["chapter"] or r["doc_id"],
        "meta": " · ".join(meta_bits),
        "hit": r["text"][:180],
        "tag": r["kp_name"] or r["chapter"] or "",
        "_score": None if score is None else round(score, 4),
        "_doc_id": r["doc_id"],
        "_page": r["page"],
        "_ord": r["ord"],
    }


DEFAULT_MIN_SCORE = 0.15


def search(
    query: str,
    corpus=None,
    k: int = 5,
    conn: sqlite3.Connection | None = None,
    min_score: float | None = None,
) -> list[dict]:
    """返回 [{title, meta, hit, tag}]，与 MockRAG.search 的返回形状一致。

    两个语义要点（第 11 轮按外部复核补）：
    1. **无命中返回 []**，而不是硬凑 k 条。
       原实现永远返回 scored[:k]，导致搜「量子力学」也返回红黑树段落（0.13/0.12/0.08），
       而前端 app.js 的兜底是 `res.length ? res : scene().kb` —— 永远不触发，界面会一本正经列垃圾。
    2. 空 query 仍按 ord 返回前 k 块（对应 mock「空查询返回全量」），**不受 min_score 限制**。
    """
    own = conn is None
    conn = conn or _connect()
    doc_ids = normalize_corpus(corpus)
    threshold = DEFAULT_MIN_SCORE if min_score is None else float(min_score)

    where, params = "", ()
    if doc_ids:
        where = " WHERE c.doc_id IN (%s)" % ",".join("?" * len(doc_ids))
        params = tuple(doc_ids)

    q = (query or "").strip()
    if not q:
        rows = conn.execute(
            f"SELECT c.* FROM chunk c{where} ORDER BY c.doc_id, c.ord LIMIT ?", params + (k,)
        ).fetchall()
        out = [_row_to_item(r) for r in rows]
        if own:
            conn.close()
        return out

    emb = rag.HashingEmbedder()
    qv = emb.embed(q)
    rows = conn.execute(
        f"SELECT c.*, v.vec AS vec FROM chunk c JOIN chunk_vec v ON v.chunk_id=c.id{where}", params
    ).fetchall()

    # 容忍退化：前端若把「自己的 kb 数组」传进来（title 不是 doc_id），
    # 过滤后会空。此时退回全库，并标记 _corpus_fallback，避免静默返回空。
    fallback = False
    if not rows and doc_ids:
        fallback = True
        rows = conn.execute(
            "SELECT c.*, v.vec AS vec FROM chunk c JOIN chunk_vec v ON v.chunk_id=c.id"
        ).fetchall()

    scored = [(rag.cosine(qv, json.loads(r["vec"])), r) for r in rows]
    scored.sort(key=lambda x: x[0], reverse=True)

    # 无命中返回 []：低于阈值的一律丢弃，让前端的「没找到就回退场景语料」能真正触发。
    hits = [(s, r) for s, r in scored if s >= threshold]
    out = [_row_to_item(r, s) for s, r in hits[:k]]
    if fallback:
        for it in out:
            it["_corpus_fallback"] = True
    if own:
        conn.close()
    return out

def stats(conn: sqlite3.Connection | None = None) -> dict:
    own = conn is None
    conn = conn or _connect()
    q = lambda s: conn.execute(s).fetchone()[0]
    out = {
        "chunks": q("SELECT COUNT(*) FROM chunk"),
        "docs": q("SELECT COUNT(DISTINCT doc_id) FROM chunk"),
        "knowledge_point": q("SELECT COUNT(*) FROM knowledge_point"),
        "question": q("SELECT COUNT(*) FROM question"),
        "mastery_record": q("SELECT COUNT(*) FROM mastery_record"),
        "db": db_path(),
    }
    if own:
        conn.close()
    return out


def add_knowledge_point(kp_id: str, course: str, chapter: str, name: str, **kw) -> None:
    conn = _connect()
    conn.execute(
        """INSERT OR REPLACE INTO knowledge_point (id,course,chapter,name,prereq,difficulty,source,version)
           VALUES (?,?,?,?,?,?,?,?)""",
        (kp_id, course, chapter, name, kw.get("prereq", ""), kw.get("difficulty", ""),
         kw.get("source", ""), kw.get("version", "v1")),
    )
    conn.commit()
    conn.close()


def add_mastery(kp_id: str, correct: bool, score: float = 0.0, stuck_sec: int = 0, note: str = "", qid: str = "") -> None:
    conn = _connect()
    conn.execute(
        """INSERT INTO mastery_record (id,kp_id,qid,correct,score,stuck_sec,note)
           VALUES (?,?,?,?,?,?,?)""",
        (uuid.uuid4().hex[:12], kp_id, qid, 1 if correct else 0, score, stuck_sec, note),
    )
    conn.commit()
    conn.close()
