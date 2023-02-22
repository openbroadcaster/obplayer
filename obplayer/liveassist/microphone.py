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
import json
import traceback
import threading

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst, GstVideo


class ObLiveAssistMicrophone (object):
    def __init__(self, conn, mode, params):
        self.conn = conn
        self.mode = mode

        self.encoder = None
        self.microphone_queue = [ ]
        self.monitor_queue = bytearray()
        self.lock = threading.Lock()
        self.pipeline = Gst.Pipeline()

        self.volume = None
        self.appsink = None
        self.appsrc = None

        if mode == 'mic' or mode == 'mic+monitor':
            self.add_microphone()
        if mode == 'monitor' or mode == 'mic+monitor':
            self.add_monitor()

        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self.message_handler)

        self.change_format(params)

    def add_microphone(self):
        elements = [ ]

        #elements.append(Gst.ElementFactory.make('autoaudiosrc', 'audiomixer-src'))
        self.appsrc = Gst.ElementFactory.make('appsrc', 'audiomixer-src')
        self.appsrc.set_property('is-live', True)
        self.appsrc.set_property('format', 3)
        #self.appsrc.set_property('caps', Gst.Caps.from_string("audio/x-raw,channels=1,rate=" + str(self.rate) + ",format=S16LE,layout=interleaved"))
        self.appsrc.connect("need-data", self.cb_need_data)
        elements.append(self.appsrc)

        self.volume = Gst.ElementFactory.make('volume', 'audiomixer-volume')
        elements.append(self.volume)

        self.level = Gst.ElementFactory.make("level", "level")
        self.level.set_property('interval', int(0.5 * Gst.SECOND))
        elements.append(self.level)

        elements.append(Gst.ElementFactory.make('queue2'))

        ## create audio sink element
        audio_output = obplayer.Config.setting('live_assist_mic_mode')
        if audio_output == 'alsa':
            self.audiosink = Gst.ElementFactory.make('alsasink', 'audiosink')
            alsa_device = obplayer.Config.setting('live_assist_mic_alsa_device')
            if alsa_device != '':
                self.audiosink.set_property('device', alsa_device)

        elif audio_output == 'esd':
            self.audiosink = Gst.ElementFactory.make('esdsink', 'audiosink')

        elif audio_output == 'jack':
            self.audiosink = Gst.ElementFactory.make('jackaudiosink', 'audiosink')
            self.audiosink.set_property('connect', 0)  # don't autoconnect ports.
            name = obplayer.Config.setting('live_assist_mic_jack_name')
            self.audiosink.set_property('client-name', name if name else 'obplayer-liveassist-mic')

        elif audio_output == 'oss':
            self.audiosink = Gst.ElementFactory.make('osssink', 'audiosink')

        elif audio_output == 'pulse':
            self.audiosink = Gst.ElementFactory.make('pulsesink', 'audiosink')
            self.audiosrc.set_property('client-name', 'obplayer-liveassist: microphone')

        elif audio_output == 'test':
            self.audiosink = Gst.ElementFactory.make('fakesink', 'audiosink')

        else:
            self.audiosink = Gst.ElementFactory.make('autoaudiosink', 'audiosink')

        elements.append(self.audiosink)

        self.build_pipeline(elements)

    def add_monitor(self):
        elements = [ ]

        audio_input = obplayer.Config.setting('live_assist_monitor_mode')
        if audio_input == 'alsa':
            self.audiosrc = Gst.ElementFactory.make('alsasrc', 'audiosrc')
            alsa_device = obplayer.Config.setting('live_assist_monitor_alsa_device')
            if alsa_device != '':
                self.audiosrc.set_property('device', alsa_device)

        elif audio_input == 'jack':
            self.audiosrc = Gst.ElementFactory.make('jackaudiosrc', 'audiosrc')
            self.audiosrc.set_property('connect', 0)  # don't autoconnect ports.
            name = obplayer.Config.setting('live_assist_monitor_jack_name')
            self.audiosrc.set_property('client-name', name if name else 'obplayer-liveassist-monitor')

        elif audio_input == 'oss':
            self.audiosrc = Gst.ElementFactory.make('osssrc', 'audiosrc')

        elif audio_input == 'pulse':
            self.audiosrc = Gst.ElementFactory.make('pulsesrc', 'audiosrc')
            self.audiosrc.set_property('client-name', 'obplayer-liveassist: monitor')

        elif audio_input == 'test':
            self.audiosrc = Gst.ElementFactory.make('fakesrc', 'audiosrc')

        else:
            self.audiosrc = Gst.ElementFactory.make('autoaudiosrc', 'audiosrc')

        elements.append(self.audiosrc)
        elements.append(Gst.ElementFactory.make('queue2'))
        elements.append(Gst.ElementFactory.make('audioconvert'))
        elements.append(Gst.ElementFactory.make('audioresample'))

        self.appsink = Gst.ElementFactory.make("appsink", "appsink")
        self.appsink.set_property('emit-signals', True)
        #self.appsink.set_property('caps', Gst.Caps.from_string("audio/x-raw,channels=1,rate=" + str(self.rate) + ",format=S16LE,layout=interleaved"))
        #self.appsink.set_property('blocksize', 4096)
        #self.appsink.set_property('max-buffers', 10)
        self.appsink.set_property('drop', True)
        self.appsink.set_property('max-lateness', 500000000)
        self.appsink.connect("new-sample", self.cb_new_sample)
        elements.append(self.appsink)

        self.build_pipeline(elements)

    def change_format(self, params):
        self.rate = params['rate']
        self.encoding = params['encoding']
        if self.encoding == 'a-law':
            self.encoder = AlawEncoder()
        self.blocksize = params['blocksize']

        if self.appsink:
            self.appsink.set_property('caps', Gst.Caps.from_string("audio/x-raw,channels=1,rate=" + str(self.rate) + ",format=S16LE,layout=interleaved"))
        if self.appsrc:
            self.appsrc.set_property('caps', Gst.Caps.from_string("audio/x-raw,channels=1,rate=" + str(self.rate) + ",format=S16LE,layout=interleaved"))

    def build_pipeline(self, elements):
        for element in elements:
            obplayer.Log.log("adding element to bin: " + element.get_name(), 'debug')
            self.pipeline.add(element)
        for index in range(0, len(elements) - 1):
            elements[index].link(elements[index + 1])

    def message_handler(self, bus, message):
        if message.type == Gst.MessageType.STATE_CHANGED:
            oldstate, newstate, pending = message.parse_state_changed()

        elif message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            obplayer.Log.log("gstreamer error: %s, %s, %s" % (err, debug, err.code), 'error')
            # TODO send something

        #elif message.type == Gst.MessageType.EOS:
        #    obplayer.Log.log("player received end of stream signal", 'debug')
        #    self.player.request_update.set()

        elif message.type == Gst.MessageType.ELEMENT:
            struct = message.get_structure()
            #self.player.audio_levels = [ pow(10, rms / 20) for rms in rms_values ]
            #print(struct.get_value('rms'))
            self.conn.websocket_write_message(obplayer.httpadmin.httpserver.WS_OP_TEXT, json.dumps({ 'type': 'mic-level', 'level': struct.get_value('rms') }))

    def toggle_mute(self):
        if self.volume:
            mute = self.volume.get_property('mute')
            self.volume.set_property('mute', not mute)
            return self.volume.get_property('mute')

    def change_volume(self, volume):
        if self.volume:
            self.volume.set_property('volume', float(volume) / 100.0)

    def get_volume(self):
        if self.volume:
            return {
                'volume': self.volume.get_property('volume') * 100,
                'mute': self.volume.get_property('mute')
            }

    def start(self):
        self.wait_state(Gst.State.PLAYING)

    def stop(self):
        self.wait_state(Gst.State.NULL)

    def quit(self):
        self.wait_state(Gst.State.NULL)

    def wait_state(self, target_state):
        self.pipeline.set_state(target_state)
        (statechange, state, pending) = self.pipeline.get_state(timeout=5 * Gst.SECOND)
        if statechange != Gst.StateChangeReturn.SUCCESS:
            obplayer.Log.log("gstreamer failed waiting for state change to " + str(pending), 'error')
            #raise Exception("Failed waiting for state change")
            return False
        return True

    def queue_data(self, data):
        with self.lock:
            self.microphone_queue.append(data)

    def cb_need_data(self, unused, userdata):
        with self.lock:
            if len(self.microphone_queue):
                data = self.microphone_queue.pop(0)
            else:
                data = bytearray(self.blocksize)
        if self.encoder:
            data = self.encoder.decode_buffer(data)
        #print("Decoded: " + str(len(data)) + " " + repr(data[:20]))
        gbuffer = Gst.Buffer.new_allocate(None, len(data), None)
        gbuffer.fill(0, data)
        ret = self.appsrc.emit('push-buffer', gbuffer)

    def cb_new_sample(self, userdata):
        gbuffer = self.appsink.get_property('last-sample').get_buffer()
        data = gbuffer.extract_dup(0, gbuffer.get_size())
        if self.encoder:
            data = self.encoder.encode_buffer(data)
        #print("Encoded: " + str(len(data)) + " " + repr(data[:20]))
        self.monitor_queue += data

        while len(self.monitor_queue) >= self.blocksize:
            data = self.monitor_queue[:self.blocksize]
            self.monitor_queue = self.monitor_queue[self.blocksize:]
            #obplayer.Log.log("websocket send: " + str(len(data)) + " " + repr(data[:20]) + "...", 'debug')
            if self.conn:
                self.conn.websocket_write_message(obplayer.httpadmin.httpserver.WS_OP_BIN, data)
        return Gst.FlowReturn.OK

    """
    def pull_buffer(self):
        sample = self.appsink.emit('pull-sample')
        buffer = sample.get_buffer()
        data = buffer.extract_dup(0, buffer.get_size())
        return data
    """


