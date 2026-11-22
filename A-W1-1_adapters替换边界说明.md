# adapters.js 替换边界说明

> 赛题1 · StudyFlow 智学伴侣 ｜ 负责人：**A**（CS 后端+算法+多模态）｜ W1 交付物 ③
> **版本 v1.7**（2026-11-11）｜ 依据：`demo/js/adapters.js`（75 行）、`demo/js/app.js`（334 行）**逐行核对**
> v1.1：真实实现映射、分模态阈值、契约伪代码；v1.2：别名调用检索提示（11 处行号全对）
> **v1.3：阈值按 PP-OCRv6 官方分场景数据重算（手写 0.58 而非 0.55），并补"置信度会骗人"的教训**
> 交接对象：队长（审架构）、B（界面侧确认**调用点**不改）

---

> **关于手册 3.3 ③「B 的界面代码不用改」的理解**：这句宜理解为**调用点不改**——5 个调用点的签名与业务逻辑确实不用动；
> 但「读 `degraded`、加 `if(!res.ok)`」属于**新增降级渲染**，那几行落在 `app.js` 里。
> 所以更精确的说法是：**调用点不改，降级渲染需另加几行。** 建议在队会上与队长对齐这一口径。

---

## 〇、结论



1. `demo/js/adapters.js` 是 UI 层与 AI 能力层的**唯一边界**。**5 个方法的入参/返回形状不变；`app.js` 的 5 个调用点签名与业务逻辑不改，但降级渲染必须加**（读 `degraded`、加 `if(!res.ok)`）。
 不能说"一行都不用改"——读字段就是改代码。
2. 这个边界有两个洞，但性质不同：
 - `structure` 返回引用不是拷贝（真缺陷，演示跑两次会串数据）
 - 失败态「有的没人读、没有的也没补」：`MockCrossDevice` 本来就有 `ok` 字段，但 `app.js` 的 `doHandoff()`（L240）**从不检查它**，`res.ok` 全库出现 **0 次**；其余 4 个则完全没有失败态。
 > 所以准确说法不是"5 个适配器全部只有 resolve"（CrossDevice 有 `ok`），而是"有失败态的没人读，没有失败态的也没补"。
3. 建议升到**契约 v1.1：不改签名，只加字段**（`degraded` / `reason`），失败走"标黄核对"而不是报错。
 **但要注意**：如果 UI 仍然不读 `degraded`，那只是把"没人读 `ok`"这个问题复制一遍——**W3 必须同时做两件事：加字段 + 在 `doHandoff` 里真的用上它。**

---

## 一、五个适配器：签名、返回、调用点、真实依赖

| # | 适配器 | 入参 | 返回（Promise 解析值） | app.js 调用点 | 真实实现依赖 |
|---|---|---|---|---|---|
| 1 | `MockASR.transcribe` | `(audioRef, fallbackText, fallbackConf)` | `{ text, confidence, source, engine, latencyMs }` | `addCap()` **L112**（`type==='audio'`）；触发：`.cap` 按钮 `bind()` **L304–309**、`tour()` **L278** | 端侧 sherpa-onnx 或云端 ASR（W3 Spike 定） |
| 2 | `MockOCR.recognize` | `(imageRef, fallbackText, fallbackConf)` | 同上 | `addCap()` **L113**（`type==='image'` 与 `'hand'` **共用同一个 OCR**）；触发同上 | **PP-OCRv6**（small 手写 57.6% / medium 62.1%，古籍 72.4%，印刷 91.5%）+ PaddleOCR 内置公式识别模块 |
| 3 | `MockLLM.structure` | `(segments, noteTemplate)` | `{ title, sections, segmentCount, engine }`，`sections = [{ h, points:[], src }]` | `structureNote()` **L172**；触发 `#structureBtn` **L310**、`tour()` **L281** | 大模型 API + 编排；**必须保留每段 `src`**，否则「溯源」交互失效 |
| 4 | `MockRAG.search` | `(query, corpus)` | `[{ title, meta, hit, tag }]`（当前为 `indexOf` 子串匹配） | `doSearch()` **L211**；触发 `#kbBtn` **L311**、`#kbInput` Enter **L312–314**、`tour()` **L285** | 向量库（嵌入式优先，见 《A-W1-2》第四节） |
| 5 | `MockCrossDevice.handoff` | `(taskState)` | `{ ok, via, task, timestamp }` | `doHandoff()` **L240**；触发 `#handoffBtn` **L315**、`tour()` **L290–294** | OPPO 互联开放能力 + 超级碰一碰；必须用户显式确认，不自动同步 |

