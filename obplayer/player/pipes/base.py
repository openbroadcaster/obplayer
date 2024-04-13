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
import time
import traceback

import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstVideo", "1.0")
gi.require_version("GstController", "1.0")
from gi.repository import GObject, Gst, GstVideo, GstController


class ObGstPipeline(object):
    def __init__(self, name):
        # Gst.Bin.__init__(self)
        self.mode = set()
        self.name = name

    def start(self):
        # print(self.name + ": starting")
        self.wait_state(Gst.State.PLAYING)

    def stop(self, label=""):
        # print(self.name + ": stopping")
        obplayer.Log.log(self.name + ": stopped " + label, "debug")
        self.wait_state(Gst.State.NULL)

    def quit(self):
        self.wait_state(Gst.State.NULL)

    def is_playing(self):
        (change, state, pending) = self.pipeline.get_state(0)
        if state == Gst.State.PLAYING:
            return True
        return False

    def patch(self, mode):
        for output in mode.split("/"):
            self.mode.add(output)

    def unpatch(self, mode):
        for output in mode.split("/"):
            self.mode.discard(output)

    def set_request(self, req):
        pass

    def build_pipeline(self, elements):
        for element in elements:
            obplayer.Log.log("adding element to bin: " + element.get_name(), "debug")
            self.pipeline.add(element)
        for index in range(0, len(elements) - 1):
            elements[index].link(elements[index + 1])

    """
    def build_pipeline(self, elements):
        # TODO this totally doesn't work yet
        for element in elements:
            if type(element) != type(list):
                obplayer.Log.log("adding element to bin: " + element.get_name(), 'debug')
                self.pipeline.add(element)
        for index in range(0, len(elements) - 1):
            if type(element) == type(list):
                segment = self.build_pipeline(element)
                # TODO then add it to the pipeline
            else:
                elements[index].link(elements[index + 1])
        return
    """

    """

        self.elements = [ ]
        # TODO actually this doesn't get linked up until later, so we don't include it??
        #self.elements.append(Gst.ElementFactory.make('uridecoder', 'uridecoder'))

        self.branch1 = [ ]
        self.branch1.append(Gst.ElementFactory.make('imagefreeze', 'imagefreeze1'))
        self.branch1.append(Gst.ElementFactory.make('alpha', 'alpha1'))

        self.branch2 = [ ]
        self.branch2.append(Gst.ElementFactory.make('imagefreeze', 'imagefreeze2'))
        self.branch2.append(Gst.ElementFactory.make('alpha', 'alpha2'))

        self.elements.append([ self.branch1, self.branch2 ])
        self.elements.append(Gst.ElementFactory.make('videomixer', 'videomixer'))
    """

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
            obplayer.Log.log(
                "gstreamer failed waiting for state change to " + str(pending), "error"
            )
            # raise Exception("Failed waiting for state change")
            return False
        return True

    # sync handler (assigns video sink to drawing area)
    def sync_handler(self, bus, message):
        if message.get_structure() is None:
            return Gst.BusSyncReply.PASS
        if message.get_structure().get_name() == "prepare-window-handle":
            if obplayer.Gui.gst_xid != "Wayland":
                message.src.set_window_handle(obplayer.Gui.gst_xid)
            else:
                obplayer.Log.log(
                    message="The player doesn't support Wayland due to limited python support. The player will now restart under X11."
                )
                obplayer.Main.quit()
        return Gst.BusSyncReply.PASS

    # message handler (handles gstreamer messages posted to the bus)
    def message_handler(self, bus, message):
        if message.type == Gst.MessageType.STATE_CHANGED:
            oldstate, newstate, pending = message.parse_state_changed()
            # obplayer.Log.log("gstreamer state changed to " + str(newstate), 'debug')
            """
            if message.src == self.pipeline:
                obplayer.Log.log("State Changed to " + str(newstate), "player")
                if newstate == Gst.State.PLAYING:
                    self.is_playing.set()
                else:
                    self.is_playing.clear()
            """

        elif message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            obplayer.Log.log(
                "gstreamer error: %s, %s, %s" % (err, debug, err.code), "error"
            )
            # self.pipeline.set_state(Gst.State.READY)
            self.player.request_update.set()

        elif message.type == Gst.MessageType.WARNING:
            err, debug = message.parse_warning()
            obplayer.Log.log(
                "gstreamer warning: %s, %s, %s" % (err, debug, err.code), "warning"
            )

        elif message.type == Gst.MessageType.INFO:
            err, debug = message.parse_info()
            obplayer.Log.log(
                "gstreamer info: %s, %s, %s" % (err, debug, err.code), "info"
            )

        elif message.type == Gst.MessageType.BUFFERING:
            print("Buffering Issue")
            # percent = message.parse_buffering()
            # if percent < 100:
            #    self.pipeline.set_state(Gst.State.PAUSED)
            # else:
            #    self.pipeline.set_state(Gst.State.PLAYING)

        elif message.type == Gst.MessageType.EOS:
            obplayer.Log.log("player received end of stream signal", "debug")
            self.player.request_update.set()

        elif message.type == Gst.MessageType.ELEMENT:
            struct = message.get_structure()
            # print(struct.to_string())
            # self.player.audio_levels = [ pow(10, rms / 20) for rms in rms_values ]
            self.player.audio_levels = struct.get_value("rms")
            self.player.audio_levels_timestamp = time.time()
            """
            peaks = struct.get_value('peak')
            if peaks is None:
                self.player.audio_silence = 0
            else:
                for level in peaks:
                    if level > -60:
                        self.player.audio_silence = 0
                        return
                self.player.audio_silence += 1
            print(self.player.audio_silence)
            """

    """
    def signal_about_to_finish(self, message):
        print("About to finish")
        with self.lock:
            for ctrl in self.controllers:
                # TODO this function needs to 
                req = ctrl.get_next_request()
                # you can't just play the request... you need a function that just sets the uri, does the playlog, and all the log statements
    """
