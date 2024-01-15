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
from gi.repository import GObject, Gst, GstVideo, GstController

from .base import ObGstPipeline

class ObAlertPipeline (ObGstPipeline):
    min_class = [ 'alert' ]
    max_class = [ 'alert' ]
    playbin = False

    def __init__(self, name, player):
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
            self.pipeline = Gst.ElementFactory.make("playbin", "playbin")
            self.pipeline.set_property("uri", req['uri'])
            self.pipeline.set_property("audio-sink", Gst.ElementFactory.make("interpipesink", 'interpipe-alert'))
            self.pipeline.set_state(Gst.State.PAUSED)

        else:
            self.pipeline = Gst.parse_launch('audiotestsrc ! audioconvert ! fakesink')