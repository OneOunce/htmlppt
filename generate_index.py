#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
扫描 pages/ 与 subtitle.txt，整份生成两个数据文件。**不碰 index.html。**

产物
----
    js/pages.js      const SLIDE_PAGES = [...]; 以及派生出的 slideFiles / slideTitles
    js/subtitle.js   const SUBTITLE_TEXT = "...";

index.html 只用两个 <script src> 引入它们，脚本对 index.html 零写入——
所以 index.html 你怎么改都不会影响构建，也没有"定位失败"这回事。

命名规则
--------
    03-目录.html   → 序号 3，页名「目录」
    5-封面.html    → 序号 5，页名「封面」
    0006.html      → 序号 6，页名取 <title> / <h1>，取不到则为空
    slide-2.html   → 兼容旧命名，序号 2，页名同样取 <title> / <h1>

- 序号是自然数，位数不限：1、01、001、0006 都合法，只按数值比较大小。
  前导零只在文件管理器里做视觉对齐，不参与排序，也不影响显示。
- 排序后显示序号由数组下标决定（1、2、3…），目录中间留空号会自动挤紧。
- 页名缺失时退化为空字符串，缩略图只显示序号，不会留下空标签。
- 无序号的文件（如 template.html）默认忽略并提示，
  需要收录时加 --append-unnumbered，会按文件名排在所有编号页之后。

用法
----
    python generate_index.py              # 生成两个数据文件
    python generate_index.py --dry-run    # 只打印结果，不写文件
    python generate_index.py --check      # 校验两个文件是否已最新（不一致退出码 1）
    python generate_index.py --strict     # 出现重号、无序号文件等歧义时直接失败
    python generate_index.py --no-subtitle  # 只生成 pages.js，不动字幕
