# 知识点数据模型 v1 与 API 契约（W2 v1.1）

> A · W2 交付物 ③（手册 3.3）｜ 2026-11-22
> 权威来源：《产品功能规格_赛题1.md》**§1.2 六标签 / §1.3 三对象 / §3.3 错题八字段**
> 本文与 `backend/schema.sql` **逐字段一致**（代码是契约的实现，不是另一份东西）。

---

## 一、三条铁律（先立规矩，再谈字段）

1. **底层用「知识点关联」，不用文件夹分组**（手册 3.3 ③ 要求）。
   课程 → 章节 → 知识点 是**层级归属**，知识点之间的 `prereq` / `related_courses` 是**关联**。
   同一份资料可以挂多个知识点，**不做物理目录移动**。
2. **每个 AI 产出的结论必须能点回原始位置**：`chunk.page`（课件页码）+ `doc_id`（哪份资料）+ `ord`（块序号）。
   没有溯源字段的结论**不允许入库**。
3. **低置信度一律可检查可修正**：`confidence < 0.8` 标黄（沿用 demo 既有范式），人工改后的文本才进 `chunk.text`。

---

## 二、六标签（每份资料块必打）

> 规格 §1.2 原文：`课程 / 章节 / 知识点 / 难度 / 来源 / 版本`

| 标签 | 字段名 | 类型 | 必填 | 取值 | 说明 |
|---|---|---|---|---|---|
| 课程 | `course` | string | ✅ | 如「数据结构」「中国古代文学」 | |
| 章节 | `chapter` | string | ✅ | 如「平衡树」「文心雕龙」 | |
| 知识点 | `kp_id` + `kp_name` | string | ⭕ | `kp_id` 关联 `knowledge_point.id`；`kp_name` 供显示 | `kp_id` 可为空（未挂知识点的块允许存在） |
| 难度 | `difficulty` | string | ⭕ | `易` / `中` / `难` | 空表示未标 |
| 来源 | `source` | string | ⭕ | `课件` / `教材` / `手写笔记` / `录音` / `代码截图` | |
| 版本 | `version` | string | ⭕ | 默认 `v1` | 资料修订时递增 |

---

## 三、三核心数据对象

### 3.1 知识点 `knowledge_point`

> 规格 §1.3①：课程-章节归属、前置关系、**关联课程**、资料溯源

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string (PK) | ✅ | 如 `kp_rbt_rotate` |
| `course` | string | ✅ | 课程 |
| `chapter` | string | ✅ | 章节 |
| `name` | string | ✅ | 知识点名，如「红黑树旋转」 |
| `prereq` | string | ⭕ | 前置知识点 id，逗号分隔（如 `kp_bst,kp_rotation`） |
| **`related_courses`** | string | ⭕ | **关联课程**（跨课程的知识点复用），逗号分隔 |
| `difficulty` | string | ⭕ | 难度 |
| `source` | string | ⭕ | 来源 |
| `version` | string | ⭕ | 默认 `v1` |
| `created_at` | string | 自动 | 本地时间 |

**资料溯源不在本表**：知识点级的溯源由 `chunk.kp_id` 反查（一个知识点对应哪些块、每块在第几页），避免在知识点上复制一堆页码。

### 3.2 题目 `question`

> 规格 §1.3②：对应知识点、难度、题型、来源

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string (PK) | ✅ | |
| `kp_id` | string | ✅ | 对应知识点 |
| `stem` | string | ✅ | 题干 |
| `qtype` | string | ⭕ | `选择` / `填空` / `简答` / `证明` |
| `difficulty` | string | ⭕ | |
| `source` | string | ⭕ | 自编 / 教材 / AI 生成 |
| `version` | string | ⭕ | |
| `created_at` | string | 自动 | |

### 3.3 错题·掌握度记录 `mastery_record` —— **严格对齐 §3.3 八字段**

> 规格 §3.3 原文：`题目 / 错误答案 / 错误类型 / 对应知识点 / 难度 / 首次错因 / 复习次数 / 掌握状态`

| # | 规格字段 | 字段名 | 类型 | 必填 | 取值 / 说明 |
|---|---|---|---|---|---|
| ① | 题目 | `qid` | string | ⭕ | 指向 `question.id`；手工录入时可为空 |
| ② | 错误答案 | `wrong_answer` | string | ⭕ | 学生实际写下的答案 |
| ③ | 错误类型 | `error_type` | string | ⭕ | `概念错` / `计算错` / `审题错` / `漏步` / `表达不清` |
| ④ | 对应知识点 | `kp_id` | string | ✅ | |
| ⑤ | 难度 | `difficulty` | string | ⭕ | 与题目难度一致 |
| ⑥ | 首次错因 | `first_cause` | string | ⭕ | 人可读的一句话，如「把左旋右旋记反了」 |
| ⑦ | 复习次数 | `review_count` | int | ⭕ | 默认 0 |
| ⑧ | 掌握状态 | `mastery_status` | string | ⭕ | `未掌握` / `模糊` / `已掌握`，默认 `未掌握` |
| — | *（派生）* | `correct` | int | ⭕ | 本次判定 1 对 / 0 错 |
| — | *（派生）* | `score` | real | ⭕ | 掌握度数值快照 0–1 |
| — | *（过程侧）* | `stuck_sec` | int | ⭕ | **卡住时长（秒）**——比「对/错」更能反映掌握情况 |
| — | *（过程侧）* | `note` | string | ⭕ | 备注 |
| — | *（自动）* | `id` / `created_at` | — | — | |

