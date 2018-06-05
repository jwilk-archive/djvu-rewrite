#!/usr/bin/python

from __future__ import print_function

import cgitb
cgitb.enable()

import cgi
import getpass
import os
import re
import subprocess
import sys
import urllib

import jinja2

user = getpass.getuser()

DJVU_BASE_LOCAL_DIR = os.path.expanduser('~/public_html/')
DJVU_BASE_URI = '/~{user}/'.format(user=user)
DJVU_FILES = {
    # 'path/to/djvu/file.djvu': 'Document title',
    # ...
}
HTML_TEMPLATE = os.path.join(sys.path[0], 'rewrite-template.html')

import djvu.sexpr
import djvu.const

class NothingToRewrite(Exception):
    pass

class DjVuSedError(Exception):
    def __init__(self, message):
        if message.startswith('*** '):
            message = message[4:]
        Exception.__init__(self, message)

class SilentUndefined(jinja2.Undefined):
    def _fail_with_undefined_error(self, *args, **kwargs):
        return ''

with open(HTML_TEMPLATE, 'rt') as file:
    html_template = jinja2.Template(file.read(), autoescape=True, undefined=SilentUndefined)

def get_text(djvu_file_name, page):
    djvused = subprocess.Popen(
        ['djvused', '-e', 'select %s; print-txt' % page, djvu_file_name],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        return djvu.sexpr.Expression.from_stream(djvused.stdout)
    except:
        rc = djvused.wait()
        if rc != 0:
            raise DjVuSedError(djvused.stderr.readline().strip())

def get_subexprs(text, type):
    if not isinstance(text, djvu.sexpr.ListExpression):
        return
    if len(text) < 5:
        return
    if text[0].value == type:
        yield text
    else:
        for subtext in text[5:]:
            for line in get_subexprs(subtext, type):
                yield line

def get_lines(text):
    return get_subexprs(text, djvu.const.TEXT_ZONE_LINE)

def get_words(text):
    return get_subexprs(text, djvu.const.TEXT_ZONE_WORD)

is_valid_page_id = re.compile('^[a-zA-Z_+.-]+$').match

query_string = os.getenv('QUERY_STRING', '')
djvu_file_name = None
try:
    items = query_string.split('&')
    y0 = None
    x0 = None
    page = 1
    for i, item in enumerate(items):
        if item.startswith('l='):
            try:
                y0 = int(item[2:], 10) - 1
            except ValueError:
                raise ValueError('Invalid line number')
        elif item.startswith('w='):
            try:
                x0 = int(item[2:], 10) - 1
            except ValueError:
                raise ValueError('Invalid word number')
        elif item.startswith('p='):
            page = item[2:]
            if is_valid_page_id(page):
                raise ValueError('Invalid page identifier')
        elif item.startswith('f='):
            djvu_file_name = urllib.unquote(item[2:]).decode('UTF-8', 'replace')
        elif item == 'djvuopts':
            break
    else:
        del items[:]
    djvuopts = items[i:]
    if not djvuopts:
        djvuopts = ['djvuopts']
    djvuopts += 'page=%s' % page,
    del items

    if y0 is None or x0 is None or djvu_file_name is None:
        raise NothingToRewrite
    if djvu_file_name not in DJVU_FILES:
        raise ValueError('Invalid DjVu file name')
    djvu_uri = urllib.basejoin(DJVU_BASE_URI, djvu_file_name)
    djvu_file_name = os.path.join(DJVU_BASE_LOCAL_DIR, djvu_file_name)

    text = get_text(djvu_file_name, page)
    if y0 is not None and x0 is not None:
        for y, line in enumerate(get_lines(text)):
            if y != y0:
                continue
            for x, word in enumerate(get_words(line)):
                if x != x0:
                    continue
                x0, y0, x1, y1 = [int(word[i].value) for i in xrange(1, 5)]
                h = y1 - y0
                w = x1 - x0
                djvuopts += 'highlight=%d,%d,%d,%d' % (x0, y0, w, h),
                break
            else:
                raise IndexError('Word number out of range')
            break
        else:
            raise IndexError('Line number out of range')
    uri = '%s?%s' % (djvu_uri, '&'.join(djvuopts))
except Exception as exception:
    if isinstance(exception, NothingToRewrite):
        exception = None
    context = dict(exception=exception, files=DJVU_FILES, fields=cgi.FieldStorage())
    content = html_template.render(**context).encode('UTF-8')
    print('Content-Type: text/html; charset=UTF-8')
    print()
    print(content)
else:
    print('Status: 303 See Other')
    print('Content-Type: text/plain')
    print('Location: %s' % uri)
    print()
    print('See %s' % uri)

# vim:ts=4 sts=4 sw=4 et
