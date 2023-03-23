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
import threading
import traceback

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst

from .base import ObGstStreamer

import uuid


class ObLineinIcecastStreamer (ObGstStreamer):
    def __init__(self, streamer_icecast_ip, streamer_icecast_port, streamer_icecast_password,
        streamer_icecast_mount, streamer_icecast_streamname, streamer_icecast_description,
        streamer_icecast_url, streamer_icecast_public, streamer_icecast_bitrate):
        self.icecast_ip = streamer_icecast_ip
        self.icecast_port = streamer_icecast_port
        self.icecast_password = streamer_icecast_password
        self.icecast_mount = streamer_icecast_mount
        self.icecast_streamname = streamer_icecast_streamname
        self.icecast_description = streamer_icecast_description
        self.icecast_url = streamer_icecast_url
        self.icecast_public = streamer_icecast_public
        self.icecast_bitrate = streamer_icecast_bitrate
        ObGstStreamer.__init__(self, 'icecast_' + uuid.uuid4().hex)

        self.make_audio_pipe()

    def make_audio_pipe(self):
        self.audiopipe = [ ]

        audio_input = obplayer.Config.setting('audio_in_mode')
        if audio_input == 'alsa':
            self.audiosrc = Gst.ElementFactory.make('alsasrc', 'audiosrc')
            alsa_device = obplayer.Config.setting('audio_in_alsa_device')
            if alsa_device != '':
                self.audiosrc.set_property('device', alsa_device)

        elif audio_input == 'jack':
            self.audiosrc = Gst.ElementFactory.make('jackaudiosrc', 'audiosrc')
            self.audiosrc.set_property('connect', 0)  # don't autoconnect ports.
            name = obplayer.Config.setting('audio_in_jack_name')
            self.audiosrc.set_property('client-name', name if name else 'obplayer')

        elif audio_input == 'oss':
            self.audiosrc = Gst.ElementFactory.make('osssrc', 'audiosrc')

        elif audio_input == 'pulse':
            self.audiosrc = Gst.ElementFactory.make('pulsesrc', 'audiosrc')
            self.audiosrc.set_property('client-name', 'obplayer-line-streamer-to-icecast')

        elif audio_input == 'test':
            self.audiosrc = Gst.ElementFactory.make('fakesrc', 'audiosrc')

        elif audio_input == 'intersink':
            print(self.name)
            obplayer.Player.add_inter_tap(self.name)
            self.audiosrc = Gst.ElementFactory.make('interaudiosrc')
            self.audiosrc.set_property('channel', self.name + ':audio')
            #self.audiosrc.set_property('buffer-time', 8000000000)
            #self.audiosrc.set_property('latency-time', 8000000000)

        else:
            self.audiosrc = Gst.ElementFactory.make('autoaudiosrc', 'audiosrc')

        self.audiopipe.append(self.audiosrc)

        caps = Gst.ElementFactory.make('capsfilter')
        caps.set_property('caps', Gst.Caps.from_string("audio/x-raw,channels=2,channel-mask=(bitmask)0x3"))
        self.audiopipe.append(caps)

        self.audiopipe.append(Gst.ElementFactory.make("queue2"))

        """
        self.level = Gst.ElementFactory.make("level", "level")
        self.level.set_property('message', True)
        self.level.set_property('interval', int(1.0 * Gst.SECOND))
        self.audiopipe.append(self.level)

        self.selector = Gst.ElementFactory.make("valve", "selector")
        self.selector.set_property('drop', True)
        self.is_dropping = True
        self.pipeline.get_bus().add_signal_watch()
        self.pipeline.get_bus().connect('message::element', self.detect_silence)
        self.audiopipe.append(self.selector)
        """

        self.audiopipe.append(Gst.ElementFactory.make("audioconvert"))

        self.encoder = Gst.ElementFactory.make("lamemp3enc")
        if self.icecast_bitrate != 0:
            self.encoder.set_property('target', 1)
            self.encoder.set_property('bitrate', self.icecast_bitrate)
            self.encoder.set_property('cbr', True)
        self.audiopipe.append(self.encoder)

        self.audiopipe.append(Gst.ElementFactory.make("queue2"))

        self.shout2send = Gst.ElementFactory.make("shout2send", "shout2send")
        '''
        self.shout2send.set_property('ip', obplayer.Config.setting('streamer_icecast_ip'))
        self.shout2send.set_property('port', int(obplayer.Config.setting('streamer_icecast_port')))
        self.shout2send.set_property('password', obplayer.Config.setting('streamer_icecast_password'))
        self.shout2send.set_property('mount', obplayer.Config.setting('streamer_icecast_mount'))
        self.shout2send.set_property('streamname', obplayer.Config.setting('streamer_icecast_streamname'))
        self.shout2send.set_property('description', obplayer.Config.setting('streamer_icecast_description'))
        self.shout2send.set_property('url', obplayer.Config.setting('streamer_icecast_url'))
        self.shout2send.set_property('public', obplayer.Config.setting('streamer_icecast_public'))
        '''
        self.shout2send.set_property('ip', self.icecast_ip)
        self.shout2send.set_property('port', int(self.icecast_port))
        self.shout2send.set_property('password', self.icecast_password)
        self.shout2send.set_property('mount', self.icecast_mount)
        self.shout2send.set_property('streamname', self.icecast_streamname)
        self.shout2send.set_property('description', self.icecast_description)
        self.shout2send.set_property('url', self.icecast_url)
        self.shout2send.set_property('public', self.icecast_public)
        self.audiopipe.append(self.shout2send)

        #self.elements.append(ObRtpOutput())

        self.build_pipeline(self.audiopipe)

    def queue_data(self, data):
        with self.lock:
            self.microphone_queue.append(data)

    def _cb_need_data(self, unused, userdata):
        with self.lock:
            if len(self.microphone_queue):
                data = self.microphone_queue.pop(0)
            else:
                #data = bytearray(self.blocksize)
                raw = bytearray(self.blocksize)
                data = Gst.Buffer.new_allocate(None, len(raw), None)
                data.fill(0, raw)
                data.dts = Gst.CLOCK_TIME_NONE
                data.pts = Gst.CLOCK_TIME_NONE
                data.duration = Gst.CLOCK_TIME_NONE
        #if self.encoder:
        #    data = self.encoder.decode_buffer(data)
        #print("Decoded: " + str(len(data)) + " " + repr(data[:20]))
        #gbuffer = Gst.Buffer.new_allocate(None, len(data), None)
        #gbuffer.fill(0, data)
        #ret = self.appsrc.emit('push-buffer', gbuffer)
        ret = self.appsrc.emit('push-buffer', data)

    def detect_silence(self, bus, message, *args):
        peak = message.get_structure().get_value('peak')
        if peak[0] < -28:
            if not self.is_dropping:
                self.is_dropping = True
                self.selector.set_property('drop', True)
                print("now dropping buffers")
        else:
            if self.is_dropping:
                self.is_dropping = False
                self.selector.set_property('drop', False)
                print("now outputting buffers")
        return True


