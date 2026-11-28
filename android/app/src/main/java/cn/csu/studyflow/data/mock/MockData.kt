package cn.csu.studyflow.data.mock

import cn.csu.studyflow.data.model.Chunk
import cn.csu.studyflow.data.model.Document
import cn.csu.studyflow.data.model.KnowledgePoint
import cn.csu.studyflow.data.model.MaterialType
import cn.csu.studyflow.data.model.MistakeRecord
import cn.csu.studyflow.data.model.PlanItem
import cn.csu.studyflow.data.model.ProgressCard
import cn.csu.studyflow.data.model.Question
import cn.csu.studyflow.data.model.Scene

/**
 * 占位样例数据 —— 已按 A 契约 v1.1 形状（2026-11-22）重写
 *
 * 两个场景（文学院 / 计科）形成异质对照；id 为占位（真实数据 S4 联调时接
 * backend/seed 与 D 的 5.1 场景样例）。低置信块（confidence < 0.8）故意保留，
 * 用于「可检查可修正」范式展示。
 */
object MockData {

    /* ================= 文学院 · 中国古代文学 ================= */

    private val litPoints = listOf(
        KnowledgePoint("lit-p1", "中国古代文学", "先秦文学", "《诗经》风雅颂", "易", "课件", "v1", "", "", mastered = true),
        KnowledgePoint("lit-p2", "中国古代文学", "先秦文学", "赋比兴手法", "中", "教材", "v1", "lit-p1", "", mastered = true),
        KnowledgePoint("lit-p3", "中国古代文学", "先秦文学", "《楚辞》与屈原", "难", "教材", "v1", "lit-p2", ""),
        KnowledgePoint("lit-p4", "中国古代文学", "汉魏六朝", "《史记》叙事艺术", "难", "教材", "v1", "lit-p3", "中国古代史"),
        KnowledgePoint("lit-p5", "中国古代文学", "汉魏六朝", "建安风骨", "中", "教材", "v1", "lit-p4", ""),
        KnowledgePoint("lit-p6", "中国古代文学", "唐宋文学", "唐诗气象（李杜）", "中", "课件", "v1", "lit-p5", ""),
    )

    private val litDocuments = listOf(
        Document("lit-m1", "课件：先秦文学总论.pptx", MaterialType.COURSEWARE, "中国古代文学", "先秦文学"),
        Document("lit-m2", "古籍引文：《诗集传》节选", MaterialType.LITERATURE, "中国古代文学", "先秦文学"),
        Document("lit-m3", "书边手写批注（课堂听记）", MaterialType.HANDWRITTEN, "中国古代文学", "先秦文学"),
        Document("lit-m4", "外文片段：Owen, Anthology, ch.1", MaterialType.FOREIGN, "中国古代文学", "先秦文学"),
        Document("lit-m5", "课件：汉魏六朝文学.pptx", MaterialType.COURSEWARE, "中国古代文学", "汉魏六朝"),
        Document("lit-m6", "课件：唐诗.pptx", MaterialType.COURSEWARE, "中国古代文学", "唐宋文学"),
    )

    private val litChunks = listOf(
        Chunk("lit-c1", "lit-m1", "lit-p1", "《诗经》风雅颂", 3, 1,
            "风（民间歌谣）、雅（宫廷正声）、颂（宗庙祭祀）三体的内容与功能分野。", 0.93f, "课件", "v1.1"),
        Chunk("lit-c2", "lit-m1", "lit-p2", "赋比兴手法", 5, 2,
            "赋（铺陈）、比（比喻）、兴（起兴）三种表现手法及其辨析。", 0.87f, "课件", "v1.1"),
        Chunk("lit-c3", "lit-m2", "lit-p2", "赋比兴手法", 8, 1,
            "朱熹释「兴」：先言他物以引起所咏之辞也。", 0.89f, "教材", "v1.0"),
        Chunk("lit-c4", "lit-m3", "lit-p3", "《楚辞》与屈原", 7, 1,
            "楚辞体式特征与《离骚》的抒情结构、香草美人传统。", 0.71f, "手写笔记", "v0.9"),
        Chunk("lit-c5", "lit-m4", "lit-p3", "《楚辞》与屈原", 23, 1,
            "The Chuci and the lyric tradition of Qu Yuan.", 0.83f, "教材", "v1.0"),
        Chunk("lit-c6", "lit-m5", "lit-p4", "《史记》叙事艺术", 3, 1,
            "纪传体通史的体例与「无韵之离骚」的文学性。", 0.90f, "课件", "v1.0"),
        Chunk("lit-c7", "lit-m5", "lit-p5", "建安风骨", 6, 2,
            "三曹七子的时代背景与慷慨悲凉的文学风貌。", 0.85f, "课件", "v1.0"),
        Chunk("lit-c8", "lit-m6", "lit-p6", "唐诗气象（李杜）", 4, 1,
            "李白浪漫飘逸与杜甫沉郁顿挫的风格对照。", 0.91f, "课件", "v1.0"),
    )

    private val litQuestions = listOf(
        Question("lit-q1", "lit-p2", "简述「赋比兴」的区别并各举一例。", "简答", "中", "期中卷"),
        Question("lit-q2", "lit-p3", "结合《离骚》分析香草美人的象征体系。", "简答", "难", "课后题"),
    )

