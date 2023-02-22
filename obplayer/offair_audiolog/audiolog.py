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
import os.path
import time
import datetime
import traceback

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
from .recorder import Recorder

AUDIOLOG_SAMPLE_RATE = '22050'
AUDIOLOG_CHANNELS = '1'

# class Recorder(threading.Thread):
#     def __init__(self, fm_feq, sample_rate):
#         obplayer.ObThread.__init__(self, 'Oboff_air_AudioLog-Recorder')
#         self.daemon = True
#         self.audio_data = []
#         self.recording = False
#         self.process = subprocess.Popen(['rtl_fm', '-f', fm_feq, '-m', 'wbfm', '-r', sample_rate], stdout=subprocess.PIPE)
#         self._record_audio()
#
#     def _record_audio(self):
#         self.recording = True
#         while self.recording:
#             self.audio_data.append(self.process.read())
#
#     def get_audio(self):
#         return self.audio_data
#
#     def stop(self):
#         self.recording = False

class Oboff_air_AudioLog (object):
    def __init__(self):
        self.recording = False
        self.purge_files = obplayer.Config.setting('audiolog_purge_files')
        self.date = time.strftime('%Y-%m-%d-%H')
        self.audio_data = []
        self.recorder = None
        self.start()
        # try:
        #     self.sdr = RtlSdr()
        # except Exception as OSError:
        #     obplayer.Log.log("Could not start off-air audio log.\n\
        #     Make sure your sdr is connected.", 'offair-audiolog')
        #     self.sdr = None
        # if self.sdr != None:
        #     self.sample_rate = AUDIOLOG_SAMPLE_RATE
        #     self.fm_feq = obplayer.Config.setting('offair_audiolog_feq')
        #     self.start()

    def start(self):
        if self.recording == False:
            self.outfile = obplayer.ObData.get_datadir() + '/offair-audiologs/' + time.strftime('%Y-%m-%d_%H:%M:%S') + '.wav'
            self.recorder = Recorder(self.outfile)
            self.recorder.start()
            #self.recorder.join()
            # log that a new recording is being started.
            obplayer.Log.log("starting new off-air audio log", 'offair-audiolog')
            self.log_rotate()
        else:
            # log if already recording.
            obplayer.Log.log("can't start new off-air audio log because already recording log.", 'offair-audiolog')

    def stop(self):
        self.recording = False
        self.recorder.stop()

    def log_rotate(self):
        if self.date != time.strftime('%Y-%m-%d-%H'):
            self.date = time.strftime('%Y-%m-%d-%H')
            self.stop()
            self.start()
            if self.purge_files:
                self.log_purge()
        GObject.timeout_add(10.0, self.log_rotate)

    def log_purge(self):
        basedir = obplayer.ObData.get_datadir() + "/offair-audiologs"
        then = datetime.datetime.now() - datetime.timedelta(days=90)

        for filename in os.listdir(basedir):
            parts = filename[:10].split('-')
            if len(parts) != 3:
                continue
            filedate = datetime.datetime(int(parts[0]), int(parts[1]), int(parts[2]))
            if filedate < then:
                obplayer.Log.log("deleting audiolog file " + filename, 'debug')
                os.remove(os.path.join(basedir, filename))