> **⚠️ 检索提示（v1.2 核查后补）**：`app.js` 从不直接写 `MockASR.transcribe`，而是通过别名调用：
> ```js
> L109 var engine = type === "audio" ? MockASR : MockOCR;
> L112 ? engine.transcribe(...) // 音频
> L113 : engine.recognize(...) // 拍照 / 手写
> ```
> 所以按字符串 `MockASR.transcribe` 在 `app.js` 里是搜不到的——要搜 `engine.transcribe`。行号本身已逐条核验，11/11 正确。

### 两个易被忽略的契约细节

1. `MockOCR` 被两种模态复用（拍照 + 手写）。替换时若手写走不同引擎，要么内部路由，要么保持返回形状一致——否则 `addCap()` L114 起的渲染逻辑会崩。
2. `segmentsLength` 不在适配器返回里：它由 `structureNote()` **L173** 在拿到结果后注入。也就是说 `MockLLM.structure` 声明返回的形状**是不完整的**，替换真实实现时必须保留这个"调用方补字段"的约定。

---

## 二、两个必须在 W3 之前修掉的问题

### 问题 1：失败态「有的没人读、没有的也没补」（P0）

```js
// adapters.js 全篇都是这个形状
return MockDelay(420).then(function(){ return { ... }; });
```

而 `app.js` 两条关键路径都是 `state.busy` 设 true → 在 `.then` 里复位，没有 `catch`：

```js
// structureNote() L167–181
state.busy = true;
return MockLLM.structure(...).then(function(res){
 ...
 state.busy = false; // ← 一旦 reject，这行永远不执行
});

// doHandoff() L237–247
state.busy = true;
return MockCrossDevice.handoff(...).then(function(res){
 ...
 state.busy = false;
});
```

**后果链**：真实请求超时 → 无 catch → `state.busy` 永久 `true` → `structureNote()` 首行 `if(!state.segments.length || state.busy) return;` 永久短路 → 按钮停在被禁用的「AI 整理中…」→ 整条闭环死掉，只能刷新页面。

失效条件（什么情况下这条不用修）：只有当全部 5 个能力都是同步的、永不失败的本地调用时才成立——而 W3 起至少 LLM 与 RAG 必然走网络，所以这条一定会发生。

### 问题 2：`structure` 返回引用，编辑污染全局 Mock（P1）

`MockLLM.structure`（L42–47）：

```js
return MockDelay(520).then(function(){
 return { title: noteTemplate.title, sections: noteTemplate.sections, ... };
});
```

`sections` 是 `SCENES[scene].note.sections` 的同一个数组引用，没有拷贝。而 `renderNote()` **L144–151** 在 contenteditable blur 时直接写回：

```js
state.note.sections[si].points[pi] = t.textContent;
```

**后果**：演示一次 → 改一个要点 → 切「文学院」再切回来 → **改动还在**，与 README「刷新即重置」的边界说明不符，现场极易翻车。

**修法（一行）**：

```js
sections: JSON.parse(JSON.stringify(noteTemplate.sections))
```

---

## 三、契约 v1.1：不改签名，只加字段

### 约定 A：永不 reject，失败返回"降级结果"

每个适配器内部统一 `try/catch` + `timeoutMs`，把异常翻译成降级返回值。

| 字段 | 类型 | 说明 |
|---|---|---|
| `...原有字段` | — | **形状不变**，兼容 B 现行渲染 |
| `degraded` | `boolean?` | `true` 表示走了降级路径 |
| `reason` | `'TIMEOUT' \| 'NETWORK' \| 'LOW_CONF' \| 'ABORT' \| 'UNAVAILABLE'?` | 降级原因 |

为什么"永不 reject"是更好的设计：reject 必然要求调用方加 catch，而 catch 要写在 `app.js`（B 的文件）里——那就破坏了"B 不用改"的边界。把失败翻译成数据，失败就留在适配器内部。

### 约定 B：把降级交给已有的「标黄」范式

