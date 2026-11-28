# backend —— 最小知识库（W2 交付）

A 的 W2 任务之一：**搭后端骨架 + 跑通最小 RAG 知识库 demo**。

## 一句话

导入资料 → 切块 → 算向量 → 存 sqlite → 按语义检索，**整条链路可跑、可测、零第三方依赖**。

## 怎么跑

```bash
python backend/server.py
# 默认 http://127.0.0.1:8000，可用环境变量 PORT 覆盖
```

首次启动会把 `seed/` 下两份样例（CS 红黑树 / 中文文心雕龙）自动导入。

只依赖 Python 3.9+ 标准库（`sqlite3` / `http.server` / `hashlib` / `json`）。
**不需要 pip install 任何东西**——这台机器 pip 连不上 PyPI（试过 `pymupdf`、`pypdf` 均超时），这是实测约束。

## 怎么测

```bash
python backend/tests/test_contract.py
# 33 个用例，覆盖契约形状 / corpus 容错 / 空查询 / 检索质量 / 溯源 / 幂等 / 数据对象 / 分块 / embedder / 阈值
```

当前状态：**33 passed**（2026-11-22 复核）。测试库写在 `backend/data/test-*.sqlite3`，跑完自动删除。

## 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 + 统计 |
| GET | `/search?q=虚静&k=3&corpus=` | **检索** |
| POST | `/search` | body: `{"query":"...","corpus":null,"k":5}` |
| POST | `/ingest` | body: `{"doc_id","text","course","chapter","kp_name","kp_id","difficulty","source","version"}` |
| GET | `/stats` | 各类计数 |

`/search?q=虚静` 返回（数值为本机实测）：

```json
[{"title":"神思与虚静","meta":"教材 · 第 3 页 · 相似度 0.501",
  "hit":"「陶钧文思，贵在虚静」……","tag":"神思与虚静",
  "_score":0.5013,"_doc_id":"zh_文心雕龙","_page":3,"_ord":2}]
```

**前四个字段与 `demo/js/adapters.js` 的 `MockRAG.search` 返回形状一致**（`_` 开头的是调试字段），
所以 B 的界面切真实实现时，渲染代码不用改。

### 契约容错（踩过的坑，别再踩）

| 情况 | 行为 |
|---|---|
| `corpus` 传 `null` / 省略 | 全库检索 |
| `corpus` 传 doc_id 字符串 | 按该 doc 过滤 |
| `corpus` 传**前端自己的 kb 数组**（`[{title,meta,hit,tag}]`） | 提取不到 doc_id 时**退化全库**，并给每条结果加 `_corpus_fallback: true`（**不会静默返回空**） |
| 空 query（`q=`） | **返回 200 + 前 k 块**（对应 mock「空查询返回全量」的行为），不是 400 |
| `k` 非数字或越界 | 夹到 1..50，不报 500 |
| 内部异常 | 返回 `{error, message}` 的 JSON，不把栈丢给前端 |

## 文件

| 文件 | 作用 |
|---|---|
| `server.py` | HTTP 服务（stdlib），含参数校验与统一异常出口 |
| `rag.py` | 切块 + 向量 + 余弦（零依赖） |
| `store.py` | sqlite 存取 + 检索 + 轻量迁移 |
| `schema.sql` | **三核心数据对象**（知识点/题目/错题·掌握度）+ **六标签**（课程/章节/知识点/难度/来源/版本）+ 块与向量 |
| `tests/test_contract.py` | 33 个契约与检索用例 |
| `seed/` | 两份样例资料（理工 + 人文，对应赛题的跨专业场景） |

## 数据模型要点

- `chunk` 同时存 `kp_id`（外键 → `knowledge_point.id`）和 `kp_name`（显示用）。
  **只有 name 没有 id 会断掉「按知识点聚合掌握度」这条路**，所以两个都留。
- `mastery_record.stuck_sec` 是给「过程侧」预留的：卡住时长比答对/答错更能反映掌握情况。
- `init_db()` 会自动迁移旧库（当前会补 `chunk.kp_id`），**先补列再建索引**——
  否则 `CREATE INDEX ON chunk(kp_id)` 会在旧库上报 `no such column`。

## 实测结果（本机跑过）

```
测试：33 passed
导入：2 份资料 → 10 个块（每份 5 块）
  「红黑树 不能有连续两个红结点」→ cs_红黑树   第 2 页  0.393 ✅
  「叔叔结点是红色怎么办」        → cs_红黑树   第 4 页  0.337 ✅
  「旋转」                      → cs_红黑树   第 3 页  0.259 ✅
  「虚静」                      → zh_文心雕龙 第 3 页  0.501 ✅
  「虚静 是什么意思」             → zh_文心雕龙 第 4 页  0.302 ✅
  「左旋 右旋 指针」              → cs_红黑树   第 3 页  0.197 ✅ 不串到文学
空查询 q= → 200 + 前 k 块 ✅
k=xx     → 200，夹到合法值（原为 500）✅
旧库无 kp_id → 自动 ALTER 补列，导入检索正常 ✅
```

## 关键取舍：为什么用哈希向量而不是真 embedding

本机 **pip 连不上 PyPI**，装不了 embedding 模型。

所以 W2 用「字符 n-gram 哈希」：
- 中文不需要分词器，不依赖模型文件
- 256 维，可复现（同一文本两次向量完全相同，有测试保证）
- 在「术语 / 人名 / 公式符号」上的召回足够验证链路

**W3 换真 embedding 时只改一处**：把 `rag.HashingEmbedder` 换成调百炼 `text-embedding` 的类，
`store.py` 与 `server.py` 不动。接口已经定死，这正是 `A-W1-1` 讲的"边界"思路。

## 还没做（W3 范围，别指望它现在有）

- 真 embedding / 真 LLM（**没有 `/structure` 接口**）
- 三核心数据对象的 CRUD API（表已建好，只留了 `add_knowledge_point` / `add_mastery` 两个写入函数）
- 鉴权、并发、限流
- 前端对接（`adapters.real.js` 还没建）
