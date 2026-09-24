#!/usr/bin/env python3
"""grade.py <run_dir> <eval_id>  -> writes <run_dir>/grading.json"""
import json, os, re, sys

PREEXISTING = {"README.md", "Local LLM モデル・用途.md"}
FORBIDDEN = set(':/\\*?"<>|#^[]')
CALLOUT_RE = re.compile(r"^>\s*\[!([a-zA-Z]+)\][+-]?", re.M)

def find_notes(vault):
    out = []
    for root, dirs, files in os.walk(vault):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if f.endswith(".md") and f not in PREEXISTING:
                out.append(os.path.join(root, f))
    return sorted(out)

def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return m.group(1) if m else None

def common_assertions(vault, notes, expected_subdir):
    text = open(notes[0], encoding="utf-8").read() if notes else ""
    fm = frontmatter(text) if text else None
    rel = os.path.relpath(notes[0], vault) if notes else "(none)"
    name = os.path.basename(notes[0])[:-3] if notes else ""
    top = "\n".join(text.splitlines()[:40])
    callouts = set(c.lower() for c in CALLOUT_RE.findall(text))
    tables = len(re.findall(r"^\|.*\|\s*$\n^\|[\s:\-|]+\|\s*$", text, re.M))
    wikilinks = re.findall(r"\[\[([^\]|#]+)", text)
    A = []
    A.append(("Exactly one new note created inside vault/%s/" % expected_subdir,
              len(notes) == 1 and rel.startswith(expected_subdir + os.sep),
              "new notes: %s" % [os.path.relpath(n, vault) for n in notes]))
    A.append(("Filename has no link-breaking characters (: / \\ * ? \" < > | # ^ [ ])",
              bool(name) and not (set(name) & FORBIDDEN), "filename: %r" % name))
    A.append(("YAML frontmatter present with tags list and created date (YYYY-MM-DD)",
              fm is not None and re.search(r"^tags:", fm, re.M) is not None and re.search(r"^created:\s*\d{4}-\d{2}-\d{2}", fm, re.M) is not None,
              "frontmatter: " + (fm[:200].replace("\n", " | ") if fm else "none")))
    A.append(("Summary callout ([!abstract]/[!summary]/[!tldr]) within first 40 lines",
              re.search(r"^>\s*\[!(abstract|summary|tldr)\]", top, re.M | re.I) is not None,
              "top callouts: %s" % CALLOUT_RE.findall(top)))
    A.append(("At least one Markdown table", tables >= 1, "tables found: %d" % tables))
    A.append(("At least 2 distinct callout types used", len(callouts) >= 2, "callout types: %s" % sorted(callouts)))
    A.append(("At least one [[wikilink]] to another note", len(wikilinks) >= 1, "wikilinks: %s" % wikilinks[:6]))
    A.append(("Has a related-links section heading (関連 / Related)",
              re.search(r"^##+\s*.*(関連|Related|リンク)", text, re.M) is not None,
              "headings: %s" % re.findall(r"^##+\s*(.+)$", text, re.M)[:12]))
    A.append(("No plugin-only syntax (dataview / templater)",
              "```dataview" not in text and "<%" not in text, "checked for ```dataview and <%"))
    return A, text, fm, name

def main():
    run_dir, eval_id = sys.argv[1], int(sys.argv[2])
    vault = os.path.join(run_dir, "outputs", "vault")
    notes = find_notes(vault)
    sub = {0: "Engineering/Frontend", 1: "Books", 2: "Works/IJU"}[eval_id]
    A, text, fm, name = common_assertions(vault, notes, sub)
    if eval_id == 0:
        A.append(("Contains a Mermaid diagram", "```mermaid" in text, "mermaid block present: %s" % ("```mermaid" in text)))
        A.append(("Mentions 'use client' directive", "use client" in text, "'use client' present: %s" % ("use client" in text)))
        A.append(("Has a warning/caution callout for pitfalls", bool(re.search(r"\[!(warning|caution|attention|failure|danger|bug)\]", text, re.I)), "callouts: %s" % sorted(set(CALLOUT_RE.findall(text)))))
    elif eval_id == 1:
        concepts = ["DRY", "直交", "曳光弾", "割れ窓", "契約"]
        missing = [c for c in concepts if c not in text]
        A.append(("Covers all 5 concepts (DRY, 直交性, 曳光弾, 割れ窓, 契約による設計)", not missing, "missing: %s" % missing))
        A.append(("Rating 5/5 recorded (⭐⭐⭐⭐⭐ or 5)", ("⭐⭐⭐⭐⭐" in text) or re.search(r"(評価|rating)[^\n]*5", text, re.I) is not None, "rating markers found"))
        A.append(("Has an action checklist (- [ ])", "- [ ]" in text, "checkbox present: %s" % ("- [ ]" in text)))
        A.append(("Frontmatter has type book or a book tag", fm is not None and (re.search(r"^type:\s*book", fm, re.M) is not None or re.search(r"-\s*book", fm) is not None or "読書" in fm), "fm: " + (fm[:200].replace("\n", " | ") if fm else "none")))
    elif eval_id == 2:
        A.append(("Filename starts with ISO date (YYYY-MM-DD)", re.match(r"^\d{4}-\d{2}-\d{2}", name or "") is not None, "filename: %r" % name))
        A.append(("TODO checklist with owner 田中 and deadline", "- [ ]" in text and "田中" in text and ("金曜" in text or "来週" in text), "checkbox=%s 田中=%s" % ("- [ ]" in text, "田中" in text)))
        A.append(("Carry-over item in a question/todo callout", bool(re.search(r"\[!(question|help|faq|todo|warning)\]", text, re.I)) and "パスワード" in text, "callouts: %s" % sorted(set(CALLOUT_RE.findall(text)))))
        A.append(("Records all decisions: Cognito, 11月, 並行稼働", all(k in text for k in ["Cognito", "11", "並行"]), "keys present: %s" % {k: (k in text) for k in ["Cognito", "11", "並行"]}))
    exp = [{"text": t, "passed": bool(p), "evidence": e} for t, p, e in A]
    passed = sum(1 for x in exp if x["passed"])
    timing = {}
    tp = os.path.join(run_dir, "timing.json")
    if os.path.exists(tp):
        timing = json.load(open(tp))
    out = {"expectations": exp, "summary": {"passed": passed, "failed": len(exp) - passed, "total": len(exp), "pass_rate": round(passed / len(exp), 4)},
           "execution_metrics": {"output_chars": len(text)}}
    json.dump(out, open(os.path.join(run_dir, "grading.json"), "w"), ensure_ascii=False, indent=2)
    print("%s: %d/%d" % (run_dir, passed, len(exp)))

main()