demo 已有 `confidence < 0.8 → 标黄建议人工核对`（`renderStream()` **L79**）。失败是同一类事——不是崩溃，是"这条不可靠，请你核对"。

于是断网时的界面不是报错弹窗，而是：

> `[已降级为本地处理] 本段转写未完成，请手动补充`

这正好把断网从**演示事故**变成**演示亮点**，直接对应赛题"验证网络变化时的实际体验"。

### 建议的超时预算

| 适配器 | timeoutMs | 理由 |
|---|---|---|
| ASR | 8000 | 5 分钟录音 + 上传 |
| OCR | 5000 | 单图 |
| LLM.structure | 20000 | 长上下文生成 |
| RAG | 2000 | 本地检索应极快，慢就是有问题 |
| CrossDevice | 3000 | 设备发现 + 传输握手 |

---

## 三·五、真实实现映射与分模态置信度阈值（v1.1 新增）

### 五个适配器 → 具体组件

| 适配器 | 真实实现 | 关键指标 |
|---|---|---|
| `MockASR` | sherpa-onnx（Paraformer / Zipformer CTC 系列，ONNX） | 离线可用、延迟可控 |
| `MockOCR` | **PP-OCRv6 small**（移动端）/ **medium**（服务端）+ PaddleOCR 公式识别模块 | 手写中文 **57.6%（small）/ 62.1%（medium）** |
| `MockLLM.structure` | 通义千问（主）/ 智谱 GLM（备） | JSON 解析失败率 **<5%**（≥5% 需加重试层） |
| `MockRAG` | sqlite-vec 0.1.9 + BGE/M3E 系 embedding + BM25 混合 | 召回 **P95 ≤200ms**；换 embedding 需召回差 **≥15%** |
| `MockCrossDevice` | OPPO 互联开放能力 + 超级碰一碰 | 用户显式确认 |

### 置信度阈值按模态分开

现有 demo 用了一个全局阈值：`confidence < 0.8 → 标黄`（`renderStream()` L79）。但不同模态的准确率差两倍以上：

| 模态 | 准确率（**PP-OCRv6**，百度官方分场景基准） | 建议阈值 | 理由 |
|---|---|---|---|
| 印刷中文 | **91.5%**（medium）/ 90.5%（small） | **待标定** | 低于它就是异常 |
| 繁体中文 | 78.6% / 77.0% | **待标定** | |
| **古籍文本** | **72.4% / 71.1%** | **待标定** | 比手写高，别一刀切 |
| 手写英文 | 67.8% / 61.1% | **待标定** | |
| **手写中文** | **62.1%（medium）/ 57.6%（small）** | **待标定** | **最低档之一**（特殊字符 61.7% 比它更低，原写"全表最低"不准确） |

> ⚠️ **v1.4 重大修正：阈值不能按准确率推，也不能单靠相对分位。**
> 我前后写错过两次：
> - **第一次（v1.3）**："手写 62.1% → 阈值 0.58"。错在准确率 ≠ 置信度（反例：v6 tiny 读不出日文 CER 47.3%，却报 0.7~0.95）；且 **0.58 是我拍脑袋定的绝对阈值，没有任何置信度分布依据**——拿它跟准确率（57.6%）比大小本身就是混淆两个量，**该数值已废弃**。
> - **第二次（一页版 v1.1）**："取 P20 分位，换档位不用重设"。**后半句错**——P20 是分位，换档位/换模型分布就变，**必须重新采样**。
>
> 正确设计：双闸（任一满足即标黄）
> | 闸 | 规则 |
> |---|---|
> | 闸 1 绝对下限 | `confidence < 0.5` → 无条件标黄（与分布无关，兜"绝对不可信"） |
> | 闸 2 相对分位 | `confidence < 该模态 P20` → 标黄（兜"这批里最可疑的"） |
>
> **聚合粒度**：OCR/ASR 原生是行级/句级；我们的 segment 是段级 →
> 段置信度 = 该段所有行置信度的最小值（取 min 不取平均，宁可多标）。
>
> **标定样本量**：原写"每模态 ≥100 条"，但 W4 只有 5 人试用，**做不完**。改为
> **W4 每模态 20~30 条**先跑通，W5+ 再扩到 100。换档位/换模态必须重采。
>
> 临时值（给 B）：**全局 0.8 保持不变**，只把它抽成常量——`app.js` **L79** 与 **L162**。
> 详细方案与验收指标（复用「识别修正率」）见一页版 `A-W1-1b` 第五节。

