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
gi.require_version('GstController', '1.0')
from gi.repository import GObject, Gst, GstVideo, GstController

from .base import ObGstPipeline


class ObImagePipeline (ObGstPipeline):
    min_class = [ 'visual' ]
    max_class = [ 'visual' ]

    def __init__(self, name, player, audiovis=False):
        ObGstPipeline.__init__(self, name)
        self.player = player
        self.request = None
        self.videosink = None

        self.images_transitions_enable = obplayer.Config.setting('images_transitions_enable')
        self.images_width = obplayer.Config.setting('images_width')
        self.images_height = obplayer.Config.setting('images_height')
        self.images_framerate = obplayer.Config.setting('images_framerate')

        self.pipeline = Gst.Pipeline(name)

        #self.imagebin = Gst.parse_launch('uridecodebin uri="file:///home/trans/Downloads/kitty.jpg" ! imagefreeze ! videoconvert ! videoscale ! video/x-raw, height=1920, width=1080 ! autovideosink')

        self.decodebin = Gst.ElementFactory.make('uridecodebin', name + '-uridecodebin')
        self.pipeline.add(self.decodebin)
        self.decodebin.connect("pad-added", self.on_decoder_pad_added)

        self.elements = [ ]
        self.elements.append(Gst.ElementFactory.make('imagefreeze', name + '-freeze'))

        ## create basic filter elements
        self.elements.append(Gst.ElementFactory.make('videoscale', name + '-scale'))
        #self.elements[-1].set_property('add-borders', False)
        self.elements.append(Gst.ElementFactory.make('videoconvert', name + '-convert'))
        self.elements.append(Gst.ElementFactory.make('videorate', name + '-rate'))

        ## create caps filter element to set the output video parameters
        caps = Gst.ElementFactory.make('capsfilter', name + '-capsfilter')
        #caps.set_property('caps', Gst.Caps.from_string("video/x-raw,width=" + str(self.video_width) + ",height=" + str(self.video_height)))
        #caps.set_property('caps', Gst.Caps.from_string("video/x-raw,width=640,height=480,framerate=15/1"))
        caps.set_property('caps', Gst.Caps.from_string("video/x-raw,width=%d,height=%d,framerate=%d/1" % (self.images_width, self.images_height, self.images_framerate)))
        self.elements.append(caps)

        #self.videobalance = Gst.ElementFactory.make('videobalance', 'image-pipeline-videobalance')
        #self.videobalance.set_property('videobalance', 0.0)
        #self.elements.append(self.videobalance)

        self.control_source = GstController.InterpolationControlSource.new()
        self.control_source.props.mode = GstController.InterpolationMode.LINEAR

        #binding = GstController.DirectControlBinding.new(self.videobalance, 'contrast', self.control_source)
        #self.videobalance.add_control_binding(binding)

        if self.images_transitions_enable:
            self.elements.append(Gst.ElementFactory.make('alpha', name + '-alpha'))
            #self.elements[-1].set_property('method', 1)
            binding = GstController.DirectControlBinding.new(self.elements[-1], 'alpha', self.control_source)
            self.elements[-1].add_control_binding(binding)

            self.elements.append(Gst.ElementFactory.make('videomixer', name + '-videomixer'))
            self.elements[-1].set_property('background', 1)

        """
        self.elements.append(Gst.ElementFactory.make('videorate', name + '-videorate'))

        ## create caps filter element to set the output video parameters
        caps_filter = Gst.ElementFactory.make('capsfilter', name + '-capsfilter3')
        caps_filter.set_property('caps', Gst.Caps.from_string("video/x-raw,framerate=5/1"))
        self.elements.append(caps_filter)
        """

        self.build_pipeline(self.elements)

        self.register_signals()

    def on_decoder_pad_added(self, element, pad):
        #caps = pad.get_current_caps()
        #if caps.to_string().startswith('video'):
            #pad.link(self.elements[0].get_static_pad('sink'))
        sinkpad = self.elements[0].get_compatible_pad(pad, pad.get_current_caps())
        pad.link(sinkpad)

    def patch(self, mode):
        obplayer.Log.log(self.name + ": patching " + mode, 'debug')

        (change, state, pending) = self.pipeline.get_state(0)
        self.wait_state(Gst.State.NULL)

        for output in mode.split('/'):
            if output not in self.mode:
                #print self.name + " -- Connecting " + output
                if self.videosink:
                    self.pipeline.remove(self.videosink)
                self.videosink = self.player.outputs[output].get_bin()
                if self.videosink:
                    self.pipeline.add(self.videosink)
                    self.elements[-1].link(self.videosink)
                self.mode.add(output)

        if state == Gst.State.PLAYING:
            self.wait_state(Gst.State.PLAYING)

    def unpatch(self, mode):
        obplayer.Log.log(self.name + ": unpatching " + mode, 'debug')

        (change, state, pending) = self.pipeline.get_state(0)
        self.wait_state(Gst.State.NULL)

        for output in mode.split('/'):
            if output in self.mode:
                #print self.name + " -- Disconnecting " + output
                if self.videosink:
                    self.pipeline.remove(self.videosink)
                    self.videosink = None
                self.mode.discard(output)

        if len(self.mode) > 0 and state == Gst.State.PLAYING:
            self.wait_state(Gst.State.PLAYING)

    def set_request(self, req):
        self.request = req
        self.decodebin.set_property('uri', req['uri'])

        self.control_source.unset_all()
        end_time = req['end_time'] - time.time()
        if end_time >= 1:
            self.control_source.set(0, 0.0)
            self.control_source.set(1 * Gst.SECOND, 1.0)
            self.control_source.set((end_time - 1) * Gst.SECOND, 1.0)
            self.control_source.set(end_time * Gst.SECOND, 0.0)



