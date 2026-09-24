#!/usr/bin/env python3
"""Claude のアーティファクト HTML を Obsidian ボルトに保存する。

同じアーティファクトを何度保存しても増殖しないことを重視している。
アーティファクトは公開後に更新されることが多く、素朴に書き出すと
「名前 (2).html」が積み上がってボルトが汚れるため、
先頭に埋め込む出所コメントと内容ハッシュで同一性を判定して上書きする。
"""

import argparse
import datetime
import hashlib
import html
import os
import re
import shutil
import sys

DEFAULT_VAULT = os.path.expanduser("~/Obsidian/Knowledge")
DEFAULT_DIR = "AI/Artifacts"

# Obsidian のリンクを壊す文字を全角に寄せる (obsidian スキルと同じ規則)
_FILENAME_MAP = {
    "/": "／", "\\": "＼", ":": "：", "*": "＊", "?": "？", '"': "”",
    "<": "＜", ">": "＞", "|": "｜", "#": "＃", "^": "＾", "[": "［", "]": "］",
}

STAMP_RE = re.compile(r"<!--\s*claude-artifact\b[^>]*-->\s*", re.I)
STAMP_SOURCE_RE = re.compile(r'<!--\s*claude-artifact\b[^>]*?source="([^"]*)"', re.I)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)


def sanitize_filename(title):
    name = "".join(_FILENAME_MAP.get(ch, ch) for ch in title)
    name = re.sub(r"\s+", " ", name).strip().strip(".")
    return name or "untitled"


def extract_title(text):
    m = TITLE_RE.search(text)
    if not m:
        return None
    t = html.unescape(re.sub(r"<[^>]+>", "", m.group(1)))
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def normalize_url(url):
    """共有トークン (?sk=...) を落として正規 URL だけ残す。

    ボルトが同期・共有される可能性があるので、閲覧権限を与えてしまう
    クエリ文字列をファイルに焼き込まない。
    """
    if not url:
        return None
    return url.split("?", 1)[0].split("#", 1)[0].rstrip("/") or None


def strip_stamp(text):
    return STAMP_RE.sub("", text, count=1)


def body_hash(text):
    return hashlib.sha256(strip_stamp(text).encode("utf-8", "replace")).hexdigest()


def stamp_of(text):
    m = STAMP_SOURCE_RE.search(text)
    return m.group(1) if m else None


def add_stamp(text, source_url, today):
    text = strip_stamp(text)
    bits = ['<!-- claude-artifact']
    if source_url:
        bits.append('source="%s"' % source_url)
    bits.append('saved="%s" -->' % today)
    return " ".join(bits) + "\n" + text


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def scan_existing(dirpath):
    """保存先にある .html を読み、出所 URL と内容ハッシュを引けるようにする。"""
    out = []
    if not os.path.isdir(dirpath):
        return out
    for entry in sorted(os.listdir(dirpath)):
        full = os.path.join(dirpath, entry)
        page = full
        if os.path.isdir(full):
            page = os.path.join(full, "index.html")
            if not os.path.isfile(page):
                continue
        elif not entry.lower().endswith(".html"):
            continue
        try:
            text = read_text(page)
        except OSError:
            continue
        out.append({"entry": full, "page": page, "source": stamp_of(text), "hash": body_hash(text)})
    return out


def unique_path(path):
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    n = 2
    while os.path.exists("%s (%d)%s" % (base, n, ext)):
        n += 1
    return "%s (%d)%s" % (base, n, ext)


def resolve_dir(vault, target):
    vault = os.path.abspath(os.path.expanduser(vault))
    target = os.path.expanduser(target or "")
    if not target:
        return vault
    if os.path.isabs(target):
        return os.path.abspath(target)
    return os.path.abspath(os.path.join(vault, target))


def safe_rel(rel):
    rel = rel.replace("\\", "/").lstrip("/")
    parts = [p for p in rel.split("/") if p not in ("", ".", "..")]
    if not parts:
        raise ValueError("公開パスが空か不正: %r" % rel)
    return os.path.join(*parts)


def report(lines):
    for line in lines:
        print(line)


