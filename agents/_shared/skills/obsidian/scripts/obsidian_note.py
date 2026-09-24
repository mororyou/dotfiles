#!/usr/bin/env python3
"""Obsidian ノート作成ヘルパー (Python 3.9+, 標準ライブラリのみ)

サブコマンド:
  tree    ボルトのフォルダ構成と既存ノート (title / tags) を一覧する
  create  frontmatter 付きノートを作成 / 追記 / 上書きする

例:
  python3 obsidian_note.py tree
  python3 obsidian_note.py create --title "Qwen3.5 ローカル運用" --dir AI \
      --type knowledge --tags ai llm --body-file body.md
"""
import argparse
import datetime as _dt
import os
import re
import sys

DEFAULT_VAULT = os.path.expanduser("~/Obsidian/Knowledge")
SKIP_DIRS = {".obsidian", ".trash", ".git", ".DS_Store"}
STATUS_EMOJI = {"draft": "🌱 draft", "growing": "🌿 growing", "evergreen": "🌳 evergreen"}

# Obsidian でファイル名 / wikilink を壊す文字 → 置換
_FILENAME_MAP = {
    "/": "／", "\\": "＼", ":": "：", "*": "＊", "?": "？", '"': "”",
    "<": "＜", ">": "＞", "|": "｜", "#": "＃", "^": "＾", "[": "［", "]": "］",
}


def sanitize_filename(title):
    name = "".join(_FILENAME_MAP.get(ch, ch) for ch in title)
    name = re.sub(r"\s+", " ", name).strip().strip(".")
    return name or "untitled"


def resolve_dir(vault, target):
    vault = os.path.abspath(os.path.expanduser(vault))
    if not target:
        return vault
    target = os.path.expanduser(target)
    if os.path.isabs(target):
        return os.path.abspath(target)
    return os.path.abspath(os.path.join(vault, target))


def yaml_scalar(value):
    """簡易 YAML スカラー。日付や数字っぽい文字列・特殊文字はクオートする。"""
    s = str(value)
    if s == "":
        return '""'
    if re.fullmatch(r"-?\d+(\.\d+)?", s):
        return s  # 数値はそのまま
    needs_quote = (
        re.match(r"^[\d\-:\s./]+$", s) is not None and not re.match(r"^\d{4}-\d{2}-\d{2}$", s)
    ) or any(c in s for c in ":#{}[],&*!|>'\"%@`") or s.strip() != s or s.lower() in {"true", "false", "null", "yes", "no"}
    if needs_quote:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def build_frontmatter(title, note_type, status, tags, aliases, source, created, updated, extra):
    lines = ["---", "title: " + yaml_scalar(title)]
    if note_type:
        lines.append("type: " + yaml_scalar(note_type))
    if status:
        lines.append("status: " + yaml_scalar(STATUS_EMOJI.get(status, status)))
    lines.append("created: " + created)
    lines.append("updated: " + updated)
    lines.append("tags:")
    for t in tags or []:
        lines.append("  - " + yaml_scalar(t.lstrip("#")))
    if aliases:
        lines.append("aliases:")
        for a in aliases:
            lines.append("  - " + yaml_scalar(a))
    if source:
        lines.append("source: " + yaml_scalar(source))
    for kv in extra or []:
        if "=" not in kv:
            raise SystemExit("--extra は key=value 形式で指定してください: %r" % kv)
        k, v = kv.split("=", 1)
        lines.append("%s: %s" % (k.strip(), yaml_scalar(v.strip())))
    lines.append("---")
    return "\n".join(lines) + "\n"


def read_body(args):
    if args.body_file:
        with open(args.body_file, encoding="utf-8") as f:
            body = f.read()
    elif args.body is not None:
        body = args.body
    elif not sys.stdin.isatty():
        body = sys.stdin.read()
    else:
        raise SystemExit("本文を --body-file / --body / 標準入力のいずれかで渡してください")
    # 本文側に frontmatter が付いていたら剥がす (二重化防止)
    if body.lstrip().startswith("---"):
        m = re.match(r"^\s*---\n.*?\n---\n", body, re.S)
        if m:
            body = body[m.end():]
    return body.strip("\n") + "\n"


def unique_path(path):
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    n = 2
    while os.path.exists("%s (%d)%s" % (base, n, ext)):
        n += 1
    return "%s (%d)%s" % (base, n, ext)


def bump_updated(text, today):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return text
    fm = m.group(1)
    if re.search(r"^updated:.*$", fm, re.M):
        fm = re.sub(r"^updated:.*$", "updated: " + today, fm, flags=re.M)
    else:
        fm += "\nupdated: " + today
    return "---\n" + fm + "\n---\n" + text[m.end():]


