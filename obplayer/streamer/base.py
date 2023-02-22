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
from gi.repository import GObject, Gst


class ObGstStreamer (object):
    def __init__(self, name):
        self.name = name
        self.pipeline = Gst.Pipeline()

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.message_handler)

    def start(self):
        obplayer.Log.log("starting {0} streamer".format(self.name), 'debug')
        self.pipeline.set_state(Gst.State.PLAYING)

    def stop(self):
        obplayer.Log.log("stopping {0} streamer".format(self.name), 'debug')
        self.pipeline.set_state(Gst.State.NULL)

    def quit(self):
        self.pipeline.set_state(Gst.State.NULL)

    def restart_pipeline(self):
        self.wait_state(Gst.State.NULL)
        self.wait_state(Gst.State.PLAYING)

    def is_playing(self):
        (change, state, pending) = self.pipeline.get_state(0)
        if state == Gst.State.PLAYING:
            return True
        return False

    def build_pipeline(self, elements):
        for element in elements:
            obplayer.Log.log("adding element to bin: " + element.get_name(), 'debug')
            self.pipeline.add(element)
        for index in range(0, len(elements) - 1):
            elements[index].link(elements[index + 1])

    def register_signals(self):
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("sync-message::element", self.sync_handler)
        bus.connect("message", self.message_handler)

    def wait_state(self, target_state):
        self.pipeline.set_state(target_state)
        (statechange, state, pending) = self.pipeline.get_state(timeout=5 * Gst.SECOND)
        if statechange != Gst.StateChangeReturn.SUCCESS:
            obplayer.Log.log("gstreamer failed waiting for state change to " + str(pending), 'error')
            #raise Exception("Failed waiting for state change")
            return False
        return True

    # message handler (handles gstreamer messages posted to the bus)
    def message_handler(self, bus, message):
        if message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            obplayer.Log.log("gstreamer error: %s, %s, %s" % (err, debug, err.code), 'error')
            obplayer.Log.log("attempting to restart {0} pipeline".format(self.name), 'info')
            GObject.timeout_add(5000, self.restart_pipeline)

        elif message.type == Gst.MessageType.WARNING:
            err, debug = message.parse_warning()
            obplayer.Log.log("gstreamer warning: %s, %s, %s" % (err, debug, err.code), 'warning')

        elif message.type == Gst.MessageType.INFO:
            err, debug = message.parse_info()
            obplayer.Log.log("gstreamer info: %s, %s, %s" % (err, debug, err.code), 'info')