class AlawEncoder (object):
    def encode_buffer(self, data):
        output = bytearray(len(data) / 2)
        for i in range(0, len(data), 2):
            sample = (ord(data[i + 1]) << 8) | ord(data[i])
            sign = 0x80 if sample < 0 else 0
            sample = abs(sample)
            exponent = self.AlawEncodeTable[(sample >> 8) & 0x7f]
            output[i >> 1] = chr(sign | (exponent << 4) | ((sample >> exponent + 3) & 0x0f))
        return output

    def decode_buffer(self, data):
        output = bytearray(len(data) * 2)
        for i in range(0, len(data)):
            sign = True if data[i] & 0x80 else False
            exponent = (data[i] & 0x70) >> 4
            if exponent == 0:
                sample = (data[i] & 0x0f) << 4
            else:
                sample = (((data[i] & 0x0f) | 0x10) << (exponent + 3))
            if sign:
                sample = sample * -1
            output[i << 1] = sample & 0xff
            output[(i << 1) + 1] = (sample >> 8) & 0xff
        return output

    AlawEncodeTable = [
         0,1,2,2,3,3,3,3,
         4,4,4,4,4,4,4,4,
         5,5,5,5,5,5,5,5,
         5,5,5,5,5,5,5,5,
         6,6,6,6,6,6,6,6,
         6,6,6,6,6,6,6,6,
         6,6,6,6,6,6,6,6,
         6,6,6,6,6,6,6,6,
         7,7,7,7,7,7,7,7,
         7,7,7,7,7,7,7,7,
         7,7,7,7,7,7,7,7,
         7,7,7,7,7,7,7,7,
         7,7,7,7,7,7,7,7,
         7,7,7,7,7,7,7,7,
         7,7,7,7,7,7,7,7,
         7,7,7,7,7,7,7,7
    ]

"""
enc = AlawEncoder()
buffer = bytearray(256)
for i in range(256):
    buffer[i] = chr(i)
print(repr(buffer))

buffer = ''.join(chr(i) for i in range(256))

data = enc.decode_buffer(buffer)
data2 = enc.encode_buffer(data)

print(repr(data))
print(repr(data2))
"""

