# -*- coding: utf-8 -*-
"""把 PDF 论文抽取成带页码标记的纯文本，供 Grep / 定点 Read 使用。

用法:
    py extract_paper.py paper.pdf -o _paper_text.txt
    py extract_paper.py paper.pdf -o _paper_text.txt --pages 1-8,15
"""
import argparse
import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        print("missing dependency: pip install pymupdf", file=sys.stderr)
        sys.exit(2)


def parse_pages(spec, n):
    if not spec:
        return list(range(n))
    out = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a) - 1, min(int(b), n)))
        elif part:
            out.append(int(part) - 1)
    return [i for i in out if 0 <= i < n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("-o", "--out", default="_paper_text.txt")
    ap.add_argument("--pages", help="如 1-10,15；默认全部")
    args = ap.parse_args()

    doc = fitz.open(args.pdf)
    pages = parse_pages(args.pages, doc.page_count)
    chars = 0
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("# %s\n# pages: %d\n" % (os.path.basename(args.pdf), doc.page_count))
        for i in pages:
            text = doc[i].get_text()
            chars += len(text)
            f.write("\n=== PAGE %d ===\n" % (i + 1))
            f.write(text)
    doc.close()

    size = os.path.getsize(args.out)
    print("wrote %s | %d pages | %d chars | %.1f KB" %
          (args.out, len(pages), chars, size / 1024.0))
    if chars < 200:
        print("WARNING: almost no text extracted; PDF may be scanned. "
              "Needs OCR before reading.", file=sys.stderr)


if __name__ == "__main__":
    main()