"""

from __future__ import print_function

import argparse
import json
import os
import re
import sys
import tempfile

# ---------------------------------------------------------------- 常量

PAGES_DIR = 'pages'
OUTPUT_DIR = 'js'
PAGES_JS = 'pages.js'
SUBTITLE_JS = 'subtitle.js'
SUBTITLE_TXT = 'subtitle.txt'
INDEX_FILE = 'index.html'

PAGE_EXTS = ('.html', '.htm')

# 「序号 + 分隔符 + 页名」：分隔符允许半角/全角横线与下划线，两侧可有空格
SEP = r'[-\uFF0D\u2013\u2014_]'
NUMBERED_RE = re.compile(r'^(?P<num>\d+)\s*(?:' + SEP + r'\s*(?P<name>.*))?$')
# 旧命名：slide-1 / slide_1 / slide1
LEGACY_RE = re.compile(r'^slide[-\s_]*(?P<num>\d+)$', re.IGNORECASE)


# ---------------------------------------------------------------- 基础 IO

def read_text_file(path):
    """读取文本，容忍 BOM 与 Windows 编辑器保存的 GBK 编码。"""
    last_error = None
    for enc in ('utf-8-sig', 'utf-8', 'gbk'):
        try:
            with open(path, 'r', encoding=enc, newline='') as f:
                return f.read()
        except UnicodeDecodeError as e:
            last_error = e
    raise last_error


def read_head(path, limit=65536):
    """只读文件开头一小段，用于找 <title>；读不了就返回空串。"""
    try:
        with open(path, 'rb') as f:
            raw = f.read(limit)
    except OSError:
        return ''
    for enc in ('utf-8-sig', 'utf-8', 'gbk', 'latin-1'):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return ''


def atomic_write(path, text):
    """先写临时文件再替换，避免中途失败留下半截文件。"""
    directory = os.path.dirname(os.path.abspath(path)) or '.'
    if not os.path.isdir(directory):
        os.makedirs(directory)
    fd, tmp = tempfile.mkstemp(prefix='.gen-', suffix='.tmp', dir=directory)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as f:
            f.write(text)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------- 扫描 pages/

def strip_tags(fragment):
    text = re.sub(r'<[^>]*>', ' ', fragment)
    return re.sub(r'\s+', ' ', text.replace('&nbsp;', ' ')).strip()


def guess_title(path):
    """从分页 HTML 里猜页名：<title> 优先，其次第一个 <h1>。"""
    head = read_head(path)
    if not head:
        return ''
    for tag in ('title', 'h1'):
        m = re.search(r'<%s\b[^>]*>(.*?)</%s>' % (tag, tag), head, re.IGNORECASE | re.DOTALL)
        if m:
            text = strip_tags(m.group(1))
            if text:
                return text
    return ''


def parse_page_name(stem):
    """把文件名主干解析成 (序号, 页名)；解析不了返回 None。"""
    m = NUMBERED_RE.match(stem.strip())
    if m:
        return int(m.group('num')), (m.group('name') or '').strip()
    m = LEGACY_RE.match(stem.strip())
    if m:
        return int(m.group('num')), ''      # 旧名没有页名，留给 <title> 兜底
    return None


def scan_pages(pages_dir, append_unnumbered=False, strict=False):
    """扫描目录，返回 (已排序的分页列表, 无序号文件列表, 警告列表)。"""
    if not os.path.isdir(pages_dir):
        raise RuntimeError('找不到目录：%s' % pages_dir)

    numbered = []     # [(num, file, title)]
    unnumbered = []
    warnings = []

    for filename in sorted(os.listdir(pages_dir)):
        path = os.path.join(pages_dir, filename)
        if not os.path.isfile(path):
            continue
        if filename.startswith(('.', '_', '~$')):
            continue                                  # 隐藏文件 / 暂存文件
        stem, ext = os.path.splitext(filename)
        if ext.lower() not in PAGE_EXTS:
            continue
        if stem.lower() in ('index', 'template'):
            unnumbered.append(filename)
            continue

        parsed = parse_page_name(stem)
        if parsed is None:
            unnumbered.append(filename)
            continue

        num, name = parsed
        if not name:
            name = guess_title(path)                  # 页名缺失时用 <title>/<h1> 兜底
        numbered.append((num, filename, name))

    # 按数值排序：1 < 2 < 03 < 0006；同号时按文件名稳定排序
    numbered.sort(key=lambda item: (item[0], item[1]))

    seen = {}
    for num, filename, _ in numbered:
        seen.setdefault(num, []).append(filename)
    for num in sorted(seen):
        if len(seen[num]) > 1:
            warnings.append('序号 %d 重复：%s（按文件名排序，建议改名）'
                            % (num, '、'.join(seen[num])))

    if unnumbered:
        warnings.append('未编号、默认忽略：%s' % '、'.join(unnumbered))
        if append_unnumbered:
            for filename in unnumbered:
                stem = os.path.splitext(filename)[0]
                numbered.append((None, filename,
                                 guess_title(os.path.join(pages_dir, filename)) or stem))

    if strict and warnings:
        raise RuntimeError('存在需要人工处理的命名问题：\n  - ' + '\n  - '.join(warnings))

    return numbered, unnumbered, warnings


# ---------------------------------------------------------------- 生成两个数据文件

PAGES_JS_HEADER = """\
/* 分页清单 —— 由 generate_index.py 整份生成，请勿手改。
   数据来源：pages/ 目录下的文件名（序号-页名.html，序号位数不限、可以有空号）。
   重新生成：python generate_index.py
   排序：按序号的数值升序；显示用的序号是数组下标（1、2、3…），与文件名编号无关。 */
"""

SUBTITLE_JS_HEADER = """\
/* 字幕文本 —— 由 generate_index.py 整份生成，请勿手改。
   数据来源：subtitle.txt（一行一句，空行忽略）。
   重新生成：python generate_index.py */
