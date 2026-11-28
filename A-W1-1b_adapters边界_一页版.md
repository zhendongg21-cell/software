# adapters.js 替换边界说明（一页版）

> W1 交付物 ③ ｜ 负责人 A ｜ **v2.2**（2026-11-22 复核） ｜ 完整版 `A-W1-1`（阈值校准与分模态数据）
> **A4 单页。** 手册 3.3 要「入参/返回形状 + 改哪里 + 依赖什么」，本页三项都有。

## 一、结论

`demo/js/adapters.js` 是**唯一边界**。**5 个方法的入参与返回形状不变；`app.js` 的 5 个调用点签名与业务逻辑不改，但降级渲染必须加**（读 `degraded`、加 `if(!res.ok)`）。
> ⚠️ 不能说「界面代码一行不改」——读字段就是改代码。**手册 3.3 ③ 原写"B 的界面代码不用改"，这个前提也要修正。**

## 二、五个适配器

| # | 方法 | **入参** | 返回（Promise 解析值） | 调用点 | 真实依赖 |
|---|---|---|---|---|---|
| 1 | `MockASR.transcribe` | `(audioRef, fallbackText, fallbackConf)` | `{text, confidence, source*, engine, latencyMs}` | `addCap()` **L112** | sherpa-onnx · Qwen3-ASR（端侧 vs 云端**待 W3 Spike**） |
| 2 | `MockOCR.recognize` | `(imageRef, fallbackText, fallbackConf)` | 同上 | `addCap()` **L113**（图片/手写共用） | PP-OCRv6 + 公式模块；四场景分别评测：代码截图 / 公式 / 古籍竖排 / 手写批注 |
| 3 | `MockLLM.structure` | `(segments, noteTemplate)` | `{title, sections[{h,points:[],src}], segmentCount*, engine*}` | `structureNote()` **L172** | qwen3.8-flash；每段 `src` 引用必须保留 |
| 4 | `MockRAG.search` | `(query, corpus)` | `[{title, meta, hit, tag}]` | `doSearch()` **L211** | sqlite-vec + embedding；按 课程/章节/知识点 三级组织 |
| 5 | `MockCrossDevice.handoff` | `(taskState)` | `{ok, via, task*, timestamp*}` | `doHandoff()` **L240** | OPPO 互联 + 碰一碰；必须用户显式确认，不自动同步 |

`*` = 声明了但 UI 不读的死字段。`app.js` 用别名调用（**L109**）：搜 `MockASR.transcribe` 搜不到，要搜 `engine.transcribe`。

## 三、三条必须记住的约定

1. **`segmentsLength` 由 `structureNote()` L173 注入**（`res.segmentsLength = state.segments.length`），渲染靠它、不是 `segmentCount`。真实 LLM 不认识这字段，漏了 W4 联调必崩。
2. **`confidence` 必须是 0–1 的 `number`**，不可 `null`/字符串 —— **L83** 直接 `.toFixed(2)`，否则 TypeError 崩渲染。归一化：非数值或非有限 → **`0.5`**（落进标黄区；不能用 0）。
3. `ok` 必须被读 —— `doHandoff()` **L240** 目前**无条件** `handoffIndex++`，全库 `res.ok` 出现 **0 次**；真实实现返回 `{ok:false}` 时界面照样报「已确认接力」。

## 四、两个必须先修的隐患

| # | 隐患 | 修法 |
|---|---|---|
| 1 | 4 个适配器只有 `resolve`（无超时/无 reject），CrossDevice 有 `ok` 却没人读 → `state.busy` 永不复位，界面永久「AI 整理中…」 | 加 `timeoutMs`，**永不 reject**，失败返回 `{degraded:true, reason}`。预算：ASR 8s / OCR 5s / LLM 20s / RAG 2s / handoff 3s |
| 2 | `structure` 返回 `noteTemplate.sections` 的**引用不是拷贝** → 改一个字污染 `SCENES` | `JSON.parse(JSON.stringify(noteTemplate.sections))` |

## 五、置信度阈值：**W3 先别改数值**

**维持全局 `0.8`**，只抽常量：**L79** 与 **L162** → `const CONF = { default: 0.8, floor: 0.5 }`。
**W4 由 A 标定**：5 名试用者、每模态 **20~30 条**真实样本，取 **P20 + 绝对下限 0.5** 双闸。段置信度 = 该段所有行置信度的最小值（取 min，宁可多标）。
⚠️ 准确率不能当阈值（62.1%/57.6% 是「答对比例」，不是「自报概率」）。

## 六、W3 检查清单

- [ ] 新建 `adapters.real.js`，保留 Mock，`?mock=1` 切换
- [ ] 5 个实现加 `timeoutMs` + `degraded/reason`，不得 reject
- [ ] 修深拷贝 ｜ [ ] 抽 `0.8` 常量（L79/L162） ｜ [ ] `doHandoff` 加 `if(!res.ok)`
- [ ] 断网测试（Offline）：5 个能力全降级但界面可交互
- [ ] 请 B 用同一份 `index.html` 回归，证明**调用点没改**
