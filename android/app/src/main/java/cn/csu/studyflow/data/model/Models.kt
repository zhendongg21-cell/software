package cn.csu.studyflow.data.model

/**
 * 本地数据模型 —— 已对齐 A《知识点数据模型 v1 与 API 契约》v1.1（2026-11-22）
 *
 * 三条铁律：① 底层用知识点关联（prereq / related_courses），不用文件夹分组；
 * ② 溯源在 chunk（page + doc_id + ord），知识点表不存溯源——UI 用 chunk 反查渲染；
 * ③ confidence < 0.8 标黄可修正（沿用 demo 范式）。
 *
 * 与契约的映射（本层为 UI 骨架，S4 联调时接 backend/schema.sql 真实数据）：
 *  - KnowledgePoint  ↔ knowledge_point（difficulty 为 易/中/难 字符串；prereq/related_courses 为逗号分隔串）
 *  - Question        ↔ question（qtype：选择/填空/简答/证明）
 *  - MistakeRecord   ↔ mastery_record（严格八字段 + 派生 score）
 *  - Document+Chunk  ↔ doc + chunk（RAG 检索单元；六标签挂 chunk 上）
 *  - 章节无独立表：契约中 chapter 是知识点上的字符串字段，UI 按出现顺序派生导航
 */

/** 知识点（三核心数据对象之一） */
data class KnowledgePoint(
    val id: String,              // PK，如 kp_rbt_rotate（骨架暂用 lit-p1 等占位）
    val course: String,          // 六标签①课程
    val chapter: String,         // 六标签②章节（字符串，无独立章节表）
    val name: String,            // 六标签③知识点
    val difficulty: String,      // 六标签④难度：易 / 中 / 难
    val source: String,          // 六标签⑤来源：课件/教材/手写笔记/录音/代码截图
    val version: String,         // 六标签⑥版本，默认 v1
    val prereq: String,          // 前置知识点 id，逗号分隔（如 "kp_bst,kp_rotation"）
    val relatedCourses: String,  // 关联课程（跨课程复用），逗号分隔
    val mastered: Boolean = false, // UI 展示用掌握标记
)

/** 题目（三核心数据对象之一） */
data class Question(
    val id: String,
    val kpId: String,            // 对应知识点
    val stem: String,            // 题干
    val qtype: String,           // 选择 / 填空 / 简答 / 证明
    val difficulty: String,      // 易 / 中 / 难
    val source: String,          // 自编 / 教材 / AI 生成
)

/** 错题·掌握度记录（三核心数据对象之一）——严格对齐契约 3.3 八字段 */
data class MistakeRecord(
    val id: String,
    val qid: String?,            // ①题目：指向 question.id；手工录入可空（骨架带展示文本 questionText）
    val questionText: String,    // 展示用题干（联调后由 qid 反查 question.stem）
    val wrongAnswer: String,     // ②错误答案
    val errorType: String,       // ③错误类型：概念错/计算错/审题错/漏步/表达不清
    val kpId: String,            // ④对应知识点
    val difficulty: String,      // ⑤难度：易/中/难
    val firstCause: String,      // ⑥首次错因（人可读一句话）
    val reviewCount: Int,        // ⑦复习次数
    val masteryStatus: String,   // ⑧掌握状态：未掌握/模糊/已掌握
    val score: Float,            // 派生：掌握度数值快照 0–1（UI 进度条用）
)

/** 资料（对应契约的 doc；RAG 检索单元是它的 chunk） */
enum class MaterialType(val label: String) {
    COURSEWARE("课件"),
    LITERATURE("文献"),
    HANDWRITTEN("手写批注"),
    FOREIGN("外文片段"),
    CODE_SCREENSHOT("代码截图"),
}

data class Document(
    val id: String,              // 对应契约 chunk.doc_id
    val title: String,
    val type: MaterialType,
    val course: String,
    val chapter: String,
)

/**
 * 资料块（契约 chunk：六标签的载体、溯源所在、标黄对象）
 * 铁律②：每个 AI 结论必须能点回 chunk.page + doc_id + ord
 */
data class Chunk(
    val id: String,
    val docId: String,           // 哪份资料
    val kpId: String?,           // 可空——未挂知识点的块允许存在（不存 ''，防外键失败）
    val kpName: String?,         // 显示与检索权重用
    val page: Int?,              // 溯源：课件页码
    val ord: Int?,               // 溯源：块序号
    val text: String,            // 块正文（人工修正后的文本才进这里）
    val confidence: Float,       // < 0.8 标黄
    val source: String?,         // 六标签⑤来源
    val version: String?,        // 六标签⑥版本
)

data class PlanItem(
    val title: String,
    val detail: String,
    val progress: Float,   // 0–1
    val due: String,       // 截止
)

/** 顶栏进度卡片 */
data class ProgressCard(
    val mastered: Int,
    val total: Int,
    val todayPages: Int,
    val todayGoal: Int,
    val streakDays: Int,
)

/** 场景（对应 demo 的 SCENES：文学院 / 计科） */
data class Scene(
    val id: String,
    val label: String,
    val courseName: String,
    val chapterNames: List<String>,   // 章节名（按导航顺序；章节=知识点上的字符串字段）
    val points: List<KnowledgePoint>,
    val questions: List<Question>,
    val documents: List<Document>,
    val chunks: List<Chunk>,
    val mistakes: List<MistakeRecord>,
    val plan: List<PlanItem>,
    val progress: ProgressCard,
)

/** 按知识点 id 反查其资料块（铁律②：UI 渲染溯源/摘要/待确认都走这里） */
fun Scene.chunksOf(kpId: String): List<Chunk> = chunks.filter { it.kpId == kpId }

/** 按资料 id 反查其块 */
fun Scene.chunksOfDoc(docId: String): List<Chunk> = chunks.filter { it.docId == docId }
