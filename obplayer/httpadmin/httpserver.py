#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Copyright 2012-2015 OpenBroadcaster, Inc.

This file is part of OpenBroadcaster Player.

OpenBroadcaster Player is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

OpenBroadcaster Player is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with OpenBroadcaster Player.  If not, see <http://www.gnu.org/licenses/>.
"""

import obplayer

import os
import sys
import time
import traceback

import re
import cgi
import json
import base64
import struct
import random
import hashlib

if sys.version.startswith('3'):
    from urllib.parse import parse_qs,urlparse,quote,unquote
    import socketserver as SocketServer
    import http.server as BaseHTTPServer
    unicode = str
else:
    from urlparse import parse_qs,urlparse
    from urllib import quote,unquote
    import SocketServer
    import BaseHTTPServer

from obplayer.httpadmin.pyhtml import PyHTML


class HTTPError (Exception): errno = 500
class HTTPNotFoundError (HTTPError): errno = 404


class Request (object):
    def __init__(self, reqtype, path, args, access, headers):
        self.reqtype = reqtype
        self.path = path
        self.access = access
        self.args = args
        self.headers = headers


class Response (object):
    def __init__(self, status=200, mimetype='text/plain', content=None):
        self.status = status
        self.mimetype = mimetype
        self.content = content
        self.headers = [ ]

    def send_content(self, mimetype, content):
        self.mimetype = mimetype
        self.content = content
        return self

    def send_json(self, data):
        self.mimetype = 'application/json'
        self.content = json.dumps(data)
        return self

    def redirect(self, redirect):
        self.status = 302
        self.content = ''
        self.headers.append( ('Location', redirect) )
        return self

    def add_header(self, name, value):
        self.headers.append( (name, value) )
        return self


class ObHTTPServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
    daemon_threads = True

    def __init__(self, server_address, sslenable=False, sslreq=None, sslkey=None, sslcert=None, sslca=None):
        BaseHTTPServer.HTTPServer.__init__(self, server_address, ObHTTPRequestHandler)
        if sslenable:
            import ssl
            sslreq = ssl.CERT_NONE if not sslca else ssl.CERT_OPTIONAL if not sslreq else ssl.CERT_REQUIRED
            try:
                self.socket = ssl.wrap_socket(self.socket, keyfile=sslkey, certfile=sslcert, cert_reqs=sslreq, ca_certs=sslca, server_side=True)
            except:
                obplayer.Log.log("Error starting OpenSSL server. Falling back to normal HTTP", 'error')
                obplayer.Log.log(traceback.format_exc(), 'error')
        self.routes = [ ]

    def shutdown(self):
        BaseHTTPServer.HTTPServer.shutdown(self)

    def route(self, path, view, requires=None):
        self.routes.append( (path, view, requires) )

    def handle_post(self, request):
        for (pathref, view, requires) in self.routes:
            if pathref == request.path:
                if requires == 'admin' and not request.access:
                    return { 'status' : False, 'error' : "permissions-error-guest" }
                if callable(view):
                    return view(request)
                else:
                    raise HTTPError("view object is invalid type: " + str(view))
        raise HTTPNotFoundError(str(path) + " not found")


class ObHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    server_version = "OpenBroadcasterHTTP/0.1"

    extensions = {
        'css' : 'text/css',
        'html' : 'text/html',
        'js' : 'application/javascript',
        'svg' : 'image/svg+xml'
    }

    def log_message(self, format, *args):
        self.server.log(self.address_string() + ' ' + format % args)

    def translate(self, string):
        return string

    def check_authorization(self):

        self.admin_access = False
        self.authenticated = False

        if not self.server.username and not self.server.readonly_username:
            return True

        authdata = self.headers.get('Authorization')
        if type(authdata) == str:
            (username, _, password) = base64.b64decode(authdata.split(' ')[-1].encode('utf-8')).decode('utf-8').partition(':')
            #authdata = authdata.split(' ')[-1].decode('base64')
            #username = authdata.split(':')[0]
            #password = authdata.split(':')[1]

            if username == self.server.readonly_username and password == self.server.readonly_password:
                self.admin_access = False
                self.authenticated = True
            elif username == self.server.username and password == self.server.password:
                self.admin_access = True
                self.authenticated = True

        return self.authenticated

    def send_content(self, code, mimetype, content, headers=None):
        if sys.version.startswith('3') and isinstance(content, str):
            content = bytes(content, 'utf-8')
        self.send_response(code)
        if headers:
            for name, value in headers:
                self.send_header(name, value)
        self.send_header('Content-Type', mimetype)
        self.send_header('Content-Length', len(content))
        self.end_headers()
        self.wfile.write(content)

    def send_404(self):
        self.send_content(404, 'text/plain', "404 Not Found")

    def do_GET(self):
        url = urlparse(self.path)
        getargs = parse_qs(url.query, keep_blank_values=True)

        if self.check_authorization() == False:
            self.send_content(401, 'text/plain', "Authorization Required", [ ('WWW-Authenticate', 'Basic realm="Secure Area"') ])
            return

        if 'upgrade' in self.headers and self.headers['upgrade'] == 'websocket':
            self.handle_websocket(getargs)
            return

        #request = Request('GET', url.path, getargs, self.admin_access, self.headers)
        headers = [ ]

        if not self.is_valid_path(url.path):
            self.send_404()
            return

        if url.path.startswith('/logs/') or url.path.startswith('/audiologs/'):
            filename = obplayer.Config.get_datadir() + '/' + unquote(url.path[1:])
            headers.append( ('Content-Disposition', 'attachment; filename=' + os.path.basename(unquote(url.path[1:]))) )
        else:
            filename = self.server.root + '/' + url.path[1:]

        # If the path resolves to a directory, then set the filename to the index.html file inside that directory
        if os.path.isdir(filename):
            filename = filename.strip('/') + '/index.html'

        # server up the file
        if os.path.isfile(filename):
            self.extension = self.get_extension(filename)
            self.mimetype = self.get_mimetype(filename)

            with open(filename, 'rb') as f:
                contents = f.read()
                if self.extension == 'html':
                    #contents = self.parse(contents.decode('utf-8'), getargs)
                    contents = PyHTML(None, getargs, filename, contents.decode('utf-8')).get_output()
                self.send_content(200, self.mimetype, contents, headers)
                return

        # send error if nothing found
        self.send_404()

    def do_POST(self):

        if self.check_authorization() == False:
            self.send_content(401, 'text/plain', "Authorization Required", [ ('WWW-Authenticate', 'Basic realm="Secure Area"') ])
            return

        # empty post doesn't provide a content-type.
        ctype = None
        try:
            (ctype, pdict) = cgi.parse_header(self.headers['content-type'])
        except:
            pass

        if ctype == 'multipart/form-data':
            postvars = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={ 'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': self.headers['Content-Type'] })
            #postvars = cgi.parse_multipart(self.rfile, pdict)
        elif ctype == 'application/x-www-form-urlencoded':
            length = int(self.headers['content-length'])
            postvars = parse_qs(self.rfile.read(length).decode('utf-8'), keep_blank_values=True)
        else:
            postvars = {}

        request = Request('POST', self.path, postvars, self.admin_access, self.headers)

        try:
            response = self.server.handle_post(request)
        except:
            obplayer.Log.log(traceback.format_exc(), 'error')
            #if 'content-type' in self.headers and self.headers['content-type'] == 'application/json':
            #    response = { 'status': False, 'error': "Internal Server Error: " + traceback.format_exc() }
            #else:
            response = Response(500, 'text/plain', traceback.format_exc())

        if type(response) == Response:
            self.send_content(response.status, response.mimetype, response.content, headers=response.headers)
        else:
            self.send_content(200, 'application/json', json.dumps(response))

    @staticmethod
    def is_valid_path(path):
        if not path[0] == '/':
            return False
        for name in path.split('/'):
            if name == '.' or name == '..':
                return False
        return True

    @staticmethod
    def get_extension(filename):
        return filename.rpartition('.')[2]

    @staticmethod
    def get_mimetype(filename):
        extension = ObHTTPRequestHandler.get_extension(filename)
        if extension in ObHTTPRequestHandler.extensions:
            return ObHTTPRequestHandler.extensions[extension]
        else:
            return 'text/plain'


    def handle_websocket(self, postvars):
        protocol = self.headers['Sec-WebSocket-Protocol']
        if protocol.lower() != 'audio':
            self.send_content(500, 'text/plain', "Unrecognized websocket protocol: " + protocol)
            return

        self.send_response(101, "Switching Protocols")
        self.send_header('Upgrade', 'websocket')
        self.send_header('Connection', 'Upgrade')
        key = hashlib.sha1(bytearray(self.headers['Sec-WebSocket-Key'] + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11", 'utf-8')).digest()
        self.send_header('Sec-WebSocket-Accept', base64.b64encode(key).decode('utf-8'))
        self.send_header('Sec-WebSocket-Protocol', protocol)
        self.end_headers()

        conn = WebSocketConnection(self.rfile, self.wfile)

        if hasattr(self.server, 'handle_websocket'):
            self.server.handle_websocket(conn, self.path)

        conn.websocket_wait_for_close()
        return


WS_OP_CONT = 0x0
WS_OP_TEXT = 0x1
WS_OP_BIN = 0x2

WS_OP_CONTROL = 0x8
WS_OP_CLOSE = 0x8
WS_OP_PING = 0x9
WS_OP_PONG = 0xa

WS_B1_FINBIT = 0x80
WS_B1_RSV = 0x70
WS_B1_OPCODE = 0x0f
WS_B2_MASKBIT = 0x80
WS_B2_LENGTH = 0x7f

class WebSocketError (OSError): pass
class WebSocketClose (Exception): pass


class WebSocketConnection (object):
    def __init__(self, rfile, wfile):
        self.rfile = rfile
        self.wfile = wfile

    def websocket_read_message(self):
        data = bytearray()
        msg_opcode = None
        while True:
            (opcode, payload, headbyte1, headbyte2) = self.websocket_read_frame()

            if headbyte1 & WS_B1_RSV:
                raise WebSocketError("websocket: received an invalid frame where first byte is " + hex(headbyte1))
            if (headbyte2 & WS_B2_MASKBIT) == 0:
                raise WebSocketError("websocket: received an invalid frame where second byte is " + hex(headbyte2))

            if opcode & WS_OP_CONTROL:
                if opcode == WS_OP_CLOSE:
                    return (opcode, None)
                elif opcode == WS_OP_PING:
                    obplayer.Log.log("websocket: recieved ping from " + ':'.join(self.client_address))
                    self.websocket_write_frame(WS_OP_PONG, payload)
                    continue
                elif opcode == WS_OP_PONG:
                    continue
                else:
                    raise WebSocketError("websocket: received invalid opcode " + hex(opcode))

            else:
                if msg_opcode == None:
                    msg_opcode = opcode
                else:
                    if opcode != WS_OP_CONT:
                        raise WebSocketError("websocket: expected CONT opcode, received " + hex(opcode))

                data += payload
                if headbyte1 & WS_B1_FINBIT:
                    break

        if msg_opcode == WS_OP_TEXT:
            return (msg_opcode, data.decode('utf-8'))
        elif msg_opcode == WS_OP_BIN:
            return (msg_opcode, data)
        raise WebSocketError("websocket: expected non-control opcode, received " + hex(opcode))

    def websocket_read_frame(self):
        (headbyte1, headbyte2) = struct.unpack('!BB', self.websocket_read_bytes(2))
        opcode = headbyte1 & 0xf
        length = headbyte2 & WS_B2_LENGTH
        if length == 0x7e:
            (length,) = struct.unpack("!H", self.websocket_read_bytes(2))
            if length == 0x7f:
                (length,) = struct.unpack("!Q", self.websocket_read_bytes(8))
        maskkey = self.websocket_read_bytes(4) if headbyte2 & WS_B2_MASKBIT else None

        payload = self.websocket_read_bytes(length)
        if maskkey:
            payload = bytearray(ord(b) ^ ord(maskkey[i % 4]) for (i, b) in enumerate(payload))

        #print("RECV: " + hex(headbyte1) + " " + hex(headbyte2) + " " + str(payload))
        return (opcode, payload, headbyte1, headbyte2)

    def websocket_read_bytes(self, num):
        data = self.rfile.read(num)
        if len(data) != num:
            raise WebSocketError("websocket: unexpected end of data")
        return data

    def websocket_write_message(self, opcode, data):
        if opcode == WS_OP_TEXT:
            self.websocket_write_frame(WS_OP_TEXT, bytearray(data, 'utf-8'))
        elif opcode == WS_OP_BIN:
            self.websocket_write_frame(WS_OP_BIN, data)
        else:
            raise WebSocketError("websocket: expected non-control opcode, received " + hex(opcode))

    def websocket_write_frame(self, opcode, data):
        length = len(data)
        frame = bytearray()
        frame += struct.pack("!B", WS_B1_FINBIT | opcode)
        if length < 0x7e:
            frame += struct.pack("!B", length)
        elif length < 0xffff:
            frame += struct.pack("!BH", 0x7e, length)
        else:
            frame += struct.pack("!BQ", 0x7f, length)
        #maskkey = struct.pack("!I", random.getrandbits(32))
        #frame += maskkey
        #frame += bytes(b ^ maskkey[i % 4] for (i, b) in enumerate(data))
        frame += data

        #print("SEND: " + ' '.join(hex(b) for b in frame))
        self.wfile.write(frame)

    def websocket_write_close(self, statuscode, message):
        status = bytearray(2)
        status[0] = (statuscode >> 8) & 0xff
        status[1] = statuscode & 0xff
        self.websocket_write_frame(WS_OP_CLOSE, status + bytearray(message, 'utf-8'))

    def websocket_wait_for_close(self):
        while True:
            (opcode, payload, headbyte1, headbyte2) = self.websocket_read_frame()
            if opcode == WS_OP_CLOSE:
                if payload:
                    obplayer.Log.log("websocket: received close message: " + str(struct.unpack("!H", payload[0:2])[0]) + " - " + payload[2:].decode('utf-8'))
                else:
                    obplayer.Log.log("websocket: received close message")
                return



