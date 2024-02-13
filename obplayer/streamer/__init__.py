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

from __future__ import absolute_import

import obplayer

import gi
from gi.repository import GObject


def init():
    obplayer.Streamer_stream_0 = None
    obplayer.Streamer_stream_1 = None
    obplayer.RTSPStreamer = None
    obplayer.RTPStreamer = None
    obplayer.RTMPStreamer = None

    from .icecast import ObIcecastStreamer
    def delaystart():
        obplayer.Streamer_stream_0 = ObIcecastStreamer(obplayer.Config.setting('streamer_0_icecast_ip'), int(obplayer.Config.setting('streamer_0_icecast_port')),
                obplayer.Config.setting('streamer_0_icecast_username'), obplayer.Config.setting('streamer_0_icecast_password'), obplayer.Config.setting('streamer_0_icecast_mount'),
                obplayer.Config.setting('streamer_0_icecast_streamname'), obplayer.Config.setting('streamer_0_icecast_description'),
                obplayer.Config.setting('streamer_0_icecast_url'), obplayer.Config.setting('streamer_0_icecast_public'), obplayer.Config.setting('streamer_0_icecast_bitrate'),
                obplayer.Config.setting('streamer_0_title_streaming_mode'), obplayer.Config.setting('streamer_0_icecast_mode'))
        obplayer.Streamer_stream_1 = ObIcecastStreamer(obplayer.Config.setting('streamer_1_icecast_ip'), int(obplayer.Config.setting('streamer_1_icecast_port')),
                    obplayer.Config.setting('streamer_1_icecast_username'), obplayer.Config.setting('streamer_1_icecast_password'), obplayer.Config.setting('streamer_1_icecast_mount'),
                    obplayer.Config.setting('streamer_1_icecast_streamname'), obplayer.Config.setting('streamer_1_icecast_description'),
                    obplayer.Config.setting('streamer_1_icecast_url'), obplayer.Config.setting('streamer_1_icecast_public'), obplayer.Config.setting('streamer_1_icecast_bitrate'),
                    obplayer.Config.setting('streamer_1_title_streaming_mode'), obplayer.Config.setting('streamer_1_icecast_mode'))
        if obplayer.Config.setting('streamer_play_on_startup'):
            if obplayer.Config.setting('streamer_0_icecast_enable'):
                obplayer.Streamer_stream_0.start()
                if obplayer.Streamer_stream_0.mode == 'audio':
                    obplayer.Streamer_stream_0.start_title_streaming()
            else:
                if obplayer.Streamer_stream_0.mode == 'audio':
                    obplayer.Streamer_stream_0.stop_title_streaming()
            if obplayer.Config.setting('streamer_1_icecast_enable'):
                obplayer.Streamer_stream_1.start()
                if obplayer.Streamer_stream_1.mode == 'audio':
                    obplayer.Streamer_stream_1.start_title_streaming()
            else:
                if obplayer.Streamer_stream_1.mode == 'audio':
                    obplayer.Streamer_stream_1.stop_title_streaming()

        obplayer.RTSPStreamer = None
        if obplayer.Config.setting('streamer_rtsp_enable'):
            from .rtsp import ObRTSPStreamer
            obplayer.RTSPStreamer = ObRTSPStreamer()

        if obplayer.Config.setting('streamer_rtp_enable'):
            from .rtp import ObRTPStreamer
            obplayer.ObRTPStreamer = ObRTPStreamer()
            obplayer.ObRTPStreamer.start()

        if obplayer.Config.setting('streamer_rtmp_enable'):
            from .rtmp import ObRTMPStreamer
            obplayer.RTMPStreamer = ObRTMPStreamer()
            obplayer.RTMPStreamer.start()

    GObject.timeout_add(1000, delaystart)

def quit():
    if obplayer.Streamer_stream_0:
        obplayer.Streamer_stream_0.stop_title_streaming()
        obplayer.Streamer_stream_0.quit()
    if obplayer.Streamer_stream_1:
        obplayer.Streamer_stream_1.stop_title_streaming()
        obplayer.Streamer_stream_1.quit()
    if obplayer.RTSPStreamer:
        obplayer.RTSPStreamer.quit()
    if obplayer.RTPStreamer:
        obplayer.RTPStreamer.quit()
    if obplayer.RTMPStreamer:
        obplayer.RTMPStreamer.quit()


"""
def start_streamer(name, clsname):
    exec("from .{0} import {1}".format(name, clsname))
    streamer = eval(name)()
    streamer.start()
    return streamer
"""
