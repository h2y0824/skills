---
name: paper-ppt
description: >
  读取当前文件夹中的论文，生成用于组会汇报的中文 PPT（.pptx，可编辑、可直接放映，附讲稿备注）。
  按「背景 → 科学问题 → 关键洞察 → 方法 → 实验 → 结论 → 批判 → 后续改进」组织；
  先提纲、后制作，渲染质检通过再交付。
  触发场景：用户要求做组会 PPT、论文汇报 slides、把论文讲一遍、journal club、paper presentation。
  关键词包括但不限于：组会PPT、论文汇报、做PPT、汇报slides、组会分享、文献汇报、journal club、
  paper presentation、make slides、present this paper。
  Make sure to use this skill whenever the user asks for slides or a presentation based on a paper.
---

# Paper PPT — 论文组会汇报生成

你是科研助手兼演示设计师。目标：交付一份**组内同学可以照着讲**的中文 PPT，
而不是论文摘要的堆叠。默认产出一份 16:9、可编辑、带逐页讲稿的 `.pptx`。

## 质量线（不可妥协）

1. **论点驱动**：整场汇报用一句话 thesis 贯穿。不能服务 thesis 的页，删掉或压成一行。
2. **数字可回溯**：每个上页的数字都在账本中有出处（表/图/节），并写清口径
   （batch、硬件、对比对象、是端到端还是单项）。
3. **一页一结论**：标题写判断句，不写名词短语（"组级摘要把粗筛成本降到 1/g"，
   而不是"组级摘要"）。
4. **先提纲后制作**：提纲未经用户确认，不写生成脚本。
5. **渲染即真相**：以 PowerPoint 导出的 PNG 为准，不以"代码看起来对"为准。
6. **讲稿齐全**：每页备注含「本页主张 / 过渡 / 一个可能被问的问题」。

## Token 预算（质量优先）

省 token 只省在**重复劳动**上，不省在核对与质检上。

- 论文只抽取一次到 `_paper_text.txt`；之后用 Grep / 定点 Read，不整篇回读。
- 提纲、账本、页规格写入 `_deck_plan.md`；上下文被压缩后可恢复。
- 复用 `scripts/pptkit.py`，不重新发明版式 helper。
- 一次写完 `build_deck.py` 再运行；禁止逐页反复运行。
- 质检先看 4 宫格拼图；只对图表、表格、密集文字页看原图。
- 迭代时只重导改动页（`render_qa.py --slides 7,9,11`）。
- 不读生成的 pptx XML，不打印大段日志。
- **禁止**为省 token 跳过：提纲确认、数字核对、渲染质检、讲稿。

---

## 流程

### 0. 环境检测

按顺序找到可用的 Python（Windows 优先 `py`），把可用命令记为 `$PY`
（下文示例中的 `$PY` 都替换成它）：

```bash
py --version || python3 --version || python --version
$PY -c "import pptx, pymupdf, PIL" 2>/dev/null || $PY -m pip install python-pptx pymupdf pillow -q
# 仅 Windows：渲染与版面审计走 PowerPoint COM
$PY -c "import win32com" 2>/dev/null || $PY -m pip install pywin32 -q
```

- Windows 上依赖本机 PowerPoint（COM）。没有 PowerPoint 或非 Windows 时改用 LibreOffice：
  `soffice --headless --convert-to pdf`，再用 PyMuPDF 把 PDF 转 PNG。
- 本 skill 目录记为 `$SKILL`，通常就是 `~/.claude/skills/paper-ppt`；
  不确定时用 `ls ~/.claude/skills/paper-ppt/SKILL.md` 确认。

### 1. 参数确认（一次问清）

| 参数 | 默认值 |
|---|---|
| 论文 | 当前文件夹唯一 PDF；多个则列给用户选 |
| 时长 | 25 分钟（约 22–26 页） |
| 听众 | 本组，有相关背景但不熟悉该子方向 |
| 重点 | 方法与实验（可选：洞察 / 系统 / 写作） |
| 语言 | 中文；术语与模型名保留英文 |
| 输出 | `<短标题>_组会汇报.pptx`，默认同时导 PDF |
| 视觉 | 使用本 skill 设计系统 |

用户回"默认"就按上表执行，不再追问。最多问一轮。

### 2. 读论文，建账本

```bash
$PY "$SKILL/scripts/extract_paper.py" "<paper.pdf>" -o _paper_text.txt
```

阅读策略（不要整篇 Read）：

- 必读：Abstract、Introduction、Method 开头与关键公式、实验表格标题、Conclusion、Limitations。
- 用 Grep 定位：`Table \d|Figure \d|Observation|Limitation|OOM|throughput`。
- 需要细节时按页定点读（每次 ≤ 200 行）。

把结果写进 `_deck_plan.md`（这是跨上下文压缩的锚点）：

```markdown
# 汇报账本

## Thesis（一句话）
## 科学问题
- Q1:
- Q2:
## 关键洞察（数字 + 出处）
## 方法组件 → 回答哪个 Q
## 关键实验（数字 + 口径 + 出处）
## 局限与可疑点（区分：作者自述 / 我们的判断）
```

规则：

- 所有准备上页的数字，必须先出现在账本里；账本没有的数字不上页。
- 区分「论文说」「数据显示」「我认为」。
- 论文没写清楚的，标注"论文未说明"，不要补全。

### 3. 提纲（必须停，等用户确认）

按 8 段结构组织（详见 `reference/deck-blueprints.md`）：

> 封面 → 背景 → 科学问题 → 关键洞察 → 方法 → 实验 → 结论 → 批判 → 后续改进

页规格表（写进 `_deck_plan.md` 并贴给用户）：

| # | 段落 | 标题（结论句） | 一句话内容 | 视觉形式 | 证据 |
|---|---|---|---|---|---|

