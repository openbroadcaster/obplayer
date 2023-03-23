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
import socket
import threading
import traceback

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstSdp', '1.0')
from gi.repository import GObject, Gst, GstVideo, GstSdp

from .base import ObGstPipeline

if sys.version.startswith('3'):
    import urllib.parse as urlparse
else:
    import urlparse


class ObRTSPAInputPipeline (ObGstPipeline):
    min_class = [ 'audio' ]
    max_class = [ 'audio' ]

    def __init__(self, name, player):
        ObGstPipeline.__init__(self, name)
        self.player = player
        self.location = None
        self.request_in_progress = threading.Event()

        self.pipeline = Gst.Pipeline(name)
        self.elements = [ ]

        self.filesrc = Gst.ElementFactory.make('filesrc', name + '-filesrc')
        self.pipeline.add(self.filesrc)

        """
        self.appsrc = Gst.ElementFactory.make('appsrc')
        self.appsrc.set_property('is-live', False)
        self.appsrc.set_property('format', 2)
        self.pipeline.add(self.appsrc)
        """

        self.sdpdemux = Gst.ElementFactory.make('sdpdemux', name + '-sdpdemux')
        #self.sdpdemux.set_property('debug', True)
        self.pipeline.add(self.sdpdemux)
        self.filesrc.link(self.sdpdemux)

        def sdpdemux_pad_added(obj, pad):
            #print("Pad added " + str(pad))
            #caps = pad.get_current_caps()
            pad.link(self.decodebin.get_static_pad('sink'))
        self.sdpdemux.connect('pad-added', sdpdemux_pad_added)

        self.decodebin = Gst.ElementFactory.make('decodebin', name + '-decodebin')
        self.pipeline.add(self.decodebin)

        def decodebin_pad_added(obj, pad):
            caps = pad.get_current_caps().to_string()
            #print(caps, pad.is_linked())

            if caps.startswith('audio'):
                pad.link(self.audioconvert.get_static_pad('sink'))
            else:
                print("Fake sink thing that we don't want")
                fakesink = Gst.ElementFactory.make('fakesink')
                self.pipeline.add(fakesink)
                pad.link(fakesink.get_static_pad('sink'))

            #for p in self.decodebin.iterate_pads():
            #    print("Pad: ", p, p.is_linked())
        self.decodebin.connect('pad-added', decodebin_pad_added)

        self.audioconvert = Gst.ElementFactory.make('audioconvert', name + '-convert')
        self.pipeline.add(self.audioconvert)

        self.queue = Gst.ElementFactory.make('queue2', name + '-queue')
        self.pipeline.add(self.queue)
        self.audioconvert.link(self.queue)


        self.audiosink = None
        self.fakesink = Gst.ElementFactory.make('fakesink')
        self.set_property('audio-sink', self.fakesink)

        self.register_signals()
        #self.bus.connect("message", self.message_handler_rtp)
        #self.bus.add_signal_watch()

    def set_property(self, property, value):
        if property == 'audio-sink':
            if self.audiosink:
                self.queue.unlink(self.audiosink)
                self.pipeline.remove(self.audiosink)
            self.audiosink = value
            if self.audiosink:
                self.pipeline.add(self.audiosink)
                self.queue.link(self.audiosink)

    def patch(self, mode):
        (change, state, pending) = self.pipeline.get_state(0)
        self.wait_state(Gst.State.NULL)
        if 'audio' in mode:
            self.set_property('audio-sink', self.player.outputs['audio'].get_bin())
        ObGstPipeline.patch(self, mode)

        if state == Gst.State.PLAYING:
            #self.wait_state(Gst.State.PLAYING)
            self.pipeline.set_state(Gst.State.PLAYING)
            if obplayer.Config.setting('gst_init_callback'):
                os.system(obplayer.Config.setting('gst_init_callback'))

    def unpatch(self, mode):
        (change, state, pending) = self.pipeline.get_state(0)
        self.wait_state(Gst.State.NULL)
        if 'audio' in mode:
            self.set_property('audio-sink', self.fakesink)
        ObGstPipeline.unpatch(self, mode)
        if len(self.mode) > 0 and state == Gst.State.PLAYING:
            #self.wait_state(Gst.State.PLAYING)
            self.pipeline.set_state(Gst.State.PLAYING)
            if obplayer.Config.setting('gst_init_callback'):
                os.system(obplayer.Config.setting('gst_init_callback'))

    def set_request(self, req):
        self.start_time = req['start_time']
        if not req['uri'].startswith('rtsp'):
            obplayer.Log.log("invalid RTSP uri: " + req['uri'], 'info')
            return
        self.rtspsrc.set_property('location', req['uri'])

    def message_handler_rtp(self, bus, message):
        if message.type == Gst.MessageType.ERROR:
            obplayer.Log.log("attempting to restart pipeline", 'info')
            GObject.timeout_add(1.0, self.restart_pipeline)

    def restart_pipeline(self):
        self.wait_state(Gst.State.NULL)
        self.wait_state(Gst.State.PLAYING)

    def start(self):
        if self.request_in_progress.is_set():
            obplayer.Log.log("rtspa: a start request was already in progress when attempting to start", 'error')
            return
        GObject.idle_add(self.do_rtsp_request)

    def do_rtsp_request(self):
        self.request_in_progress.set()

        try:
            # TODO you need to do the request and get the SDP
            conn = ObRTSPAConnection(self, (self.location,))
            conn.start()

            # We start the pipe without waiting because it wont enter the playing state until the transmitting end is connected 
            #self.pipeline.set_state(Gst.State.PLAYING)
        except:
            obplayer.Log.log("exception in rtspa do_rtsp_request:", 'error')
            obplayer.Log.log(traceback.format_exc(), 'error')

        self.request_in_progress.clear()


