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
import traceback

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst, GstVideo

from .base import ObGstPipeline


class ObRTPInputPipeline (ObGstPipeline):
    min_class = [ 'audio' ]
    max_class = [ 'audio' ]

    def __init__(self, name, player):
        ObGstPipeline.__init__(self, name)
        self.player = player

        self.pipeline = Gst.Pipeline(name)
        self.elements = [ ]

        self.prequeue = Gst.ElementFactory.make('queue2', name  + '-pre-queue')
        self.elements.append(self.prequeue)

        encoding = obplayer.Config.setting('rtp_in_encoding')
        if encoding == 'OPUS':
            self.rtpdepay = Gst.ElementFactory.make('rtpopusdepay', name  + '-depay')
            self.elements.append(self.rtpdepay)

            self.decoder = Gst.ElementFactory.make('opusdec', name  + '-decode')
            self.decoder.set_property('plc', True)  # Packet loss concealment
            self.decoder.set_property('use-inband-fec', True)  # FEC
            self.elements.append(self.decoder)

        elif encoding == 'MPA':
            self.rtpdepay = Gst.ElementFactory.make('rtpmpadepay', name  + '-depay')
            self.elements.append(self.rtpdepay)

            self.decoder = Gst.ElementFactory.make('avdec_mp3', name  + '-decode')
            #self.decoder.set_property('plc', True)  # Packet loss concealment
            self.elements.append(self.decoder)

        elif encoding == 'L16':
            self.rtpdepay = Gst.ElementFactory.make('rtpL16depay', name  + '-depay')
            self.elements.append(self.rtpdepay)

        elif encoding == 'L24':
            self.rtpdepay = Gst.ElementFactory.make('rtpL24depay', name  + '-depay')
            self.elements.append(self.rtpdepay)

        else:
            obplayer.Log.log("invalid encoding format " + str(encoding) + " for RTP input", 'error')

        self.audioconvert = Gst.ElementFactory.make('audioconvert', name + '-convert')
        self.elements.append(self.audioconvert)
        self.audioresample = Gst.ElementFactory.make('audioresample', name + '-resample')
        self.audioresample.set_property('quality', 6)
        self.elements.append(self.audioresample)

        self.postqueue = Gst.ElementFactory.make('queue2', name  + '-post-queue')
        self.elements.append(self.postqueue)

        self.build_pipeline(self.elements)

        ## Hook up RTPBin
        self.rtpbin = Gst.ElementFactory.make('rtpbin', name  + '-rtpbin')
        #self.rtpbin.set_property('latency', 2000)
        #self.rtpbin.set_property('autoremove', True)
        #self.rtpbin.set_property('do-lost', True)
        #self.rtpbin.set_property('buffer-mode', 1)
        self.rtpbin.set_property('drop-on-latency', True)
        #self.elements.append(self.rtpbin)
        self.pipeline.add(self.rtpbin)

        def rtpbin_pad_added(obj, pad):
            self.rtpbin.unlink(self.elements[0])
            self.rtpbin.link(self.elements[0])
        self.rtpbin.connect('pad-added', rtpbin_pad_added)

        ## Hook up RTP socket
        port = int(obplayer.Config.setting('rtp_in_port'))
        address = obplayer.Config.setting('rtp_in_address')
        self.udpsrc_rtp = Gst.ElementFactory.make('udpsrc', name + '-udp-rtp')
        self.udpsrc_rtp.set_property('port', port)
        if address:
            self.udpsrc_rtp.set_property('address', address)
        #self.udpsrc_rtp.set_property('caps', Gst.Caps.from_string("application/x-rtp,payload=96,media=audio,clock-rate=48000,encoding-name=OPUS"))
        #self.udpsrc_rtp.set_property('caps', Gst.Caps.from_string("application/x-rtp,media=audio,channels=2,clock-rate=44100,encoding-name=L16"))
        self.udpsrc_rtp.set_property('caps', Gst.Caps.from_string("application/x-rtp,payload=96,media=audio,channels=2,clock-rate=" + str(obplayer.Config.setting('rtp_in_clock_rate')) + ",encoding-name=" + str(encoding)))
        #self.udpsrc_rtp.set_property('timeout', 3000000)
        #self.elements.append(self.udpsrc_rtp)
        self.pipeline.add(self.udpsrc_rtp)
        self.udpsrc_rtp.link_pads('src', self.rtpbin, 'recv_rtp_sink_0')

        ## Hook up RTCP socket
        if obplayer.Config.setting('rtp_in_enable_rtcp'):
            self.udpsrc_rtcp = Gst.ElementFactory.make('udpsrc', name + '-udp-rtcp')
            self.udpsrc_rtcp.set_property('port', port + 1)
            self.pipeline.add(self.udpsrc_rtcp)
            self.udpsrc_rtcp.link_pads('src', self.rtpbin, 'recv_rtcp_sink_0')


        self.audiosink = None
        self.fakesink = Gst.ElementFactory.make('fakesink')
        self.set_property('audio-src', self.fakesink)

        self.register_signals()
        bus = self.pipeline.get_bus()
        bus.connect("message", self.message_handler_rtp)
        #self.bus.add_signal_watch()

    def start(self):
        # We start the pipe without waiting because it wont enter the playing state until the transmitting end is connected 
        self.pipeline.set_state(Gst.State.PLAYING)

    def set_property(self, property, value):
        if property == 'audio-sink':
            if self.audiosink:
                self.pipeline.remove(self.audiosink)
            self.audiosink = value
            if self.audiosink:
                self.pipeline.add(self.audiosink)
                self.elements[-1].link(self.audiosink)

    def patch(self, mode):
        self.wait_state(Gst.State.NULL)
        if 'audio' in mode:
            self.set_property('audio-sink', self.player.outputs['audio'].get_bin())
        ObGstPipeline.patch(self, mode)

        self.pipeline.set_state(Gst.State.PLAYING)

        if obplayer.Config.setting('gst_init_callback'):
            os.system(obplayer.Config.setting('gst_init_callback'))

    def unpatch(self, mode):
        self.wait_state(Gst.State.NULL)
        if 'audio' in mode:
            self.set_property('audio-sink', self.fakesink)
        ObGstPipeline.unpatch(self, mode)
        if len(self.mode) > 0:
            self.pipeline.set_state(Gst.State.PLAYING)

            if obplayer.Config.setting('gst_init_callback'):
                os.system(obplayer.Config.setting('gst_init_callback'))

    def message_handler_rtp(self, bus, message):
        if message.type == Gst.MessageType.ERROR:
            obplayer.Log.log("attempting to restart pipeline", 'info')
            GObject.timeout_add(1.0, self.restart_pipeline)

    def restart_pipeline(self):
        self.wait_state(Gst.State.NULL)
        self.wait_state(Gst.State.PLAYING)


