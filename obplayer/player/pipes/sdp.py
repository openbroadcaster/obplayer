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


class ObSDPInputPipeline (ObGstPipeline):
    min_class = [ 'audio' ]
    max_class = [ 'audio' ]

    def __init__(self, name, player):
        ObGstPipeline.__init__(self, name)
        self.player = player

        self.pipeline = Gst.Pipeline(name)
        self.elements = [ ]

        self.filesrc = Gst.ElementFactory.make('filesrc', name + '-filesrc')
        self.pipeline.add(self.filesrc)

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

    def start(self):
        # We start the pipe without waiting because it wont enter the playing state until the transmitting end is connected 
        self.pipeline.set_state(Gst.State.PLAYING)

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
        self.wait_state(Gst.State.NULL)
        if 'audio' in mode:
            self.set_property('audio-sink', self.player.outputs['audio'].get_bin())
        ObGstPipeline.patch(self, mode)

        #self.wait_state(Gst.State.PLAYING)
        self.pipeline.set_state(Gst.State.PLAYING)
        if obplayer.Config.setting('gst_init_callback'):
            os.system(obplayer.Config.setting('gst_init_callback'))

    def unpatch(self, mode):
        self.wait_state(Gst.State.NULL)
        if 'audio' in mode:
            self.set_property('audio-sink', self.fakesink)
        ObGstPipeline.unpatch(self, mode)
        if len(self.mode) > 0:
            #self.wait_state(Gst.State.PLAYING)
            self.pipeline.set_state(Gst.State.PLAYING)
            if obplayer.Config.setting('gst_init_callback'):
                os.system(obplayer.Config.setting('gst_init_callback'))

    def set_request(self, req):
        self.start_time = req['start_time']
        self.filesrc.set_property('location', req['uri'][7:] if req['uri'].startswith('file://') else req['uri'])

    def message_handler_rtp(self, bus, message):
        if message.type == Gst.MessageType.ERROR:
            obplayer.Log.log("attempting to restart pipeline", 'info')
            GObject.timeout_add(1.0, self.restart_pipeline)

    def restart_pipeline(self):
        self.wait_state(Gst.State.NULL)
        self.wait_state(Gst.State.PLAYING)


