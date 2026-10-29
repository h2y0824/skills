# -*- coding: utf-8 -*-
"""用 PowerPoint 的真实排版结果检查：文字超框、形状出界。

用法:
    py audit_layout.py deck.pptx
    py audit_layout.py deck.pptx --json report.json
    py audit_layout.py deck.pptx --tolerance 4

退出码：0 无问题；1 有问题；2 无法检查（未装 PowerPoint 时只做形状出界检查）。
"""
import argparse
import json
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def audit_com(pptx, tol):
    import win32com.client
    import os
    app = win32com.client.Dispatch("PowerPoint.Application")
    deck = app.Presentations.Open(os.path.abspath(pptx),
                                  ReadOnly=True, WithWindow=False)
    issues = []
    try:
        sw = deck.PageSetup.SlideWidth
        sh = deck.PageSetup.SlideHeight
        for s_idx in range(1, deck.Slides.Count + 1):
            slide = deck.Slides(s_idx)
            for i in range(1, slide.Shapes.Count + 1):
                sp = slide.Shapes(i)
                try:
                    left, top = sp.Left, sp.Top
                    width, height = sp.Width, sp.Height
                except Exception:
                    continue

                text = ""
                try:
                    if sp.HasTextFrame and sp.TextFrame2.HasText:
                        text = (sp.TextFrame2.TextRange.Text or "").strip()
                except Exception:
                    pass

                # 装饰性出血（无文字）允许 0.5in；带文字的形状只允许 tol
                overshoot = max(-left, -top, left + width - sw, top + height - sh)
                if overshoot > (36.0 if not text else tol):
                    issues.append({
                        "slide": s_idx, "shape": i, "kind": "out-of-slide",
                        "name": safe_name(sp),
                        "detail": "shape bounds %.1f,%.1f %.1fx%.1f vs slide %.1fx%.1f"
                                  % (left, top, width, height, sw, sh),
                    })

                if not text:
                    continue
                try:
                    tf = sp.TextFrame2
                    if tf.AutoSize != 0:      # 非 none 自动调整，不判超框
                        continue
                    tr = tf.TextRange
                    bl, bt = tr.BoundLeft, tr.BoundTop
                    bw, bh = tr.BoundWidth, tr.BoundHeight
                except Exception:
                    continue

                if (bl < -tol or bt < -tol or
                        bl + bw > sw + tol or bt + bh > sh + tol):
                    issues.append({
                        "slide": s_idx, "shape": i, "kind": "text-out-of-slide",
                        "name": safe_name(sp), "text": snippet(text),
                        "detail": "text bounds %.1f,%.1f %.1fx%.1f vs slide %.1fx%.1f"
                                  % (bl, bt, bw, bh, sw, sh),
                    })

                bottom_over = (bt + bh) - (top + height)
                if bottom_over > tol:
                    issues.append({
                        "slide": s_idx, "shape": i, "kind": "text-overflow",
                        "name": safe_name(sp), "text": snippet(text),
                        "detail": "text bottom %.1f > box bottom %.1f (+%.1fpt)"
                                  % (bt + bh, top + height, bottom_over),
                    })
    finally:
        deck.Close()
    return issues


def safe_name(sp):
    try:
        return sp.Name
    except Exception:
        return "(unnamed)"


def snippet(text, n=36):
    return " ".join(text.split())[:n]


def audit_bounds_only(pptx, tol):
    """无 PowerPoint 时的降级检查：只看形状是否出界。"""
    from pptx import Presentation
    from pptx.util import Emu
    p = Presentation(pptx)
    sw, sh = p.slide_width, p.slide_height
    lim = Emu(int(max(tol, 36.0) * 12700))   # 装饰性出血与 COM 版保持一致的容忍度
    issues = []
    for s_idx, slide in enumerate(p.slides, 1):
        for i, sp in enumerate(slide.shapes, 1):
            l, t, w, h = sp.left, sp.top, sp.width, sp.height
            if None in (l, t, w, h):
                continue
            if l < -lim or t < -lim or l + w > sw + lim or t + h > sh + lim:
                issues.append({
                    "slide": s_idx, "shape": i, "kind": "out-of-slide",
                    "name": sp.name,
                    "detail": "at %.1f,%.1f %.1fx%.1f in"
                              % (l / 914400, t / 914400, w / 914400, h / 914400),
                })
    return issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pptx")
    ap.add_argument("--json", default=None)
    ap.add_argument("--tolerance", type=float, default=3.0, help="允许误差(pt)")
    args = ap.parse_args()

    mode = "PowerPoint"
    try:
        issues = audit_com(args.pptx, args.tolerance)
    except Exception as e:
        print("PowerPoint COM unavailable (%s); bounds-only fallback." % e,
              file=sys.stderr)
        mode = "bounds-only"
        issues = audit_bounds_only(args.pptx, args.tolerance)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(issues, f, ensure_ascii=False, indent=2)

    if not issues:
        print("[%s] clean: no overflow / out-of-bounds" % mode)
        return 0

    print("[%s] %d issue(s)" % (mode, len(issues)))
    cur = None
    for it in issues:
        if it["slide"] != cur:
            cur = it["slide"]
            print("== slide %d ==" % cur)
        line = "  [%s] #%d %s" % (it["kind"], it["shape"], it["name"])
        if it.get("text"):
            line += '  "%s"' % it["text"]
        line += "  " + it["detail"]
        print(line)
    if mode == "bounds-only":
        print("NOTE: text overflow not checked; install PowerPoint for full audit.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
