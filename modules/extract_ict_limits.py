#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
import pdfplumber
import re


def normalize_num(v):
    if not v:
        return None
    v = v.replace(",", ".")
    nums = re.findall(r"[0-9]+\.[0-9]+", v)
    if len(nums) >= 1:
        return nums[-1]
    return None


def group_by_y(chars, tolerance=3):
    """Regroupe les caractères par lignes en fonction de leur coordonnée Y."""
    lines = {}
    for c in chars:
        y = round(c["top"] / tolerance)
        lines.setdefault(y, []).append(c)
    for y in lines:
        lines[y] = sorted(lines[y], key=lambda c: c["x0"])
    return lines


def extract_lines(pdf_path):
    all_lines = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            chars = page.chars
            lines = group_by_y(chars)
            for _, line_chars in lines.items():
                txt = "".join(c["text"] for c in line_chars).strip()
                if txt:
                    all_lines.append((line_chars, txt))
    return all_lines


def extract_ict(lines):

    results = []
    inside_ict = False

    for line_chars, text in lines:

        if "6.1" in text and "Power" in text:
            inside_ict = True
            continue

        if inside_ict and ("Part 7" in text or "7." in text):
            break

        if not inside_ict:
            continue

        txt = re.sub(r"\s+", " ", text)

        m = re.search(r"(PT[0-9]+)", txt)
        if not m:
            continue
        pt = m.group(1)

        nums = re.findall(r"[0-9]+[.,][0-9]+", txt)
        if len(nums) < 2:
            continue

        nums = [float(x.replace(",", ".")) for x in nums]

        if len(nums) >= 3:
            min_v = nums[-2]
            max_v = nums[-1]
        else:
            continue

        results.append({
            "TestPoint": pt,
            "Min": min_v,
            "Max": max_v
        })

    return results


def main():
    if len(sys.argv) != 2:
        print("Usage: python extract_ict_limits.py <pdf>")
        sys.exit(1)

    pdf = sys.argv[1]
    lines = extract_lines(pdf)
    results = extract_ict(lines)

    print("\n=== Résultats ICT : PT | Min | Max ===\n")
    for r in results:
        print(f"{r['TestPoint']} | {r['Min']} | {r['Max']}")

    out = pdf.replace(".pdf", "_ict_limits.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"ICT": results}, f, indent=4, ensure_ascii=False)

    print("\nExtraction terminée :", out)


if __name__ == "__main__":
    main()