def cmd_save(args):
    today = datetime.date.today().isoformat()
    source_url = normalize_url(args.source_url)
    dirpath = resolve_dir(args.vault, args.dir)

    if not os.path.isfile(args.html):
        sys.exit("HTML が見つかりません: %s" % args.html)
    text = read_text(args.html)

    title = args.title or extract_title(text) or os.path.splitext(os.path.basename(args.html))[0]
    name = sanitize_filename(title)

    extras = []
    for spec in args.extra_file or []:
        if "=" not in spec:
            sys.exit("--extra-file は published/path=local/path の形式で渡してください: %s" % spec)
        pub, local = spec.split("=", 1)
        if not os.path.isfile(local):
            sys.exit("--extra-file のローカルファイルが見つかりません: %s" % local)
        extras.append((safe_rel(pub), local))

    new_text = text if args.no_stamp else add_stamp(text, source_url, today)
    new_hash = body_hash(new_text)

    existing = scan_existing(dirpath)
    by_source = [e for e in existing if source_url and e["source"] == source_url]
    by_hash = [e for e in existing if e["hash"] == new_hash]

    # 1) 同じアーティファクト由来のファイルがある → 名前を尊重して中身だけ更新
    target_page = None
    mode = "created"
    if len(by_source) > 1:
        report(["warning\t同じ出所の保存が %d 件あります。整理が必要かもしれません:" % len(by_source)]
               + ["  - %s" % e["entry"] for e in by_source])
    if by_source:
        hit = by_source[0]
        target_page = hit["page"]
        mode = "updated"
        # 改名は明示的な指示なので、内容が同じでも先に実行する
        if args.rename:
            cur_entry = hit["entry"]
            as_dir = os.path.isdir(cur_entry)
            wanted_entry = os.path.join(dirpath, name if as_dir else name + ".html")
            if os.path.abspath(wanted_entry) != os.path.abspath(cur_entry):
                if os.path.exists(wanted_entry):
                    # 既存ファイルの削除は取り返しがつかないので改名は行わない
                    report(["rename-skipped\t%s" % wanted_entry,
                            "改名先が既に存在するため改名しませんでした。手動で整理してください。"])
                else:
                    if not args.dry_run:
                        os.replace(cur_entry, wanted_entry)
                    target_page = os.path.join(wanted_entry, "index.html") if as_dir else wanted_entry
                    mode = "renamed"
        if hit["hash"] == new_hash and not args.force and mode != "renamed":
            report(["unchanged\t%s" % target_page,
                    "同じ内容で既に保存されています。書き込みはしていません。"])
            return
    # 2) 出所は不明だが内容が一致するファイルがある → 重複保存しない
    elif by_hash and not args.force:
        hit = by_hash[0]
        report(["duplicate\t%s" % hit["page"],
                "同じ内容のファイルが別名で既に存在します。重複保存を避けました。",
                "出所コメントを埋め込みたい場合は --force を付けて再実行してください。"])
        return

    if target_page is None:
        if extras:
            folder = os.path.join(dirpath, name)
            if os.path.exists(folder) and not args.force:
                folder = unique_path(folder)
            target_page = os.path.join(folder, "index.html")
        else:
            cand = os.path.join(dirpath, name + ".html")
            if os.path.exists(cand) and not args.force:
                cand = unique_path(cand)
                mode = "created (連番)"
            target_page = cand

    written = [target_page]
    if args.dry_run:
        report(["dry-run\t%s" % target_page, "mode=%s" % mode])
        for pub, _ in extras:
            report(["dry-run\t%s" % os.path.join(os.path.dirname(target_page), pub)])
        return

    os.makedirs(os.path.dirname(target_page), exist_ok=True)
    with open(target_page, "w", encoding="utf-8") as fh:
        fh.write(new_text)
    for pub, local in extras:
        dest = os.path.join(os.path.dirname(target_page), pub)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(local, dest)
        written.append(dest)

    report(["%s\t%s" % (mode, target_page)])
    for extra in written[1:]:
        report(["  + %s" % extra])
    if source_url:
        report(["source\t%s" % source_url])


def cmd_list(args):
    dirpath = resolve_dir(args.vault, args.dir)
    rows = scan_existing(dirpath)
    print("dir: %s" % dirpath)
    if not rows:
        print("(アーティファクトはまだありません)")
        return
    for row in rows:
        rel = os.path.relpath(row["entry"], dirpath)
        print("- %s%s" % (rel, "  <- %s" % row["source"] if row["source"] else ""))


def main(argv=None):
    p = argparse.ArgumentParser(description="アーティファクト HTML を Obsidian ボルトに保存する")
    p.add_argument("--vault", default=DEFAULT_VAULT, help="ボルトのルート (既定: %s)" % DEFAULT_VAULT)
    p.add_argument("--dir", default=DEFAULT_DIR, help="保存先 (既定: %s)" % DEFAULT_DIR)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("save", help="HTML を保存する")
    s.add_argument("--html", required=True, help="保存する HTML のローカルパス")
    s.add_argument("--title", help="ファイル名にする名詞句 (省略時は <title>)")
    s.add_argument("--source-url", help="元アーティファクトの URL (共有トークンは自動で除去)")
    s.add_argument("--extra-file", action="append", metavar="PUB=LOCAL",
                   help="複数ファイル構成の場合の追加ファイル (繰り返し可)")
    s.add_argument("--no-stamp", action="store_true", help="出所コメントを埋め込まない")
    s.add_argument("--rename", action="store_true", help="同じ出所のファイルを --title の名前に改名する")
    s.add_argument("--force", action="store_true", help="既存ファイルを無条件に上書きする")
    s.add_argument("--dry-run", action="store_true", help="書き込まず結果だけ表示する")
    s.add_argument("--vault", dest="vault", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    s.add_argument("--dir", dest="dir", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    s.set_defaults(func=cmd_save)

    l = sub.add_parser("list", help="保存済みアーティファクトを一覧する")
    l.add_argument("--vault", dest="vault", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    l.add_argument("--dir", dest="dir", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    l.set_defaults(func=cmd_list)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    main()
