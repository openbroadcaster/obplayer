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

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstNet', '1.0')
gi.require_version('GstRtsp', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import GObject, Gst, GstNet, GstRtsp, GstRtspServer



class ObRTSPStreamer (object):
    def __init__(self):
        self.discovery_proc = None
        self.server = GstRtspServer.RTSPServer()
        self.server.set_service(str(obplayer.Config.setting('streamer_rtsp_port')))
        self.server.connect("client-connected", self.client_connected) 

        self.clock_rate = obplayer.Config.setting('streamer_rtsp_clock_rate')

        #auth = GstRtspServer.RTSPAuth.new()
        #self.server.set_auth(auth)

        factory = GstRtspServer.RTSPMediaFactory.new()
        #factory.set_launch('( uridecodebin uri="file:///media/obsuser/Wheatley/GoaTrance.mp3" is-live=1 ! audioconvert ! lamemp3enc ! rtpmpapay name=pay0 pt=96 )')
        #factory.set_launch('( uridecodebin uri="file:///media/obsuser/Wheatley/GoaTrance.mp3" is-live=1 ! audioconvert ! audioresample ! "audio/x-raw,clock-rate=48000,channels=2" ! rtpL24pay name=pay0 pt=96 )')
        #factory.set_launch('uridecodebin uri="file:///media/obsuser/Wheatley/GoaTrance.mp3" is-live=1 ! audioresample ! audioconvert ! capsfilter caps="audio/x-raw,rate=48000,channels=2" ! queue2 ! rtpL24pay name=pay0 pt=96 max-ptime=1000000')
        factory.set_launch('pulsesrc client-name="AudioOut@ObPlayer" ! audioresample ! audioconvert ! capsfilter caps="audio/x-raw,rate=' + self.clock_rate + ',channels=2" ! queue2 ! rtpL24pay name=pay0 pt=96 max-ptime=1000000')
        #factory.set_launch("( videotestsrc is-live=1 ! x264enc ! rtph264pay name=pay0 pt=96 )")
        factory.set_shared(True)
        #factory.set_protocols(GstRtsp.RTSPLowerTrans.UDP | GstRtsp.RTSPLowerTrans.UDP_MCAST)
        factory.set_protocols(GstRtsp.RTSPLowerTrans.UDP_MCAST)
        factory.set_transport_mode(GstRtspServer.RTSPTransportMode.PLAY)
        #factory.set_clock(GstNet.PtpClock.new())
        factory.set_latency(1)
        factory.connect("media-configure", self.media_configure) 

        addrpool = GstRtspServer.RTSPAddressPool.new()
        addrpool.add_range('239.192.1.101', '239.192.1.108', 5004, 5008, 100)
        factory.set_address_pool(addrpool)

        mounts = self.server.get_mount_points()
        mounts.add_factory('/by-id/1', factory)
        mounts.add_factory('/by-name/AudioOut%40ObPlayer', factory)

        # NOTE this is to circumvent a bug in Axia xNode (2.0.0r): non-numeric session IDs are ignored
        class SessPool (GstRtspServer.RTSPSessionPool):
            last = 1
            def do_create_session_id(self):
                self.last += 1
                return str(self.last)
        sesspool = SessPool()
        #sesspool = GstRtspServer.RTSPSessionPool.new()
        self.server.set_session_pool(sesspool)

        self.server.attach(None)

        if obplayer.Config.setting('streamer_rtsp_allow_discovery'):
            self.start_discovery()

    def client_connected(self, server, client):
        obplayer.Log.log('client connected to RTSP streaming server', 'debug')

    def media_configure(self, factory, media):
        obplayer.Log.log('RTSP streaming server media configured', 'debug')

    def quit(self):
        if self.discovery_proc:
            self.discovery_proc.terminate()

    def start_discovery(self):
        import subprocess

        obplayer.Log.log('starting avahi service discovery for RTSP/Ravenna', 'debug')
        self.discovery_proc = subprocess.Popen([ 'obplayer/streamer/avahi_publish.py' ], close_fds=True)

