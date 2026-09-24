#!/usr/bin/env python3
"""artifact-copy の評価結果を機械的に採点する。

各 eval のボルトを走査して assertion を検証し、grading.json を書き出す。
目で見て判定するとブレるので、判定可能なものはすべてここで確定させる。
"""
import json
import os
import re
import sys

IT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "iteration-1")
STAMP_RE = re.compile(r"<!--\s*claude-artifact\b[^>]*-->", re.I)
REF_RE = re.compile(r'(?:href|src)="([^"#:]+)"')


def art_dir(run):
    return os.path.join(run, "vault", "AI", "Artifacts")


def walk(root, ext=None):
    hits = []
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if ext is None or f.lower().endswith(ext):
                hits.append(os.path.join(dirpath, f))
    return sorted(hits)


def read(p):
    with open(p, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def ck(text, passed, evidence):
    return {"text": text, "passed": bool(passed), "evidence": evidence}


def grade_eval0(run):
    d = art_dir(run)
    htmls = walk(d, ".html")
    names = [os.path.splitext(os.path.basename(h))[0] for h in htmls]
    body = "\n".join(read(h) for h in htmls) if htmls else ""
    searchable = any(("terraform" in n.lower()) or ("モジュール" in n) for n in names)
    return [
        ck("AI/Artifacts 配下に HTML が 1 件保存されている", len(htmls) == 1,
           "見つかった HTML: %s" % (names or "なし")),
        ck("ファイル名が <title> の標語そのままになっていない",
           bool(names) and "小さく始めて、大きく育てる" not in names,
           "ファイル名: %s" % (names or "なし")),
        ck("ファイル名が内容 (Terraform のモジュール分割) を表す名詞句になっている", searchable,
           "ファイル名: %s" % (names or "なし")),
        ck("出所コメントが埋め込まれている", bool(STAMP_RE.search(body)),
           (STAMP_RE.search(body).group(0) if STAMP_RE.search(body) else "出所コメントなし")),
        ck("元 HTML の本文が保持されている", "tfstate" in body,
           "tfstate の記述: %s" % ("あり" if "tfstate" in body else "なし")),
    ]


def grade_eval1(run):
    d = art_dir(run)
    files = walk(d)
    rel = [os.path.relpath(f, d) for f in files]
    idx = [f for f in files if os.path.basename(f).lower() == "index.html"]
    css = [f for f in files if os.path.basename(f) == "style.css"]
    js = [f for f in files if os.path.basename(f) == "app.js"]
    same_dir = bool(idx and css and os.path.dirname(idx[0]) == os.path.dirname(css[0]))
    # 直下に散らばっていない = index.html が AI/Artifacts 直下ではなく 1 段下にある
    foldered = bool(idx and os.path.dirname(idx[0]) != d)
    # index.html の相対参照がすべて解決するか
    broken = []
    if idx:
        base = os.path.dirname(idx[0])
        for ref in REF_RE.findall(read(idx[0])):
            if ref.startswith(("http", "//", "data:")):
                continue
            if not os.path.exists(os.path.join(base, ref)):
                broken.append(ref)
    return [
        ck("index.html が保存されている", bool(idx), "保存物: %s" % (rel or "なし")),
        ck("style.css が index.html と同じ階層に保存されている", same_dir,
           "index: %s / css: %s" % (rel[files.index(idx[0])] if idx else "なし",
                                    rel[files.index(css[0])] if css else "なし")),
        ck("app.js が保存されている", bool(js),
           rel[files.index(js[0])] if js else "なし"),
        ck("3 ファイルが 1 つのフォルダにまとまっている", foldered and len(files) >= 3,
           "保存物 %d 件: %s" % (len(files), rel)),
        ck("index.html の相対参照が保存後も解決する", bool(idx) and not broken,
           "解決できない参照: %s" % (broken or "なし")),
    ]


def grade_eval2(run):
    d = art_dir(run)
    top = [f for f in os.listdir(d) if f.lower().endswith(".html")] if os.path.isdir(d) else []
    all_html = walk(d, ".html")
    keep = "Terraform モジュール分割ガイド.html"
    body = "\n".join(read(h) for h in all_html) if all_html else ""
    return [
        ck("AI/Artifacts 直下の HTML が 1 件のまま (連番が増えていない)", len(top) == 1,
           "直下の HTML: %s" % (sorted(top) or "なし")),
        ck("既存の「%s」という名前が維持されている" % keep, keep in top,
           "直下の HTML: %s" % (sorted(top) or "なし")),
        ck("保存後の内容に更新分の見出し「バージョン固定」が含まれている", "バージョン固定" in body,
           "更新分の反映: %s" % ("あり" if "バージョン固定" in body else "なし")),
        ck("タイトル由来の「小さく始めて、大きく育てる.html」が新規作成されていない",
           "小さく始めて、大きく育てる.html" not in top,
           "直下の HTML: %s" % (sorted(top) or "なし")),
    ]


GRADERS = {
    "eval-0-slogan-title-to-searchable-filename": grade_eval0,
    "eval-1-multi-file-artifact": grade_eval1,
    "eval-2-update-preserves-user-filename": grade_eval2,
}


def main():
    summary = []
    for name, fn in GRADERS.items():
        for cfg in ("with_skill", "without_skill"):
            run = os.path.join(IT, name, cfg)
            if not os.path.isdir(run):
                continue
            try:
                exps = fn(run)
            except Exception as exc:  # 採点自体が落ちても全体を止めない
                exps = [ck("採点が完了した", False, "採点中に例外: %r" % (exc,))]
            passed = sum(1 for e in exps if e["passed"])
            out = {"eval_name": name, "configuration": cfg,
                   "passed": passed, "total": len(exps), "expectations": exps}
            with open(os.path.join(run, "grading.json"), "w", encoding="utf-8") as fh:
                json.dump(out, fh, ensure_ascii=False, indent=2)
            summary.append(out)

    print("%-46s %-14s %s" % ("eval", "config", "pass"))
    print("-" * 74)
    for s in summary:
        print("%-46s %-14s %d/%d" % (s["eval_name"][:46], s["configuration"], s["passed"], s["total"]))
    print()
    for s in summary:
        fails = [e for e in s["expectations"] if not e["passed"]]
        if fails:
            print("[%s / %s] 失敗した観点:" % (s["eval_name"], s["configuration"]))
            for f in fails:
                print("  x %s\n    -> %s" % (f["text"], f["evidence"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
