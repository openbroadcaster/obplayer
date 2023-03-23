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

AUDIOLOG_SAMPLE_RATE = '22050'
AUDIOLOG_CHANNELS = '1'

class ObAudioLog (object):
    def __init__(self):
        self.purge_files = obplayer.Config.setting('audiolog_purge_files')
        self.pipeline = None
        self.date = time.strftime('%Y-%m-%d-%H')
        self.start()

    def start(self):
        obplayer.Log.log("starting new audio log", 'audiolog')
        outfile = obplayer.ObData.get_datadir() + '/audiologs/' + time.strftime('%Y-%m-%d_%H:%M:%S') + '.ogg'

        """
        audio_output = obplayer.Config.setting('audio_out_mode')
        #launchcmd = 'pulsesrc device=' + self.args.alsa_device \
        launchcmd = 'pulsesrc client-name="obplayer-audiolog"' \
                    + ' ! audioconvert ! audioresample ' \
                    + ' ! audio/x-raw, rate=' + AUDIOLOG_SAMPLE_RATE + ', channels=' + AUDIOLOG_CHANNELS \
                    + ' ! queue ! vorbisenc quality=0.0 ! oggmux ! queue ! filesink location=' + outfile
        self.pipeline = Gst.parse_launch(launchcmd)
        """

        self.pipeline = Gst.Pipeline()

        self.elements = [ ]

        # NOTE we are using the main audio output mode here to determine the audio input mode, since they should match
        audio_input = obplayer.Config.setting('audio_out_mode')
        if audio_input == 'alsa':
            self.audiosrc = Gst.ElementFactory.make('alsasrc', 'audiosrc')
            alsa_device = obplayer.Config.setting('audio_out_alsa_device')
            if alsa_device != '':
                self.audiosrc.set_property('device', alsa_device)

        elif audio_input == 'jack':
            self.audiosrc = Gst.ElementFactory.make('jackaudiosrc', 'audiosrc')
            self.audiosrc.set_property('connect', 0)  # don't autoconnect ports.
            self.audiosrc.set_property('client-name', 'obplayer-audiolog')

        elif audio_input == 'oss':
            self.audiosrc = Gst.ElementFactory.make('osssrc', 'audiosrc')

        elif audio_input == 'pulse':
            self.audiosrc = Gst.ElementFactory.make('pulsesrc', 'audiosrc')
            self.audiosrc.set_property('client-name', 'obplayer-audiolog')

        elif audio_input == 'test':
            self.audiosrc = Gst.ElementFactory.make('fakesrc', 'audiosrc')

        else:
            self.audiosrc = Gst.ElementFactory.make('autoaudiosrc', 'audiosrc')
        self.elements.append(self.audiosrc)

        self.elements.append(Gst.ElementFactory.make('audioconvert'))
        self.elements.append(Gst.ElementFactory.make('audioresample'))

        ## create caps filter element to set the output audio parameters
        self.audiocaps = Gst.ElementFactory.make('capsfilter')
        self.audiocaps.set_property('caps', Gst.Caps.from_string('audio/x-raw, rate=' + AUDIOLOG_SAMPLE_RATE + ', channels=' + AUDIOLOG_CHANNELS))
        self.elements.append(self.audiocaps)

        self.elements.append(Gst.ElementFactory.make('queue2'))

        self.encoder = Gst.ElementFactory.make('vorbisenc')
        self.encoder.set_property('quality', 0.0)
        self.elements.append(self.encoder)

        self.elements.append(Gst.ElementFactory.make('oggmux'))
        self.elements.append(Gst.ElementFactory.make('queue2'))

        self.filesink = Gst.ElementFactory.make('filesink')
        self.filesink.set_property('location', outfile)
        self.elements.append(self.filesink)

        self.build_pipeline(self.elements)
        self.pipeline.set_state(Gst.State.PLAYING)
        self.log_rotate()


    def stop(self):
        self.pipeline.set_state(Gst.State.NULL)
        self.pipeline = None

    def build_pipeline(self, elements):
        for element in elements:
            #print("adding element to bin: " + element.get_name())
            self.pipeline.add(element)
        for index in range(0, len(elements) - 1):
            elements[index].link(elements[index + 1])

    def log_rotate(self):
        if self.date != time.strftime('%Y-%m-%d-%H'):
            self.date = time.strftime('%Y-%m-%d-%H')
            self.stop()
            self.start()
            if self.purge_files:
                self.log_purge()
        GObject.timeout_add(10.0, self.log_rotate)

    def log_purge(self):
        basedir = obplayer.ObData.get_datadir() + "/audiologs"
        then = datetime.datetime.now() - datetime.timedelta(days=90)

        for filename in os.listdir(basedir):
            parts = filename[:10].split('-')
            if len(parts) != 3:
                continue
            filedate = datetime.datetime(int(parts[0]), int(parts[1]), int(parts[2]))
            if filedate < then:
                obplayer.Log.log("deleting audiolog file " + filename, 'debug')
                os.remove(os.path.join(basedir, filename))
