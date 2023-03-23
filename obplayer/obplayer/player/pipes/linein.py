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
import atexit

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst, GstVideo

from .base import ObGstPipeline


class ObLineInPipeline (ObGstPipeline):
    min_class = [ 'audio' ]
    max_class = [ 'audio' ]

    def __init__(self, name, player):
        ObGstPipeline.__init__(self, name)
        self.player = player

        self.pipeline = Gst.Pipeline(name)
        self.elements = [ ]

        self.log = obplayer.Config.setting('audio_in_log')

        audio_input = obplayer.Config.setting('audio_in_mode')
        if audio_input == 'alsa':
            self.audiosrc = Gst.ElementFactory.make('alsasrc', name + '-src')
            alsa_device = obplayer.Config.setting('audio_in_alsa_device')
            if alsa_device != '':
                self.audiosrc.set_property('device', alsa_device)

        elif audio_input == 'jack':
            self.audiosrc = Gst.ElementFactory.make('jackaudiosrc', name + '-src')
            self.audiosrc.set_property('connect', 0)  # don't autoconnect ports.
            name = obplayer.Config.setting('audio_in_jack_name')
            self.audiosrc.set_property('client-name', name if name else 'obplayer')

        elif audio_input == 'oss':
            self.audiosrc = Gst.ElementFactory.make('osssrc', name + '-src')

        elif audio_input == 'pulse':
            self.audiosrc = Gst.ElementFactory.make('pulsesrc', name + '-src')
            self.audiosrc.set_property('client-name', 'obplayer-pipe: line-in')

        elif audio_input == 'test':
            self.audiosrc = Gst.ElementFactory.make('fakesrc', name + '-src')

        else:
            self.audiosrc = Gst.ElementFactory.make('autoaudiosrc', name + '-src')

        self.elements.append(self.audiosrc)

        self.queue = Gst.ElementFactory.make('queue2', name + '-queue')
        self.elements.append(self.queue)

        self.is_silent = True
        self.silence_callback = None
        self.last_change = None
        if obplayer.Config.setting('audio_in_disable_on_silence'):
            self.detect_silence = True
            self.level = Gst.ElementFactory.make("level", name + '-level')
            self.level.set_property('message', True)
            self.level.set_property('interval', int(0.5 * Gst.SECOND))
            self.elements.append(self.level)
        else:
            self.detect_silence = False

        self.audioconvert = Gst.ElementFactory.make('audioconvert', name + '-convert')
        self.elements.append(self.audioconvert)

        self.build_pipeline(self.elements)

        # bin for handling file output
        if self.log:
            self.logfilename = None
            self.logbin = Gst.ElementFactory.make('bin', name + '-logbin')
            self.logtee = Gst.ElementFactory.make('tee', name + '-logtee')
            self.logqueue1 = Gst.ElementFactory.make('queue2', name + '-queue1')
            self.logenc = Gst.ElementFactory.make('vorbisenc', name + '-logenc')
            self.logmux = Gst.ElementFactory.make('oggmux', name + '-logmux')
            self.logqueue2 = Gst.ElementFactory.make('queue2', name + '-queue2')
            self.logsink = Gst.ElementFactory.make('filesink', name + '-logsink')
            self.logbin.add(self.logtee)
            self.logbin.add(self.logqueue1)
            self.logbin.add(self.logenc)
            self.logbin.add(self.logmux)
            self.logbin.add(self.logqueue2)
            self.logbin.add(self.logsink)
            self.logtee.link(self.logqueue1)
            self.logqueue1.link(self.logenc)
            self.logenc.link(self.logmux)
            self.logmux.link(self.logqueue2)
            self.logqueue2.link(self.logsink)
            self.logbin_sinkpad = Gst.GhostPad.new('sink', self.logtee.get_static_pad('sink'))
            self.logbin.add_pad(self.logbin_sinkpad)
            
            # unlock logfile if program exits while recording
            atexit.register(self.unlock_logfile)

        self.audiosink = None
        self.fakesink = Gst.ElementFactory.make('fakesink', name + '-fakesink')
        self.set_property('audio-src', self.fakesink)

        self.register_signals()

        if self.detect_silence:
            self.pipeline.get_bus().add_signal_watch()
            self.pipeline.get_bus().connect('message::element', self.msg_detect_silence)
            self.unpatch('audio')
            self.start()

    def unlock_logfile(self):
        if self.log and self.logfilename:
            os.rename(self.logfilename, self.logfilename[:-5])
            self.logfilename = None

    def set_property(self, property, value):
        if property == 'audio-sink':
        
            # this happens after init so we know these elements are available to remove
            if self.audiosink:
                self.pipeline.remove(self.audiosink)
                if value == self.fakesink and self.log:
                    self.pipeline.remove(self.logbin)
                    
            self.audiosink = value
            
            if self.audiosink: 
            
                if value == self.fakesink or self.log == False:
                    self.pipeline.add(self.audiosink)
                    self.audioconvert.link(self.audiosink)
                    self.unlock_logfile()
                    
                else:
                    self.pipeline.add(self.logbin)
                    self.logfilename = obplayer.ObData.get_datadir() + '/lineinlogs/' + time.strftime('%Y%m%d-%H%M%S') + '.ogg.lock';
                    self.pipeline.add(self.audiosink)
                    self.logsink.set_property('location',self.logfilename)
                    self.audioconvert.link(self.logbin)
                    self.logtee.link(self.audiosink)

    def patch(self, mode):
        obplayer.Log.log(self.name + ": patching " + mode, 'debug')

        self.wait_state(Gst.State.NULL)
        if 'audio' in mode:
            self.set_property('audio-sink', self.player.outputs['audio'].get_bin())
        ObGstPipeline.patch(self, mode)

        self.wait_state(Gst.State.PLAYING)
        if obplayer.Config.setting('gst_init_callback'):
            os.system(obplayer.Config.setting('gst_init_callback'))

    def unpatch(self, mode):
        obplayer.Log.log(self.name + ": unpatching " + mode, 'debug')

        self.wait_state(Gst.State.NULL)
        if 'audio' in mode:
            self.set_property('audio-sink', self.fakesink)
        ObGstPipeline.unpatch(self, mode)
        if len(self.mode) > 0 or self.detect_silence:
            self.wait_state(Gst.State.PLAYING)
            if obplayer.Config.setting('gst_init_callback'):
                os.system(obplayer.Config.setting('gst_init_callback'))

    def set_silence_callback(self, callback):
        self.silence_callback = callback
        if self.silence_callback:
            self.silence_callback(self.is_silent)

    def msg_detect_silence(self, bus, message, *args):
        peak = message.get_structure().get_value('peak')
        if peak[0] < float(obplayer.Config.setting('audio_in_threshold')):
            if not self.is_silent:
                obplayer.Log.log(self.name + ": silence detected (threshold: " + str(obplayer.Config.setting('audio_in_threshold')) + " dB, disable time: " + str(obplayer.Config.setting('audio_in_disable_time')) + "s)", 'debug')      
                self.is_silent = True
                self.last_change = time.time()
        else:
            if self.is_silent:
                obplayer.Log.log(self.name + ": audio detected (threshold: " + str(obplayer.Config.setting('audio_in_threshold')) + " dB, enable time: " + str(obplayer.Config.setting('audio_in_enable_time')) + "s)", 'debug') 
                obplayer.Log.log(self.name + ": enable time is " + str(obplayer.Config.setting('audio_in_enable_time')) + " seconds", 'debug')
                self.is_silent = False
                self.last_change = time.time()
        
        if self.is_silent:
            wait_time = float(obplayer.Config.setting('audio_in_disable_time'))
        else:
            wait_time = float(obplayer.Config.setting('audio_in_enable_time'))
                
        if self.last_change is not None and (time.time() - self.last_change) > wait_time:
            self.last_change = None
            if self.silence_callback:
                self.silence_callback(self.is_silent)
        return True
