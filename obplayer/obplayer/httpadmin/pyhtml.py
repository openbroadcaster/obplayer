#!/usr/bin/python3
# -*- coding: utf-8 -*-

import obplayer

import os
import sys
import time
import traceback

import io
import re

import cgi
import json
import mimetypes

if sys.version.startswith('3'):
    from urllib.parse import quote, unquote
    unicode = str
else:
    from urllib import quote, unquote


class PyHTML (object):
    version = '0.3'

    def __init__(self, request=None, data=None, filename=None, code=None):
        self._mimetype = None
        self._encoding = 'utf-8'
        self._contents = ''
        self._segments = [ ]
        self._pycode = ''
        self._output = io.StringIO()

        self.FILENAME = filename
        self.REQUEST = request
        self.PATH = request.url.path if request else ''

        if data is None:
            data = { }
        self._data = data
        self._init_globals()

        if code is not None:
            self._contents = code
        elif filename is not None:
            self._contents = self._read_contents(filename)

    def ARGS(self, name, default='', as_array=False):
        if not self.REQUEST or name not in self.REQUEST.args:
            return default
        if as_array is False:
            return self.REQUEST.args[name][0]
        else:
            return self.REQUEST.args[name]

    def GET(self, name, default='', as_array=False):
        if not self.REQUEST or self.REQUEST.reqtype != "GET":
            return default
        return self.ARGS(name, default, as_array)

    def POST(self, name, default='', as_array=False):
        if not self.REQUEST or self.REQUEST.reqtype != "POST":
            return default
        return self.ARGS(name, default, as_array)

    def DATA(self, name, default=''):
        if name not in self._data:
            return default
        return self._data[name]

    def _init_globals(self):
        self._globals = self._data.copy()
        self._globals['py'] = self
        self._globals['obplayer'] = obplayer
        self._globals['unicode'] = unicode
        self._globals['print'] = self.write
        self._globals['t'] = self.translate

        self._globals['sys'] = sys
        self._globals['json'] = json
        self._globals['re'] = re
        self._globals['time'] = time
        self._globals['urlencode'] = quote
        self._globals['urldecode'] = unquote

    def write(self, *args, **kwargs):
        #kwargs['file'] = self._output
        #print(*args, **kwargs)
        self._output.write(unicode(args[0]))

    def translate(self, string):
        return string

    @staticmethod
    def htmlspecialchars(text):
        return cgi.escape(text, True)

    ### Parser and Execution Code ###

    def get_output(self):
        self.evaluate()
        #return bytes(self._output.getvalue(), self._encoding)
        return self._output.getvalue().encode(self._encoding)

    def evaluate(self):
        #self._output = io.StringIO()
        segments = self._parse_segments(self._contents)
        self._pycode = self._generate_python(segments)
        self._execute_python()

    def inline(self, code):
        """ Execute code as PyHTML inline with the currently running script. """
        segments = self._parse_segments(code)
        pycode = self._generate_python(segments)
        exec(pycode, self._globals)

    def include(self, filename):
        """ Load file and execute as PyHTML. """
        code = self._read_contents(filename)
        self.inline(code)

    def _read_contents(self, filename):
        with open(filename, 'r') as f:
            contents = f.read()
        return contents

    def _parse_segments(self, contents):
        segments = [ ]
        while contents != '':
            first = contents.partition('<%')
            second = first[2].partition('%>')

            segments.append({ 'type' : 'raw', 'data' : first[0] if len(first[0]) > 0 and first[0][-1] == '\n' else first[0].rstrip(' \t') })

            if second[0]:
                if second[0].startswith('%include'):
                    include = self._read_contents(second[0].replace('%include', '').strip())
                    segments.extend(self._parse_segments(include))
                elif second[0][0] == '=':
                    segments.append({ 'type' : 'eval', 'data' : second[0][1:] })
                else:
                    segments.append({ 'type' : 'exec', 'data' : second[0] })

            if len(second[2]) > 0 and second[2][0] == '\n':
                contents = second[2][1:]
            else:
                contents = second[2]
        return segments

    def _generate_python(self, segments):
        base = len(self._segments)
        self._segments += segments

        lines = [ ]
        for i, seg in enumerate(segments):
            i += base
            if seg['type'] == 'raw':
                lines.append("py._output.write(py._segments[%d]['data'])" % (i,))
            elif seg['type'] == 'eval':
                lines.append("py._output.write(unicode(eval(py._segments[%d]['data'])))" % (i,))
            elif seg['type'] == 'exec':
                sublines = seg['data'].split('\n')
                lines.extend(sublines)

        lines = self._fix_indentation(lines)
        return '\n'.join(lines)

    def _fix_indentation(self, lines):
        indent = 0
        for i in range(0, len(lines)):
            code, sep, comment = lines[i].partition('#')
            code = code.strip()
            # TODO also take into account \ and """ """, [ ], { }, etc
            #quote_i = code.find("\"\"\"")

            if code.endswith(':'):
                found = False
                for kw in [ 'elif', 'else', 'except', 'finally' ]:
                    if code.startswith(kw):
                        found = True
                        break
                if not found:
                    indent += 1
                lines[i] = ((indent - 1) * '  ') + lines[i].lstrip()
            elif code.lower() == 'end':
                indent -= 1
                lines[i] = ''
            else:
                lines[i] = (indent * '  ') + lines[i].lstrip()
        return lines

    def _execute_python(self):

        #old_stdout = sys.stdout

        try:
            #sys.stdout = self._output
            exec(self._pycode, self._globals)

        except Exception as e:
            # TODO you need to let this defer to the error handler, don't you?
            self.write('\n<b>Eval Error:</b>\n<pre>\n%s</pre><br />\n' % (traceback.format_exc(),))
            self.write('<br /><pre>' + self.htmlspecialchars('\n'.join([ str(num + 1) + ':  ' + line for num,line in enumerate(self._pycode.splitlines()) ])) + '</pre>')
            return False

        finally:
            #sys.stdout = old_stdout
            pass

        return True



