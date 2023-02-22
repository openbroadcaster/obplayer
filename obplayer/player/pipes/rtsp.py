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
import traceback

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstSdp', '1.0')
from gi.repository import GObject, Gst, GstVideo, GstSdp

from .base import ObGstPipeline


class ObRTSPInputPipeline (ObGstPipeline):
    min_class = [ 'audio' ]
    max_class = [ 'audio' ]

    def __init__(self, name, player):
        ObGstPipeline.__init__(self, name)
        self.player = player

        self.pipeline = Gst.Pipeline(name)
        self.elements = [ ]


        self.rtspsrc = Gst.ElementFactory.make('rtspsrc', name + '-rtspsrc')
        self.pipeline.add(self.rtspsrc)
        self.rtspsrc.connect('on-sdp', self.rtspsrc_on_sdp)
        #self.rtspsrc.connect('select-stream', self.rtspsrc_select_stream)

        def rtspsrc_pad_added(obj, pad):
            print("Pad added " + str(pad))

            caps = pad.get_current_caps().to_string()
            #print(caps)

            if 'media=(string)audio' in caps:
                pad.link(self.decodebin.get_static_pad('sink'))
            else:
                pad.link(Gst.ElementFactory.make('fakesink').get_static_pad('sink'))
        self.rtspsrc.connect('pad-added', rtspsrc_pad_added)

        self.decodebin = Gst.ElementFactory.make('decodebin', name + '-decodebin')
        self.pipeline.add(self.decodebin)
        #self.rtspsrc.link(self.decodebin)

        self.queue = Gst.ElementFactory.make('queue2', name + '-queue')
        self.pipeline.add(self.queue)

        self.audioconvert = Gst.ElementFactory.make('audioconvert', name + '-convert')
        self.pipeline.add(self.audioconvert)
        self.queue.link(self.audioconvert)

        #self.foo = Gst.ElementFactory.make('autoaudiosink')
        #self.pipeline.add(self.foo)
        #self.queue.link(self.foo)

        def decodebin_pad_added(obj, pad):
            print("Decode pad added " + str(pad))

            caps = pad.get_current_caps().to_string()
            print(caps, pad.is_linked())

            if caps.startswith('audio'):
                pad.link(self.queue.get_static_pad('sink'))
            else:
                print("Fake sink thing that we don't want")
                fakesink = Gst.ElementFactory.make('fakesink')
                self.pipeline.add(fakesink)
                pad.link(fakesink.get_static_pad('sink'))

            #for p in self.decodebin.iterate_pads():
            #    print("Pad: ", p, p.is_linked())

        self.decodebin.connect('pad-added', decodebin_pad_added)


        self.audiosink = None
        self.fakesinks = { }
        self.fakesinks['audio'] = Gst.ElementFactory.make('fakesink')
        self.fakesinks['visual'] = Gst.ElementFactory.make('fakesink')
        self.set_property('audio-sink', self.fakesinks['audio'])
        self.set_property('video-sink', self.fakesinks['visual'])

        self.register_signals()
        #self.bus.connect("message", self.message_handler_rtp)
        #self.bus.add_signal_watch()

    def start(self):
        # We start the pipe without waiting because it wont enter the playing state until the transmitting end is connected 
        self.pipeline.set_state(Gst.State.PLAYING)

    def set_property(self, property, value):
        if property == 'audio-sink':
            if self.audiosink:
                #self.decodebin.unlink(self.audiosink)
                self.audioconvert.unlink(self.audiosink)
                self.pipeline.remove(self.audiosink)
            self.audiosink = value
            if self.audiosink:
                self.pipeline.add(self.audiosink)
                self.audioconvert.link(self.audiosink)
                #self.decodebin.link(self.audiosink)

    def patch(self, mode):
        self.wait_state(Gst.State.NULL)
        if 'audio' in mode:
            self.set_property('audio-sink', self.player.outputs['audio'].get_bin())
        if 'visual' in mode:
            self.set_property('video-sink', self.player.outputs['visual'].get_bin())
        ObGstPipeline.patch(self, mode)

        #self.wait_state(Gst.State.PLAYING)
        self.pipeline.set_state(Gst.State.PLAYING)
        if obplayer.Config.setting('gst_init_callback'):
            os.system(obplayer.Config.setting('gst_init_callback'))

    def unpatch(self, mode):
        self.wait_state(Gst.State.NULL)
        if 'audio' in mode:
            self.set_property('audio-sink', self.fakesinks['audio'])
        if 'visual' in mode:
            self.set_property('video-sink', self.fakesinks['visual'])
        ObGstPipeline.unpatch(self, mode)
        if len(self.mode) > 0:
            #self.wait_state(Gst.State.PLAYING)
            self.pipeline.set_state(Gst.State.PLAYING)
            if obplayer.Config.setting('gst_init_callback'):
                os.system(obplayer.Config.setting('gst_init_callback'))

    def set_request(self, req):
        #self.rtspsrc.set_property('location', "rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mov")
        #self.rtspsrc.set_property('location', "rtsp://localhost:8000/GoaTrance.mp3")
        #self.rtspsrc.set_property('location', "rtsp://localhost:8554/by-id/1")
        #self.rtspsrc.set_property('location', "rtsp://172.16.0.15/by-id/2")
        #self.rtspsrc.set_property('location', "rtsp://localhost:5544/")
        if not req['uri'].startswith('rtsp'):
            obplayer.Log.log("invalid RTSP uri: " + req['uri'], 'info')
            return
        self.rtspsrc.set_property('location', req['uri'])
        #self.seek_pause()

    def message_handler_rtp(self, bus, message):
        if message.type == Gst.MessageType.ERROR:
            obplayer.Log.log("attempting to restart pipeline", 'info')
            GObject.timeout_add(1.0, self.restart_pipeline)

    def restart_pipeline(self):
        self.wait_state(Gst.State.NULL)
        self.wait_state(Gst.State.PLAYING)

    def rtspsrc_on_sdp(self, element, sdp):
        print(repr(sdp))
        print(sdp.as_text())

    def rtspsrc_select_stream(self, element, num, caps):
        #caps.set_value('media-type', 'application/x-rtp')
        print("CONF", num, caps)
        return True

