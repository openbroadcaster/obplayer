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
        self.modules = [ ]
        self.exit_code = 0

        parser = argparse.ArgumentParser(prog='obplayer', formatter_class=argparse.ArgumentDefaultsHelpFormatter, description='OpenBroadcaster Player')
        parser.add_argument('-f', '--fullscreen', action='store_true', help='start fullscreen', default=False)
        parser.add_argument('-m', '--minimize', action='store_true', help='start minimized', default=False)
        parser.add_argument('-r', '--reset', action='store_true', help='reset show, media, and priority broadcast databases', default=False)
        parser.add_argument('-H', '--headless', action='store_true', help='run headless (audio only)', default=False)
        parser.add_argument('-d', '--debug', action='store_true', help='print log messages to stdout', default=False)
        parser.add_argument('-c', '--configdir', nargs=1, help='specifies an alternate data directory', default=[ '~/.openbroadcaster' ])
        parser.add_argument('--disable-http', action='store_true', help='disables the http admin', default=False)

        self.args = parser.parse_args()
        obplayer.ObData.set_datadir(self.args.configdir[0])

        obplayer.Log = obplayer.ObLog()
        obplayer.Log.set_debug(self.args.debug)

        obplayer.Config = obplayer.ObConfigData()

        obplayer.Config.args = self.args

        if self.args.headless is True:
            obplayer.Config.headless = self.args.headless

        obplayer.Main = self

    def start(self):
        signal.signal(signal.SIGINT, self.sigint_handler)

        try:
            self.loop = GObject.MainLoop()

            obplayer.Gui = obplayer.ObGui()
            obplayer.Gui.create_window()

            self.load_module('player')
            self.load_module('httpadmin')

            if obplayer.Config.setting('audio_out_mode') == 'pulse' or obplayer.Config.setting('audio_in_mode') == 'pulse':
                self.load_module('pulse')
            if not obplayer.Config.headless:
                self.load_module('xrandr')
            if obplayer.Config.setting('testsignal_enable'):
                self.load_module('testsignal')
            if obplayer.Config.setting('alerts_enable'):
                self.load_module('alerts')
            if obplayer.Config.setting('fallback_enable'):
                self.load_module('fallback')
            if obplayer.Config.setting('aoip_in_enable'):
                self.load_module('aoipin')
            if obplayer.Config.setting('rtp_in_enable'):
                self.load_module('rtpin')
            if obplayer.Config.setting('audio_in_enable'):
                self.load_module('linein')
            if obplayer.Config.setting('scheduler_enable'):
                self.load_module('scheduler')
            if obplayer.Config.setting('live_assist_enable'):
                self.load_module('liveassist')
            if obplayer.Config.setting('audiolog_enable'):
                self.load_module('audiolog')
            if obplayer.Config.setting('offair_audiolog_enable'):
               self.load_module('offair_audiolog')
            if obplayer.Config.setting('streamer_enable'):
                self.load_module('streamer')
            if obplayer.Config.setting('station_override_enabled'):
                self.load_module('override_streamer')
            if obplayer.Config.setting('newsfeed_override_enabled'):
                self.load_module('newsfeed_override')


            #### TEST CODE ####

            #time.sleep(2)

            #alert = obplayer.alerts.parse_alert_file("/media/work/Projects/OpenBroadcaster/Information/2014-08 Pelmorex Tie-In/CAP Examples/2example_CAPCP_with_Embedded_Large_Audio_File(2).xml")
            #alert = obplayer.alerts.parse_alert_file("/media/work/Projects/OpenBroadcaster/Information/2014-08 Pelmorex Tie-In/CAP Examples/4example_CAPCP_with_External_Large_Audio_File(2).xml")
            #obplayer.alerts.Processor.dispatch(alert)

            #ctrl = obplayer.Player.create_controller('testsource', 60, default_play_mode='overlap')
            #ctrl.add_request(media_type='break', duration=40)
            #ctrl.add_request(media_type='testsignal', duration=40)
            #ctrl.add_request(media_type='video', uri="file:///home/trans/.openbroadcaster/fallback_media/110-Unknown-The_Return_Of_Doctor_X.ogg", duration=153)
            #ctrl.add_request(media_type='audio', start_time=time.time() + 5, uri="file:///home/trans/.openbroadcaster/alerts/2014_12_01T00_13_00_00_00I2.49.0.1.124.b7fb9ec4.2014", duration=10)
            #ctrl.add_request(media_type='video', uri="file:///home/trans/.openbroadcaster/fallback_media/110-Unknown-The_Return_Of_Doctor_X.ogg", duration=153)
            #ctrl.add_request(media_type='image', start_time=time.time(), uri="file:///home/trans/.openbroadcaster/fallback_media/97-ctfn_potlatch-sdfsdg.svg", duration=5)
            #ctrl.add_request(media_type='audio', start_time=time.time(), uri="file:///home/trans/.openbroadcaster/fallback_media/104-Lamb-Piste_6.mp3", duration=70)
            #ctrl.add_request(media_type='audio', start_time=time.time(), uri="file:///home/trans/.openbroadcaster/alerts-backup/2014_07_08T10_09_38_05_00I473E9B47_D474_B3F1_9765_1AFED0761075-english.wav", duration=70)
            #ctrl.add_request(media_type='video', start_time=time.time() + 2, uri="file:///home/trans/.openbroadcaster/fallback_media/109-Unknown-The_Pit_And_The_Pendulum.ogg", duration=153)
            #ctrl.add_request(media_type='rtsp', start_time=time.time() + 2, uri="rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mov", duration=153)
            #ctrl.add_request(media_type='sdp', start_time=time.time() + 2, uri="file:///home/obsuser/xnode-rtsp.sdp", duration=3600)
            #ctrl.add_request(media_type='sdp', start_time=time.time() + 2, uri="file:///media/work/OpenBroadcaster/Player/tools/local_streamer.sdp", duration=3600)
            #ctrl.add_request(media_type='rtp', start_time=time.time() + 2, duration=3600)
            #ctrl.add_request(media_type='rtsp', start_time=time.time() + 2, uri="rtsp://localhost:8554/by-id/1", duration=153)
            #ctrl.add_request(media_type='rtspa', start_time=time.time() + 2, uri="rtsp://localhost:8554/by-id/1", duration=153)

            #alertctrl = obplayer.Player.create_controller('testalert', 100, default_play_mode='overlap', allow_overlay=True)
            #alertctrl.add_request(media_type='audio', start_time=time.time() + 7, uri=obplayer.Player.file_uri("obplayer/alerts/data", "attention-signal.ogg"), duration=4)
            #alertctrl.add_request(media_type='audio', uri="file:///home/trans/.openbroadcaster/alerts/2014_12_01T00_13_00_00_00I2.49.0.1.124.b7fb9ec4.2014", duration=5)

            #ctrl.add_request(media_type='rtp_2', start_time=time.time() + 2, duration=3600)

            #ctrl.add_request(media_type='rtp_2', start_time=time.time() + 2, duration=3600)

            #### END TEST CODE ####

            obplayer.Player.start_player()
            self.loop.run()
        except KeyboardInterrupt:
            print("Keyboard Interrupt")
        except:
            obplayer.Log.log("exception occurred in main thead. Terminating...", 'error')
            obplayer.Log.log(traceback.format_exc(), 'error')

        self.application_shutdown()

    def quit(self):
        self.loop.quit()

    def sigint_handler(self, signal, frame):
        self.quit()

    def application_shutdown(self):
        obplayer.Log.log("shutting down player...", 'debug')

        # call quit() or all modules to allow them to shutdown
        self.quit_modules()

        # send stop signals to all threads
        obplayer.ObThread.stop_all()

        # wait for all threads to complete
        obplayer.ObThread.join_all()

        # quit main thread.
        sys.exit(self.exit_code)

    def load_module(self, name):
        if name in self.modules:
            return
        obplayer.Log.log('loading module ' + name, 'module')
        exec('import obplayer.%s; obplayer.%s.init()' % (name, name))
        self.modules.append(name)

    def quit_modules(self):
        for name in self.modules:
            exec('obplayer.%s.quit()' % (name,))