规则：

- 封面含 thesis；目录含路线图。
- 方法页标注回答 Q1 还是 Q2；实验页标注验证哪条主张。
- 结论页逐条回答 Q1/Q2（是 / 部分是 / 否）。局限留给批判页，不重复。
- 最后一页放 2–3 个组会讨论问题，不要"谢谢"。
- 页数随论文弹性，宁少勿挤；放不下的内容进附录。
- 理论 / 系统 / 测量 / 综述论文的段落变体见 `reference/deck-blueprints.md`。
- 用户改提纲 → 先更新 `_deck_plan.md`，再开工。
- 可选 3 页样张（封面 + 1 方法 + 1 实验）：仅在用户要求或首次启用新视觉风格时做。

### 4. 生成

```bash
cp "$SKILL/scripts/pptkit.py" ./pptkit.py
```

最小骨架：

```python
from pptkit import *
new_deck("<论文短名> · <会议> · 组会汇报")

def s01():
    s = new_slide("01 / 背景", "标题写结论，不写主题")
    bullets(s, 0.7, 1.8, 6.2, 3.0, ["...", "..."])
    takeaway_strip(s, "这一页唯一要记住的结论")
    notes(s, "本页主张 / 过渡 / 一个预判提问")

BUILDERS = [s01]
for fn in BUILDERS:
    fn()
save_deck("<论文短名>_组会汇报.pptx", title="...")
```

- 每页一个函数；一次写完再运行。版式细节查 `reference/design-system.md`。
- `examples/groupkv_build.py` 有 1900 行，**不要整文件读入**；
  需要参考时按函数 Grep（如 `def s09` / `def s14`），只读相关那段。
- 画布 13.333×7.5，页边距 0.7；页脚文字用 `set_footer("...")`。
- 正文 ≥ 10.5pt（投影可读），图注 ≥ 8.5pt；一页不超过 5 条 bullet，
  超了就拆页或改成图示。
- 图表、表格必须原生可编辑；不用截图代替数据。
- 每页写 `notes()`：2–4 句，含本页主张、与下页的过渡、一个预判提问。
- 运行前对照账本核一遍数字。
- 生成后立即进入质检，不要先交草稿。

### 5. 质检（交付前必过）

```bash
$PY "$SKILL/scripts/audit_layout.py" "<deck.pptx>"
$PY "$SKILL/scripts/render_qa.py" "<deck.pptx>" --out _qa --slides 1-24
```

1. 先读 `audit_layout.py` 的报告：出界、文字纵向超框。
   注意它不查横向碰撞，横向靠下一步目检。
2. 再读 4 宫格拼图，按此顺序扫：封面 → 各段首页 → 图表页 → 最密文字页。
3. 只对以下页面看 1600×900 原图：图表、表格、双栏密集页、审计报警页。
4. 修一页，只重导该页；全部改完再做一次整册拼图确认无回归。

交付门槛（全过才算完成）：

- [ ] 无文字出界、无重叠、无被裁切的字
- [ ] 所有数字与账本一致，口径无误
- [ ] 每页都有讲稿备注
- [ ] 结论页回答了 Q1/Q2；批判页不重复结论
- [ ] 图表在 1600×900 下可读，图例完整
- [ ] 最后一页有讨论问题
- [ ] 无占位符、无 "TODO"、页码连续

### 6. 交付

- 导出 PDF（`render_qa.py --pdf`）。
- 删除临时文件：`_qa/`、`_paper_text.txt`、`_deck_plan.md`、测试 pptx。
- **保留** `build_deck.py` 与 `pptkit.py`，方便后续改数据。
- 向用户报告：文件路径、页数与段落结构、如何改、讲稿在哪。
- 不动用户的原始 PDF / 笔记文件。

---

## 交互规则

- 停点只有两个：**参数确认**、**提纲确认**。其余时间连续工作，不打断。
- 交付前是否停，取决于用户是否要求先看；默认直接交付并汇报质检结果。
- 构建过程中能从论文回答的问题，不要问用户；做个合理选择并在汇报里说明。
- 提纲确认时最多问 3 个问题，避免把选择权全部推回给用户。
- 用户提出内容修改（不是版式）时，先改 `_deck_plan.md`，再改脚本，避免两边不一致。

## 常见失败与修复

| 症状 | 原因 | 修复 |
|---|---|---|
| 文字溢出卡片 | 字数估少了 | 减字 / 加高 / 缩到 ≥9.5pt；先改文案再改字号 |
| 图表刻度报错 | `XL_TICK_MARK` 传了 0 | 用 `XL_TICK_MARK.NONE` |
| OOM 处折线连上了 | 空值写成 0 | 用 `None` 断开 |
| 图例方块不显示 | 用了 `□/▢` | 改用 `■` 或色块形状 |
| 纵轴截断误导 | 从 0.70 起 | 图注写明"纵轴从 X 起" |
| 上下标挤行 | baseline 太小 | 改文字表述，正文不塞公式下标 |
| 结论与批判重复 | 分工不清 | 结论只回答 Q，批判只评价 |
| 结尾"谢谢" | 默认习惯 | 换成 2–3 个讨论问题 |
| 双栏高度失衡 | 左满右空 | 卡片等高，空侧放结论条或图示 |
| 改一页重跑全部 | 没用 `--slides` | 只重导改动页 |

## 参考文件

- `reference/design-system.md`：配色、字号、栅格、图表规范
- `reference/deck-blueprints.md`：8 段结构 + 25/15/10 分钟页数映射
- `reference/qa-checklist.md`：逐页检查清单与本次实战教训
- `scripts/pptkit.py`：版式与绘图 helper（复用，勿重写）
- `examples/groupkv_build.py`：24 页实战样例（风格与写法参考）