class ObRtpOutput (Gst.Bin):
    def __init__(self):
        Gst.Bin.__init__(self)

        """
        self.encoder = Gst.ElementFactory.make("opusenc")
        self.add(self.encoder)

        self.payloader = Gst.ElementFactory.make("rtpopuspay")
        self.add(self.payloader)
        """

        self.capsfilter = Gst.ElementFactory.make('capsfilter')
        self.capsfilter.set_property('caps', Gst.Caps.from_string("audio/x-raw,channels=2,rate=44100,format=S16LE,layout=interleaved"))
        self.add(self.capsfilter)

        self.payloader = Gst.ElementFactory.make("rtpL16pay")
        self.add(self.payloader)

        self.rtpbin = Gst.ElementFactory.make("rtpbin")
        self.add(self.rtpbin)

        self.udp_rtp = Gst.ElementFactory.make("udpsink")
        self.udp_rtp.set_property('host', '192.168.1.248')
        self.udp_rtp.set_property('port', 4000)
        self.add(self.udp_rtp)

        self.udp_rtcp = Gst.ElementFactory.make("udpsink")
        self.udp_rtcp.set_property('host', '192.168.1.248')
        self.udp_rtcp.set_property('port', 4001)
        self.udp_rtcp.set_property('sync', False)
        self.udp_rtcp.set_property('async', False)
        self.add(self.udp_rtcp)

        # link elements
        self.sinkpad = Gst.GhostPad.new('sink', self.capsfilter.get_static_pad('sink'))
        self.add_pad(self.sinkpad)

        self.capsfilter.link(self.payloader)
        #self.encoder.link(self.payloader)

        """
        self.rtp_sink = self.rtpbin.get_request_pad('send_rtp_sink_0')
        self.payloader.get_static_pad('src').link(self.rtp_sink)
        self.rtp_src = self.rtpbin.get_request_pad('send_rtp_src_0')
        self.rtp_src.link(self.udp_rtp.get_static_pad('sink'))

        self.rtcp_src = self.rtpbin.get_request_pad('send_rtcp_src_0')
        self.rtcp_src.link(self.udp_rtcp.get_static_pad('sink'))
        """

        self.payloader.link_pads('src', self.rtpbin, 'send_rtp_sink_0')
        self.rtpbin.link_pads('send_rtp_src_0', self.udp_rtp, 'sink')

        self.rtpbin.link_pads('send_rtcp_src_0', self.udp_rtcp, 'sink')
