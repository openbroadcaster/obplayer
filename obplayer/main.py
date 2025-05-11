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

from obplayer.alert_counter import *

import sys
import time
import signal
import traceback

import argparse

import gi
from gi.repository import GObject

GObject.threads_init()


class ObMainApp:

    def __init__(self):
        self.modules = []
        self.exit_code = 0
        self.lock_file = "/tmp/obplayer.gui.lock"

        parser = argparse.ArgumentParser(
            prog="obplayer",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description="OpenBroadcaster Player",
        )
        parser.add_argument(
            "-f",
            "--fullscreen",
            action="store_true",
            help="start fullscreen",
            default=False,
        )
        parser.add_argument(
            "-m",
            "--minimize",
            action="store_true",
            help="start minimized",
            default=False,
        )
        parser.add_argument(
            "-r",
            "--reset",
            action="store_true",
            help="reset show, media, and priority broadcast databases",
            default=False,
        )
        parser.add_argument(
            "-H",
            "--headless",
            action="store_true",
            help="run headless (audio only)",
            default=False,
        )
        parser.add_argument(
            "-d",
            "--debug",
            action="store_true",
            help="print log messages to stdout",
            default=False,
        )
        parser.add_argument(
            "-c",
            "--configdir",
            nargs=1,
            help="specifies an alternate data directory",
            default=["~/.openbroadcaster"],
        )
        parser.add_argument(
            "--disable-http",
            action="store_true",
            help="disables the http admin",
            default=False,
        )
        parser.add_argument(
            "--disable-updater",
            action="store_true",
            help="disables the OS updater",
            default=False,
        )
        parser.add_argument(
            "--desktop",
            action="store_true",
            help="Handles desktop video output. This is only to prevent mutiple players with video playback.",
            default=False,
        )

        self.args = parser.parse_args()
        obplayer.ObData.set_datadir(self.args.configdir[0])

        if (
            os.access(self.lock_file, os.F_OK)
            and self.args.desktop
            and self.args.headless == False
        ):
            # print(self.args.desktop)
            print("Another player is already running...")
            exit(1)

        with open(self.lock_file, "w") as file:
            file.write("Please do not remove this file.")

        obplayer.Log = obplayer.ObLog()
        obplayer.Log.set_debug(self.args.debug)

        obplayer.Config = obplayer.ObConfigData()

        obplayer.Config.args = self.args

        if os.environ["HOME"] != None:
            obplayer.SUPPORTED = bool(int(os.environ.get("OBPLAYER_SUPPORTED", "0")))

        if self.args.headless is True:
            obplayer.Config.headless = self.args.headless

        obplayer.Main = self

    def start(self):
        signal.signal(signal.SIGINT, self.sigint_handler)

        try:
            self.loop = GObject.MainLoop()

            obplayer.Gui = obplayer.ObGui()
            obplayer.Gui.create_window()

            self.load_module("player")
            self.load_module("httpadmin")

            if (
                obplayer.Config.setting("audio_out_mode") == "pulse"
                or obplayer.Config.setting("audio_in_mode") == "pulse"
            ):
                self.load_module("pulse")
            if not obplayer.Config.headless:
                self.load_module("xrandr")
            if obplayer.Config.setting("testsignal_enable"):
                self.load_module("testsignal")
            if obplayer.Config.setting("alerts_enable"):
                self.load_module("alerts")
            if obplayer.Config.setting("fallback_enable"):
                self.load_module("fallback")
            if obplayer.Config.setting("aoip_in_enable"):
                self.load_module("aoipin")
            if obplayer.Config.setting("rtp_in_enable"):
                self.load_module("rtpin")
            if obplayer.Config.setting("audio_in_enable"):
                self.load_module("linein")
            if obplayer.Config.setting("scheduler_enable"):
                self.load_module("scheduler")
            if obplayer.Config.setting("live_assist_enable"):
                self.load_module("liveassist")
            if obplayer.Config.setting("audiolog_enable"):
                self.load_module("audiolog")
            if obplayer.Config.setting("offair_audiolog_enable"):
                self.load_module("offair_audiolog")
            if obplayer.Config.setting("streamer_enable"):
                self.load_module("streamer")
            if obplayer.Config.setting("station_override_enabled"):
                self.load_module("override_streamer")
            if obplayer.Config.setting("newsfeed_override_enabled"):
                self.load_module("newsfeed_override")

            obplayer.Player.start_player()
            self.loop.run()
        except KeyboardInterrupt:
            print("Keyboard Interrupt")
        except:
            obplayer.Log.log(
                "exception occurred in main thead. Terminating...", "error"
            )
            obplayer.Log.log(traceback.format_exc(), "error")

        self.application_shutdown()

    def quit(self):
        self.loop.quit()

    def sigint_handler(self, signal, frame):
        self.quit()

    def application_shutdown(self):
        obplayer.Log.log("shutting down player...", "debug")

        # call quit() or all modules to allow them to shutdown
        self.quit_modules()

        # send stop signals to all threads
        obplayer.ObThread.stop_all()

        # wait for all threads to complete
        obplayer.ObThread.join_all()

        if os.access(self.lock_file, os.F_OK):
            os.remove(self.lock_file)

        # quit main thread.
        sys.exit(self.exit_code)

    def load_module(self, name):
        if name in self.modules:
            return
        obplayer.Log.log("loading module " + name, "module")
        exec("import obplayer.%s; obplayer.%s.init()" % (name, name))
        self.modules.append(name)

    def quit_modules(self):
        for name in self.modules:
            exec("obplayer.%s.quit()" % (name,))
