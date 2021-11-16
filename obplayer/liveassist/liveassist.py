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

import json

from obplayer.httpadmin import httpserver

from . import microphone


class ObLiveAssist (httpserver.ObHTTPServer):
    def __init__(self):
        self.root = 'obplayer/liveassist/http'
        self.username = None
        self.readonly_username = None
        self.websockets = [ ]

        server_address = ('', obplayer.Config.setting('live_assist_port'))  # (address, port)

        httpserver.ObHTTPServer.__init__(self, server_address, None)
        sa = self.socket.getsockname()
        obplayer.Log.log('serving live assist http on port ' + str(sa[1]), 'liveassist')

    def log(self, message):
        if not "POST /info/levels" in message:
            obplayer.Log.log(message, 'debug')

    def shutdown(self):
        for conn in self.websockets:
            conn.websocket_write_close(200, "Server Exiting")
        httpserver.ObHTTPServer.shutdown(self)

    def handle_post(self, request):
        #if not request.access:
        #    return { 'status' : False, 'error' : "You don't have permission to do that.  You are current logged in as a guest" }

        if request.path == '/info/levels':
            return obplayer.Scheduler.get_audio_levels()

        elif request.path == '/info/play_status':
            return obplayer.Scheduler.get_now_playing()

        elif request.path == '/info/current_time':
            return { 'value' : str(time.time()) }

        elif request.path == '/info/show_name':
            return { 'value' : obplayer.Scheduler.get_show_name() }

        elif request.path == '/info/show_end':
            return { 'value' : str(obplayer.Scheduler.get_show_end()) }

        elif request.path == '/info/playlist':
            playlist = obplayer.Scheduler.get_current_playlist()
            return playlist

        elif request.path == '/info/liveassist_groups':
            groups = obplayer.Scheduler.get_current_groups()
            return groups

        elif request.path == '/command/play':
            if obplayer.Scheduler.unpause_show() == True:
                return {'status' : True }
            return { 'status' : False }

        elif request.path == '/command/pause':
            if obplayer.Scheduler.pause_show() == True:
                return { 'status' : True }
            return { 'status' : False }

        elif request.path == '/command/next':
            if obplayer.Scheduler.next_track() == True:
                return {'status' : True }
            return { 'status' : False }

        elif request.path == '/command/prev':
            if obplayer.Scheduler.previous_track() == True:
                return {'status' : True }
            return { 'status' : False }

        elif request.path == '/command/play_group_item':
            try:
                group_num = int(request.args['group_num'][0])
                group_item_num = int(request.args['group_item_num'][0])
                position = float(request.args['position'][0])
            except AttributeError as e:
                return { 'status' : False, 'error': "invalid request, missing " + e.args[0] + "." }

            if obplayer.Scheduler.play_group_item(group_num, group_item_num, position):
                return { 'status' : True }
            else:
                return { 'status' : False }

        elif request.path == '/command/playlist_seek':
            print(request.args)
            try:
                track_num = int(request.args['track_num'][0])
                position = float(request.args['position'][0])
            except AttributeError as e:
                return { 'status' : False, 'error': "invalid request, missing " + e.args[0] + "." }

            if obplayer.Scheduler.playlist_seek(track_num, position):
                return { 'status' : True }
            else:
                return { 'status' : False }


    def handle_websocket(self, conn, path):
        if path != '/stream':
            return

        self.websockets.append(conn)
        conn.microphone = None
        while True:
            try:
                (opcode, msg) = conn.websocket_read_message()
                if not msg:
                    break

                if opcode == httpserver.WS_OP_TEXT:
                    msg = json.loads(msg)
                    if msg['type'] == 'negotiate':
                        #print(repr(msg))
                        if not conn.microphone:
                            conn.microphone = microphone.ObLiveAssistMicrophone(conn, msg['mode'], msg)
                            conn.microphone.start()
                            self.send_mic_status(conn)
                        else:
                            pass #conn.microphone.change_format(msg['rate'], msg['encoding'])

                    elif msg['type'] == 'mute':
                        if conn.microphone:
                            conn.microphone.toggle_mute()
                        self.send_mic_status(conn)

                    elif msg['type'] == 'volume':
                        if conn.microphone:
                            conn.microphone.change_volume(msg['volume'])
                        self.send_mic_status(conn)

                elif opcode == httpserver.WS_OP_BIN:
                    #obplayer.Log.log("websocket recv: " + str(len(msg)) + " " + repr(msg[:20]) + "...", 'debug')
                    #conn.websocket_write_message(httpserver.WS_OP_BIN, ''.join(chr(random.getrandbits(8)) for i in range(len(msg))))
                    #conn.websocket_write_message(opcode, msg)
                    if not conn.microphone:
                        obplayer.Log.log("websocket audio stream not negotiated", 'error')
                    elif type(msg) == bytearray:
                        conn.microphone.queue_data(msg)
                    #conn.websocket_write_message(httpserver.WS_OP_BIN, data)

            except OSError as e:
                obplayer.Log.log("OSError: " + str(e), 'error')
                break

            except httpserver.WebSocketError as e:
                obplayer.Log.log(str(e), 'error')
                break

            except Exception as e:
                obplayer.Log.log(traceback.format_exc(), 'error')

        obplayer.Log.log("websocket connection closed", 'liveassist')
        if conn.microphone:
            conn.microphone.quit()
        self.websockets.remove(conn)

    def send_mic_status(self, conn):
        if not conn.microphone:
            return
        msg = conn.microphone.get_volume()
        if not msg:
            return
        msg['type'] = 'mic-status'
        conn.websocket_write_message(httpserver.WS_OP_TEXT, json.dumps(msg))

