"""契约与检索自测（标准库 unittest，零依赖）。

跑法：  python backend/tests/test_contract.py
    或 python -m unittest discover -s backend/tests

测什么（对应 W2「跑通最小 RAG demo」的验收面）：
1. 接口形状与 demo/js/adapters.js 的 MockRAG 一致（title/meta/hit/tag 四字段齐全）
2. corpus 参数三种形态都能吃（None / doc_id 字符串 / 前端 kb 对象数组）
3. 空 query 不报错（mock 的行为是返回全量）
4. 检索质量：三组跨学科查询各自命中本学科段落，不串科
5. 溯源：每条结果带页码
6. 导入幂等：同一 doc_id 重复导入不翻倍
7. 三核心数据对象 + 六标签的写入可用
8. 分块：按标题切、页码由 [第N页] 推算、超长块再切
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import unittest
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, BACKEND)

# 用工作区内的目录（系统 TEMP 不可写；且新建子目录会被 ACL 拦住，
# 所以测试库直接放在 backend/data/ 下的唯一文件名里，不建子目录）
_DATA_DIR = os.path.join(BACKEND, "data")
os.makedirs(_DATA_DIR, exist_ok=True)
_TMP = _DATA_DIR
os.environ["STUDYFLOW_DB"] = os.path.join(_DATA_DIR, f"test-{os.getpid()}-{uuid.uuid4().hex[:8]}.sqlite3")

import rag  # noqa: E402
import store  # noqa: E402

SEED_CS = os.path.join(BACKEND, "seed", "cs_红黑树.md")
SEED_ZH = os.path.join(BACKEND, "seed", "zh_文心雕龙.md")

CS_META = dict(course="数据结构", chapter="平衡树", kp_name="红黑树旋转", difficulty="难", source="课件")
ZH_META = dict(course="中国古代文学", chapter="文心雕龙", kp_name="神思与虚静", difficulty="中", source="教材")


def setUpModule() -> None:
    store.init_db()
    store.ingest_file(SEED_CS, **CS_META)
    store.ingest_file(SEED_ZH, **ZH_META)


class TestContractShape(unittest.TestCase):
    """1. 与 MockRAG 的返回形状一致。"""

    def test_required_fields(self):
        items = store.search("虚静", None, 3)
        self.assertTrue(items, "检索不该返回空")
        for it in items:
            for field in ("title", "meta", "hit", "tag"):
                self.assertIn(field, it, f"缺少 mock 需要的字段 {field}")
            self.assertIsInstance(it["title"], str)
            self.assertIsInstance(it["hit"], str)

    def test_returns_plain_list(self):
        self.assertIsInstance(store.search("红黑树", None, 2), list)

    def test_json_serializable(self):
        """前端要 JSON.parse，必须能序列化且中文不转义损坏。"""
        raw = json.dumps(store.search("虚静", None, 2), ensure_ascii=False)
        self.assertIn("虚静", raw)


class TestCorpusTolerance(unittest.TestCase):
    """2. corpus 三种形态。"""

    def test_corpus_none(self):
        self.assertTrue(store.search("虚静", None, 2))

    def test_corpus_doc_id_string(self):
        items = store.search("虚静", "zh_文心雕龙", 2)
        self.assertTrue(items)
        self.assertTrue(all(i["_doc_id"] == "zh_文心雕龙" for i in items))

    def test_corpus_frontend_kb_array(self):
        """前端传的是 [{title,meta,hit,tag}]，不是 doc_id —— 不该静默返回空。"""
        fake_kb = [{"title": "无关", "meta": "", "hit": "", "tag": ""}]
        items = store.search("虚静", fake_kb, 2)
        self.assertTrue(items, "退化全库后不该为空")
        self.assertTrue(items[0].get("_corpus_fallback"), "应标记 _corpus_fallback")

    def test_corpus_string_list(self):
        self.assertTrue(store.search("虚静", ["zh_文心雕龙"], 2))

    def test_normalize_corpus_direct(self):
        self.assertIsNone(store.normalize_corpus(None))
        self.assertEqual(store.normalize_corpus("a"), ["a"])
        self.assertEqual(store.normalize_corpus([{"id": "b"}]), ["b"])


class TestEmptyQuery(unittest.TestCase):
    """3. 空查询不报错。"""

    def test_empty_returns_items(self):
        items = store.search("", None, 3)
        self.assertTrue(items, "空查询应返回前 k 块，而不是空或异常")

    def test_whitespace_only(self):
        self.assertTrue(store.search("   ", None, 2))


class TestRetrievalQuality(unittest.TestCase):
    """4. 跨学科不串。"""

    def test_cs_query_hits_cs(self):
        items = store.search("红黑树 不能有连续两个红结点", None, 3)
        self.assertEqual(items[0]["_doc_id"], "cs_红黑树")

    def test_zh_query_hits_zh(self):
        items = store.search("虚静 是什么意思", None, 3)
        self.assertEqual(items[0]["_doc_id"], "zh_文心雕龙")

    def test_cs_query_not_returning_zh_at_top1(self):
        items = store.search("左旋 右旋 指针", None, 1)
        self.assertNotEqual(items[0]["_doc_id"], "zh_文心雕龙", "理工查询不该把文学段落排第一")

    def test_score_descending(self):
        items = store.search("红黑树", None, 4)
        scores = [i["_score"] for i in items if i["_score"] is not None]
        self.assertEqual(scores, sorted(scores, reverse=True))


class TestTraceability(unittest.TestCase):
    """5. 溯源：带页码，能点回原始位置。"""

    def test_meta_has_page(self):
        items = store.search("虚静", None, 3)
        for it in items:
            self.assertIn("页", it["meta"], "meta 必须能定位到页码（溯源要求）")

    def test_page_is_int(self):
        items = store.search("虚静", None, 3)
        for it in items:
            self.assertIsInstance(it["_page"], int)
            self.assertGreaterEqual(it["_page"], 1)


class TestIngestIdempotent(unittest.TestCase):
    """6. 重复导入不翻倍。"""

    def test_reingest_same_doc(self):
        before = store.stats()["chunks"]
        store.ingest_file(SEED_CS, **CS_META)
        after = store.stats()["chunks"]
        self.assertEqual(before, after, "同一 doc_id 重复导入应幂等")


class TestDataObjects(unittest.TestCase):
    """7. 三核心数据对象可写。"""

    def test_add_knowledge_point(self):
        store.add_knowledge_point("kp_rb", "数据结构", "平衡树", "红黑树旋转", difficulty="难")
        self.assertGreaterEqual(store.stats()["knowledge_point"], 1)

    def test_add_mastery(self):
        store.add_mastery("kp_rb", correct=False, score=0.3, stuck_sec=42, note="卡在旋转方向")
        self.assertGreaterEqual(store.stats()["mastery_record"], 1)

    def test_schema_has_three_objects(self):
        conn = sqlite3.connect(os.environ["STUDYFLOW_DB"])
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        for t in ("knowledge_point", "question", "mastery_record"):
            self.assertIn(t, names, f"规格 §1.3 要求的三核心对象缺表 {t}")

    def test_chunk_with_kp_id_links(self):
        """第 9 轮回归：chunk.kp_id 是外键，空值必须存 NULL。

        存 '' 是非 NULL 值，在 knowledge_point 里找不到 → FOREIGN KEY constraint failed。
        """
        store.add_knowledge_point("kp_link", "数据结构", "平衡树", "红黑树旋转")
        r = store.ingest_document(
            "doc_with_kp", "# T\n\n红黑树的旋转。\n",
            course="数据结构", kp_id="kp_link", kp_name="红黑树旋转",
        )
        self.assertEqual(r["chunks"], 1)
        # 不挂知识点的资料块（kp_id 留空）也必须能导入
        r2 = store.ingest_document("doc_no_kp", "# T\n\n没有挂知识点。\n", course="数据结构")
        self.assertEqual(r2["chunks"], 1)


class TestChunking(unittest.TestCase):
    """8. 分块规则。"""

    def test_heading_split(self):
        blocks = rag.chunk_text("# A\n\n段落一。\n\n## B\n\n段落二。\n")
        self.assertGreaterEqual(len(blocks), 2)
        self.assertEqual(blocks[0]["heading"], "A")

    def test_page_marker(self):
        blocks = rag.chunk_text("[第1页]\n\n内容一。\n\n[第5页]\n\n内容五。\n")
        pages = [b["page"] for b in blocks]
        self.assertIn(1, pages)
        self.assertIn(5, pages)

    def test_long_block_split(self):
        long_text = "。" * 40 + "甲" * 400
        blocks = rag.chunk_text(long_text, max_chars=100)
        self.assertGreater(len(blocks), 1)
        for b in blocks:
            self.assertLessEqual(len(b["text"]), 100 + 5)

    def test_ord_sequential(self):
        blocks = rag.chunk_text("# T\n\n一。\n\n二。\n\n三。\n")
        self.assertEqual([b["ord"] for b in blocks], list(range(len(blocks))))


class TestEmbedder(unittest.TestCase):
    def test_dim_and_norm(self):
        v = rag.HashingEmbedder().embed("红黑树")
        self.assertEqual(len(v), rag.DIM)
        norm = sum(x * x for x in v) ** 0.5
        self.assertAlmostEqual(norm, 1.0, places=6)

    def test_deterministic(self):
        a = rag.HashingEmbedder().embed("虚静")
        b = rag.HashingEmbedder().embed("虚静")
        self.assertEqual(a, b)

    def test_cosine_self_is_one(self):
        v = rag.HashingEmbedder().embed("神思")
        self.assertAlmostEqual(rag.cosine(v, v), 1.0, places=6)


def tearDownModule() -> None:
    """删掉本次测试用的临时库。"""
    path = os.environ.get("STUDYFLOW_DB", "")
    for suffix in ("", "-wal", "-shm"):
        try:
            os.remove(path + suffix)
        except OSError:
            pass


class TestRelevanceThreshold(unittest.TestCase):
    """第 11 轮：无关查询必须返回 []，否则前端的「没找到就回退」永远不触发。"""

    def test_unrelated_query_returns_empty(self):
        for q in ("量子力学", "如何做红烧肉", "python decorator", "xyzzy plugh"):
            self.assertEqual(store.search(q, None, 3), [], f"无关查询「{q}」不该返回结果")

    def test_related_query_not_empty(self):
        for q in ("虚静", "旋转", "红黑树 不能有连续两个红结点"):
            self.assertTrue(store.search(q, None, 3), f"相关查询「{q}」不该为空")

    def test_empty_query_ignores_threshold(self):
        """空查询是「浏览」语义，不该被阈值拦住。"""
        self.assertTrue(store.search("", None, 3))

    def test_explicit_min_score_zero_returns_all(self):
        self.assertGreater(len(store.search("量子力学", None, 3, min_score=0.0)), 0)

    def test_all_hits_above_default_threshold(self):
        for it in store.search("红黑树", None, 5):
            self.assertGreaterEqual(it["_score"], store.DEFAULT_MIN_SCORE)




if __name__ == "__main__":
    unittest.main(verbosity=2)
