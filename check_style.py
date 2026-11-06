#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 pages/ 下纳入规范的分页，其 STYLE-BLOCK 是否与 _template.html 逐字节一致。

用法：python check_style.py
退出码：0 = 全部一致（含全部未纳入规范）；1 = 存在 DIFF；2 = 模板缺少定界标记。

没有 STYLE-BLOCK 标记的文件列为 SKIP 并跳过：现有 slide-1..4.html 是旧测试稿，
未纳入样式规范，属预期状态。
"""
import hashlib
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
PAGES = ROOT / 'pages'
TPL = PAGES / '_template.html'
PAT = re.compile(r'<!-- STYLE-BLOCK:BEGIN.*?-->(.*?)<!-- STYLE-BLOCK:END -->', re.S)


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]


def main():
    if not TPL.exists():
        print('错误：找不到模板 %s' % TPL)
        return 2
    m = PAT.search(TPL.read_text(encoding='utf-8'))
    if not m:
        print('错误：模板里找不到 STYLE-BLOCK 定界标记')
        return 2

    want = digest(m.group(1))
    print('模板样式块：', want)

    bad = 0
    for p in sorted(PAGES.glob('*.html')):
        if p.name == TPL.name:
            continue
        hit = PAT.search(p.read_text(encoding='utf-8'))
        if not hit:
            print('SKIP  ', p.name, '(未纳入规范)')
            continue
        got = digest(hit.group(1))
        ok = (got == want)
        print('OK    ' if ok else 'DIFF  ', p.name, got)
        if not ok:
            bad += 1

    if bad:
        print('校验失败：%d 个分页的样式块与模板不一致，请整块同步后重跑' % bad)
        return 1
    print('校验通过：所有纳入规范的分页样式一致')
    return 0


if __name__ == '__main__':
    sys.exit(main())
