# -*- coding: utf-8 -*-
"""GroupKV 24 页实战样例（组会汇报）。

这是 paper-ppt skill 的"活样例"：版式、图表、讲稿、批判页写法都可直接借鉴。
运行前确保本机有 PowerPoint / python-pptx / pymupdf / pillow：

    py groupkv_build.py
输出到当前目录的 GroupKV_组会汇报.pptx。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from pptkit import *

new_deck("GroupKV · ICPP '26 · 组会论文汇报")
# ================================================================== 1 title
def s01():
    s = new_slide(page=False)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = NAVY

    # faint decorative panel
    dec = rect(s, 8.1, 0.0, 5.5, 7.5, fill=RGBColor(0x14, 0x30, 0x4A))
    try:
        for srgb in dec.fill._xPr.findall(".//" + qn("a:srgbClr")):
            srgb.append(srgb.makeelement(qn("a:alpha"), {"val": "45000"}))
    except Exception:
        pass

    rect(s, 0.9, 1.28, 0.06, 0.3, fill=AMBER)
    tb, tf = textbox(s, 1.08, 1.24, 6.0, 0.3)
    p = para(tf, first=True)
    r = p.add_run()
    r.text = "论文精读 · 组会汇报"
    style_run(r, size=12, bold=True, color=AMBER, spc=180)

    tb, tf = textbox(s, 0.86, 1.72, 7.3, 1.2)
    p = para(tf, first=True, line=0.9)
    r = p.add_run()
    r.text = "GroupKV"
    style_run(r, size=60, bold=True, color=WHITE)

    tb, tf = textbox(s, 0.9, 2.92, 7.0, 0.6)
    p = para(tf, first=True)
    r = p.add_run()
    r.text = "面向长上下文扩散大模型的分层 KV Cache 管理"
    style_run(r, size=21, bold=True, color=RGBColor(0xDF, 0xEC, 0xF2))

    tb, tf = textbox(s, 0.9, 3.55, 6.9, 0.8)
    p = para(tf, first=True, line=1.15)
    add_runs(p, [
        ("Hierarchical KV Cache Management\n", {"size": 12.5, "color": RGBColor(0x9F, 0xBF, 0xCE)}),
        ("for Long-Context Diffusion LLM Inference", {"size": 12.5, "color": RGBColor(0x9F, 0xBF, 0xCE)}),
    ])

    line(s, 0.9, 4.42, 6.6, 4.42, color=RGBColor(0x2C, 0x4A, 0x61), width=0.9)

    tb, tf = textbox(s, 0.9, 4.62, 7.0, 0.3)
    p = para(tf, first=True)
    r = p.add_run()
    r.text = "Jinhao Wang, Zhexin Hu, Kangjie Zhou, Xin Zhou, Fangfang Liu"
    style_run(r, size=10.5, color=RGBColor(0xC4, 0xD6, 0xE0))

    tb, tf = textbox(s, 0.9, 4.93, 7.0, 0.3)
    p = para(tf, first=True)
    r = p.add_run()
    r.text = "中科院软件研究所 · 国科大 · 南京理工大学"
    style_run(r, size=9.5, color=RGBColor(0x8F, 0xAD, 0xBD))

    pill(s, 0.9, 5.62, 2.25, 0.34, "ICPP '26 · Singapore", fill=RGBColor(0x1B, 0x3A, 0x52),
         color=RGBColor(0xCF, 0xE4, 0xEE), size=9.5)
    pill(s, 3.3, 5.62, 2.35, 0.34, "2026.10.29 · 组会", fill=RGBColor(0x1B, 0x3A, 0x52),
         color=RGBColor(0xCF, 0xE4, 0xEE), size=9.5)

    # group blocks decoration
    tb, tf = textbox(s, 8.55, 4.02, 4.2, 0.25)
    p = para(tf, first=True, align=PP_ALIGN.LEFT)
    r = p.add_run()
    r.text = "CONTEXT  →  GROUPS  →  TOP-k"
    style_run(r, size=8, bold=True, color=RGBColor(0x6E, 0x93, 0xA8), spc=140)

    bw, bh, gap = 0.46, 0.52, 0.09
    for row in range(3):
        for col in range(7):
            x = 8.55 + col * (bw + gap)
            y = 4.42 + row * (bh + 0.14)
            selected = (row == 0 and col in (2,)) or (row == 1 and col in (4, 5)) or (row == 2 and col in (1,))
            if selected:
                b = rect(s, x, y, bw, bh, fill=TEAL if row != 1 else AMBER, line=None,
                         shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
                try:
                    for srgb in b.fill._xPr.findall(".//" + qn("a:srgbClr")):
                        srgb.append(srgb.makeelement(qn("a:alpha"), {"val": "88000"}))
                except Exception:
                    pass
            else:
                rect(s, x, y, bw, bh, fill=None, line=RGBColor(0x2E, 0x4E, 0x66),
                     shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
    tb, tf = textbox(s, 8.55, 6.35, 4.2, 0.25)
    p = para(tf, first=True)
    r = p.add_run()
    r.text = "coarse-to-fine group selection"
    style_run(r, size=8.5, color=RGBColor(0x7D, 0xA3, 0xB8), italic=True)

    tb, tf = textbox(s, 11.1, 6.7, 1.6, 0.25)
    p = para(tf, first=True, align=PP_ALIGN.RIGHT)
    r = p.add_run()
    r.text = "汇报人：________"
    style_run(r, size=9, color=RGBColor(0x7D, 0xA3, 0xB8))

    notes(s, "开场：今天汇报的是 ICPP'26 的 GroupKV，一篇面向长上下文扩散语言模型（dLLM）的 KV cache 系统论文。"
             "它不是提出新模型，而是解决显存受限时长上下文推理的 KV 管理问题。")


# ================================================================== 2 contents
def s02():
    s = new_slide("CONTENTS", "汇报大纲")
    items = [
        ("01", "研究背景与问题", "dLLM 的解码范式、KV 膨胀、offload 后的传输瓶颈"),
        ("02", "两个关键观察", "块内访问重叠 + 层间显著性一致，分别支撑组级选择与跨层预取"),
        ("03", "GroupKV 系统设计", "组级分层访问、预测预取、陈旧性修复、流式 prefill"),
        ("04", "实验评估", "LongBench / RULER / NIAH，A100 与 RTX 4090 上的吞吐与消融"),
        ("05", "批判性讨论", "大数字的边界、未验证的机制、可继续做的方向"),
    ]
    y0 = 1.82
    line(s, 1.56, y0 + 0.12, 1.56, y0 + 4.55, color=BORDER, width=1.0)
    for i, (num, title, desc) in enumerate(items):
        y = y0 + i * 0.93
        dot = rect(s, 1.49, y + 0.1, 0.14, 0.14, fill=WHITE, line=TEAL, line_w=1.6,
                   shape=MSO_SHAPE.OVAL)
        tb, tf = textbox(s, 0.66, y, 0.68, 0.5)
        p = para(tf, first=True, align=PP_ALIGN.RIGHT)
        r = p.add_run()
        r.text = num
        style_run(r, size=20, bold=True, color=TEAL)
        tb, tf = textbox(s, 1.95, y - 0.02, 6.4, 0.4)
        p = para(tf, first=True)
        r = p.add_run()
        r.text = title
        style_run(r, size=17, bold=True, color=INK)
        tb, tf = textbox(s, 1.95, y + 0.35, 6.5, 0.35)
        p = para(tf, first=True)
        r = p.add_run()
        r.text = desc
        style_run(r, size=11, color=MUTED)

    card(s, 8.95, 1.8, 3.68, 4.55, fill=NAVY, line=None)
    tb, tf = textbox(s, 9.22, 2.0, 3.1, 0.3)
    p = para(tf, first=True)
    r = p.add_run()
    r.text = "论文速览"
    style_run(r, size=11, bold=True, color=RGBColor(0x7D, 0xC6, 0xC4), spc=80)
    stats = [
        ("48.00×", "最大可服务上下文扩展", "RTX 4090：Fast-dLLM 2K → GroupKV 96K"),
        ("3.73×", "offload 场景端到端加速", "A100：32K 上下文，相对 FlexGen 风格基线"),
        ("98.17%", "NIAH 平均检索精度", "4K–128K；128K 仍保持 95%"),
    ]
    for i, (v, lab, sub) in enumerate(stats):
        y = 2.5 + i * 1.28
        tb, tf = textbox(s, 9.22, y, 3.1, 0.55)
        p = para(tf, first=True)
        r = p.add_run()
        r.text = v
        style_run(r, size=26, bold=True, color=WHITE)
        tb, tf = textbox(s, 9.22, y + 0.48, 3.15, 0.3)
        p = para(tf, first=True)
        r = p.add_run()
        r.text = lab
        style_run(r, size=9.5, bold=True, color=RGBColor(0xC8, 0xDC, 0xE7))
        tb, tf = textbox(s, 9.22, y + 0.73, 3.15, 0.4)
        p = para(tf, first=True)
        r = p.add_run()
        r.text = sub
        style_run(r, size=8.5, color=RGBColor(0x8F, 0xAD, 0xBD))

    notes(s, "汇报分五部分：先讲 dLLM 与长上下文推理的瓶颈，再讲两个支撑设计的观察，"
             "然后拆解五个组件，最后看实验并做批判性讨论。三个数字先给大家一个整体印象。")


# ================================================================== 3 dLLM
def s03():
    s = new_slide("01 / 研究背景", "dLLM：用「整块去噪」替代「逐 token 生成」")

    # AR card
    card(s, 0.7, 1.78, 5.85, 3.55)
    pill(s, 0.95, 1.98, 1.55, 0.3, "AUTOREGRESSIVE", fill=BLUE_LIGHT, color=BLUE, size=8)
    tb, tf = textbox(s, 0.95, 2.35, 5.2, 0.4)
    p = para(tf, first=True)
    r = p.add_run()
    r.text = "自回归 LLM：从左到右，一次一个"
    style_run(r, size=14.5, bold=True, color=INK)

    # AR mini diagram
    for i in range(7):
        filled = i < 3
        b = box(s, 0.98 + i * 0.63, 2.9, 0.5, 0.5, "t%d" % (i + 1) if filled else "",
                fill=NAVY if filled else WHITE, line=NAVY if filled else BORDER,
                color=WHITE, size=8)
        if not filled:
            b.line.dash_style = MSO_LINE.DASH
    tb, tf = textbox(s, 0.98, 3.45, 4.6, 0.25)
    p = para(tf, first=True)
    r = p.add_run()
    r.text = "t1 → t2 → t3 → …　（已生成 / 待生成）"
    style_run(r, size=8.5, color=MUTED)

    bullets(s, 0.98, 3.9, 5.25, 1.3, [
        "因果注意力：每个 token 只能看到左侧历史",
        "prefill 之后 KV 只追加（append-only），历史 KV 可长期复用",
        "KV 生命周期稳定、可预测",
    ], size=11.5, gap=5)

    # dLLM card
    card(s, 6.78, 1.78, 5.85, 3.55)
    pill(s, 7.03, 1.98, 1.25, 0.3, "DIFFUSION", fill=TEAL_LIGHT, color=TEAL_DARK, size=8)
    tb, tf = textbox(s, 7.03, 2.35, 5.2, 0.4)
    p = para(tf, first=True)
    r = p.add_run()
    r.text = "扩散 LLM：整块迭代去噪"
    style_run(r, size=14.5, bold=True, color=INK)

    # dLLM diagrams: two rows
    for row in range(2):
        for i in range(7):
            if row == 0:
                filled = i < 3
                label = "t%d" % (i + 1) if filled else "?"
            else:
                filled = i < 5
                label = "t%d" % (i + 1)
            x = 7.03 + i * 0.63
            y = 2.84 + row * 0.52
            b = box(s, x, y, 0.5, 0.42, label,
                    fill=(NAVY if (row == 0 and filled) else (TEAL if (row == 1 and filled) else WHITE)),
                    line=(NAVY if (row == 0 and filled) else (TEAL if (row == 1 and filled) else BORDER)),
                    color=WHITE if (filled) else MUTED, size=8, radius=0.12)
            if not filled:
                b.line.dash_style = MSO_LINE.DASH
    tb, tf = textbox(s, 11.55, 2.94, 0.95, 0.8)
    p = para(tf, first=True)
    r = p.add_run()
    r.text = "iteration\nk → k+1"
    style_run(r, size=8, color=MUTED)
    p.line_spacing = 1.0

    bullets(s, 7.03, 3.9, 5.3, 1.3, [
        "双向注意力：可见前后文，支持 infilling",
        "一次更新块内多个 token，可并行解码",
        "KV 需要周期性全序列重算 + 生成槽位非顺序覆盖",
    ], size=11.5, gap=5, bullet_color=AMBER)

    # bottom takeaway
    rect(s, 0.7, 5.52, 11.93, 1.32, fill=RGBColor(0x10, 0x2B, 0x42),
         shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.05)
    rect(s, 0.7, 5.52, 0.07, 1.32, fill=AMBER)
    tb, tf = textbox(s, 0.98, 5.68, 11.4, 0.35)
    p = para(tf, first=True)
    add_runs(p, [
        ("关键差异：", {"size": 13, "bold": True, "color": AMBER}),
        ("KV 的生命周期从「只追加」变成「反复刷新 + 非顺序覆盖」。", {"size": 13, "bold": True, "color": WHITE}),
    ])
    tb, tf = textbox(s, 0.98, 6.1, 11.35, 0.6)
    p = para(tf, first=True, line=1.15)
    r = p.add_run()
    r.text = ("代表模型：LLaDA / Dream / Mercury / Gemini Diffusion；部署形态以 block-wise decoding 为主。"
              "本文是系统论文：不提出新模型，而是设计 KV cache 的运行时管理。")
    style_run(r, size=10.5, color=RGBColor(0xB9, 0xCE, 0xD9))

    notes(s, "先把 dLLM 和 AR 的区别讲清楚：AR 的 KV 只追加、生命周期稳定；dLLM 一次更新一个块，"
             "会周期性地重算整条序列，还会非顺序地改写生成槽位，所以 KV 是动态的。这是整篇论文的前提。")


# ================================================================== 4 two walls
def s04():
    s = new_slide("01 / 研究背景", "两道墙：先撞上显存容量，再换成 PCIe 带宽")

    # left card
    card(s, 0.7, 1.78, 5.72, 3.45, fill=WHITE)
    pill(s, 0.95, 1.96, 1.65, 0.3, "① 全量 KV 常驻 GPU", fill=RED_LIGHT, color=RED, size=8.5)
    tb, tf = textbox(s, 0.95, 2.33, 5.2, 0.4)
    p = para(tf, first=True)
    r = p.add_run()
    r.text = "容量随 S × batch 线性增长"
    style_run(r, size=15, bold=True, color=INK)

    bullets(s, 0.95, 2.8, 5.2, 1.0, [
        "LLaDA-8B 量级：每 token 每层 K+V = 2×32×128×2B = 16 KiB",
        "32 层 × 16 KiB = 512 KiB / token；权重本身还要 ~16 GiB",
    ], size=11.5, gap=5, bullet_color=RED)

    rect(s, 0.95, 3.86, 5.2, 0.62, fill=RED_LIGHT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06)
    tb, tf = textbox(s, 1.08, 3.96, 4.95, 0.45)
    p = para(tf, first=True)
    add_runs(p, [
        ("128K 上下文 × 512 KiB ≈ ", {"size": 12, "color": INK}),
        ("64 GiB", {"size": 13.5, "bold": True, "color": RED}),
        ("（batch=1）", {"size": 11, "color": BODY}),
    ])
    tb, tf = textbox(s, 0.95, 4.56, 5.2, 0.45)
    p = para(tf, first=True)
    r = p.add_run()
    r.text = "A100-80G：32K 已接近极限；RTX 4090-24G：4K 即 OOM"
    style_run(r, size=10.5, color=BODY)

    # right card
    card(s, 6.92, 1.78, 5.72, 3.45, fill=WHITE)
    pill(s, 7.17, 1.96, 1.62, 0.3, "② KV offload 到 CPU", fill=AMBER_LIGHT, color=AMBER, size=8.5)
    tb, tf = textbox(s, 7.17, 2.33, 5.2, 0.4)
    p = para(tf, first=True)
    r = p.add_run()
    r.text = "容量换来了，但搬运成为新瓶颈"
    style_run(r, size=15, bold=True, color=INK)
    bullets(s, 7.17, 2.8, 5.2, 1.85, [
        "128K 上下文：单层 K/V ≈ 2 GiB；一次全层刷新 ≈ 64 GiB 搬运",
        "PCIe 4.0×16 有效带宽 ~25 GB/s，对比 HBM ~2 TB/s",
        "传输被暴露在解码关键路径上，每一步都要等数据",
    ], size=11.5, gap=5, bullet_color=AMBER)

    # GPU-CPU visual
    rect(s, 7.3, 4.55, 1.55, 0.5, fill=TEAL_LIGHT, line=TEAL, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.1)
    tb, tf = textbox(s, 7.3, 4.64, 1.55, 0.3)
    p = para(tf, first=True, align=PP_ALIGN.CENTER)
    r = p.add_run(); r.text = "GPU / HBM"
    style_run(r, size=9.5, bold=True, color=TEAL_DARK)
    line(s, 8.92, 4.8, 9.95, 4.8, color=AMBER, width=1.6, head=True, tail=True)
    tb, tf = textbox(s, 8.85, 4.42, 1.2, 0.3)
    p = para(tf, first=True, align=PP_ALIGN.CENTER)
    r = p.add_run(); r.text = "H2D / D2H"
    style_run(r, size=8, bold=True, color=AMBER)
    rect(s, 10.0, 4.55, 1.55, 0.5, fill=BLUE_LIGHT, line=BLUE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.1)
    tb, tf = textbox(s, 10.0, 4.64, 1.55, 0.3)
    p = para(tf, first=True, align=PP_ALIGN.CENTER)
    r = p.add_run(); r.text = "CPU / pinned"
    style_run(r, size=9.5, bold=True, color=BLUE)

    # bottom takeaway
    rect(s, 0.7, 5.55, 11.93, 1.15, fill=AMBER_LIGHT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.05)
    rect(s, 0.7, 5.55, 0.07, 1.15, fill=AMBER)
    tb, tf = textbox(s, 0.98, 5.7, 11.4, 0.45)
    p = para(tf, first=True)
    add_runs(p, [
        ("offload 没有消除瓶颈，", {"size": 13, "bold": True, "color": INK}),
        ("只是把「容量墙」换成了「带宽墙」。", {"size": 13, "bold": True, "color": AMBER}),
    ])
    tb, tf = textbox(s, 0.98, 6.12, 11.4, 0.45)
    p = para(tf, first=True)
    r = p.add_run()
    r.text = ("更麻烦的是：dLLM 周期重算 + 局部覆盖，让搬运更频繁、token 级统计更难摊销。"
              "问题从「放不放得下」变成「能不能高效地搬」。")
    style_run(r, size=10.5, color=BODY)

    notes(s, "两道墙：第一，全量 KV 随序列和 batch 线性涨，128K 在 8B 模型上粗算就是 64GiB；"
             "第二，offload 把容量问题换成 PCIe 搬运问题，而 dLLM 的 KV 还会反复刷新。"
             "这就解释了为什么直接复用 AR 的 KV 优化不够。")


# ================================================================== 5 why not AR
def s05():
    s = new_slide("01 / 研究背景", "为什么 AR 的 KV 优化不能直接搬过来？")

    cards = [
        ("① 依赖稳定统计", "AR 稀疏/索引方法", [
            "H2O / SnapKV / InfiniGen / HISA 都假设 append-only",
            "token 统计、索引、聚类可跨解码步复用",
            "dLLM 周期重算 + 非顺序覆盖 ⇒ 索引失效、维护成本无法摊销",
        ], RED),
        ("② 传输在关键路径", "按需 token 级恢复", [
            "必须先把 K 传到 GPU 才能打分，再决定取哪些 V",
            "传输与计算串行，无法提前预取",
            "K/V 等大 ⇒ 压缩比结构上限 ≈ 2×",
        ], AMBER),
        ("③ 块内并集膨胀", "block-wise 解码放大问题", [
            "同一块内多个 token 需要同时备好上下文 KV",
            "若各 token 关注位置分散，访问并集迅速逼近全上下文",
            "细粒度稀疏的收益被并集抵消",
        ], BLUE),
    ]
    responses = [
        "→ 组摘要只随受影响组刷新（组件一 / 三）",
        "→ 跨层预测预取，把 H2D 藏进计算（组件二）",
        "→ 连续组覆盖，避免逐 token 并集（组件一）",
    ]
    for i, (tag, title, items, color) in enumerate(cards):
        x = 0.7 + i * 4.04
        card(s, x, 1.78, 3.85, 3.55)
        rect(s, x, 1.78, 3.85, 0.07, fill=color)
        pill(s, x + 0.22, 2.0, 1.72, 0.3, tag, fill=LIGHT, color=color, size=8.5)
        tb, tf = textbox(s, x + 0.22, 2.38, 3.4, 0.55)
        p = para(tf, first=True)
        r = p.add_run(); r.text = title
        style_run(r, size=13.5, bold=True, color=INK)
        bullets(s, x + 0.22, 2.95, 3.42, 1.4, items, size=10.5, gap=8, bullet_color=color)
        rect(s, x + 0.22, 4.4, 3.42, 0.72, fill=LIGHT, line=None,
             shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06)
        tb, tf = textbox(s, x + 0.34, 4.48, 3.2, 0.58)
        p = para(tf, first=True, line=1.1)
        add_runs(p, [("本文对策：", {"size": 8.5, "bold": True, "color": color}),
                     (responses[i].replace("→ ", ""), {"size": 8.8, "color": BODY})])

    rect(s, 0.7, 5.58, 11.93, 1.15, fill=TEAL_LIGHT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.05)
    rect(s, 0.7, 5.58, 0.07, 1.15, fill=TEAL)
    tb, tf = textbox(s, 0.98, 5.72, 11.4, 0.4)
    p = para(tf, first=True)
    add_runs(p, [
        ("机会：", {"size": 13, "bold": True, "color": TEAL_DARK}),
        ("实测块内访问高度重叠、空间集中 → 把选择与预取的单位从 token 提升为连续的「组」。",
         {"size": 13, "bold": True, "color": INK}),
    ])
    # token -> group visual
    tb, tf = textbox(s, 0.98, 6.18, 11.3, 0.4)
    p = para(tf, first=True)
    add_runs(p, [
        ("token 级：", {"size": 10.5, "color": MUTED}),
        ("2N 条目全量搬运、压缩上限 2×　", {"size": 10.5, "color": BODY}),
        ("→  group 级：", {"size": 10.5, "bold": True, "color": TEAL}),
        ("N/g 摘要 + 2fN 恢复，可流水、可预取", {"size": 10.5, "bold": True, "color": TEAL}),
    ])

    notes(s, "三类障碍：AR 方法依赖稳定统计；token 级按需要把 K 先传上 GPU，压缩比结构上只能到 2 倍；"
             "block 解码会让多个 token 的选择并集膨胀。但块内访问又有很强的重叠性，于是作者把单位换成组。")


# ================================================================== 6 observation 1
def s06():
    s = new_slide("02 / 关键观察", "观察一：块内访问高度重叠，且空间集中")

    # stats
    stats = [("Jaccard", "0.744", "UltraLLaDA 0.7442 ｜ LLaDA-8B 0.7308"),
             ("Overlap", "0.843", "UltraLLaDA 0.8428 ｜ LLaDA-8B 0.8318")]
    for i, (lab, val, sub) in enumerate(stats):
        x = 0.7 + i * 3.12
        card(s, x, 1.78, 2.95, 1.3, fill=LIGHT, line=None)
        tb, tf = textbox(s, x + 0.18, 1.93, 2.6, 0.25)
        p = para(tf, first=True)
        r = p.add_run(); r.text = lab
        style_run(r, size=10, bold=True, color=TEAL, spc=80)
        tb, tf = textbox(s, x + 0.18, 2.18, 2.6, 0.5)
        p = para(tf, first=True)
        r = p.add_run(); r.text = val
        style_run(r, size=28, bold=True, color=INK)
        tb, tf = textbox(s, x + 0.18, 2.72, 2.7, 0.3)
        p = para(tf, first=True)
        r = p.add_run(); r.text = sub
        style_run(r, size=8.5, color=MUTED)

    tb, tf = textbox(s, 0.7, 3.18, 6.1, 0.3)
    p = para(tf, first=True)
    r = p.add_run()
    r.text = "top-k = 20%；块内 token 两两访问集的平均重叠"
    style_run(r, size=9.5, color=MUTED, italic=True)

    bullets(s, 0.7, 3.58, 6.1, 2.1, [
        "块级访问集 Ω_B = 块内各 token 访问集的并集；重叠越低，越接近全上下文",
        "显著 token 集中在少数连续区间，而不是散落在整个上下文",
        "覆盖这些区间所需的组数 ≤ Σ(⌈L/g⌉ + 1)，+1 吸收组边界错位",
        "组边界多纳入的 token 紧邻显著段、权重低，softmax 后贡献可忽略",
    ], size=11.5, gap=9)

    rect(s, 0.7, 5.68, 6.1, 0.7, fill=TEAL_LIGHT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
    rect(s, 0.7, 5.68, 0.06, 0.7, fill=TEAL)
    tb, tf = textbox(s, 0.92, 5.8, 5.75, 0.5)
    p = para(tf, first=True, line=1.1)
    r = p.add_run()
    r.text = "→ 组数 M = ⌈S/g⌉ 远小于 token 数；每段边界最多多取 g−1 个 token。"
    style_run(r, size=9.5, bold=True, color=TEAL_DARK)

    # right visual
    card(s, 7.1, 1.78, 5.53, 4.75, fill=LIGHT, line=None)
    tb, tf = textbox(s, 7.32, 1.95, 5.0, 0.3)
    p = para(tf, first=True)
    r = p.add_run(); r.text = "粗到细：组级粗筛 → 组内恢复"
    style_run(r, size=13, bold=True, color=INK)

    box(s, 7.4, 2.4, 2.15, 0.72, "生成块 B\n（多个 token 同时解码）", fill=NAVY, line=None,
        color=WHITE, size=9.5, bold=True)

    gw, gg = 0.5, 0.06
    for i in range(9):
        x = 7.35 + i * (gw + gg)
        sel = i in (2, 6, 7)
        rect(s, x, 3.55, gw, 0.52, fill=TEAL_LIGHT if sel else WHITE,
             line=TEAL if sel else BORDER, line_w=1.2 if sel else 0.8,
             shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.1)
        tb, tf = textbox(s, x, 4.1, gw, 0.2)
        p = para(tf, first=True, align=PP_ALIGN.CENTER)
        r = p.add_run(); r.text = "G%d" % i
        style_run(r, size=7, color=TEAL_DARK if sel else MUTED)

    line(s, 8.0, 3.12, 8.67, 3.53, color=TEAL, width=1.3, tail=True)
    line(s, 8.3, 3.12, 10.95, 3.53, color=TEAL, width=1.3, tail=True)
    tb, tf = textbox(s, 10.35, 4.32, 1.9, 0.25)
    p = para(tf, first=True)
    r = p.add_run(); r.text = "选中的 top-k_g 组"
    style_run(r, size=8, color=TEAL_DARK)

    plain_paras(s, 7.35, 4.72, 5.0, 1.2, [
        [("① ", {"bold": True, "color": TEAL}), ("只读组摘要（N/g 个键）定位显著段", {})],
        [("② ", {"bold": True, "color": TEAL}), ("只拉取选中组内的 token K/V", {})],
        [("③ ", {"bold": True, "color": TEAL}), ("连续内存访问，索引开销可忽略", {})],
    ], size=10.5, gap=5)

    tb, tf = textbox(s, 7.35, 6.05, 5.05, 0.4)
    p = para(tf, first=True, line=1.1)
    r = p.add_run()
    r.text = "组是选择与预取的最小单位；组内/边界 token 的低权重保证了保真度。"
    style_run(r, size=9.5, color=MUTED, italic=True)

    notes(s, "观察一有两个层面：块内 token 的访问集重叠很高（Jaccard 0.744，Overlap 0.843），"
             "而且最重要的 token 不是散落的，是成片集中。于是可以用连续组覆盖这些段：先粗筛组，再在组内恢复 token KV。")


# ================================================================== 7 observation 2
def s07():
    s = new_slide("02 / 关键观察", "观察二：相邻层的组级显著性高度一致")

    tb, tf = textbox(s, 0.7, 1.74, 6.1, 0.3)
    p = para(tf, first=True)
    r = p.add_run(); r.text = "相邻层召回率（k = 20%）"
    style_run(r, size=12, bold=True, color=INK)

    cd = CategoryChartData()
    cd.categories = ["LLaDA-8B", "UltraLLaDA"]
    cd.add_series("Token 级选择", (0.8021, 0.8210))
    cd.add_series("Group 级选择", (0.8610, 0.8806))
    gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.62), Inches(2.02),
                            Inches(6.25), Inches(4.1), cd)
    ch = gf.chart
    ch.has_title = False
    ch.has_legend = True
    ch.legend.position = XL_LEGEND_POSITION.TOP
    ch.legend.include_in_layout = False
    ch.legend.font.size = Pt(10)
    ch.legend.font.color.rgb = BODY
    chart_font(ch, 10)
    style_axes(ch, ymin=0.70, ymax=0.92, major=0.05, fmt="0.00")
    plot = ch.plots[0]
    plot.gap_width = 90
    plot.overlap = -8
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.font.size = Pt(9.5)
    dl.font.bold = True
    dl.font.color.rgb = BODY
    dl.number_format = "0.00"
    dl.number_format_is_linked = False
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    for ser, col in zip(plot.series, (BLUE, TEAL)):
        ser.format.fill.solid()
        ser.format.fill.fore_color.rgb = col
        ser.format.line.fill.background()

    tb, tf = textbox(s, 0.7, 6.12, 6.1, 0.3)
    p = para(tf, first=True)
    r = p.add_run()
    r.text = "纵轴从 0.70 起，用于放大差异；实际差距约 +0.06。"
    style_run(r, size=8.5, color=MUTED, italic=True)

    bullets(s, 7.15, 1.82, 5.45, 4.1, [
        "层间变化主要是注意力权重的强度微调，关注区域并不整体迁移",
        [("组级召回 0.88 > token 级 0.82：", {"bold": True, "color": INK}),
         ("组聚合起到了降噪作用", {})],
        "约 11% 的 top-k token 跨多层持续显著 → 存在稳定的高重要区域",
        [("含义：", {"bold": True, "color": TEAL}),
         ("当前层可作为下一层预取的有效先验", {})],
        [("但 0.88 也意味着 ~12% 的显著组预测不到 —— ", {}),
         ("预取必然存在漏检", {"color": RED, "bold": True})],
    ], size=12, gap=10)

    tb, tf = textbox(s, 7.15, 4.46, 5.4, 0.25)
    p = para(tf, first=True)
    r = p.add_run()
    r.text = "同一块在相邻层的 top-k_g 选择"
    style_run(r, size=9, bold=True, color=MUTED, spc=30)

    row_sets = [{2, 6}, {2, 6}, {3, 6}]
    for ri, sel in enumerate(row_sets):
        y = 4.72 + ri * 0.3
        tb, tf = textbox(s, 7.15, y + 0.02, 0.45, 0.2)
        p = para(tf, first=True, align=PP_ALIGN.RIGHT)
        r = p.add_run(); r.text = "层 i" if ri == 0 else "i+%d" % ri
        style_run(r, size=7.5, bold=True, color=MUTED)
        for gi in range(9):
            on = gi in sel
            drifted = (ri == 2 and gi == 3)
            rect(s, 7.7 + gi * 0.41, y, 0.3, 0.22,
                 fill=(AMBER_LIGHT if drifted else (TEAL_LIGHT if on else WHITE)),
                 line=(AMBER if drifted else (TEAL if on else BORDER)),
                 line_w=1.1 if on else 0.6,
                 shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.15)
        tb, tf = textbox(s, 11.45, y + 0.01, 1.0, 0.2)
        p = para(tf, first=True)
        if ri < 2:
            add_runs(p, [("✓", {"size": 8, "bold": True, "color": TEAL}), (" 2/2", {"size": 7.5, "color": TEAL_DARK})])
        else:
            add_runs(p, [("~", {"size": 8, "bold": True, "color": AMBER}), (" 1/2", {"size": 7.5, "color": AMBER})])

    tb, tf = textbox(s, 7.15, 5.58, 5.35, 0.3)
    p = para(tf, first=True)
    r = p.add_run()
    r.text = "选择高度重合，个别组轻微漂移 → 当前层可作为下一层的预取先验。"
    style_run(r, size=8.8, color=TEAL_DARK, italic=True)

    line(s, 7.15, 5.94, 12.55, 5.94, color=BORDER, width=0.7)
    tb, tf = textbox(s, 7.15, 6.05, 5.4, 0.4)
    p = para(tf, first=True)
    r = p.add_run()
    r.text = "观察 1 决定「按组选」，观察 2 决定「跨层预取」。"
    style_run(r, size=11, bold=True, color=TEAL_DARK)

    notes(s, "观察二：相邻层关注哪些组非常稳定，组级召回 0.88，比 token 级高 0.06；约 11% 的 token 跨层持续显著。"
             "所以当前层的组分数可以当作下一层的调度先验。但 0.88 不是 1，预取一定会有漏检，这也是后面要讨论的点。")


# ================================================================== 8 overview
def s08():
    s = new_slide("03 / 系统设计", "系统总览：把选择、搬运、计算组织成一条流水线")

    # --- prefill band
    rect(s, 0.7, 1.76, 11.93, 1.12, fill=LIGHT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.04)
    pill(s, 0.85, 1.9, 0.82, 0.26, "PREFILL", fill=NAVY, color=WHITE, size=7.5)
    labels = [
        ("长上下文 S\n4K – 128K", WHITE, BORDER, INK),
        ("切分为连续组\ng = 8", WHITE, BORDER, INK),
        ("组级摘要 k^g_m\n（token key 均值）", TEAL_LIGHT, TEAL, TEAL_DARK),
        ("K / V / G offload\n→ CPU pinned", BLUE_LIGHT, BLUE, BLUE),
    ]
    bx = 1.85
    for i, (txt, fill, line_c, col) in enumerate(labels):
        box(s, bx, 1.95, 2.38, 0.72, txt, fill=fill, line=line_c, color=col, size=10)
        if i < 3:
            line(s, bx + 2.4, 2.31, bx + 2.55, 2.31, color=MUTED, width=1.1, tail=True)
        bx += 2.55

    # --- decode band
    rect(s, 0.7, 3.02, 11.93, 1.95, fill=WHITE, line=BORDER, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.04)
    pill(s, 0.85, 3.15, 0.82, 0.26, "DECODE", fill=TEAL, color=WHITE, size=7.5)

    tb, tf = textbox(s, 1.0, 3.23, 0.8, 0.25)
    p = para(tf, first=True); r = p.add_run(); r.text = "计算流"
    style_run(r, size=9.5, bold=True, color=TEAL_DARK)

    comp = [("组级粗筛\ntop-k_g", 2.05), ("从 CPU gather\n选中组 K/V", 2.25),
            ("层内细化\ntop-k2", 1.95), ("Attention\n+ FFN", 1.95)]
    bx = 1.85
    for i, (txt, w) in enumerate(comp):
        box(s, bx, 3.12, w, 0.68, txt, fill=TEAL_LIGHT, line=TEAL, color=TEAL_DARK, size=9.5)
        if i < 3:
            line(s, bx + w + 0.02, 3.46, bx + w + 0.16, 3.46, color=TEAL, width=1.2, tail=True)
        bx += w + 0.19
    tb, tf = textbox(s, bx + 0.05, 3.33, 1.2, 0.25)
    p = para(tf, first=True); r = p.add_run(); r.text = "Layer i"
    style_run(r, size=8.5, bold=True, color=MUTED)

    tb, tf = textbox(s, 1.0, 4.05, 0.8, 0.25)
    p = para(tf, first=True); r = p.add_run(); r.text = "预取流"
    style_run(r, size=9.5, bold=True, color=AMBER)

    pref = [("用当前层输入 + 组 key\n预测下一层显著组", 3.25), ("异步 gather 下一层 K/V\n到另一个 compact buffer", 3.1),
            ("消费前做\n陈旧性修复", 2.25)]
    bx = 1.85
    for i, (txt, w) in enumerate(pref):
        box(s, bx, 3.95, w, 0.68, txt, fill=AMBER_LIGHT, line=AMBER, color=AMBER, size=9.5)
        if i < 2:
            line(s, bx + w + 0.02, 4.29, bx + w + 0.16, 4.29, color=AMBER, width=1.2, tail=True)
        bx += w + 0.19
    tb, tf = textbox(s, bx + 0.02, 4.18, 1.6, 0.25)
    p = para(tf, first=True); r = p.add_run(); r.text = "Layer i+1"
    style_run(r, size=8.5, bold=True, color=MUTED)

    # dashed link between streams
    line(s, 1.62, 3.5, 1.62, 4.25, color=BORDER, width=1.0, dash=MSO_LINE.DASH, tail=True)

    # --- pipeline gantt
    tb, tf = textbox(s, 0.7, 5.2, 1.45, 0.25)
    p = para(tf, first=True); r = p.add_run(); r.text = "跨层乒乓流水"
    style_run(r, size=10, bold=True, color=INK)

    tb, tf = textbox(s, 0.7, 5.55, 0.75, 0.2)
    p = para(tf, first=True); r = p.add_run(); r.text = "计算"
    style_run(r, size=7.5, color=TEAL_DARK)
    tb, tf = textbox(s, 0.7, 5.87, 0.75, 0.2)
    p = para(tf, first=True); r = p.add_run(); r.text = "预取"
    style_run(r, size=7.5, color=AMBER)

    for i in range(4):
        bx = 1.6 + i * 1.12
        rect(s, bx, 5.56, 0.92, 0.2, fill=TEAL, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.3)
        rect(s, bx + 0.5, 5.87, 0.92, 0.2, fill=AMBER, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.3)
        tb, tf = textbox(s, bx, 5.56, 0.92, 0.2)
        p = para(tf, first=True, align=PP_ALIGN.CENTER); r = p.add_run(); r.text = "i+%d" % i if i else "i"
        style_run(r, size=7, bold=True, color=WHITE)
        tb, tf = textbox(s, bx + 0.5, 5.87, 0.92, 0.2)
        p = para(tf, first=True, align=PP_ALIGN.CENTER); r = p.add_run(); r.text = "i+%d" % (i + 1)
        style_run(r, size=7, bold=True, color=WHITE)

    tb, tf = textbox(s, 6.65, 5.55, 5.95, 0.6)
    p = para(tf, first=True, line=1.15)
    r = p.add_run()
    r.text = "两个 compact buffer 交替使用：预取第 i+1 层时，第 i 层同时在算，\nH2D 被计算覆盖。"
    style_run(r, size=9.5, color=BODY)

    # --- chips
    chips = ["① 组级分层访问", "② 预测性预取", "③ 两级一致性修复", "④ 流式 prefill", "⑤ 预算与部署"]
    for i, c in enumerate(chips):
        x = 0.7 + i * 2.4
        pill(s, x, 6.42, 2.25, 0.36, c, fill=NAVY, color=WHITE, size=9)

    notes(s, "这是总览图。Prefill 阶段分组、算组级摘要、把 K/V/G 放到 CPU；解码时计算流做组级粗筛、gather、细化、"
             "Attention+FFN，预取流同时为下一层选组并搬运；两个 compact buffer 乒乓交替；消费前做修复。"
             "五个组件后面逐个讲。")


# ================================================================== 9 component 1
def s09():
    s = new_slide("03 / 系统设计 · 组件一", "组级摘要：用 1/g 的键完成粗筛，再按需恢复")

    card(s, 0.7, 1.78, 6.35, 3.02, fill=RGBColor(0xF2, 0xF8, 0xF8), line=None)
    rect(s, 0.7, 1.78, 0.05, 3.02, fill=TEAL)
    tb, tf = textbox(s, 0.92, 1.93, 5.9, 0.3)
    p = para(tf, first=True); r = p.add_run(); r.text = "组级摘要与显著性打分"
    style_run(r, size=11, bold=True, color=TEAL_DARK, spc=60)

    formulas = [
        [("G", {"bold": True}), ("m", {"size": 9, "baseline": -25000}), (" = { (m−1)g+1, …, min(mg, S) },   m = 1…M", {})],
        [("k", {"bold": True}), ("g", {"size": 9, "baseline": 30000}), ("m", {"size": 9, "baseline": -25000}),
         (" = (1 / |G", {"bold": True}), ("m", {"size": 9, "baseline": -25000}), ("|) Σ", {"bold": True}),
         ("i∈Gm", {"size": 9, "baseline": -25000}), (" k", {"bold": True}), ("i", {"size": 9, "baseline": -25000})],
        [("t", {"bold": True}), ("m", {"size": 9, "baseline": -25000}), (" = (1 / |B|) Σ", {"bold": True}),
         ("q∈B", {"size": 9, "baseline": -25000}), (" q", {"bold": True}), ("T", {"size": 9, "baseline": 30000}),
         (" k", {"bold": True}), ("g", {"size": 9, "baseline": 30000}), ("m", {"size": 9, "baseline": -25000}),
         ("    →   Top-k", {"bold": True}), ("g", {"size": 9, "baseline": -25000}), (" groups", {"bold": True})],
    ]
    for i, segs in enumerate(formulas):
        tb, tf = textbox(s, 0.95, 2.4 + i * 0.52, 5.9, 0.45)
        p = para(tf, first=True, line=1.0)
        add_runs(p, segs, size=14.5, color=INK, latin=FONT_MATH)

    tb, tf = textbox(s, 0.95, 4.05, 5.9, 0.6)
    p = para(tf, first=True, line=1.15)
    r = p.add_run()
    r.text = "k_i 为 RoPE 后的 token key：均值同时保留语义与位置信息；\n无需聚类、索引或学习结构，更新也只影响所在组。"
    style_run(r, size=9.5, color=BODY)

    bullets(s, 0.7, 5.0, 6.35, 1.8, [
        "只访问组摘要（N/g）+ 选中组 token KV（2fN），避免全量 K 扫描",
        "结构上突破 token 级按需恢复的 ~2× 压缩上限",
        "代价：组内只有一个「针」时，均值可能被稀释（128K NIAH 95%）",
    ], size=11.5, gap=8)

    # right: transfer math
    card(s, 7.28, 1.78, 5.35, 4.95, fill=WHITE)
    tb, tf = textbox(s, 7.5, 1.95, 4.9, 0.3)
    p = para(tf, first=True); r = p.add_run(); r.text = "每层 K/V 传输条目数"
    style_run(r, size=12, bold=True, color=INK)

    # full bar
    tb, tf = textbox(s, 7.5, 2.38, 4.9, 0.25)
    p = para(tf, first=True); r = p.add_run(); r.text = "标准 offload"
    style_run(r, size=9.5, color=MUTED)
    rect(s, 7.5, 2.64, 4.6, 0.3, fill=RED_LIGHT, line=RED, line_w=0.8,
         shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.25)
    tb, tf = textbox(s, 11.55, 2.64, 0.85, 0.3)
    p = para(tf, first=True); r = p.add_run(); r.text = "2N"
    style_run(r, size=10.5, bold=True, color=RED)

    tb, tf = textbox(s, 7.5, 3.12, 4.9, 0.25)
    p = para(tf, first=True); r = p.add_run(); r.text = "GroupKV（g=8, f=0.2）"
    style_run(r, size=9.5, color=MUTED)
    rect(s, 7.5, 3.38, 0.2875, 0.3, fill=TEAL, line=None,
         shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
    rect(s, 7.79, 3.38, 0.92, 0.3, fill=TEAL_LIGHT, line=TEAL, line_w=0.8,
         shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
    tb, tf = textbox(s, 8.82, 3.41, 1.6, 0.3)
    p = para(tf, first=True); r = p.add_run(); r.text = "0.525N"
    style_run(r, size=11, bold=True, color=TEAL_DARK)

    tb, tf = textbox(s, 7.5, 3.78, 4.9, 0.25)
    p = para(tf, first=True)
    add_runs(p, [
        ("= 0.125N ", {"size": 9, "color": TEAL_DARK, "bold": True}),
        ("组摘要", {"size": 9, "color": MUTED}),
        ("  +  0.4N ", {"size": 9, "color": TEAL_DARK, "bold": True}),
        ("选中 token K/V", {"size": 9, "color": MUTED}),
    ])

    tb, tf = textbox(s, 7.5, 4.18, 4.9, 0.7)
    p = para(tf, first=True)
    add_runs(p, [("3.81", {"size": 40, "bold": True, "color": TEAL}),
                 ("×", {"size": 24, "bold": True, "color": TEAL}),
                 ("  理论每层传输缩减", {"size": 10.5, "color": BODY})])

    tb, tf = textbox(s, 7.5, 5.05, 4.9, 0.35)
    p = para(tf, first=True)
    r = p.add_run(); r.text = "2N / (N/g + 2fN) = 2 / (1/g + 2f)"
    style_run(r, size=12, color=INK, latin=FONT_MATH)

    tb, tf = textbox(s, 7.5, 5.52, 4.9, 1.0)
    p = para(tf, first=True, line=1.18)
    r = p.add_run()
    r.text = "理想化口径：假设条目等大，忽略 gather 随机访问、组评分算力与 buffer 占用；实测相对 InfiniGen 为 1.25–1.35×。"
    style_run(r, size=9, color=MUTED, italic=True)

    rect(s, 0.7, 6.02, 6.35, 0.62, fill=TEAL_LIGHT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.1)
    rect(s, 0.7, 6.02, 0.06, 0.62, fill=TEAL)
    tb, tf = textbox(s, 0.95, 6.12, 5.95, 0.45)
    p = para(tf, first=True, line=1.12)
    add_runs(p, [
        ("一句话：", {"size": 9.8, "bold": True, "color": TEAL_DARK}),
        ("粗筛在组上做（成本 1/g），恢复在 token 上做——分层，而非二选一。",
         {"size": 9.8, "color": BODY}),
    ])

    notes(s, "组件一的核心：不逐 token 打分，而是把上下文切成连续组，用 RoPE key 的均值做组摘要。"
             "每层只传 N/g 个组键加选中组的 token KV，理论传输从 2N 降到 0.525N，约 3.81 倍。"
             "注意这是每层传输条目的理论比，不是端到端加速比。")


# ================================================================== 10 component 2
def s10():
    s = new_slide("03 / 系统设计 · 组件二", "预测性预取：把下一层的 KV 搬运藏进当前层计算")

    card(s, 0.7, 1.78, 6.6, 3.7, fill=LIGHT, line=None)
    tb, tf = textbox(s, 0.92, 1.92, 5.8, 0.3)
    p = para(tf, first=True); r = p.add_run(); r.text = "时间线对比：传输（琥珀）/ 计算（青）/ 暴露停顿（红）"
    style_run(r, size=9.5, bold=True, color=BODY)

    rows = [
        ("(a) 预取完整 KV", [(0, 4.05, AMBER_LIGHT, AMBER, "搬运量最大")], None),
        ("(b) 按需 token 取数", [(0, 1.12, AMBER_LIGHT, AMBER, ""), (1.12, 0.5, RED_LIGHT, RED, "暴露 H2D"), (1.62, 1.36, TEAL_LIGHT, TEAL, "")], None),
    ]
    y = 2.3
    for label, bars, _ in rows:
        tb, tf = textbox(s, 0.9, y + 0.06, 1.5, 0.3)
        p = para(tf, first=True); r = p.add_run(); r.text = label
        style_run(r, size=9, bold=True, color=INK)
        for (off, w, fill, linec, txt) in bars:
            rect(s, 2.48 + off, y, w, 0.36, fill=fill, line=linec, line_w=0.8,
                 shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.2)
            if txt:
                tb, tf = textbox(s, 2.48 + off, y + 0.07, w, 0.22)
                p = para(tf, first=True, align=PP_ALIGN.CENTER)
                r = p.add_run(); r.text = txt
                style_run(r, size=7.5, bold=True, color=linec)
        y += 0.72

    # (c) and (d): two lanes
    for idx, (label, compute_w, note) in enumerate([
        ("(c) 预测预取", 1.36, "重叠 → 总时长缩短"),
        ("(d) + 层内细化", 0.95, "计算进一步变短"),
    ]):
        tb, tf = textbox(s, 0.9, y + 0.02, 1.5, 0.3)
        p = para(tf, first=True); r = p.add_run(); r.text = label
        style_run(r, size=9, bold=True, color=INK)
        # prefetch lane
        rect(s, 2.48, y - 0.04, 1.2, 0.16, fill=AMBER_LIGHT, line=AMBER, line_w=0.7,
             shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.4)
        tb, tf = textbox(s, 2.5, y - 0.05, 1.15, 0.16)
        p = para(tf, first=True, align=PP_ALIGN.CENTER); r = p.add_run(); r.text = "预取 i+1"
        style_run(r, size=6.5, bold=True, color=AMBER)
        # compute lane
        rect(s, 2.86, y + 0.24, compute_w, 0.16, fill=TEAL, line=None,
             shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.4)
        tb, tf = textbox(s, 2.88, y + 0.235, compute_w, 0.16)
        p = para(tf, first=True, align=PP_ALIGN.CENTER); r = p.add_run(); r.text = "计算 i"
        style_run(r, size=6.5, bold=True, color=WHITE)
        tb, tf = textbox(s, 4.9, y + 0.04, 2.2, 0.3)
        p = para(tf, first=True); r = p.add_run(); r.text = note
        style_run(r, size=7.5, color=MUTED)
        y += 0.78

    tb, tf = textbox(s, 1.58, 5.03, 4.7, 0.22)
    p = para(tf, first=True); r = p.add_run(); r.text = "时间 →"
    style_run(r, size=7.5, color=MUTED)

    tb, tf = textbox(s, 0.95, 5.2, 6.15, 0.25)
    p = para(tf, first=True)
    r = p.add_run()
    r.text = "预取只覆盖预测组（组级召回 0.88）；漏检由按需取数 / 修复兜底，并非零成本。"
    style_run(r, size=8.3, color=MUTED, italic=True)

    bullets(s, 7.55, 1.8, 5.05, 3.6, [
        [("依据：", {"bold": True, "color": TEAL}), ("相邻层选择相似（组级召回 0.88）→ 当前层组分数 = 下一层调度先验", {})],
        "计算流消费已备好的 compact KV；预取流用当前层输入异步 gather 下一层",
        "两个 compact buffer 乒乓交替：把不规则稀疏恢复变成 producer–consumer 流水",
        [("层内细化：", {"bold": True, "color": TEAL}), ("在已到 GPU 的候选上再取 top-k2，只减计算、不减传输", {})],
    ], size=11, gap=9)

    # metrics
    metrics = [("32K", "1.08 → 1.79", "tok/s，+66%"),
               ("64K", "0.60 → 0.99", "tok/s，+65%"),
               ("显存代价", "+0.13 / +0.25", "GiB（ping-pong buffer）")]
    for i, (lab, val, sub) in enumerate(metrics):
        x = 0.7 + i * 4.04
        card(s, x, 5.66, 3.8, 1.08, fill=WHITE)
        tb, tf = textbox(s, x + 0.18, 5.78, 1.1, 0.25)
        p = para(tf, first=True); r = p.add_run(); r.text = lab
        style_run(r, size=9, bold=True, color=MUTED)
        tb, tf = textbox(s, x + 0.18, 6.0, 3.5, 0.4)
        p = para(tf, first=True); r = p.add_run(); r.text = val
        style_run(r, size=18, bold=True, color=INK)
        tb, tf = textbox(s, x + 0.18, 6.41, 3.4, 0.25)
        p = para(tf, first=True); r = p.add_run(); r.text = sub
        style_run(r, size=8.5, color=MUTED)

    notes(s, "组件二解决「什么时候搬」。相邻层选组很像，所以当前层选完就知道下一层大概要什么，"
             "可以异步加载到另一个 buffer，和当前层计算重叠。消融显示 32K 从 1.08 提到 1.79，64K 从 0.60 到 0.99，"
             "显存只多了一点，因为 buffer 只复制稀疏工作集。")


# ================================================================== 11 component 3
def s11():
    s = new_slide("03 / 系统设计 · 组件三", "动态 KV 下的两级一致性：只修复「被改过」的条目")

    card(s, 0.7, 1.78, 6.35, 3.95, fill=LIGHT, line=None)
    tb, tf = textbox(s, 0.92, 1.93, 5.9, 0.3)
    p = para(tf, first=True); r = p.add_run(); r.text = "compact buffer 记录源位置，命中后原位修复"
    style_run(r, size=11, bold=True, color=INK)

    tb, tf = textbox(s, 0.95, 2.35, 5.8, 0.22)
    p = para(tf, first=True); r = p.add_run(); r.text = "上下文 token（部分被选中，★ 为预取后又被更新）"
    style_run(r, size=8.5, color=MUTED)

    selected = {2, 3, 5, 9, 10, 14, 15}
    updated = {3, 10}
    cw, cg = 0.265, 0.035
    for i in range(20):
        x = 0.95 + i * (cw + cg)
        sel = i in selected
        upd = i in updated
        rect(s, x, 2.65, cw, 0.42, fill=AMBER_LIGHT if upd else (TEAL_LIGHT if sel else WHITE),
             line=AMBER if upd else (TEAL if sel else BORDER), line_w=1.3 if upd else 0.7,
             shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.15)
        if upd:
            tb, tf = textbox(s, x, 2.72, cw, 0.25)
            p = para(tf, first=True, align=PP_ALIGN.CENTER); r = p.add_run(); r.text = "★"
            style_run(r, size=8, color=AMBER)

    tb, tf = textbox(s, 0.95, 3.35, 5.9, 0.22)
    p = para(tf, first=True); r = p.add_run(); r.text = "compact buffer（只装选中的稀疏工作集，每条记录源 token 位置）"
    style_run(r, size=8.5, color=MUTED)

    buf_pos = [3, 4, 6, 10, 11, 15, 16]
    for i in range(7):
        x = 0.95 + i * 0.68
        hit = i in (1, 4)
        rect(s, x, 3.65, 0.54, 0.5, fill=TEAL_LIGHT if not hit else AMBER_LIGHT,
             line=AMBER if hit else TEAL, line_w=1.4 if hit else 0.8,
             shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
        tb, tf = textbox(s, x, 3.74, 0.54, 0.3)
        p = para(tf, first=True, align=PP_ALIGN.CENTER)
        r = p.add_run(); r.text = "pos %d" % buf_pos[i]
        style_run(r, size=7, color=AMBER if hit else TEAL_DARK)
        if hit:
            tb, tf = textbox(s, x - 0.05, 4.18, 0.65, 0.22)
            p = para(tf, first=True, align=PP_ALIGN.CENTER); r = p.add_run(); r.text = "修复"
            style_run(r, size=7, bold=True, color=AMBER)

    tb, tf = textbox(s, 0.95, 4.46, 5.9, 0.25)
    p = para(tf, first=True)
    add_runs(p, [
        ("本轮更新源 token 4 / 11 ", {"size": 8.5, "color": AMBER, "bold": True}),
        ("→ 只修复 pos 4 / pos 11 两个槽位", {"size": 8.5, "color": AMBER}),
    ])

    tb, tf = textbox(s, 0.95, 4.78, 5.9, 0.65)
    p = para(tf, first=True, line=1.18)
    add_runs(p, [
        ("消费前检查：", {"size": 10, "bold": True, "color": AMBER}),
        ("只覆盖命中的槽位，不重载整组/整层；未命中的稳定 prompt 组零修复开销。", {"size": 10, "color": BODY}),
    ])

    tb, tf = textbox(s, 0.95, 5.36, 5.9, 0.25)
    p = para(tf, first=True)
    add_runs(p, [
        ("■ 未选中    ", {"size": 7.5, "color": MUTED}),
        ("■ 选中    ", {"size": 7.5, "color": TEAL}),
        ("★ 本轮更新    ", {"size": 7.5, "color": AMBER}),
        ("■ 需修复", {"size": 7.5, "color": AMBER}),
    ])

    bullets(s, 7.25, 1.8, 5.35, 3.7, [
        [("CPU 侧组刷新：", {"bold": True, "color": TEAL}),
         ("只重算受影响 token 的 KV 与所在组均值；prompt-only 组复用；周期全序列 prefill 兜底", {})],
        [("GPU 侧选择性修复：", {"bold": True, "color": TEAL}),
         ("compact 条目记录源位置，命中只覆盖该槽", {})],
        [("成本 ∝ ", {}), ("命中的陈旧条目数", {"bold": True, "color": INK}), ("，而非上下文长度", {})],
        [("论文定性：", {"bold": True, "color": RED}),
         ("这不是可选优化，而是正确性要求", {"bold": True, "color": RED})],
    ], size=11, gap=10)

    tb, tf = textbox(s, 7.25, 4.55, 5.35, 0.25)
    p = para(tf, first=True)
    r = p.add_run(); r.text = "两级一致性检查的时序"
    style_run(r, size=9, bold=True, color=MUTED, spc=30)
    steps = ["CPU 刷新\n组摘要", "预取写入\ncompact slot", "消费前\n命中检查", "仅覆盖\n命中槽"]
    for i, st in enumerate(steps):
        x = 7.25 + i * 1.33
        box(s, x, 4.84, 1.16, 0.55, st, fill=LIGHT if i < 3 else AMBER_LIGHT,
            line=BORDER if i < 3 else AMBER, color=BODY if i < 3 else AMBER, size=7.8)
        if i < 3:
            line(s, x + 1.18, 5.11, x + 1.3, 5.11, color=MUTED, width=0.8, tail=True)

    rect(s, 0.7, 5.95, 11.93, 0.82, fill=AMBER_LIGHT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06)
    rect(s, 0.7, 5.95, 0.06, 0.82, fill=AMBER)
    tb, tf = textbox(s, 0.95, 6.05, 11.45, 0.65)
    p = para(tf, first=True, line=1.15)
    add_runs(p, [
        ("边界：", {"size": 10, "bold": True, "color": AMBER}),
        ("修复只能补「已预取但变旧」；若因陈旧摘要而选错组、漏预取，修复补不回来。"
         "论文未给出形式化正确性条件，也未做关闭修复的精度消融。", {"size": 10, "color": BODY}),
    ])

    notes(s, "组件三处理动态性。CPU 侧只刷新受影响的组摘要；GPU 侧给每个 compact 条目记源位置，"
             "消费前检查这一轮有没有被改，命中就只覆盖那一个槽。作者说这是正确性要求。"
             "但要注意，它补不了「组本身就选错了」的情况，论文也没有形式化证明。")


# ================================================================== 12 component 4/5
def s12():
    s = new_slide("03 / 系统设计 · 组件四 / 五", "流式 prefill 控制峰值，三个旋钮决定权衡")

    card(s, 0.7, 1.78, 6.1, 4.15, fill=WHITE)
    pill(s, 0.95, 1.96, 1.5, 0.3, "④ STREAMING PREFILL", fill=BLUE_LIGHT, color=BLUE, size=7.5)
    tb, tf = textbox(s, 0.95, 2.34, 5.55, 0.4)
    p = para(tf, first=True); r = p.add_run(); r.text = "峰值由 S 降为 S_blk"
    style_run(r, size=15, bold=True, color=INK)

    bullets(s, 0.95, 2.85, 5.55, 1.75, [
        "dLLM prefill 要对全序列算 logits；AR 只算最后一个位置 → 中间张量峰值更高",
        "峰值来自短命张量：全词表 logits、RoPE 临时量、FFN 激活",
        "沿序列维分块执行 logits / RoPE / FFN，复用临时缓冲并即时写回",
        [("定位：", {"bold": True, "color": BLUE}),
         ("只降 prefill 峰值，不减少解码 KV 与 H2D；与解码侧机制正交", {})],
    ], size=11, gap=9)

    tb, tf = textbox(s, 0.95, 4.7, 5.5, 0.25)
    p = para(tf, first=True)
    r = p.add_run(); r.text = "按序列分块执行（S → S_blk）"
    style_run(r, size=9, bold=True, color=MUTED, spc=30)
    for i in range(5):
        box(s, 0.95 + i * 1.03, 4.98, 0.95, 0.38, "块 %d" % (i + 1),
            fill=BLUE_LIGHT if i == 0 else WHITE, line=BLUE if i == 0 else BORDER,
            color=BLUE if i == 0 else MUTED, size=7.8, radius=0.1)

    tb, tf = textbox(s, 0.95, 5.45, 5.6, 0.22)
    p = para(tf, first=True)
    r = p.add_run(); r.text = "逐块执行 logits / RoPE / FFN，算完即写回"
    style_run(r, size=8.5, color=BODY)

    tb, tf = textbox(s, 0.95, 5.7, 5.6, 0.2)
    p = para(tf, first=True)
    r = p.add_run(); r.text = "副作用：块越细，重算与同步开销越高（未给敏感性分析）"
    style_run(r, size=7.8, color=MUTED, italic=True)

    # right: knobs table
    tb, tf = textbox(s, 7.0, 1.8, 5.6, 0.3)
    p = para(tf, first=True); r = p.add_run(); r.text = "⑤ 三个预算参数：粒度 / 传输 / 计算"
    style_run(r, size=12.5, bold=True, color=INK)

    rows = [
        [{"t": "参数", "fill": NAVY, "color": WHITE, "bold": True},
         {"t": "控制什么", "fill": NAVY, "color": WHITE, "bold": True},
         {"t": "调大 / 调小的代价", "fill": NAVY, "color": WHITE, "bold": True}],
        [{"t": "g = 8\n组大小", "fill": TEAL_LIGHT, "color": TEAL_DARK, "bold": True, "align": PP_ALIGN.LEFT},
         {"t": "选择粒度与打分成本", "align": PP_ALIGN.LEFT},
         {"t": "更小 g：召回↑、开销↑", "align": PP_ALIGN.LEFT}],
        [{"t": "k_g = 20%\n组检索预算", "fill": TEAL_LIGHT, "color": TEAL_DARK, "bold": True, "align": PP_ALIGN.LEFT},
         {"t": "恢复组数、传输量、buffer 大小", "align": PP_ALIGN.LEFT},
         {"t": "更大 k_g：精度↑、搬运↑", "align": PP_ALIGN.LEFT}],
        [{"t": "k2 = 0.50\n细化预算", "fill": TEAL_LIGHT, "color": TEAL_DARK, "bold": True, "align": PP_ALIGN.LEFT},
         {"t": "value 侧保留的候选 token 比例", "align": PP_ALIGN.LEFT},
         {"t": "更大 k2：精度略升、吞吐↓", "align": PP_ALIGN.LEFT}],
    ]
    styled_table(s, 7.0, 2.18, 5.6, 2.55, rows, col_ratios=[1.15, 1.55, 1.5],
                 font_size=9, align=PP_ALIGN.LEFT)

    tb, tf = textbox(s, 7.0, 4.9, 5.6, 0.5)
    p = para(tf, first=True, line=1.15)
    r = p.add_run()
    r.text = "默认配置为吞吐/显存折中，不是精度最优（见消融）。"
    style_run(r, size=9.5, color=MUTED, italic=True)

    presets = [("精度优先", "g=4 · k2=0.75", TEAL), ("默认", "g=8 · 20% · 0.50", TEAL_DARK),
               ("吞吐优先", "g=8 · k2=0.25", AMBER)]
    for i, (lab, cfg, col) in enumerate(presets):
        x = 7.0 + i * 1.88
        fill = TEAL_LIGHT if i == 1 else WHITE
        rect(s, x, 5.38, 1.78, 0.5, fill=fill, line=col, line_w=0.9,
             shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.1)
        tb, tf = textbox(s, x + 0.1, 5.43, 1.6, 0.2)
        p = para(tf, first=True); r = p.add_run(); r.text = lab
        style_run(r, size=7.5, bold=True, color=col)
        tb, tf = textbox(s, x + 0.1, 5.62, 1.6, 0.2)
        p = para(tf, first=True); r = p.add_run(); r.text = cfg
        style_run(r, size=7.5, color=BODY)

    rect(s, 0.7, 6.12, 11.93, 0.68, fill=TEAL_LIGHT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06)
    rect(s, 0.7, 6.12, 0.06, 0.68, fill=TEAL)
    tb, tf = textbox(s, 0.95, 6.2, 11.45, 0.5)
    p = para(tf, first=True, line=1.1)
    add_runs(p, [
        ("部署策略：", {"size": 10.5, "bold": True, "color": TEAL_DARK}),
        ("短上下文 → Fast-dLLM 全驻留；offload 密集的长上下文 → GroupKV。查表调度、后端无关，把两者做成互补，而非替代。",
         {"size": 10.5, "color": BODY}),
    ])

    notes(s, "组件四流式 prefill：dLLM 要对全序列算 logits，峰值高；按序列分块算 logits、RoPE、FFN，"
             "峰值就从 S 变成 S_blk。它只作用于 prefill，与解码侧正交。组件五是三个旋钮：g 控制粒度，"
             "k_g 控制传输预算，k2 控制计算预算。部署上把短上下文交给 Fast-dLLM，长上下文才用 GroupKV。")


# ================================================================== 13 setup
def s13():
    s = new_slide("04 / 实验评估", "实验设置：两模型、三类基线、三套长上下文基准")

    items = [
        ("模型", "Backbone", [
            "LLaDA-8B：基础 dLLM 主干",
            "UltraLLaDA：SOTA 长上下文 dLLM，窗口 128K",
            "均为 8B 级参数规模，单卡可承载权重",
            "只覆盖 LLaDA 系列，未测 Dream / Mercury / LLaDA-MoE",
        ], TEAL),
        ("基线", "Baselines", [
            "全注意力：UltraLLaDA、Fast-dLLM",
            "FlexGen 风格 offload：KV offload + sparse；KV pipeline + sparse",
            "InfiniGen 风格 token 级推测：相同 dLLM 条件下重实现",
            "所有稀疏方法统一 20% 稀疏率，保证同条件比较",
        ], BLUE),
        ("基准", "Benchmarks", [
            "LongBench：7 个子任务（MFQA/NQA/2WQA/QMS/TQA/SAM/LCC）",
            "RULER：4K–32K，多跳推理、变量追踪、检索",
            "NIAH：4K–128K 单针检索",
            "覆盖平均能力、复杂推理、极端长上下文三个层次",
        ], AMBER),
        ("平台", "Platform", [
            "A100-80G + 双 Xeon 4214 + 1.5 TB DDR4（PCIe）",
            "RTX 4090-24G + PCIe 4.0×16",
            "pinned host memory；主实验 batch = 1",
            "吞吐从 prefill 到解码结束，包含 H2D 与修复开销",
        ], NAVY),
    ]
    for i, (tag, en, lines, color) in enumerate(items):
        x = 0.7 + (i % 2) * 6.08
        y = 1.78 + (i // 2) * 2.34
        card(s, x, y, 5.85, 2.15)
        rect(s, x, y, 0.05, 2.15, fill=color)
        tb, tf = textbox(s, x + 0.22, y + 0.15, 1.2, 0.3)
        p = para(tf, first=True); r = p.add_run(); r.text = tag
        style_run(r, size=12.5, bold=True, color=color)
        tb, tf = textbox(s, x + 0.85, y + 0.2, 3.6, 0.25)
        p = para(tf, first=True); r = p.add_run(); r.text = en.upper()
        style_run(r, size=7.5, bold=True, color=MUTED, spc=120)
        bullets(s, x + 0.22, y + 0.6, 5.4, 1.5, lines, size=9.7, gap=4, bullet_color=color)

    rect(s, 0.7, 6.45, 11.93, 0.42, fill=LIGHT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.2)
    tb, tf = textbox(s, 0.95, 6.52, 11.45, 0.3)
    p = para(tf, first=True)
    add_runs(p, [
        ("默认配置：", {"size": 10, "bold": True, "color": TEAL_DARK}),
        ("g = 8 ｜ top-k = 20% ｜ k2 = 0.50；所有稀疏方法使用相同稀疏率；吞吐从 prefill 到解码结束计。",
         {"size": 10, "color": BODY}),
    ])

    notes(s, "实验设置：LLaDA 和 UltraLLaDA 两个主干；基线分全注意力、FlexGen 风格 offload、InfiniGen 风格 token 级选择；"
             "三个基准；两块卡。默认 g=8、top-20%、k2=0.5，主实验 batch=1。")


# ================================================================== 14 LongBench
def s14():
    s = new_slide("04 / 实验评估 · 精度", "LongBench：只保留 20% KV，平均分仍接近全注意力")

    tb, tf = textbox(s, 0.7, 1.72, 6.2, 0.3)
    p = para(tf, first=True); r = p.add_run(); r.text = "LongBench 平均分（7 个子任务）"
    style_run(r, size=11.5, bold=True, color=INK)

    cd = CategoryChartData()
    cd.categories = ["LLaDA", "UltraLLaDA"]
    cd.add_series("全注意力", (33.10, 36.61))
    cd.add_series("Fast-dLLM", (33.38, 38.26))
    cd.add_series("InfiniGen 风格", (30.57, 34.92))
    cd.add_series("GroupKV", (32.73, 37.43))
    gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.62), Inches(2.0),
                            Inches(6.4), Inches(4.25), cd)
    ch = gf.chart
    ch.has_title = False
    ch.has_legend = True
    ch.legend.position = XL_LEGEND_POSITION.TOP
    ch.legend.include_in_layout = False
    ch.legend.font.size = Pt(9.5)
    ch.legend.font.color.rgb = BODY
    chart_font(ch, 10)
    style_axes(ch, ymin=28, ymax=40, major=2, fmt="0.0")
    plot = ch.plots[0]
    plot.gap_width = 55
    plot.overlap = -5
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.font.size = Pt(8)
    dl.font.color.rgb = BODY
    dl.number_format = "0.0"
    dl.number_format_is_linked = False
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    for ser, col in zip(plot.series, (RGBColor(0x8C, 0x9A, 0xA8), BLUE, AMBER, TEAL)):
        ser.format.fill.solid()
        ser.format.fill.fore_color.rgb = col
        ser.format.line.fill.background()

    tb, tf = textbox(s, 0.7, 6.3, 6.3, 0.3)
    p = para(tf, first=True); r = p.add_run(); r.text = "纵轴从 28 起，用于放大方法间差异。"
    style_run(r, size=8.5, color=MUTED, italic=True)

    bullets(s, 7.25, 1.8, 5.35, 3.5, [
        [("LLaDA：", {"bold": True}), ("32.73，与全注意力 33.10 基本持平", {})],
        [("UltraLLaDA：", {"bold": True}), ("37.43 > 全注意力 36.61（+0.82）", {"color": TEAL_DARK, "bold": True}),
         ("；作者猜测组级稀疏有「轻正则化」效果，但未验证", {})],
        [("相对 InfiniGen 风格：", {"bold": True}), ("+2.16 / +2.51", {"color": TEAL_DARK, "bold": True}),
         (" → 支持「组级选择优于 token 级推测」", {})],
        [("但低于 Fast-dLLM 的 38.26：", {"bold": True}), ("同属加速方法，短上下文的纯计算加速更强", {})],
        [("证据强度：", {"bold": True, "color": RED}), ("无方差、无置信区间、无显著性检验", {"color": RED})],
    ], size=11, gap=10)

    card(s, 7.25, 5.42, 5.35, 1.33, fill=LIGHT, line=None)
    rect(s, 7.25, 5.42, 0.05, 1.33, fill=AMBER)
    tb, tf = textbox(s, 7.45, 5.53, 5.0, 0.25)
    p = para(tf, first=True)
    r = p.add_run(); r.text = "平均值之下：子任务差异明显"
    style_run(r, size=9.5, bold=True, color=AMBER)
    plain_paras(s, 7.45, 5.8, 5.0, 0.9, [
        [("LLaDA：", {"bold": True, "color": INK}),
         ("LCC 66.13 vs 71.05（−4.92）是差距主因；QMS / TQA 反而更高。", {})],
        [("UltraLLaDA：", {"bold": True, "color": INK}),
         ("NQA 17.12 vs 12.18（+4.94）抵消了 MFQA 的 −1.35。", {})],
    ], size=8.5, gap=3, color=BODY)

    notes(s, "LongBench 平均分：LLaDA 上 32.73，对全注意力 33.10；UltraLLaDA 上 37.43，比全注意力还高 0.82，"
             "作者猜是稀疏的正则化效应，但没有验证。相对 InfiniGen 风格高 2.16/2.51，这是最能支撑「组优于 token」的证据。"
             "不过 Fast-dLLM 在短上下文更强。")


# ================================================================== 15 RULER NIAH
def s15():
    s = new_slide("04 / 实验评估 · 精度", "RULER 与 NIAH：上下文变长时，可服务性开始分化")

    tb, tf = textbox(s, 0.7, 1.72, 6.2, 0.3)
    p = para(tf, first=True); r = p.add_run(); r.text = "RULER 平均分（4K–32K）"
    style_run(r, size=11.5, bold=True, color=INK)

    cd = CategoryChartData()
    cd.categories = ["4K", "8K", "16K", "32K"]
    cd.add_series("UltraLLaDA", (75.66, 71.48, 68.46, 62.70))
    cd.add_series("Fast-dLLM", (77.92, 74.86, None, None))
    cd.add_series("GroupKV", (75.25, 72.21, 70.22, 62.81))
    gf = s.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, Inches(0.62), Inches(1.98),
                            Inches(6.3), Inches(3.75), cd)
    ch = gf.chart
    ch.has_title = False
    ch.has_legend = True
    ch.legend.position = XL_LEGEND_POSITION.TOP
    ch.legend.include_in_layout = False
    ch.legend.font.size = Pt(9.5)
    ch.legend.font.color.rgb = BODY
    chart_font(ch, 10)
    style_axes(ch, ymin=55, ymax=82, major=5, fmt="0")
    plot = ch.plots[0]
    for ser, col in zip(plot.series, (RGBColor(0x8C, 0x9A, 0xA8), BLUE, TEAL)):
        ser.format.line.color.rgb = col
        ser.format.line.width = Pt(2.4)
        ser.smooth = False
        ser.marker.style = XL_MARKER_STYLE.CIRCLE
        ser.marker.size = 7
        ser.marker.format.fill.solid()
        ser.marker.format.fill.fore_color.rgb = col
        ser.marker.format.line.color.rgb = WHITE

    tb, tf = textbox(s, 0.7, 5.78, 6.3, 0.3)
    p = para(tf, first=True); r = p.add_run(); r.text = "Fast-dLLM 在 16K / 32K OOM，曲线中断。"
    style_run(r, size=8.5, color=MUTED, italic=True)

    # NIAH panel
    card(s, 7.2, 1.78, 5.4, 1.95, fill=LIGHT, line=None)
    tb, tf = textbox(s, 7.4, 1.9, 4.9, 0.25)
    p = para(tf, first=True); r = p.add_run(); r.text = "NIAH 单针检索精度（%）"
    style_run(r, size=10.5, bold=True, color=INK)
    vals = [("4K", 98), ("8K", 98), ("16K", 99), ("32K", 100), ("64K", 99), ("128K", 95)]
    for i, (lab, v) in enumerate(vals):
        x = 7.38 + i * 0.83
        tb, tf = textbox(s, x, 2.2, 0.78, 0.35)
        p = para(tf, first=True, align=PP_ALIGN.CENTER)
        r = p.add_run(); r.text = str(v)
        style_run(r, size=15, bold=True, color=TEAL_DARK if v >= 98 else AMBER)
        tb, tf = textbox(s, x, 2.56, 0.78, 0.2)
        p = para(tf, first=True, align=PP_ALIGN.CENTER)
        r = p.add_run(); r.text = lab
        style_run(r, size=7.5, color=MUTED)
    tb, tf = textbox(s, 7.4, 2.95, 4.9, 0.25)
    p = para(tf, first=True)
    add_runs(p, [("平均 ", {"size": 9.5, "color": BODY}),
                 ("98.17%", {"size": 12, "bold": True, "color": TEAL_DARK}),
                 ("；128K 仍保持 95% —— 但只报告了 GroupKV 自身", {"size": 9, "color": MUTED})])

    bullets(s, 7.2, 3.92, 5.4, 2.4, [
        [("RULER 16K/32K：", {"bold": True}), ("Fast-dLLM OOM；GroupKV 70.22 / 62.81，略高于全注意力", {})],
        [("4K/8K：", {"bold": True}), ("GroupKV 低于 Fast-dLLM（75.25 vs 77.92；72.21 vs 74.86）", {})],
        [("子任务并非全面更好：", {"bold": True}), ("32K fwe 35.29 vs 41.18；vt 93–96 vs 97–100", {})],
        [("NIAH 无同条件基线；", {"bold": True, "color": RED}), ("95% 说明极端稀疏下仍有信息损失", {"color": RED})],
    ], size=10.3, gap=7)

    notes(s, "RULER：16K、32K 上 Fast-dLLM OOM，GroupKV 还能跑，平均分略高于全注意力；但 4K/8K 不如 Fast-dLLM，"
             "而且子任务不是全面更好。NIAH 平均 98.17，128K 95%，说明激进组过滤下针信息仍有少量丢失。"
             "注意 NIAH 没有同条件基线。")


# ================================================================== 16 A100 throughput
def s16():
    s = new_slide("04 / 实验评估 · 效率", "A100-80G：offload 方案中最快，但不是绝对最快")

    hdr = ["方法", "4K", "8K", "16K", "32K", "64K", "128K"]
    om = {"t": "OOM", "color": RED, "bold": True}
    rows = [
        [{"t": h, "fill": NAVY, "color": WHITE, "bold": True} for h in hdr],
        [{"t": "UltraLLaDA（全注意力）", "fill": WHITE, "align": PP_ALIGN.LEFT}, "2.51", "1.12", "0.48", om, om, om],
        [{"t": "Fast-dLLM（全注意力）", "fill": LIGHT, "align": PP_ALIGN.LEFT}, "23.55", "11.83", om, om, om, om],
        [{"t": "KV offload + sparse", "fill": WHITE, "align": PP_ALIGN.LEFT}, "4.32", "1.96", "1.07", "0.48", "0.27", "0.12"],
        [{"t": "KV pipeline + sparse", "fill": LIGHT, "align": PP_ALIGN.LEFT}, "5.33", "2.57", "1.33", "0.69", "0.34", "0.15"],
        [{"t": "InfiniGen 风格", "fill": WHITE, "align": PP_ALIGN.LEFT}, "8.21", "4.68", "2.18", "1.33", "0.79", "0.31"],
        [{"t": "GroupKV", "fill": TEAL_LIGHT, "color": TEAL_DARK, "bold": True, "align": PP_ALIGN.LEFT},
         {"t": "10.64", "fill": TEAL_LIGHT, "color": TEAL_DARK, "bold": True},
         {"t": "5.91", "fill": TEAL_LIGHT, "color": TEAL_DARK, "bold": True},
         {"t": "2.84", "fill": TEAL_LIGHT, "color": TEAL_DARK, "bold": True},
         {"t": "1.79", "fill": TEAL_LIGHT, "color": TEAL_DARK, "bold": True},
         {"t": "0.99", "fill": TEAL_LIGHT, "color": TEAL_DARK, "bold": True},
         {"t": "0.39", "fill": TEAL_LIGHT, "color": TEAL_DARK, "bold": True}],
    ]
    styled_table(s, 0.7, 1.8, 8.55, 3.05, rows, col_ratios=[3.3, 1, 1, 1, 1, 1, 1],
                 font_size=9.5)

    tb, tf = textbox(s, 0.7, 5.0, 8.5, 0.25)
    p = para(tf, first=True); r = p.add_run(); r.text = "端到端吞吐（tok/s），batch = 1；所有稀疏方法同稀疏率。"
    style_run(r, size=8.5, color=MUTED, italic=True)

    stats = [("2.0–3.7×", "相对 FlexGen 风格 offload", "32K：1.79 vs 0.48 → 3.73×"),
             ("1.25–1.35×", "相对 InfiniGen 风格", "组级选择 + compact 调度"),
             ("0.39 tok/s", "128K 仍可服务", "但距交互式仍有数量级差距")]
    for i, (v, lab, sub) in enumerate(stats):
        y = 1.8 + i * 1.32
        card(s, 9.45, y, 3.15, 1.12, fill=LIGHT if i < 2 else AMBER_LIGHT, line=None)
        tb, tf = textbox(s, 9.62, y + 0.08, 2.85, 0.35)
        p = para(tf, first=True); r = p.add_run(); r.text = v
        style_run(r, size=17, bold=True, color=TEAL_DARK if i < 2 else AMBER)
        tb, tf = textbox(s, 9.62, y + 0.44, 2.9, 0.25)
        p = para(tf, first=True); r = p.add_run(); r.text = lab
        style_run(r, size=8.5, bold=True, color=BODY)
        tb, tf = textbox(s, 9.62, y + 0.68, 2.9, 0.4)
        p = para(tf, first=True, line=1.05); r = p.add_run(); r.text = sub
        style_run(r, size=7.5, color=MUTED)

    rect(s, 0.7, 5.86, 11.93, 0.9, fill=WHITE, line=TEAL, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.05)
    tb, tf = textbox(s, 0.95, 5.96, 11.45, 0.7)
    p = para(tf, first=True, line=1.2)
    add_runs(p, [
        ("读法：", {"size": 10.5, "bold": True, "color": TEAL_DARK}),
        ("全注意力放得下时，Fast-dLLM 在 4K/8K 是 23.55/11.83 tok/s，远快于 GroupKV；但它 16K 起 OOM。", {"size": 10.5, "color": BODY}),
    ])
    p2 = para(tf, first=False, before=3)
    add_runs(p2, [
        ("GroupKV 的价值是「显存受限时仍能服务」，而不是在所有场景下最快。", {"size": 10.5, "bold": True, "color": INK}),
    ])

    notes(s, "A100 上，GroupKV 在 4K–128K 都是 offload 方法里最快的，相对 FlexGen 风格 2–3.7 倍，"
             "相对 InfiniGen 1.25–1.35 倍。但绝对速度不高：128K 只有 0.39 tok/s。而且全注意力放得下时，"
             "Fast-dLLM 4K 能到 23.55，比 GroupKV 快一倍多。所以它的卖点是可服务性。")


# ================================================================== 17 4090 + 48x
def s17():
    s = new_slide("04 / 实验评估 · 效率", "RTX 4090-24G：把可服务上下文从 2K 推到 96K")

    card(s, 0.7, 1.85, 6.0, 3.7, fill=LIGHT, line=None)
    tb, tf = textbox(s, 0.95, 2.0, 5.5, 0.3)
    p = para(tf, first=True); r = p.add_run(); r.text = "最大可服务上下文（同一块 24GB GPU）"
    style_run(r, size=11.5, bold=True, color=INK)

    # Fast-dLLM bar
    tb, tf = textbox(s, 0.95, 2.55, 1.4, 0.3)
    p = para(tf, first=True); r = p.add_run(); r.text = "Fast-dLLM"
    style_run(r, size=10, bold=True, color=BLUE)
    rect(s, 0.95, 2.88, 0.3, 0.45, fill=RED, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.2)
    tb, tf = textbox(s, 1.35, 2.92, 2.2, 0.35)
    p = para(tf, first=True); r = p.add_run(); r.text = "2K（4K 起 OOM）"
    style_run(r, size=10.5, bold=True, color=RED)

    # GroupKV bar
    tb, tf = textbox(s, 0.95, 3.55, 1.4, 0.3)
    p = para(tf, first=True); r = p.add_run(); r.text = "GroupKV"
    style_run(r, size=10, bold=True, color=TEAL_DARK)
    rect(s, 0.95, 3.88, 4.7, 0.45, fill=TEAL, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.2)
    tb, tf = textbox(s, 5.75, 3.92, 0.8, 0.35)
    p = para(tf, first=True); r = p.add_run(); r.text = "96K"
    style_run(r, size=14, bold=True, color=TEAL_DARK)

    tb, tf = textbox(s, 0.95, 4.48, 5.5, 0.65)
    p = para(tf, first=True)
    add_runs(p, [("48", {"size": 36, "bold": True, "color": AMBER}),
                 ("×", {"size": 22, "bold": True, "color": AMBER}),
                 ("  可服务上下文扩展", {"size": 11, "bold": True, "color": INK})])
    tb, tf = textbox(s, 0.95, 5.2, 5.5, 0.3)
    p = para(tf, first=True)
    r = p.add_run(); r.text = "对比基准：同一平台、同一模型、Fast-dLLM 的最大上下文"
    style_run(r, size=8.5, color=MUTED, italic=True)

    # right table
    oom = {"t": "OOM", "color": RED, "bold": True}
    rows = [
        [{"t": "tok/s", "fill": NAVY, "color": WHITE, "bold": True, "align": PP_ALIGN.LEFT},
         "1K", "2K", "4K", "8K", "16K", "32K", "64K", "96K"],
        [{"t": "Fast-dLLM", "fill": WHITE, "align": PP_ALIGN.LEFT}, "30.46", "15.90", oom,
         oom, oom, oom, oom, oom],
        [{"t": "GroupKV", "fill": TEAL_LIGHT, "color": TEAL_DARK, "bold": True, "align": PP_ALIGN.LEFT},
         "30.66", "18.62", "10.25", "5.78", "2.76", "1.33", "0.59", "0.35"],
    ]
    styled_table(s, 7.0, 1.9, 5.6, 1.65, rows, col_ratios=[1.55, 1, 1, 1, 1, 1, 1, 1, 1],
                 font_size=8.2)

    bullets(s, 7.0, 3.75, 5.6, 1.45, [
        "Fast-dLLM 在 4K 起 OOM；GroupKV 服务到 96K",
        [("1K/2K 上 GroupKV 还略快：", {"bold": True}), ("30.66 vs 30.46；18.62 vs 15.90", {})],
        "96K 时仍有 0.35 tok/s，但已是「能跑」而非「好用」",
    ], size=10.3, gap=7)

    tb, tf = textbox(s, 7.0, 5.0, 5.55, 0.55)
    p = para(tf, first=True, line=1.15)
    r = p.add_run()
    r.text = "直观感受：96K 时约 3 秒生成一个 token —— 适合离线长文处理，不适合交互。"
    style_run(r, size=8.8, color=MUTED, italic=True)

    rect(s, 0.7, 5.8, 11.93, 1.05, fill=AMBER_LIGHT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06)
    rect(s, 0.7, 5.8, 0.07, 1.05, fill=AMBER)
    tb, tf = textbox(s, 0.95, 5.92, 11.45, 0.4)
    p = para(tf, first=True)
    add_runs(p, [("读法：", {"size": 12, "bold": True, "color": AMBER}),
                 ("48× 是「可服务性倍数」，不是「速度倍数」。", {"size": 12, "bold": True, "color": INK})])
    tb, tf = textbox(s, 0.95, 6.28, 11.45, 0.45)
    p = para(tf, first=True, line=1.1)
    r = p.add_run()
    r.text = ("容量维度：2K → 96K；速度维度：96K 仅 0.35 tok/s，而 2K 时 18.62 tok/s。"
              "两个数字回答不同问题，引用时必须带上维度。")
    style_run(r, size=9.8, color=BODY)

    notes(s, "RTX 4090 上对比最能体现定位：Fast-dLLM 只能到 2K，GroupKV 能到 96K，所以是 48 倍的可服务上下文。"
             "注意这不是速度的 48 倍；绝对吞吐 96K 只有 0.35 tok/s。短上下文上 GroupKV 甚至略快于 Fast-dLLM。")


# ================================================================== 18 ablation
def s18():
    s = new_slide("04 / 实验评估 · 消融", "消融：组稀疏降传输，预测预取藏停顿")

    tb, tf = textbox(s, 0.7, 1.68, 11.9, 0.3)
    p = para(tf, first=True)
    r = p.add_run(); r.text = "逐组件叠加（均为 streaming prefill；上：32K / 下：64K；单位 GiB 与 tok/s）"
    style_run(r, size=9.5, color=MUTED)

    stages = [
        ("Fast-dLLM\n+ streaming prefill", "38.62 GiB · 4.68", "OOM", RED, "—（基线）"),
        ("+ KV pipeline", "17.91 GiB · 0.70", "20.88 GiB · 0.36", AMBER, "Δ −20.7 GiB ｜ −3.98 tok/s"),
        ("+ 组稀疏", "15.87 GiB · 1.08", "16.28 GiB · 0.60", BLUE, "Δ −2.04 GiB ｜ +0.38 tok/s"),
        ("+ 预测预取", "16.00 GiB · 1.79", "16.53 GiB · 0.99", TEAL, "Δ +0.13 GiB ｜ +0.71 tok/s"),
    ]
    for i, (title, v32, v64, color, delta) in enumerate(stages):
        x = 0.7 + i * 3.05
        card(s, x, 1.95, 2.75, 2.05, fill=WHITE, line=BORDER)
        rect(s, x, 1.95, 2.75, 0.07, fill=color)
        tb, tf = textbox(s, x + 0.18, 2.1, 2.4, 0.5)
        p = para(tf, first=True, line=0.95); r = p.add_run(); r.text = title
        style_run(r, size=10.5, bold=True, color=INK)
        tb, tf = textbox(s, x + 0.18, 2.66, 2.45, 0.3)
        p = para(tf, first=True); r = p.add_run(); r.text = "32K  " + v32
        style_run(r, size=9.2, bold=True, color=color if i < 3 else TEAL_DARK)
        tb, tf = textbox(s, x + 0.18, 2.96, 2.45, 0.3)
        p = para(tf, first=True)
        r = p.add_run(); r.text = "64K  " + v64
        style_run(r, size=9.2, color=(RED if v64 == "OOM" else BODY))
        tb, tf = textbox(s, x + 0.18, 3.32, 2.45, 0.25)
        p = para(tf, first=True, line=1.05)
        msg = ["容量瓶颈", "容量↓但停顿↑", "传输↓吞吐↑", "停顿被覆盖"][i]
        r = p.add_run(); r.text = msg
        style_run(r, size=8.2, color=MUTED, italic=True)
        tb, tf = textbox(s, x + 0.18, 3.64, 2.45, 0.22)
        p = para(tf, first=True)
        r = p.add_run(); r.text = delta
        style_run(r, size=7.4, color=color if i > 0 else MUTED)
        if i < 3:
            line(s, x + 2.78, 2.95, x + 3.0, 2.95, color=MUTED, width=1.1, tail=True)

    # k2 table
    tb, tf = textbox(s, 0.7, 4.15, 6.0, 0.3)
    p = para(tf, first=True); r = p.add_run(); r.text = "层内细化预算 k2（UltraLLaDA，A100）"
    style_run(r, size=10.5, bold=True, color=INK)
    rows = [
        [{"t": "k2", "fill": NAVY, "color": WHITE, "bold": True},
         {"t": "LongBench", "fill": NAVY, "color": WHITE, "bold": True},
         {"t": "32K 吞吐", "fill": NAVY, "color": WHITE, "bold": True},
         {"t": "64K 吞吐", "fill": NAVY, "color": WHITE, "bold": True}],
        [{"t": "0.25", "fill": WHITE}, "36.89（−0.54）", "1.90（+6.4%）", "1.08（+8.9%）"],
        [{"t": "0.50 默认", "fill": TEAL_LIGHT, "color": TEAL_DARK, "bold": True},
         {"t": "37.43", "fill": TEAL_LIGHT, "bold": True},
         {"t": "1.79", "fill": TEAL_LIGHT, "bold": True},
         {"t": "0.99", "fill": TEAL_LIGHT, "bold": True}],
        [{"t": "0.75", "fill": LIGHT}, "37.72（+0.29）", "1.42（−20.4%）", "0.71（−28.7%）"],
    ]
    styled_table(s, 0.7, 4.47, 6.0, 1.5, rows, col_ratios=[1, 1.35, 1.2, 1.2], font_size=8.8)

    # right bullets
    card(s, 7.0, 4.18, 5.6, 1.95, fill=LIGHT, line=None)
    bullets(s, 7.2, 4.32, 5.25, 1.0, [
        [("g × top-k 网格：", {"bold": True}), ("top-k 超过 20–30% 后收益递减；g=8 多数格更优", {})],
        [("但 UltraLLaDA 上 g=4 / top-20% = 38.27", {"color": AMBER, "bold": True}),
         ("，高于默认 37.43", {})],
        [("默认配置是吞吐/显存折中，", {}), ("不是精度最优", {"bold": True})],
    ], size=9.8, gap=5, bullet_color=AMBER)

    line(s, 7.2, 5.38, 12.45, 5.38, color=BORDER, width=0.7)
    tb, tf = textbox(s, 7.2, 5.5, 5.25, 0.5)
    p = para(tf, first=True, line=1.15)
    r = p.add_run()
    r.text = "k2 取舍：0.25 比默认快 6–9%，但掉 0.54 分；0.75 只多 0.29 分，却慢 20–29%。"
    style_run(r, size=8.8, color=BODY)

    tb, tf = textbox(s, 0.7, 6.28, 11.9, 0.35)
    p = para(tf, first=True)
    add_runs(p, [
        ("一句话：", {"size": 10.5, "bold": True, "color": TEAL_DARK}),
        ("pipeline 解决容量但引入停顿，组稀疏降低传输，预取把停顿藏起来 —— 三者缺一不可。", {"size": 10.5, "color": BODY}),
    ])

    notes(s, "组件消融很清楚：KV pipeline 把显存从 38.6 降到 17.9，但吞吐掉到 0.70；组稀疏把传输降下来，回到 1.08；"
             "预测预取再到 1.79，显存只多 0.13。k2 取 0.5 是折中：0.25 快一点但掉分，0.75 只多 0.29 分却慢 20–29%。"
             "另外，默认 g=8/top-20% 不是精度最高，g=4/top-20% 在 UltraLLaDA 上是 38.27。")


# ================================================================== 19 batch + positioning
def s19():
    s = new_slide("04 / 实验评估 · 扩展性与定位", "批处理与适用边界：它是补充，不是替代")

    card(s, 0.7, 1.8, 6.0, 4.15, fill=WHITE)
    tb, tf = textbox(s, 0.95, 1.96, 5.5, 0.3)
    p = para(tf, first=True); r = p.add_run(); r.text = "Batch-size 扩展性（A100-80G）"
    style_run(r, size=12, bold=True, color=INK)

    # simple batch visual
    batches = [1, 9, 18, 27, 45]
    heights = [0.5, 0.95, 1.25, 1.45, 1.55]
    base_y = 4.08
    for i, (b, hh) in enumerate(zip(batches, heights)):
        x = 1.1 + i * 0.82
        rect(s, x, base_y - hh, 0.55, hh, fill=TEAL if i < 4 else TEAL_DARK,
             line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
        tb, tf = textbox(s, x - 0.08, base_y + 0.05, 0.72, 0.2)
        p = para(tf, first=True, align=PP_ALIGN.CENTER); r = p.add_run(); r.text = str(b)
        style_run(r, size=7.5, color=MUTED)
    tb, tf = textbox(s, 1.05, 4.35, 4.5, 0.2)
    p = para(tf, first=True); r = p.add_run(); r.text = "batch size →"
    style_run(r, size=7.5, color=MUTED)
    tb, tf = textbox(s, 0.95, 2.32, 5.4, 0.25)
    p = para(tf, first=True)
    r = p.add_run(); r.text = "相对吞吐随 batch 上升，直到显存 / H2D 饱和"
    style_run(r, size=8.8, color=MUTED, italic=True)

    bullets(s, 0.95, 4.7, 5.5, 0.85, [
        [("4K / 8K / 16K 峰值约 ", {}), ("10 / 6 / 2.5 tok/s", {"bold": True, "color": TEAL_DARK})],
        "分层恢复与双缓冲在 batch>1 时仍有效",
    ], size=9.5, gap=3)

    tb, tf = textbox(s, 0.95, 5.5, 5.5, 0.3)
    p = para(tf, first=True)
    r = p.add_run(); r.text = "两条曲线（LLaDA / UltraLLaDA）× 三种上下文；主实验仍为 batch = 1。"
    style_run(r, size=8, color=MUTED, italic=True)

    # right decision table
    tb, tf = textbox(s, 7.0, 1.8, 5.6, 0.3)
    p = para(tf, first=True); r = p.add_run(); r.text = "什么时候用 GroupKV？"
    style_run(r, size=12, bold=True, color=INK)
    rows = [
        [{"t": "场景", "fill": NAVY, "color": WHITE, "bold": True, "align": PP_ALIGN.LEFT},
         {"t": "建议", "fill": NAVY, "color": WHITE, "bold": True, "align": PP_ALIGN.LEFT}],
        [{"t": "短上下文，全 KV 放得下", "fill": WHITE, "align": PP_ALIGN.LEFT},
         {"t": "Fast-dLLM（更快）", "fill": WHITE, "color": BLUE, "align": PP_ALIGN.LEFT}],
        [{"t": "长上下文 + 显存充足", "fill": LIGHT, "align": PP_ALIGN.LEFT},
         {"t": "全注意力 / Fast-dLLM", "fill": LIGHT, "color": BLUE, "align": PP_ALIGN.LEFT}],
        [{"t": "长上下文 + 显存受限", "fill": TEAL_LIGHT, "align": PP_ALIGN.LEFT},
         {"t": "GroupKV", "fill": TEAL_LIGHT, "color": TEAL_DARK, "bold": True, "align": PP_ALIGN.LEFT}],
        [{"t": "多请求混合负载", "fill": LIGHT, "align": PP_ALIGN.LEFT},
         {"t": "证据不足，需补调度/SLO", "fill": LIGHT, "color": AMBER, "align": PP_ALIGN.LEFT}],
    ]
    styled_table(s, 7.0, 2.15, 5.6, 2.2, rows, col_ratios=[1.5, 1.5], font_size=9.5)

    tb, tf = textbox(s, 7.0, 4.55, 5.55, 0.85)
    p = para(tf, first=True, line=1.2)
    add_runs(p, [
        ("论文的调度器：", {"size": 9.5, "bold": True, "color": BODY}),
        ("按 VRAM 可用量和输入长度查表，把短请求路由到 Fast-dLLM，长请求路由到 GroupKV；接口后端无关。",
         {"size": 9.5, "color": BODY}),
    ])

    rect(s, 0.7, 6.15, 11.93, 0.62, fill=TEAL_LIGHT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.1)
    tb, tf = textbox(s, 0.95, 6.25, 11.45, 0.4)
    p = para(tf, first=True)
    add_runs(p, [
        ("定位：", {"size": 11, "bold": True, "color": TEAL_DARK}),
        ("显存受限长上下文场景的 offload 加速器；短上下文交给更快的方法，二者组合使用。",
         {"size": 11, "bold": True, "color": INK}),
    ])

    notes(s, "batch 扩展只有一张图：吞吐随 batch 上升，然后被显存或 PCIe 限制饱和。4K/8K/16K 峰值大概 10/6/2.5。"
             "结论是它适合显存受限的长上下文；短上下文应该交给 Fast-dLLM，作者也是这么定位的。")


# ================================================================== 20 strengths
def s20():
    s = new_slide("05 / 批判性讨论", "强项：把两个可测量的结构性质，变成可运行的流水线")

    items = [
        ("01", "问题定位准确", "dLLM 的 KV 是动态生命周期：周期重算 + 非顺序覆盖；直接套用 append-only 优化会失效。",
         "把「系统问题」定义对了，而不是只做一个更好的 top-k", TEAL),
        ("02", "轻量、可摊销", "RoPE key 均值池化作为组摘要，无聚类 / 索引 / 学习结构；更新只重算受影响组。",
         "在反复刷新下仍能维持低维护成本", BLUE),
        ("03", "系统闭环", "组级选择、跨层预取、陈旧性修复、流式 prefill 一起设计，而不是单点技巧。",
         "把「按需取数的串行等待」变成 producer–consumer 流水", AMBER),
        ("04", "数据支撑", "96K/2K = 48× 可服务上下文；offload 场景 2.0–3.7×；LongBench 接近全注意力。",
         "消费级与数据中心 GPU 都验证了可服务性", TEAL_DARK),
    ]
    for i, (num, title, body, ev, color) in enumerate(items):
        x = 0.7 + (i % 2) * 6.08
        y = 1.8 + (i // 2) * 2.05
        card(s, x, y, 5.85, 1.9)
        rect(s, x, y, 0.05, 1.9, fill=color)
        tb, tf = textbox(s, x + 0.22, y + 0.14, 0.55, 0.4)
        p = para(tf, first=True); r = p.add_run(); r.text = num
        style_run(r, size=16, bold=True, color=color)
        tb, tf = textbox(s, x + 0.78, y + 0.18, 4.8, 0.35)
        p = para(tf, first=True); r = p.add_run(); r.text = title
        style_run(r, size=14, bold=True, color=INK)
        tb, tf = textbox(s, x + 0.22, y + 0.65, 5.4, 0.75)
        p = para(tf, first=True, line=1.15); r = p.add_run(); r.text = body
        style_run(r, size=10.2, color=BODY)
        tb, tf = textbox(s, x + 0.22, y + 1.42, 5.4, 0.35)
        p = para(tf, first=True); r = p.add_run(); r.text = "▸ " + ev
        style_run(r, size=8.5, color=color, italic=True)

    rect(s, 0.7, 5.98, 11.93, 0.82, fill=NAVY, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
    tb, tf = textbox(s, 0.95, 6.12, 11.4, 0.55)
    p = para(tf, first=True)
    add_runs(p, [("一句话：", {"size": 11.5, "bold": True, "color": AMBER}),
                 ("把「按需取数的串行等待」改造成「生产者—消费者流水」，是这篇论文最系统化的贡献。",
                  {"size": 11.5, "bold": True, "color": WHITE})])

    notes(s, "强项四个：问题定义准确，没有套 AR 假设；组摘要很轻，适合反复刷新；设计是闭环的；数据也够支撑可服务性。"
             "最值得学的是它把串行等待改成了流水线。")


# ================================================================== 21 limitations
def s21():
    s = new_slide("05 / 批判性讨论", "局限：大数字的边界，与未被验证的机制")

    items = [
        ("指标口径", RED, "48× 与 3.73× 基准不同；对 InfiniGen 仅 1.25–1.35×；短上下文 Fast-dLLM 更快。"),
        ("精度证据", AMBER, "非全面领先；NIAH 无同条件基线；无方差/显著性；「正则化」只是猜测。"),
        ("评估覆盖", BLUE, "仅 LLaDA 系两个模型；主实验 batch=1；无真实 serving trace 与尾延迟。"),
        ("系统测量", TEAL_DARK, "缺 H2D / 组评分 / gather / 修复的分解；理论 3.81× 与实测 1.25–1.35× 的差距未解释。"),
        ("正确性", RED, "「正确性要求」无形式化条件；~12% 预取漏检的影响未量化；均值摘要可能稀释「针」。"),
        ("默认配置", AMBER, "默认非精度最优（UltraLLaDA g=4/top-20% = 38.27 > 37.43）；流式 prefill 无单独收益分解。"),
    ]
    for i, (tag, color, body) in enumerate(items):
        x = 0.7 + (i % 3) * 4.06
        y = 1.8 + (i // 3) * 1.72
        card(s, x, y, 3.82, 1.55)
        rect(s, x, y, 0.05, 1.55, fill=color)
        tb, tf = textbox(s, x + 0.2, y + 0.14, 3.4, 0.3)
        p = para(tf, first=True); r = p.add_run(); r.text = tag
        style_run(r, size=11, bold=True, color=color)
        tb, tf = textbox(s, x + 0.2, y + 0.5, 3.45, 0.95)
        p = para(tf, first=True, line=1.12); r = p.add_run(); r.text = body
        style_run(r, size=9.3, color=BODY)

    rect(s, 0.7, 5.55, 11.93, 1.15, fill=LIGHT, line=AMBER, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.05)
    tb, tf = textbox(s, 0.95, 5.68, 11.45, 0.4)
    p = para(tf, first=True)
    add_runs(p, [("综合判断：", {"size": 11.5, "bold": True, "color": AMBER}),
                 ("它更适合被理解为「显存受限长上下文场景的 offload 加速器」，而不是普适的 dLLM 推理加速器。",
                  {"size": 11.5, "bold": True, "color": INK})])
    tb, tf = textbox(s, 0.95, 6.12, 11.45, 0.45)
    p = para(tf, first=True)
    r = p.add_run(); r.text = ("这些不足不否定方法价值，但提醒我们在引用 48×/3.73× 时必须带上比较基准；"
                               "在最关键的动态一致性上，论文的证据最薄弱。")
    style_run(r, size=9.5, color=BODY)

    notes(s, "批判部分六点。最重要的是口径：48 倍是可服务上下文，3.73 倍是对 FlexGen 风格基线，对 InfiniGen 只有 1.25–1.35。"
             "其次精度不是全面领先；评估只有两个 LLaDA 系模型、主实验 batch=1；系统分解不足；正确性没有形式化。"
             "所以它应当被理解为 offload 加速器，而不是通用加速器。")


# ================================================================== 22 discussion
def s22():
    s = new_slide("05 / 批判性讨论", "可以往哪里走：四个改造方向")

    items = [
        ("A", "多视图 · 自适应粒度", TEAL, [
            "每组存均值 + max-norm / 低秩 / top-r 摘要",
            "粗组 → 细组 + 边界细化，降低跨段代价",
            "按注意力质量累计预算，而非固定 top-k%",
        ], "目标：128K NIAH 95% → 98%"),
        ("B", "置信度感知预取", AMBER, [
            "组分数做轻量集成，估计下一层命中概率",
            "高置信先取；低置信只取候选超集 + 回退",
            "版本号 / delta 代替整组重载",
        ], "指标：stale-hit · repair bytes"),
        ("C", "低比特常驻摘要", BLUE, [
            "4-bit 组 key ≈ 1 GiB，可常驻 GPU",
            "int4 / fp8 张量核做粗筛",
            "CSR/paged + TMA + warp specialization",
        ], "目标：24 GB 上服务 128K"),
        ("D", "请求感知调度", TEAL_DARK, [
            "前缀共享：引用计数 + 写时复制",
            "多请求合批组评分与 gather",
            "SLO-aware 准入 / 驱逐与预算分配",
        ], "缺口：P99 · 公平性 · 碎片"),
    ]
    for i, (letter, title, color, lines, goal) in enumerate(items):
        x = 0.7 + i * 3.04
        card(s, x, 1.8, 2.84, 3.7)
        rect(s, x, 1.8, 2.84, 0.06, fill=color)
        tb, tf = textbox(s, x + 0.18, 1.95, 0.45, 0.4)
        p = para(tf, first=True); r = p.add_run(); r.text = letter
        style_run(r, size=18, bold=True, color=color)
        tb, tf = textbox(s, x + 0.58, 2.0, 2.15, 0.55)
        p = para(tf, first=True, line=0.98); r = p.add_run(); r.text = title
        style_run(r, size=11, bold=True, color=INK)
        bullets(s, x + 0.18, 2.65, 2.5, 1.9, lines, size=9.9, gap=10,
                line=1.2, bullet_color=color)
        line(s, x + 0.18, 4.62, x + 2.65, 4.62, color=BORDER, width=0.7)
        tb, tf = textbox(s, x + 0.18, 4.72, 2.5, 0.55)
        p = para(tf, first=True, line=1.1); r = p.add_run(); r.text = goal
        style_run(r, size=8.5, bold=True, color=color)

    rect(s, 0.7, 5.78, 11.93, 0.7, fill=TEAL_LIGHT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
    tb, tf = textbox(s, 0.95, 5.88, 11.45, 0.5)
    p = para(tf, first=True, line=1.1)
    add_runs(p, [
        ("可迁移：", {"size": 10.5, "bold": True, "color": TEAL_DARK}),
        ("「分层摘要 + 预取一致性」这套思路也适用于 MoE 专家缓存、RAG 的 KV 复用、多请求前缀共享。",
         {"size": 10.5, "color": BODY}),
    ])

    notes(s, "讨论四个方向：摘要从单均值变多视图/自适应粒度；预取从单层确定性变置信度感知 + 版本化一致性；"
             "组摘要低比特常驻 GPU 并做内核协同；最后从单请求走向请求感知调度。前三个是方法层，第四个是系统层。")


# ================================================================== 23 conclusion
def s23():
    s = new_slide(page=False)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = NAVY

    rect(s, 0.9, 1.1, 0.06, 0.3, fill=AMBER)
    tb, tf = textbox(s, 1.08, 1.06, 8.0, 0.3)
    p = para(tf, first=True)
    r = p.add_run(); r.text = "结论"
    style_run(r, size=12, bold=True, color=AMBER, spc=180)

    tb, tf = textbox(s, 0.88, 1.55, 8.4, 2.2)
    p = para(tf, first=True, line=1.18)
    add_runs(p, [("GroupKV 的贡献不是让 dLLM 全面变快，", {"size": 24, "bold": True, "color": WHITE})])
    p2 = para(tf, before=2, line=1.18)
    add_runs(p2, [("而是在显存放不下全量 KV 时，", {"size": 24, "bold": True, "color": WHITE}),
                  ("给出一条可服务、可调、精度可接受的路径。", {"size": 24, "bold": True, "color": RGBColor(0x7D, 0xC6, 0xC4)})])

    # stats
    stats = [("48×", "可服务上下文", "2K → 96K（RTX 4090）"),
             ("3.73×", "offload 吞吐", "32K，vs FlexGen 风格"),
             ("98.17%", "NIAH 检索", "平均，128K 仍 95%")]
    for i, (v, lab, sub) in enumerate(stats):
        x = 0.9 + i * 2.55
        rect(s, x, 4.2, 2.25, 1.35, fill=RGBColor(0x16, 0x33, 0x4C),
             shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.07)
        tb, tf = textbox(s, x + 0.18, 4.33, 2.0, 0.45)
        p = para(tf, first=True); r = p.add_run(); r.text = v
        style_run(r, size=24, bold=True, color=WHITE)
        tb, tf = textbox(s, x + 0.18, 4.8, 2.0, 0.25)
        p = para(tf, first=True); r = p.add_run(); r.text = lab
        style_run(r, size=8.5, bold=True, color=RGBColor(0xC8, 0xDC, 0xE7))
        tb, tf = textbox(s, x + 0.18, 5.03, 2.0, 0.4)
        p = para(tf, first=True); r = p.add_run(); r.text = sub
        style_run(r, size=7.5, color=RGBColor(0x8F, 0xAD, 0xBD))

    # takeaways
    tb, tf = textbox(s, 9.0, 1.6, 3.6, 0.3)
    p = para(tf, first=True); r = p.add_run(); r.text = "三句话带走"
    style_run(r, size=10, bold=True, color=AMBER, spc=100)
    lines = [
        ("01", "观察驱动设计", "块内局部性 → 组级选择；层间一致性 → 跨层预取"),
        ("02", "工程闭环", "粗筛、流水、修复、prefill 缺一不可"),
        ("03", "使用边界", "offload 密集长上下文；短上下文交给 Fast-dLLM"),
    ]
    for i, (n, h, d) in enumerate(lines):
        y = 2.0 + i * 1.3
        tb, tf = textbox(s, 9.0, y, 0.4, 0.3)
        p = para(tf, first=True); r = p.add_run(); r.text = n
        style_run(r, size=10, bold=True, color=TEAL)
        tb, tf = textbox(s, 9.45, y - 0.02, 3.2, 0.3)
        p = para(tf, first=True); r = p.add_run(); r.text = h
        style_run(r, size=11.5, bold=True, color=WHITE)
        tb, tf = textbox(s, 9.45, y + 0.27, 3.25, 0.6)
        p = para(tf, first=True, line=1.1); r = p.add_run(); r.text = d
        style_run(r, size=8.5, color=RGBColor(0x9F, 0xBF, 0xCE))

    line(s, 0.9, 6.35, 12.4, 6.35, color=RGBColor(0x2C, 0x4A, 0x61), width=0.8)
    tb, tf = textbox(s, 0.9, 6.5, 7.0, 0.4)
    p = para(tf, first=True); r = p.add_run(); r.text = "谢谢 · 欢迎讨论"
    style_run(r, size=18, bold=True, color=WHITE)
    tb, tf = textbox(s, 8.0, 6.55, 4.4, 0.3)
    p = para(tf, first=True, align=PP_ALIGN.RIGHT)
    r = p.add_run(); r.text = "GroupKV · ICPP '26"
    style_run(r, size=9, color=RGBColor(0x7D, 0xA3, 0xB8))

    notes(s, "收尾：GroupKV 不是一个普适加速器，而是在显存受限时给出可服务路径。三个带走点：观察驱动设计、工程闭环、"
             "知道使用边界。谢谢，欢迎提问。")


# ================================================================== 24 appendix
def s24():
    s = new_slide("附录", "关键算法与符号：预取如何与计算交错")

    # Algorithm 1
    card(s, 0.7, 1.78, 5.85, 3.3, fill=RGBColor(0xF7, 0xF9, 0xFB), line=BORDER)
    tb, tf = textbox(s, 0.92, 1.92, 5.4, 0.3)
    p = para(tf, first=True); r = p.add_run(); r.text = "Algorithm 1 · Prefill"
    style_run(r, size=10.5, bold=True, color=TEAL_DARK, latin=FONT_MONO)
    code1 = [
        "for l in range(L):",
        "    X, (K_l, V_l) = StreamedBlock_l(X)",
        "    G_l = GroupKeys(K_l, g)        # 组级 key",
        "    offload(K_l, V_l, G_l -> CPU)",
    ]
    for i, ln in enumerate(code1):
        tb, tf = textbox(s, 0.92, 2.3 + i * 0.36, 5.45, 0.3)
        p = para(tf, first=True, line=1.0); r = p.add_run(); r.text = ln
        style_run(r, size=9.5, color=INK, latin=FONT_MONO)
    tb, tf = textbox(s, 0.92, 3.9, 5.4, 0.9)
    p = para(tf, first=True, line=1.2)
    r = p.add_run(); r.text = ("预填充阶段把整条上下文的 K/V 与组级摘要一次性卸到 CPU；\n"
                               "流式分块保证峰值显存主要由 S_blk 决定。")
    style_run(r, size=9.5, color=BODY)

    # Algorithm 2
    card(s, 6.78, 1.78, 5.85, 3.3, fill=RGBColor(0xF7, 0xF9, 0xFB), line=BORDER)
    tb, tf = textbox(s, 7.0, 1.92, 5.4, 0.3)
    p = para(tf, first=True); r = p.add_run(); r.text = "Algorithm 2 · Decode (per layer)"
    style_run(r, size=10.5, bold=True, color=AMBER, latin=FONT_MONO)
    code2 = [
        "s, n = l % 2, 1 - l % 2",
        "A = ScoreTokens(X_blk, Slot_s.K)",
        "J = TopK(A, k2)                  # 层内细化",
        "X_blk = AttentionFFN_l(A, Slot_s.V, J)",
        "I_l = SelectGroups(X_blk, Slot_s.G, k_g)",
        "Slot_n.K, V = Gather(K_l+1, V_l+1, I_l, g)",
    ]
    for i, ln in enumerate(code2):
        tb, tf = textbox(s, 7.0, 2.3 + i * 0.34, 5.45, 0.3)
        p = para(tf, first=True, line=1.0); r = p.add_run(); r.text = ln
        style_run(r, size=9.2, color=INK, latin=FONT_MONO)
    tb, tf = textbox(s, 7.0, 4.35, 5.4, 0.6)
    p = para(tf, first=True, line=1.2)
    r = p.add_run(); r.text = "计算流与预取流共享 Slot_s；预取结果写入 Slot_n。"
    style_run(r, size=9.5, color=BODY)

    # notation
    tb, tf = textbox(s, 0.7, 5.3, 11.9, 0.3)
    p = para(tf, first=True); r = p.add_run(); r.text = "符号速查"
    style_run(r, size=10.5, bold=True, color=INK)
    nota = [
        ("B", "当前生成块"), ("S", "上下文长度"), ("g", "组大小（默认 8）"),
        ("M", "组数 ⌈S/g⌉"), ("k_g", "组检索预算 top-k%"), ("k2", "层内细化比例"),
        ("N_ctx", "上下文 token 数"), ("f", "恢复 token 比例"),
    ]
    for i, (sym, desc) in enumerate(nota):
        x = 0.7 + (i % 4) * 3.02
        y = 5.62 + (i // 4) * 0.45
        tb, tf = textbox(s, x, y, 0.6, 0.3)
        p = para(tf, first=True); r = p.add_run(); r.text = sym
        style_run(r, size=10, bold=True, color=TEAL_DARK, latin=FONT_MATH)
        tb, tf = textbox(s, x + 0.55, y, 2.4, 0.3)
        p = para(tf, first=True); r = p.add_run(); r.text = desc
        style_run(r, size=9, color=BODY)

    notes(s, "附录是给提问用的：Algorithm 1 是 prefill 时逐层建 K/V 和组摘要并 offload；Algorithm 2 是解码时用 "
             "Slot_s 计算、同时为下一层 gather 到 Slot_n。下面有符号表。")

# ------------------------------------------------------------------ build
BUILDERS = [s01, s02, s03, s04, s05, s06, s07, s08, s09, s10, s11, s12,
            s13, s14, s15, s16, s17, s18, s19, s20, s21, s22, s23, s24]
for fn in BUILDERS:
    fn()

save_deck("GroupKV_组会汇报.pptx",
          title="GroupKV：面向长上下文 dLLM 的分层 KV Cache 管理",
          subject="组会论文汇报 · ICPP '26",
          author="组会汇报",
          comments="Generated from the GroupKV paper (ICPP '26).")
print("saved: GroupKV_组会汇报.pptx")