> ⚠️ **修订说明（v1.3，已被 v1.4 覆盖）**：上一版这张表用的是 **PP-OCRv5 mobile** 的数字（手写 41.66%），据此定的阈值 0.55 偏低。
> v6 的官方分场景数据现已公布，手写实际为 62.1%/57.6%。
> 注：0.58 后来被证明缺乏依据，已废弃，见 §三·五。
>
> 另一个必须记住的教训：**v6 tiny 读不出日文（字符错误率 47.3%），但它的置信度仍报 0.7~0.95**。
> 这说明置信度不能单独作为"可不可信"的依据——它会在模型根本不会的场景上给出高分。所以：
> - 标黄只是第一道闸，必须配合"用户可编辑 + 可溯源核对"
> - 模型能力边界（如 tiny 不支持日文）要在**路由层**拦住，不能指望置信度兜底

> 为什么这件事重要：标黄是为了让用户核对。阈值设得比模型能力还高，会导致每条都标黄——等于一条都没标。 这是"可检查可修正"设计里最容易翻车的地方，也是 demo 里唯一一个"看起来做对了、其实失效"的机制。
>
> 阈值设计见下方"双闸"方案（绝对下限 + 相对分位）。
> ~~原建议"`confidence < 该模态历史中位数 × 0.8`"~~ —— **已被 v1.4 的双闸方案取代**，
> 因为单用相对阈值表达不了"绝对不可信"（印刷体也会被硬标 20%）。

### 契约 v1.1 伪代码

```js
function withGuard(fn, { timeoutMs }) {
 return function (...args) {
 return Promise.race([
 fn(...args),
 new Promise(r => setTimeout(() => r({ degraded: true, reason: 'TIMEOUT' }), timeoutMs))
 ])
 .catch(e => ({ degraded: true, reason: 'NETWORK', message: String(e) }));
 // 永不 reject：失败被翻译成数据，state.busy 一定能复位
 };
}

var ASR = { transcribe: withGuard(_asrImpl, { timeoutMs: 8000 }) };
```

**⚠️ 更正（v1.5）：原写"B 的界面代码一行不改"——这句话是错的，已重写（不是简单删除，见下表两句对比）。**

准确说法是两条：

| 说法 | 是否成立 |
|---|---|
| `app.js` 的调用点与业务逻辑不改（5 处调用签名、7 处 state 流转都不动） | ✅ 成立 |
| `app.js` 里与"降级/失败"相关的渲染逻辑要改（读 `degraded` 并渲染"已降级"） | ❌ 原文说"一行不改"是错的——**读字段就是改代码** |

> 所以口径改为："除渲染降级标记外，界面逻辑不改。"
> 答辩时不能说"一行没改"，只能说"调用点没改，只加了降级显示"——后者经得起现场验证。

---

### 既有的失败态

`MockCrossDevice.handoff` 本来就有 `ok` 字段（`adapters.js` L71 返回 `{ok:true, via, task, timestamp}`），
但 **`app.js` L240–245 的 `doHandoff` 无条件执行 `state.handoffIndex++`，从不检查 `res.ok`**
（grep 全库：`res.ok` 在 `app.js` 中出现 **0 次**）。

**后果**：真实实现返回 `{ok:false}` 时，界面照样会显示"已确认接力"。

**这就是为什么 §二「问题 1」的标题从"5 个适配器全部只有 resolve"改成了"有的没人读、没有的也没补"**：
- 不是"5 个适配器都没有失败态"（CrossDevice 本来就有 `ok`）
- 而是"有失败态的没人读，没有失败态的也没补"

**W3 必须做**：在 `doHandoff`（`app.js` L240）里加 `if (!res.ok) { ...降级分支... }`。
否则我给 `degraded` 加字段，只是把同一个问题复制一遍。

---

### `confidence` 的类型约束

契约要求：**`confidence` 必须是 0–1 的 `number`，不可为 `null`、不可为字符串。**

原因：`app.js` **L83** 直接调 `s.confidence.toFixed(2)`。
- 真实 ASR/OCR 返回 `null` → TypeError，整个渲染挂掉
- 返回字符串 `"0.92"` → `.toFixed` 不存在 → **同样崩**