"""


def render_pages_js(entries):
    lines = [PAGES_JS_HEADER, 'const SLIDE_PAGES = [']
    rows = []
    for entry in entries:
        rows.append('  { "file": %s, "title": %s }' % (
            json.dumps(entry['file'], ensure_ascii=False),
            json.dumps(entry['title'], ensure_ascii=False),
        ))
    if rows:
        lines.append(',\n'.join(rows))
    lines.append('];')
    lines.append('const slideFiles  = SLIDE_PAGES.map(function (p) { return p.file; });')
    lines.append('const slideTitles = SLIDE_PAGES.map(function (p) { return p.title; });')
    return '\n'.join(lines) + '\n'


def render_subtitle_js(text):
    # json.dumps 负责处理引号、反斜杠、换行（\n）等所有转义
    return SUBTITLE_JS_HEADER + 'const SUBTITLE_TEXT = %s;\n' % json.dumps(
        text, ensure_ascii=False)


# ---------------------------------------------------------------- 主流程

def main(argv=None):
    parser = argparse.ArgumentParser(
        description='扫描 pages/ 生成 js/pages.js，扫描 subtitle.txt 生成 js/subtitle.js')
    parser.add_argument('--root', default=None, help='项目根目录，默认脚本所在目录')
    parser.add_argument('--dry-run', action='store_true', help='只打印结果，不写文件')
    parser.add_argument('--check', action='store_true', help='只校验产物是否已最新，不一致退出码 1')
    parser.add_argument('--strict', action='store_true', help='命名有歧义（重号等）时直接失败')
    parser.add_argument('--append-unnumbered', action='store_true', help='把无序号的分页接在末尾')
    parser.add_argument('--no-subtitle', action='store_true', help='只生成 pages.js，不动字幕')
    args = parser.parse_args(argv)

    root = os.path.abspath(args.root or os.path.dirname(os.path.abspath(__file__)))
    pages_dir = os.path.join(root, PAGES_DIR)
    out_dir = os.path.join(root, OUTPUT_DIR)
    subtitle_path = os.path.join(root, SUBTITLE_TXT)

    # ---------- 分页 ----------
    try:
        numbered, unnumbered, warnings = scan_pages(
            pages_dir, args.append_unnumbered, args.strict)
    except RuntimeError as e:
        print('错误：%s' % e, file=sys.stderr)
        return 2

    for msg in warnings:
        print('提示：%s' % msg, file=sys.stderr)

    entries = [{'file': f, 'title': t} for _, f, t in numbered]
    if not entries:
        print('错误：%s 里没有可用的分页文件（需要「序号-页名.html」或 slide-N.html）'
              % pages_dir, file=sys.stderr)
        return 2

    pages_js = render_pages_js(entries)

    # ---------- 字幕 ----------
    subtitle_js = None
    if not args.no_subtitle:
        if not os.path.exists(subtitle_path):
            print('提示：%s 不存在，本次不生成 %s' % (SUBTITLE_TXT, SUBTITLE_JS), file=sys.stderr)
        else:
            raw = read_text_file(subtitle_path).replace('\r\n', '\n').replace('\r', '\n')
            text = '\n'.join(line.strip() for line in raw.split('\n') if line.strip())
            if not text:
                print('提示：%s 为空，本次不生成 %s' % (SUBTITLE_TXT, SUBTITLE_JS), file=sys.stderr)
            else:
                subtitle_js = render_subtitle_js(text)

    # ---------- 计划 ----------
    plan = [(PAGES_JS, os.path.join(out_dir, PAGES_JS), pages_js)]
    if subtitle_js is not None:
        plan.append((SUBTITLE_JS, os.path.join(out_dir, SUBTITLE_JS), subtitle_js))

    stale = []
    for label, path, text in plan:
        old = None
        if os.path.exists(path):
            try:
                old = read_text_file(path)
            except Exception:
                old = None
        if old != text:
            stale.append(label)

    # ---------- 报告 ----------
    print('扫描到 %d 个分页（%s）：' % (len(entries), '空号已挤紧' if _has_gap(numbered) else '连续编号'))
    for i, entry in enumerate(entries, 1):
        print('  %2d. %-24s %s' % (i, entry['file'], entry['title'] or '（无页名）'))

    # index.html 有没有引用这两个文件，只提示不拦截
    index_path = os.path.join(root, INDEX_FILE)
    if os.path.exists(index_path):
        try:
            index_text = read_text_file(index_path)
        except Exception:
            index_text = ''
        for ref in [OUTPUT_DIR + '/' + PAGES_JS, OUTPUT_DIR + '/' + SUBTITLE_JS]:
            if ref not in index_text:
                print('提示：%s 里没有引用 %s' % (INDEX_FILE, ref), file=sys.stderr)

    if args.check:
        if stale:
            print('校验失败：%s 与数据源不一致，请运行 generate_index.py' % '、'.join(stale))
            return 1
        print('校验通过：%s 已是最新' % '、'.join(l for l, _, _ in plan))
        return 0

    if args.dry_run:
        print('将写入：%s（dry-run，未落盘）' % '、'.join(l for l, _, _ in plan))
        return 0

    if not stale:
        print('产物已是最新，无需改动')
        return 0

    try:
        for label, path, text in plan:
            atomic_write(path, text)
    except OSError as e:
        print('错误：写入失败 %s' % e, file=sys.stderr)
        return 2

    print('已写入：%s' % '、'.join(stale))
    print('index.html 未被修改')
    return 0


def _has_gap(numbered):
    nums = [n for n, _, _ in numbered if n is not None]
    return bool(nums) and nums != list(range(nums[0], nums[0] + len(nums)))


if __name__ == '__main__':
    sys.exit(main())
