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
import time
import traceback

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst, GstVideo, GstController

from .base import ObGstPipeline


class ObPlayBinPipeline (ObGstPipeline):
    min_class = [ 'audio', 'visual' ]
    max_class = [ 'audio', 'visual' ]

    def __init__(self, name, player, audiovis=False):
        ObGstPipeline.__init__(self, name)
        self.player = player
        self.play_start_time = 0
        self.pipeline = Gst.ElementFactory.make('playbin', name)
        # TODO this is false for testing
        #self.pipeline.set_property('force-aspect-ratio', False)
        self.pipeline.set_property('force-aspect-ratio', True)

        if audiovis is True:
            self.audiovis = Gst.ElementFactory.make('libvisual_jess', name + '-visualizer')
            self.pipeline.set_property('flags', self.pipeline.get_property('flags') | 0x00000008)
            self.pipeline.set_property('vis-plugin', self.audiovis)

        self.fakesinks = { }
        for output in list(self.player.outputs.keys()) + [ 'audio', 'visual' ]:
            self.fakesinks[output] = Gst.ElementFactory.make('fakesink')

        self.pipeline.set_property('audio-sink', self.fakesinks['audio'])
        self.pipeline.set_property('video-sink', self.fakesinks['visual'])

        self.register_signals()
        #self.pipeline.connect("about-to-finish", self.about_to_finish_handler)

    def patch(self, mode):
        obplayer.Log.log(self.name + ": patching " + mode, 'debug')

        (change, state, pending) = self.pipeline.get_state(0)
        self.wait_state(Gst.State.NULL)

        for output in mode.split('/'):
            if output not in self.mode:
                #print self.name + " -- Connecting " + output
                self.pipeline.set_property('audio-sink' if output == 'audio' else 'video-sink', self.player.outputs[output].get_bin())
                self.mode.add(output)

        if state == Gst.State.PLAYING:
            self.seek_pause()
            self.wait_state(Gst.State.PLAYING)

    def unpatch(self, mode):
        obplayer.Log.log(self.name + ": unpatching " + mode, 'debug')

        (change, state, pending) = self.pipeline.get_state(0)
        self.wait_state(Gst.State.NULL)

        for output in mode.split('/'):
            if output in self.mode:
                #print self.name + " -- Disconnecting " + output
                self.pipeline.set_property('audio-sink' if output == 'audio' else 'video-sink', self.fakesinks[output])
                #parent = self.player.outputs[output].get_bin().get_parent()
                #if parent:
                #    parent.remove(self.player.outputs[output].get_bin())
                self.mode.discard(output)

        if len(self.mode) > 0 and state == Gst.State.PLAYING:
            self.seek_pause()
            self.wait_state(Gst.State.PLAYING)

    def set_request(self, req):
        self.play_start_time = req['start_time']
        #self.pipeline.set_property('uri', Gst.filename_to_uri(req['file_location'] + '/' + req['filename']))
        self.pipeline.set_property('uri', req['uri'])
        self.seek_pause()

    def seek_pause(self):
        # Set pipeline to paused state
        self.wait_state(Gst.State.PAUSED)

        if obplayer.Config.setting('gst_init_callback'):
            os.system(obplayer.Config.setting('gst_init_callback'))

        if self.play_start_time <= 0:
            self.play_start_time = time.time()

        offset = time.time() - self.play_start_time
        if offset != 0:
        #if offset > 0.25:
            if self.pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, offset * Gst.SECOND) == False:
                obplayer.Log.log('unable to seek on this track', 'error')
            obplayer.Log.log('resuming track at ' + str(offset) + ' seconds.', 'player')


class ObAudioPlayBinPipeline (ObPlayBinPipeline):
    min_class = [ 'audio' ]
    max_class = [ 'audio', 'visual' ]


