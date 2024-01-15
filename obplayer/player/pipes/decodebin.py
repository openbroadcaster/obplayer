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
        offset = 0 # TODO FIXME SEEK TEMPORARIY DISABLED
        if offset != 0:
            print(offset)
            if self.pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, offset * Gst.SECOND) == False:
                obplayer.Log.log('unable to seek on this track', 'error')
            obplayer.Log.log('resuming track at ' + str(offset) + ' seconds.', 'player')

class ObAudioPlayBinPipeline (ObPlayBinPipeline):
    min_class = [ 'audio' ]
    max_class = [ 'audio', 'visual' ]

"""
class ObAudioPlayBinPipeline (ObGstPipeline):
    min_class = [ 'audio' ]
    max_class = [ 'audio', 'visual' ]
    playbin = False

    def __init__(self, name, player, audiovis=False):
        ObGstPipeline.__init__(self, name)

        # make the rest of the code happy by having a pipeline all the time
        self.pipeline = Gst.parse_launch('audiotestsrc ! audioconvert ! fakesink')
        self.pipeline.set_state(Gst.State.PAUSED)

    def set_request(self, req):
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline.get_state(Gst.CLOCK_TIME_NONE)
            self.pipeline = False

        if req['uri']:
            if(req['start_time']):
                offset = max(0, time.time() - req['start_time'])
            else:
                offset = 0
            self.pipeline = Gst.ElementFactory.make("playbin", "playbin")
            self.pipeline.set_property("uri", req['uri'])
            interpipesink = Gst.ElementFactory.make("interpipesink", 'interpipe-main')
            interpipesink.set_property('sync', True)
            self.pipeline.set_property("audio-sink", interpipesink)
            print(self.pipeline.get_property("audio-sink"))

            print('playing ' + req['uri'])

            self.pipeline.set_state(Gst.State.PAUSED)
            self.pipeline.get_state(Gst.CLOCK_TIME_NONE)
            if(offset):
                #print('seeking to ' + str(offset))
                #print(self.pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, offset * Gst.SECOND))
                pass
                #print(self.pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, offset * Gst.SECOND))

        else:
            self.pipeline = Gst.parse_launch('audiotestsrc ! audioconvert ! fakesink')

"""