真实适配器必须在返回前做归一化：

```js
// 任何适配器返回前统一走这一步
confidence: typeof c === 'number' && isFinite(c) ? Math.min(1, Math.max(0, c)) : 0.5
```

> `0.5` 是"未知置信度"的约定值（会落进闸 2 的标黄区），**不用 `null`、不用 `0`**——
> `0` 会被当成"确定错误"，`null` 会崩。

---

## 四、W3 替换检查清单

- [ ] 新建 `adapters.real.js`，保留 `adapters.js` 作为 Mock，用 `index.html?mock=1` 切换
- [ ] 5 个实现全部加 `timeoutMs`（按上表预算）
- [ ] 5 个实现全部加 `degraded` / `reason`，不得 reject
- [ ] 修 `MockLLM.structure` 的深拷贝（问题 2，一行）
- [ ] **把 L79 / L162 的 `0.8` 抽成常量 `CONF`，数值不动**（见 §三·五；**W3 不要改数值**，W4 标定后再换）
- [ ] `doHandoff`（L240）加 `if (!res.ok)` 分支
- [ ] 段置信度改为取该段行置信度的最小值
- [ ] **断网测试**：DevTools → Network → Offline，确认 5 个能力全部降级但界面不卡
- [ ] **弱网测试**：Throttling → Fast 3G，记录 p50 / p95 延迟
- [ ] **回归测试**：请 B 用同一份 `index.html` 跑完 W1 的 6 条验收项，证明"**5 个调用点与业务逻辑没改**"（不要说"一行没改"）
- [ ] 把测试结果写成一页，作为"端云协同"的技术证据

---

## 五、给 W3 Spike 的输入（一句话交接）

W3 要出「端侧 vs 云端」结论，但判据不是"哪个准"，而是**这 5 个适配器里哪几个必须本地、哪几个可以上云**。建议先按这个假设去验：

| 适配器 | 初判 | 理由 |
|---|---|---|
| ASR | 可云可端 | 端侧 sherpa-onnx 已可用；云端准但断网即废 |
| OCR（截图/公式） | **偏端侧** | OCR 本地已成熟，且课件截图含个人信息 |
| OCR（古籍竖排/手写） | 倾向云端 | 准确率差距大，先保证能用 |
| LLM.structure | **偏云端** | 端侧小模型结构化能力不够，先云 + 本地缓存 |
| RAG | **必须本地** | 个人知识库不出设备，这是产品红线 |
| CrossDevice | 本地 | 走 OPPO SDK，与云无关 |

> 这是**假设**，W3 用实验证实或推翻，别当结论用。

---

## 六、答辩可直接念的三句

1. "我们的 AI 能力全部经过一层**适配器边界**，五个接口在 W1 就定死了形状——所以从假的换成真的，**5 个调用点签名和业务逻辑都没改**（只加了降级渲染），这是可以现场验证的。"
2. "我们的适配器**永不抛异常**。失败会被翻译成一个 `degraded` 标记，走已有的标黄核对流程——所以拔掉网线我们的界面不会崩，它只是会诚实地告诉你这一段不可靠。"
3. "这是我们有意识做的取舍：报错弹窗是在推卸责任，标黄是在把判断权还给用户。"

---

## 七、版本记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-11-11 | 首稿：五适配器边界 + 两个问题 |
| v1.0 | 2026-11-11 | 补：调用点行号核对、失效条件、契约 v1.1 字段表、超时预算表、回归测试清单、答辩话术、版本记录 |
| v1.1 | 2026-11-11 | 补：真实实现映射（PP-OCRv6 / sherpa-onnx·Qwen3-ASR / sqlite-vec）、**分模态置信度阈值**、契约伪代码 |
| v1.2 | 2026-11-11 | 补：**别名调用检索提示**（11 处行号已逐条验证，11/11 正确） |
| v1.3 | 2026-11-11 | 补：阈值按 PP-OCRv6 官方分场景数据重算（手写 0.58 而非 0.55）；修表格里残留的 PP-OCRv5 数字；新增"置信度会骗人"的教训 |
| **v1.4** | 2026-11-11 | **修正方法论**：阈值不能按准确率推、也不能只靠 P20；改为**双闸（绝对下限 0.5 + 相对分位 P20）**+ 段级取最小值 + 给 B 的临时值与行号 |
