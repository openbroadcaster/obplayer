#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Copyright 2012-2024 OpenBroadcaster, Inc.

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

gi.require_version("Gst", "1.0")
from gi.repository import GObject, Gst, GstVideo, GstController

from .base import ObGstPipeline


class ObAudioPipeline(ObGstPipeline):
    def __init__(self, name, player):
        ObGstPipeline.__init__(self, name)

        self.player = player

        # make the rest of the code happy by having a pipeline all the time
        self.pipeline = Gst.parse_launch("audiotestsrc ! audioconvert ! fakesink")
        self.pipeline.set_state(Gst.State.PAUSED)

    def set_request(self, req):
        self.mixer_off()

        self.pipeline.set_state(Gst.State.NULL)
        self.pipeline.get_state(Gst.CLOCK_TIME_NONE)
        self.pipeline = False

        if req["uri"]:
            # remove file:// from req['uri']
            if req["uri"].startswith("file://"):
                req["uri"] = req["uri"][7:]

            self.pipeline = Gst.parse_launch(
                "filesrc name=filesrc ! decodebin ! audioconvert ! audioresample ! capsfilter caps=audio/x-raw,format=S16LE,rate=44100,layout=interleaved,channels=2 ! interpipesink sync=true name="
                + self.interpipe_name
            )
            self.pipeline.get_by_name("filesrc").set_property("location", req["uri"])

        else:
            self.pipeline = Gst.parse_launch("audiotestsrc ! audioconvert ! fakesink")

        self.pipeline.set_state(Gst.State.PAUSED)
        self.pipeline.get_state(Gst.CLOCK_TIME_NONE)

        self.mixer_on()


class ObAlertPipeline(ObAudioPipeline):

    min_class = ["alert"]
    max_class = ["alert"]
    interpipe_name = "interpipe-alert"

    def mixer_on(self):
        self.player.outputs["mixer"].alert_on()

    def mixer_off(self):
        self.player.outputs["mixer"].alert_off()


class ObVoicetrackPipeline(ObAudioPipeline):

    min_class = ["voicetrack"]
    max_class = ["voicetrack"]
    interpipe_name = "interpipe-voicetrack"

    def mixer_on(self):
        self.player.outputs["mixer"].voicetrack_on()

    def mixer_off(self):
        self.player.outputs["mixer"].voicetrack_off()