class ObRTSPAConnection (obplayer.ObThread):
    def __init__(self, pipeline, hosts=None):
        obplayer.ObThread.__init__(self, 'ObRTSPAFetcher')
        self.daemon = True

        self.pipeline = pipeline
        self.socket = None
        self.buffer = b""
        self.receiving_data = False
        self.last_received = 0
        self.close_lock = threading.Lock()
        self.hosts = hosts
        self.current_url = None

    def connect(self):
        if self.socket is not None:
            self.close()

        for urlstring in self.hosts:
            url = urlparse.urlparse(urlstring, 'rtsp')
            urlparts = url.netloc.split(':')
            (self.host, self.port) = (urlparts[0], urlparts[1] if len(urlparts) > 1 else 554)
            self.socket = None
            try:
                for res in socket.getaddrinfo(self.host, self.port, socket.AF_UNSPEC, socket.SOCK_STREAM):
                    af, socktype, proto, canonname, sa = res

                    try:
                        self.socket = socket.socket(af, socktype, proto)
                        #self.socket.settimeout(360.0)
                    except socket.error as e:
                        self.socket = None
                        continue

                    try:
                        self.socket.connect(sa)
                    except socket.error as e:
                        self.socket.close()
                        self.socket = None
                        continue
                    break
            except socket.gaierror:
                pass

            if self.socket is not None:
                self.current_url = urlstring
                obplayer.Log.log("connected to rtsp server at " + str(self.host) + ":" + str(self.port), 'alerts')
                return True

            obplayer.Log.log("error connecting to rtsp server at " + str(self.host) + ":" + str(self.port), 'error')
            time.sleep(1)
        return False

    def close(self):
        with self.close_lock:
            if self.socket:
                addr, port = self.socket.getsockname()
                obplayer.Log.log("closing socket %s:%s" % (addr, port), 'alerts')
                try:
                    self.socket.shutdown(socket.SHUT_RDWR)
                    self.socket.close()
                except:
                    obplayer.Log.log("exception in " + self.name + " thread", 'error')
                    obplayer.Log.log(traceback.format_exc(), 'error')
                self.socket = None
                self.last_received = 0
                self.current_url = None

    def send(self, data):
        self.socket.send(data)

    def receive(self):
        return self.socket.recv(4096)

    def read_alert_data(self):
        while True:
            if self.buffer:
                if self.receiving_data is False:
                    i = self.buffer.find(b'<?xml')
                    if i >= 0:
                        self.buffer = self.buffer[i:]
                        self.receiving_data = True

                if self.receiving_data is True:
                    data, endtag, remain = self.buffer.partition(b'</alert>')
                    if endtag:
                        self.buffer = remain
                        self.receiving_data = False
                        self.last_received = time.time()
                        return data + endtag

            data = self.receive()
            if not data:
                with self.close_lock:
                    self.socket = None
                raise socket.error("TCP socket closed by remote end. (" + str(self.host) + ":" + str(self.port) + ")")
            self.buffer = self.buffer + data

    def try_run(self):
        while True:
            success = self.connect()
            if not success:
                time.sleep(20)
                continue

            self.send('DESCRIBE {0} RTSP/1.0\r\nCSeq: 2\r\n\r\n'.format(self.current_url).encode('utf-8'))
            data = self.receive()
            (header, body) = str(data, 'utf-8').split('\r\n\r\n')
            print(header.split('\r\n'), body)

            with open('/tmp/aoip.sdp', 'w') as f:
                f.write(body)

            #self.pipeline.filesrc.set_property('location', '/tmp/aoip.sdp')
            self.pipeline.filesrc.set_property('location', '/media/work/OpenBroadcaster/Player/tools/stream.sdp')

            """
            body = bytearray(body, 'utf-8')
            gbuffer = Gst.Buffer.new_allocate(None, len(body), None)
            gbuffer.fill(0, body)
            ret = self.pipeline.appsrc.emit('push-buffer', gbuffer)
            print(ret)
            """

            self.pipeline.wait_state(Gst.State.NULL)
            self.pipeline.pipeline.set_state(Gst.State.PLAYING)

            return

            while True:
                try:
                    data = self.read_alert_data()
                    if (data):
                        obplayer.Log.log("received alert " + str(alert.identifier) + " (" + str(alert.sent) + ")", 'debug')
                        #alert.print_data()

                except socket.error as e:
                    obplayer.Log.log("Socket Error: " + str(e), 'error')
                    break

                except:
                    obplayer.Log.log("exception in " + self.name + " thread", 'error')
                    obplayer.Log.log(traceback.format_exc(), 'error')
            self.close()
            time.sleep(5)

    def stop(self):
        self.close()
