#!/usr/bin/python

import cgitb
cgitb.enable()

import os
import sys
import glob
import subprocess

sys.path.extend(glob.glob(os.path.expanduser('~/lib/python%d.%d/site-packages/*/' % sys.version_info[:2])))

import djvu.sexpr
import djvu.const

query_string = os.getenv('QUERY_STRING', '')
items = query_string.split('&')
y0 = None
x0 = None
page = 1
for i, item in enumerate(items):
    if item.startswith('l='):
        try:
            y0 = int(item[2:], 10) - 1
        except ValueError:
            pass
    elif item.startswith('w='):
        try:
            x0 = int(item[2:], 10) - 1
        except ValueError:
            pass
    elif item.startswith('p='):
        try:
            page = int(item[2:], 10)
        except ValueError:
            pass
    elif item == 'djvuopts':
        break
else:
    del items[:]
djvuopts = items[i:]
if not djvuopts:
    djvuopts = ['djvuopts']
djvuopts += 'page=%d' % page,
del items

djvu_file_name = 'papers/thesis/thesis.djvu'
djvu_uri = '/~jw209508/' + djvu_file_name
djvu_file_name = '~/public_html/' + djvu_file_name
djvu_file_name = os.path.expanduser(djvu_file_name)

djvused = subprocess.Popen(
    ['djvused', '-e', 'select %d; print-txt' % page, djvu_file_name],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE
)
text = djvu.sexpr.Expression.from_stream(djvused.stdout)

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
        break
uri = '%s?%s' % (djvu_uri, '&'.join(djvuopts))
print 'Status: 303 See Other'
print 'Content-Type: text/plain'
print 'Location: %s' % uri
print
print 'See %s' % uri

# vim:ts=4 sw=4 et