> **为什么多留 5 个派生/过程字段**：八字段是**快照**，诊断要的是**趋势**。`stuck_sec` 是「过程侧」差异化的最小抓手（竞品都没有）。

### 3.4 资料块 `chunk`（RAG 检索单元，六标签的载体）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | int (PK 自增) | 自动 | |
| `doc_id` | string | ✅ | 哪份资料 |
| `course` / `chapter` / `difficulty` / `source` / `version` | string | ⭕ | 六标签中的 5 个 |
| `kp_id` | string (FK→`knowledge_point.id`) | ⭕ | **空则存 NULL，不能存 `''`**（非 NULL 会触发外键失败，踩过这个坑） |
| `kp_name` | string | ⭕ | 显示与检索权重用 |
| `page` | int | ⭕ | **课件页码**（溯源关键） |
| `ord` | int | ⭕ | 块序号（溯源关键） |
| `text` | string | ✅ | 块正文 |

### 3.5 向量 `chunk_vec`（与块 1:1）

| 字段 | 类型 | 说明 |
|---|---|---|
| `chunk_id` | int (PK, FK→`chunk.id` ON DELETE CASCADE) | |
| `dim` | int | 当前 256 |
| `vec` | text | JSON 数组（float），L2 已归一化 |

---

## 四、关系图（知识点关联，不是文件夹）

```
                    ┌─────────────┐
                    │   course    │  「数据结构」
                    └──────┬──────┘
                           │ 层级归属
                    ┌──────┴──────┐
                    │   chapter   │  「平衡树」
                    └──────┬──────┘
                           │ 层级归属
              ┌────────────┴────────────┐
              │     knowledge_point     │  kp_rbt_rotate
              │  id / name / difficulty │
              └───┬─────────┬───────┬───┘
        prereq   │         │       │  related_courses
        （前置）  │         │       │  （关联课程，跨课程复用）
                 ▼         │       ▼
        kp_bst, kp_rotation│     「算法设计」
                           │
              ┌────────────┴────────────┐
              │  chunk (资料块)          │  ← 六标签挂这里
              │  page / ord / text      │  ← 溯源在这里
              └────────────┬────────────┘
                           │ 1:1
                    ┌──────┴──────┐
                    │  chunk_vec  │
                    └─────────────┘

   其他两对象：
   question ──kp_id──► knowledge_point
   mastery_record ──kp_id──► knowledge_point
                  ──qid───► question
```

**三条链路都读同一批对象**（规格 §1.3 的决策理由）：

| 链路 | 读什么 | 产出 |
|---|---|---|
| 诊断（苏格拉底） | `mastery_record`（按 `kp_id` 聚合） | 薄弱知识点清单 |
| 出题（复习） | `question` + `mastery_record` | 按权重排序的题目 |
| 复习（错题本） | `mastery_record` + `chunk`（回原页） | 可点回页码的错题卡 |

---

## 五、API 契约

### 5.1 已实现（`backend/server.py`，W2 可跑）

| 方法 | 路径 | 入参 | 返回 |
|---|---|---|---|
| GET | `/health` | — | `{ok, embedder, stats}` |
| GET | `/stats` | — | `{chunks, docs, knowledge_point, question, mastery_record, db}` |
| GET | `/search` | `q`, `k`(1–50，默认 5), `corpus`(可选), `min_score`(默认 0.15) | 见 5.2 |
| POST | `/search` | `{query, corpus, k, min_score}` | 同上 |
| POST | `/ingest` | `{doc_id, text, course, chapter, kp_id, kp_name, difficulty, source, version}` | `{doc_id, chunks, embedder}` |

### 5.2 检索返回形状（v1 已实现 / v2 待加两字段）

```json
[
  {
    "title": "红黑树旋转",
    "meta": "课件 · 第 2 页 · 相似度 0.393",
    "hit": "第 5 条性质保证了最长路径不超过最短路径的两倍……",
    "tag": "红黑树旋转",
    "_score": 0.3933,
    "_doc_id": "cs_红黑树",
    "_page": 2,
    "_ord": 3
  }
]
```

