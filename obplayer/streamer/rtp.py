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


class ObRTPStreamer (ObGstStreamer):
    def __init__(self):
        ObGstStreamer.__init__(self, 'rtp')

        #obplayer.Config.setting('streamer_rtp_enable')
        self.port = obplayer.Config.setting('streamer_rtp_port')
        self.address = obplayer.Config.setting('streamer_rtp_address')
        self.encoding = obplayer.Config.setting('streamer_rtp_encoding')
        self.clock_rate = obplayer.Config.setting('streamer_rtp_clock_rate')
        self.enable_rtcp = obplayer.Config.setting('streamer_rtp_enable_rtcp')

        self.audiopipe = [ ]

        obplayer.Player.add_inter_tap(self.name)
        self.interaudiosrc = Gst.ElementFactory.make('interaudiosrc')
        self.interaudiosrc.set_property('channel', self.name + ':audio')
        #self.interaudiosrc.set_property('buffer-time', 8000000000)
        #self.interaudiosrc.set_property('latency-time', 8000000000)
        self.audiopipe.append(self.interaudiosrc)

        #self.audiopipe.append(Gst.ElementFactory.make("audiotestsrc"))
        #self.audiopipe[-1].set_property('is-live', True)

        caps = Gst.ElementFactory.make('capsfilter')
        caps.set_property('caps', Gst.Caps.from_string("audio/x-raw,channels=2,channel-mask=(bitmask)=0x3"))
        self.audiopipe.append(caps)

        self.audiopipe.append(Gst.ElementFactory.make('queue2', self.name + '-streamer-pre-queue'))

        self.audiopipe.append(Gst.ElementFactory.make('audioconvert', self.name + '-streamer-convert'))
        self.audiopipe.append(Gst.ElementFactory.make('audioresample', self.name + '-streamer-resample'))
        self.audiopipe[-1].set_property('quality', 6)

        caps = Gst.ElementFactory.make('capsfilter')
        caps.set_property('caps', Gst.Caps.from_string("audio/x-raw,channels=2,rate={0}".format(self.clock_rate)))
        self.audiopipe.append(caps)

        self.audiopipe.append(Gst.ElementFactory.make('queue2', self.name + '-streamer-post-queue'))

        if self.encoding == 'OPUS':
            self.encoder = Gst.ElementFactory.make('opusenc', self.name + '-streamer-encoder')
            self.audiopipe.append(self.encoder)
            self.payloader = Gst.ElementFactory.make('rtpopuspay', self.name + '-streamer-payloader')
            self.audiopipe.append(self.payloader)

        elif self.encoding == 'MPA':
            self.encoder = Gst.ElementFactory.make('lamemp3enc', self.name + '-streamer-encoder')
            self.audiopipe.append(self.encoder)
            self.payloader = Gst.ElementFactory.make('rtpmpapay', self.name + '-streamer-payloader')
            self.payloader.set_property('pt', 96)
            self.audiopipe.append(self.payloader)

        elif self.encoding == 'L16':
            self.payloader = Gst.ElementFactory.make('rtpL16pay', self.name + '-streamer-payloader')
            self.audiopipe.append(self.payloader)

        elif self.encoding == 'L24':
            self.payloader = Gst.ElementFactory.make('rtpL24pay', self.name + '-streamer-payloader')
            self.audiopipe.append(self.payloader)

        self.payloader.set_property('pt', 96)
        self.payloader.set_property('max-ptime', 1000000)
        self.payloader.set_property('min-ptime', 1000000)
        self.payloader.set_property('ptime-multiple', 1000000)

        self.audiopipe.append(Gst.ElementFactory.make('queue2', self.name + '-streamer-prertp-queue'))

        self.build_pipeline(self.audiopipe)



        self.rtpbin = Gst.ElementFactory.make('rtpbin', self.name + '-streamer-rtpbin')
        #self.rtpbin.set_property('latency', 0)
        #self.rtpbin.set_property('latency', 1000)
        #self.rtpbin.set_property('buffer-mode', 4)
        #self.rtpbin.set_property('rtcp-sync-send-time', False)
        self.pipeline.add(self.rtpbin)
        self.audiopipe[-1].link_pads('src', self.rtpbin, 'send_rtp_sink_0')

        self.udpsink_rtp = Gst.ElementFactory.make('udpsink', self.name + '-streamer-udpsink-rtp')
        self.udpsink_rtp.set_property('host', self.address)
        self.udpsink_rtp.set_property('port', self.port)
        #self.audiopipe.append(self.udpsink_rtp)
        self.pipeline.add(self.udpsink_rtp)
        self.rtpbin.link_pads('send_rtp_src_0', self.udpsink_rtp, 'sink')

        if self.enable_rtcp:
            self.udpsink_rtcp = Gst.ElementFactory.make('udpsink', self.name + '-streamer-udpsink-rtcp')
            self.udpsink_rtcp.set_property('host', self.address)
            self.udpsink_rtcp.set_property('port', self.port + 1)
            #self.audiopipe.append(self.udpsink_rtcp)
            self.pipeline.add(self.udpsink_rtcp)
            self.rtpbin.link_pads('send_rtcp_src_0', self.udpsink_rtcp, 'sink')