    private val litMistakes = listOf(
        MistakeRecord("lit-e1", "lit-q1", "「赋比兴」中「兴」的判别", "把「兴」答成「比」",
            "概念错", "lit-p2", "中", "起兴与比喻的触发机制未分清", 3, "模糊", 0.62f),
        MistakeRecord("lit-e2", "lit-q2", "《离骚》香草美人传统内涵", "只答字面意象",
            "漏步", "lit-p3", "难", "未联系「美政」理想作答", 2, "模糊", 0.45f),
        MistakeRecord("lit-e3", null, "李杜风格对比论述", "罗列生平未比较风格",
            "表达不清", "lit-p6", "中", "缺少「同中见异」的分析框架", 1, "未掌握", 0.3f),
    )

    private val litPlan = listOf(
        PlanItem("复习「赋比兴」错题", "重做 2 道辨析题 + 回看教材 P.18", 0.4f, "今晚"),
        PlanItem("通读《楚辞》章节", "教材 P.31–45，整理思维导图", 0.1f, "12-05"),
        PlanItem("李杜风格对照卡", "制作对比卡片 5 张", 0f, "12-06"),
    )

    private val litScene = Scene(
        id = "lit", label = "文学院 · 中国古代文学", courseName = "中国古代文学",
        chapterNames = listOf("先秦文学", "汉魏六朝", "唐宋文学"),
        points = litPoints, questions = litQuestions,
        documents = litDocuments, chunks = litChunks,
        mistakes = litMistakes, plan = litPlan,
        progress = ProgressCard(mastered = 2, total = 6, todayPages = 4, todayGoal = 10, streakDays = 3),
    )

    /* ================= 计科 · 数据结构 ================= */

    private val csPoints = listOf(
        KnowledgePoint("cs-p1", "数据结构", "线性表", "线性表与顺序存储", "易", "教材", "v1", "", "", mastered = true),
        KnowledgePoint("cs-p2", "数据结构", "线性表", "单链表操作", "中", "课件", "v1.1", "cs-p1", "", mastered = true),
        KnowledgePoint("cs-p3", "数据结构", "栈与队列", "栈的应用：表达式求值", "难", "课件", "v1", "cs-p2", ""),
        KnowledgePoint("cs-p4", "数据结构", "栈与队列", "循环队列与假溢出", "中", "教材", "v1", "cs-p3", ""),
        KnowledgePoint("cs-p5", "数据结构", "树", "二叉树遍历", "难", "课件", "v1.2", "cs-p4", ""),
    )

    private val csDocuments = listOf(
        Document("cs-m1", "课件：线性表.pptx", MaterialType.COURSEWARE, "数据结构", "线性表"),
        Document("cs-m2", "代码截图：循环队列实现", MaterialType.CODE_SCREENSHOT, "数据结构", "栈与队列"),
        Document("cs-m3", "外文片段：CLRS ch.10", MaterialType.FOREIGN, "数据结构", "栈与队列"),
        Document("cs-m4", "课件：二叉树.pptx", MaterialType.COURSEWARE, "数据结构", "树"),
    )

    private val csChunks = listOf(
        Chunk("cs-c1", "cs-m1", "cs-p1", "线性表与顺序存储", 5, 1,
            "顺序表随机存取与插入删除 O(n) 的代价。", 0.96f, "课件", "v1.2"),
        Chunk("cs-c2", "cs-m1", "cs-p2", "单链表操作", 9, 2,
            "头插/尾插、删除后继节点的指针操作要点。", 0.88f, "课件", "v1.2"),
        Chunk("cs-c3", "cs-m2", "cs-p4", "循环队列与假溢出", 11, 1,
            "取模实现环形缓冲，区分队空/队满的三种方式。", 0.74f, "代码截图", "v0.9"),
        Chunk("cs-c4", "cs-m3", "cs-p3", "栈的应用：表达式求值", 232, 1,
            "Infix to postfix conversion with operator stack.", 0.85f, "教材", "v1.0"),
        Chunk("cs-c5", "cs-m3", "cs-p4", "循环队列与假溢出", 235, 2,
            "Queue implementation with head and tail pointers.", 0.90f, "教材", "v1.0"),
        Chunk("cs-c6", "cs-m4", "cs-p5", "二叉树遍历", 17, 1,
            "前/中/后序遍历的递归与非递归实现。", 0.86f, "课件", "v1.2"),
    )

    private val csQuestions = listOf(
        Question("cs-q1", "cs-p4", "实现循环队列的入队/出队并处理假溢出。", "简答", "中", "作业三"),
    )

    private val csMistakes = listOf(
        MistakeRecord("cs-e1", "cs-q1", "循环队列判空/判满条件", "写成 front==rear 判断队满",
            "漏步", "cs-p4", "中", "未记住「牺牲一个单元」约定", 4, "模糊", 0.58f),
        MistakeRecord("cs-e2", null, "中缀转后缀时括号处理", "遇到 '(' 直接弹出",
            "概念错", "cs-p3", "难", "栈顶 '(' 的优先级特判漏掉", 2, "模糊", 0.5f),
    )

    private val csPlan = listOf(
        PlanItem("循环队列错题重做", "重做 2 道判空判满题", 0.6f, "今晚"),
        PlanItem("二叉树遍历非递归实现", "手写三种遍历 + 调试", 0.2f, "12-05"),
    )

    private val csScene = Scene(
        id = "cs", label = "计科 · 数据结构", courseName = "数据结构",
        chapterNames = listOf("线性表", "栈与队列", "树"),
        points = csPoints, questions = csQuestions,
        documents = csDocuments, chunks = csChunks,
        mistakes = csMistakes, plan = csPlan,
        progress = ProgressCard(mastered = 2, total = 5, todayPages = 6, todayGoal = 12, streakDays = 4),
    )

    val scenes: List<Scene> = listOf(litScene, csScene)
}