| 字段 | 类型 | 必填 | 说明 | 谁用 |
|---|---|---|---|---|
| `title` | string | ✅ | 知识点名 / 章节名 / doc_id（按优先级取） | B 渲染 |
| `meta` | string | ✅ | `来源 · 第 N 页 · 相似度 x` —— **溯源就在这一句里** | B 渲染 |
| `hit` | string | ✅ | 命中片段（≤180 字） | B 渲染 |
| `tag` | string | ✅ | 知识点或章节 | B 渲染 |
| `_score` | number | ⭕ | 相似度 0–1 | 调试 |
| `_doc_id` / `_page` / `_ord` | — | ⭕ | 溯源三元组 | 调试 |
| `_corpus_fallback` | bool | ⭕ | 只在「corpus 过滤后为空、已退化全库」时出现 | 调试 |

### 5.3 v2 新增（答复 B 的 F3，W4 落地）

| 新字段 | 类型 | 说明 |
|---|---|---|
| **`score`** | number 0–1 | `_score` 正式化（去掉下划线前缀） |
| **`match`** | string | 命中依据：命中的 chunk 片段（可与 `hit` 相同，语义上是「为什么匹配」） |

> **对 B 的承诺**：两个都是**新增字段**，`title/meta/hit/tag` 不动 → **B 的渲染代码不受影响**（与 B 的 F3 判断一致）。

### 5.4 入参形状 v2（答复 B 的 F1，W3 落地）

**v2 形状（W3 起）**

```json
{ "ref": "file:///.../rec1.m4a", "mime": "audio/mp4", "meta": { "dur": 421 } }
```

**v1 形状（现版本，传字符串）—— v2 必须继续接受，内部转成下面这样**

```json
{ "ref": "录音A", "mime": "", "meta": { "legacy": true } }
```

---
## 六、与 `demo/js/adapters.js` 五个 Mock 的兼容性（手册 3.3 ④ / 验收第 4 项）

| # | Mock | 入参（不变） | 返回（不变） | v1 契约新增 | 是否破坏 B 的渲染 |
|---|---|---|---|---|---|
| 1 | `MockASR.transcribe` | `(audioRef, fallbackText, fallbackConf)` | `{text, confidence, source, engine, latencyMs}` | 入参 v2 对象（**字符串仍接受**）；加 `degraded` / `reason` | ❌ 不破坏（新增字段） |
| 2 | `MockOCR.recognize` | `(imageRef, fallbackText, fallbackConf)` | 同上 | 同上 | ❌ |
| 3 | `MockLLM.structure` | `(segments, noteTemplate)` | `{title, sections[{h, points[], src}], segmentCount, engine}` | **`sections[].src` 必须保留**（溯源）；`src` 由编排层从 `chunk.doc_id + page` 拼装，**不让模型生成** | ❌ |
| 4 | `MockRAG.search` | `(query, corpus)` | `[{title, meta, hit, tag}]` | 加 `score` / `match`；无命中**返回空数组**（阈值 0.15） | ❌ |
| 5 | `MockCrossDevice.handoff` | `(taskState)` | `{ok, via, task, timestamp}` | **`ok` 必须被读**；W9 再升级 `taskState` | ⚠️ **要改 1 行**：`doHandoff()` 加 `if(!res.ok)` |

> **与 `A-W1-1` 的口径一致**：5 个调用点签名不改；但**降级渲染要加约 10 行**（每处读 `degraded` / `ok` 1–2 行）。
> 「界面代码一行不改」宜理解为**调用点不改**（不是否定 B，是把口径精确化）。

---

## 七、低置信度处理（写进契约，不是口头约定）

| 环节 | 阈值 | 行为 |
|---|---|---|
| ASR / OCR 识别 | `confidence < 0.8` | UI 标黄 + 提示人工核对；**改后文本才进 `chunk.text`** |
| 段级置信度 | 该段**所有行置信度的最小值** | 取 min，宁可多标（不用平均值，避免一行烂全段绿） |
| 检索 | `score < 0.15` | 视为未命中，**返回空数组**（让前端「没找到就回退」真正触发） |
| 结构化输出 | JSON 解析失败 | 走 `degraded: true, reason: 'PARSE'`，不抛异常 |

---

## 八、待定夺（不属本文档，但要标出来）

| 项 | 谁定 | 何时 |
|---|---|---|
| 出题权重公式的数值（0.4/0.2/0.2/0.15/0.05） | 队长 | **W8 前，本次不动**（手册 3.3 明确「待商量草案·数值勿改」） |
| `related_courses` 是否要单独建表 | A | 若跨课程复用 >50 条再考虑，当前用逗号分隔够用 |
| 是否引入 FSRS 做复习调度 | 队长 | W3 会上提 |

---

## 九、一句话

**三对象 + 六标签 + 知识点关联 + 溯源三元组（doc_id/page/ord）+ 低置信标黄，就是 v1 契约的全部。**
**代码已在 `backend/schema.sql` 落地，字段与本文逐字一致；5 个 Mock 的入参/返回形状不变，B 的界面只需要加约 10 行降级渲染。**