def cmd_create(args):
    today = _dt.date.today().isoformat()
    target_dir = resolve_dir(args.vault, args.dir)
    filename = sanitize_filename(args.title) + ".md"
    path = os.path.join(target_dir, filename)
    body = read_body(args)

    if os.path.exists(path) and args.append:
        with open(path, encoding="utf-8") as f:
            existing = f.read()
        heading = args.append_heading or ("## 📝 追記 (%s)" % today)
        new_text = bump_updated(existing, today).rstrip("\n") + "\n\n---\n\n" + heading + "\n\n" + body
        mode = "append"
    else:
        if os.path.exists(path) and not args.force:
            path = unique_path(path)
        fm = build_frontmatter(
            title=args.title, note_type=args.type, status=args.status, tags=args.tags,
            aliases=args.aliases, source=args.source, created=today, updated=today, extra=args.extra,
        )
        new_text = fm + "\n" + body
        mode = "overwrite" if args.force and os.path.exists(path) else "create"

    if args.dry_run:
        print("# [dry-run] %s -> %s\n" % (mode, path))
        print(new_text)
        return

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_text)
    print("%s\t%s" % (mode, path))


def parse_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    info = {"title": None, "tags": []}
    if not m:
        return info
    fm = m.group(1)
    t = re.search(r"^title:\s*(.+)$", fm, re.M)
    if t:
        info["title"] = t.group(1).strip().strip('"').strip("'")
    tags_block = re.search(r"^tags:\s*(\[.*?\]|\n(?:\s+-\s*.+\n?)+)", fm, re.M | re.S)
    if tags_block:
        raw = tags_block.group(1)
        if raw.startswith("["):
            info["tags"] = [x.strip().strip('"\'') for x in raw.strip("[]").split(",") if x.strip()]
        else:
            info["tags"] = [x.strip().lstrip("-").strip().strip('"\'') for x in raw.strip().splitlines()]
    return info


def cmd_tree(args):
    vault = os.path.abspath(os.path.expanduser(args.vault))
    if not os.path.isdir(vault):
        raise SystemExit("ボルトが見つかりません: %s" % vault)
    print("vault: %s\n" % vault)
    for root, dirs, files in os.walk(vault):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        rel = os.path.relpath(root, vault)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        indent = "  " * depth
        if rel != ".":
            print("%s📁 %s/" % ("  " * (depth - 1), os.path.basename(root)))
        for fn in sorted(files):
            if not fn.endswith(".md"):
                continue
            fp = os.path.join(root, fn)
            try:
                with open(fp, encoding="utf-8") as f:
                    head = f.read(4000)
            except OSError:
                head = ""
            info = parse_frontmatter(head)
            name = fn[:-3]
            extra = []
            if info["title"] and info["title"] != name:
                extra.append("title=%s" % info["title"])
            if info["tags"]:
                extra.append("tags=" + ",".join(info["tags"]))
            print("%s📄 %s%s" % (indent, name, ("  (" + "; ".join(extra) + ")") if extra else ""))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--vault", default=DEFAULT_VAULT, help="ボルトのルート (既定: %s)" % DEFAULT_VAULT)
    sub = p.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("tree", help="フォルダと既存ノートを一覧")
    t.add_argument("--vault", dest="vault_sub", default=None, help=argparse.SUPPRESS)
    t.set_defaults(func=cmd_tree)

    c = sub.add_parser("create", help="ノートを作成 / 追記")
    c.add_argument("--vault", dest="vault_sub", default=None, help="ボルトのルート (グローバル --vault と同じ)")
    c.add_argument("--title", required=True, help="ノートのタイトル (= ファイル名)")
    c.add_argument("--dir", default="", help="作成先。ボルト内相対パス or 絶対パス。省略時はボルト直下")
    c.add_argument("--type", dest="type", default=None, help="knowledge / howto / book / event / work / decision など")
    c.add_argument("--status", choices=list(STATUS_EMOJI.keys()), default=None)
    c.add_argument("--tags", nargs="*", default=[], help="タグ (複数可、# 不要)")
    c.add_argument("--aliases", nargs="*", default=[], help="別名 (複数可)")
    c.add_argument("--source", default=None, help="出典 URL / 書籍名など")
    c.add_argument("--extra", nargs="*", default=[], help="追加プロパティ key=value (複数可)")
    g = c.add_mutually_exclusive_group()
    g.add_argument("--body-file", help="本文 Markdown ファイル (frontmatter 不要)")
    g.add_argument("--body", help="本文を直接文字列で渡す")
    c.add_argument("--append", action="store_true", help="同名ノートがあれば末尾に追記")
    c.add_argument("--append-heading", default=None, help="追記時の区切り見出し (既定: '## 📝 追記 (日付)')")
    c.add_argument("--force", action="store_true", help="同名ノートを上書き")
    c.add_argument("--dry-run", action="store_true", help="書き込まず出力のみ")
    c.set_defaults(func=cmd_create)

    args = p.parse_args(argv)
    if getattr(args, "vault_sub", None):
        args.vault = args.vault_sub
    args.func(args)


if __name__ == "__main__":
    main()