class ObDecodeBinPipeline (ObGstPipeline):
    min_class = [ 'audio' ]
    max_class = [ 'audio', 'visual' ]

    def __init__(self, name, player, audiovis=False):
        ObGstPipeline.__init__(self, name)
        self.player = player
        self.play_start_time = 0
        self.audiosink = None
        self.videosink = None

        self.pipeline = Gst.Pipeline(name)

        self.decodebin = Gst.ElementFactory.make('uridecodebin', name + '-uridecodebin')
        self.pipeline.add(self.decodebin)
        self.decodebin.connect("pad-added", self.on_decoder_pad_added)

        #if audiovis is True:
        #    self.audiovis = Gst.ElementFactory.make('libvisual_jess')
        #    self.pipeline.set_property('flags', self.pipeline.get_property('flags') | 0x00000008)
        #    self.pipeline.set_property('vis-plugin', self.audiovis)

        self.fakesinks = { }
        for output in list(self.player.outputs.keys()) + [ 'audio', 'visual' ]:
            self.fakesinks[output] = Gst.ElementFactory.make('fakesink')

        self.set_property('audio-sink', self.fakesinks['audio'])
        self.set_property('video-sink', self.fakesinks['visual'])

        self.register_signals()
        #self.pipeline.connect("about-to-finish", self.about_to_finish_handler)

    def on_decoder_pad_added(self, element, pad):
        caps = pad.get_current_caps()

        #print caps.to_string()
        #print self.audiosink.get_static_pad('sink')
        #print self.audiosink.get_request_pad('sink')

        if caps.to_string().startswith('audio'):
            #self.pipeline.add(self.audiosink)
            pad.link(self.audiosink.get_static_pad('sink'))
        else:
            #self.pipeline.add(self.videosink)
            pad.link(self.videosink.get_static_pad('sink'))

    def set_property(self, property, value):
        if property == 'audio-sink':
            if self.audiosink:
                self.pipeline.remove(self.audiosink)
            self.audiosink = value
            if self.audiosink:
                self.pipeline.add(self.audiosink)
                #self.decodebin.link(self.audiosink)
        elif property == 'video-sink':
            if self.videosink:
                self.pipeline.remove(self.videosink)
            self.videosink = value
            if self.videosink:
                self.pipeline.add(self.videosink)
                #self.decodebin.link(self.videosink)

    def patch(self, mode):
        obplayer.Log.log(self.name + ": patching " + mode, 'debug')

        (change, state, pending) = self.pipeline.get_state(0)
        self.wait_state(Gst.State.NULL)

        for output in mode.split('/'):
            if output not in self.mode:
                #print self.name + " -- Connecting " + output
                self.set_property('audio-sink' if output == 'audio' else 'video-sink', self.player.outputs[output].get_bin())
                self.mode.add(output)

        if state == Gst.State.PLAYING:
            self.seek_pause()
            self.wait_state(Gst.State.PLAYING)

    def unpatch(self, mode):
        obplayer.Log.log(self.name + ": unpatching " + mode, 'debug')

        (change, state, pending) = self.pipeline.get_state(0)
        self.wait_state(Gst.State.NULL)

        for output in mode.split('/'):
            if output in self.mode:
                #print self.name + " -- Disconnecting " + output
                self.set_property('audio-sink' if output == 'audio' else 'video-sink', self.fakesinks[output])
                self.mode.discard(output)

        if len(self.mode) > 0 and state == Gst.State.PLAYING:
            self.seek_pause()
            self.wait_state(Gst.State.PLAYING)

    def set_request(self, req):
        self.play_start_time = req['start_time']
        self.decodebin.set_property('uri', req['uri'])
        self.seek_pause()

    def seek_pause(self):
        # Set pipeline to paused state
        self.wait_state(Gst.State.PAUSED)

        if obplayer.Config.setting('gst_init_callback'):
            os.system(obplayer.Config.setting('gst_init_callback'))

        if self.play_start_time <= 0:
            self.play_start_time = time.time()

        offset = time.time() - self.play_start_time
        if offset != 0:
        #if offset > 0.25:
            if self.pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, offset * Gst.SECOND) == False:
                obplayer.Log.log('unable to seek on this track', 'error')
            obplayer.Log.log('resuming track at ' + str(offset) + ' seconds.', 'player')


