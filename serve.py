#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PPT 放映本地服务器启动器（跨平台：Windows / Linux 通用）

为什么需要它：
  直接用 file:// 双击打开时，浏览器把本地 iframe 当作跨域，父页面无法读取
  iframe 内部、也无法接收其中的键盘事件（选中分页文字后空格/方向键失效）。
  用本脚本起一个本地 HTTP 服务，让 index.html 与分页同为同源，转发即可正常工作。

用法：
  python serve.py                 # 交互式配置（端口/地址/是否开浏览器）后启动
  python serve.py -p 8080         # 指定端口直接启动
  python serve.py --host 0.0.0.0  # 允许局域网其他设备访问（默认即此）
  python serve.py --no-browser    # 不自动打开浏览器
  python serve.py --list          # 仅列出幻灯片文件后退出

启动后访问终端打印的本机地址即可。Ctrl+C 停止服务。
"""
import argparse
import os
import sys
import socket
import webbrowser
from functools import partial

try:
    from http.server import ThreadingHTTPServer as HTTPServerBase
except ImportError:  # 旧版本 Python 回退
    from http.server import HTTPServer as HTTPServerBase
from http.server import SimpleHTTPRequestHandler

DEFAULT_PORT = 8000
DEFAULT_HOST = '0.0.0.0'


def project_dir():
    """脚本所在目录即放映根目录，保证无论从哪调用都能正确服务。"""
    return os.path.dirname(os.path.abspath(__file__))


def list_slides(directory):
    # 幻灯片位于 pages/ 子目录（index.html 也从 pages/ 加载）
    search = os.path.join(directory, 'pages') if os.path.isdir(
        os.path.join(directory, 'pages')) else directory
    return sorted(
        f for f in os.listdir(search)
        if f.lower().endswith(('.html', '.htm'))
        and not f.startswith(('_', '.'))
        and f.lower() not in ('index.html', 'template.html')
    )


def input_with_default(prompt, default):
    try:
        val = input("%s [%s]: " % (prompt, default)).strip()
    except EOFError:
        val = ''
    return val or default


def port_available(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('127.0.0.1' if host == '0.0.0.0' else host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    except Exception:
        return None
    finally:
        s.close()


def main():
    parser = argparse.ArgumentParser(
        description='PPT 放映本地服务器（跨平台 Windows/Linux）')
    parser.add_argument('-p', '--port', type=int, default=None, help='监听端口')
    parser.add_argument('-H', '--host', default=None,
                        help='绑定地址（默认 %s=全部网卡）' % DEFAULT_HOST)
    parser.add_argument('-d', '--directory', default=None,
                        help='服务目录（默认脚本所在目录）')
    parser.add_argument('--no-browser', action='store_true',
                        help='不自动打开浏览器')
    parser.add_argument('--list', action='store_true',
                        help='仅列出幻灯片文件后退出')
    parser.add_argument('-i', '--interactive', action='store_true',
                        help='强制交互式配置')
    args = parser.parse_args()

    directory = args.directory or project_dir()

    if args.list:
        slides = list_slides(directory)
        if slides:
            print('发现幻灯片文件：')
            for s in slides:
                print('   ', s)
        else:
            print('未在', directory, '的 pages/ 中发现幻灯片 HTML')
        return

    # 未通过参数提供关键项且处于交互终端时，进入交互式配置
    interactive = args.interactive or (
        args.port is None and args.host is None and sys.stdin.isatty()
    )
    if interactive:
        print('=== PPT 本地放映服务配置 ===')
        port = input_with_default('监听端口', args.port or DEFAULT_PORT)
        host = input_with_default('绑定地址 (0.0.0.0=全部网卡)',
                                  args.host or DEFAULT_HOST)
        ob = input_with_default('是否自动打开浏览器 (y/n)',
                                'n' if args.no_browser else 'y')
        args.no_browser = ob.lower() not in ('y', 'yes', '是', '1', 'true')
        try:
            args.port = int(port)
        except ValueError:
            args.port = DEFAULT_PORT
        args.host = host
    else:
        args.port = args.port or DEFAULT_PORT
        args.host = args.host or DEFAULT_HOST

    # 端口被占用时自动顺延
    while not port_available(args.host, args.port):
        print('端口 %d 被占用，尝试 %d ...' % (args.port, args.port + 1))
        args.port += 1

    handler = partial(SimpleHTTPRequestHandler, directory=directory)
    try:
        httpd = HTTPServerBase((args.host, args.port), handler)
    except OSError as e:
        print('无法绑定 %s:%d —— %s' % (args.host, args.port, e))
        sys.exit(1)

    local_url = 'http://127.0.0.1:%d/' % args.port
    print('放映服务已启动：')
    print('  本机访问：', local_url)
    if args.host == '0.0.0.0':
        ip = lan_ip()
        if ip:
            print('  局域网访问：', 'http://%s:%d/' % (ip, args.port))
    print('按 Ctrl+C 停止服务')

    if not args.no_browser:
        try:
            webbrowser.open(local_url)
        except Exception:
            pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\n服务已停止。')
        httpd.shutdown()


if __name__ == '__main__':
    main()
