-- W2 最小知识库 schema
-- 三核心数据对象（规格 §1.3）+ 知识图谱六标签（规格 §1.2）+ 资料块与向量
PRAGMA journal_mode=WAL;

-- ① 知识点
CREATE TABLE IF NOT EXISTS knowledge_point (
  id          TEXT PRIMARY KEY,
  course      TEXT NOT NULL,          -- 课程
  chapter     TEXT NOT NULL,          -- 章节
  name        TEXT NOT NULL,          -- 知识点名
  prereq      TEXT DEFAULT '',        -- 前置知识点 id，逗号分隔
  related_courses TEXT DEFAULT '',    -- 关联课程（规格 §1.3 要求），逗号分隔
  difficulty  TEXT DEFAULT '',        -- 难度 易/中/难
  source      TEXT DEFAULT '',        -- 来源（课件/教材/手写笔记…）
  version     TEXT DEFAULT 'v1',      -- 版本
  created_at  TEXT DEFAULT (datetime('now','localtime'))
);

-- ② 题目
CREATE TABLE IF NOT EXISTS question (
  id          TEXT PRIMARY KEY,
  kp_id       TEXT NOT NULL,          -- 对应知识点
  stem        TEXT NOT NULL,
  qtype       TEXT DEFAULT '',        -- 题型 选择/填空/简答/证明
  difficulty  TEXT DEFAULT '',
  source      TEXT DEFAULT '',
  version     TEXT DEFAULT 'v1',
  created_at  TEXT DEFAULT (datetime('now','localtime'))
);

-- ③ 错题/掌握度记录
-- 字段严格对齐《产品功能规格》§3.3 的八字段：
--   题目 / 错误答案 / 错误类型 / 对应知识点 / 难度 / 首次错因 / 复习次数 / 掌握状态
CREATE TABLE IF NOT EXISTS mastery_record (
  id            TEXT PRIMARY KEY,
  qid           TEXT DEFAULT '',      -- ① 题目（指向 question.id；手工录入时可为空）
  wrong_answer  TEXT DEFAULT '',      -- ② 错误答案
  error_type    TEXT DEFAULT '',      -- ③ 错误类型（概念错/计算错/审题错/漏步/表达不清）
  kp_id         TEXT NOT NULL,        -- ④ 对应知识点
  difficulty    TEXT DEFAULT '',      -- ⑤ 难度（易/中/难）
  first_cause   TEXT DEFAULT '',      -- ⑥ 首次错因（人可读的一句话）
  review_count  INTEGER DEFAULT 0,    -- ⑦ 复习次数
  mastery_status TEXT DEFAULT '未掌握', -- ⑧ 掌握状态（未掌握/模糊/已掌握）
  -- 以下为过程侧与派生数据，不属八字段，但诊断要用
  correct       INTEGER DEFAULT 0,    -- 本次判定 1 对 / 0 错
  score         REAL DEFAULT 0,       -- 掌握度数值快照 0..1
  stuck_sec     INTEGER DEFAULT 0,    -- 卡住时长（秒）
  note          TEXT DEFAULT '',
  created_at    TEXT DEFAULT (datetime('now','localtime'))
);

-- 资料块（RAG 的检索单元）：六标签挂在块上
-- 第 4 轮修正：原表只有 kp_name 自由文本，与 knowledge_point.id 无关联，
-- 导致「按知识点聚合掌握度」时找不到 kp_id。现补 kp_id 外键（可空：未挂知识点的资料块允许存在），
-- kp_name 保留供显示与检索权重。
CREATE TABLE IF NOT EXISTS chunk (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  doc_id     TEXT NOT NULL,
  course     TEXT DEFAULT '',
  chapter    TEXT DEFAULT '',
  kp_id      TEXT REFERENCES knowledge_point(id) ON DELETE SET NULL,  -- 空则存 NULL，不能存 ''（非 NULL 会触发外键失败）
  kp_name    TEXT DEFAULT '',
  difficulty TEXT DEFAULT '',
  source     TEXT DEFAULT '',
  version    TEXT DEFAULT 'v1',
  page       INTEGER DEFAULT 0,
  ord        INTEGER DEFAULT 0,
  text       TEXT NOT NULL
);

-- 向量与块 1:1，存 JSON 数组（256 维 float）
CREATE TABLE IF NOT EXISTS chunk_vec (
  chunk_id   INTEGER PRIMARY KEY REFERENCES chunk(id) ON DELETE CASCADE,
  dim        INTEGER NOT NULL,
  vec        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chunk_doc ON chunk(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunk_kp  ON chunk(kp_name);
CREATE INDEX IF NOT EXISTS idx_chunk_kpid ON chunk(kp_id);
