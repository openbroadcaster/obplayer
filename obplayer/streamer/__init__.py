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
    obplayer.Streamer_stream_1 = None
    obplayer.Streamer_stream_2 = None
    obplayer.RTSPStreamer = None
    obplayer.RTPStreamer = None
    obplayer.YoutubeStreamer = None

    from .icecast import ObIcecastStreamer
    def delaystart():
        # Start stream one
        #print(obplayer.Config.setting('streamer_0_icecast_port'))
        obplayer.Streamer_stream_1 = ObIcecastStreamer(obplayer.Config.setting('streamer_0_icecast_ip'), int(obplayer.Config.setting('streamer_0_icecast_port')),
                obplayer.Config.setting('streamer_0_icecast_password'), obplayer.Config.setting('streamer_0_icecast_mount'),
                obplayer.Config.setting('streamer_0_icecast_streamname'), obplayer.Config.setting('streamer_0_icecast_description'),
                obplayer.Config.setting('streamer_0_icecast_url'), obplayer.Config.setting('streamer_0_icecast_public'), obplayer.Config.setting('streamer_0_icecast_bitrate'))
        # Start stream two
        obplayer.Streamer_stream_2 = ObIcecastStreamer(obplayer.Config.setting('streamer_1_icecast_ip'), int(obplayer.Config.setting('streamer_1_icecast_port')),
                    obplayer.Config.setting('streamer_1_icecast_password'), obplayer.Config.setting('streamer_1_icecast_mount'),
                    obplayer.Config.setting('streamer_1_icecast_streamname'), obplayer.Config.setting('streamer_1_icecast_description'),
                    obplayer.Config.setting('streamer_1_icecast_url'), obplayer.Config.setting('streamer_1_icecast_public'), obplayer.Config.setting('streamer_1_icecast_bitrate'))
        if obplayer.Config.setting('streamer_play_on_startup'):
            if obplayer.Config.setting('streamer_0_icecast_enable'):
                obplayer.Streamer_stream_1.start()
            if obplayer.Config.setting('streamer_1_icecast_enable'):
                obplayer.Streamer_stream_2.start()
    GObject.timeout_add(1000, delaystart)

    obplayer.RTSPStreamer = None
    if obplayer.Config.setting('streamer_rtsp_enable'):
        from .rtsp import ObRTSPStreamer
        obplayer.RTSPStreamer = ObRTSPStreamer()

    if obplayer.Config.setting('streamer_rtp_enable'):
        from .rtp import ObRTPStreamer
        obplayer.ObRTPStreamer = ObRTPStreamer()
        obplayer.ObRTPStreamer.start()

    if obplayer.Config.setting('streamer_youtube_enable'):
        from .youtube import ObYoutubeStreamer
        obplayer.YoutubeStreamer = ObYoutubeStreamer()
        obplayer.YoutubeStreamer.start()

def quit():
    if obplayer.Streamer_stream_1:
        obplayer.Streamer_stream_1.quit()
    if obplayer.Streamer_stream_2:
        obplayer.Streamer_stream_2.quit()
    if obplayer.RTSPStreamer:
        obplayer.RTSPStreamer.quit()
    if obplayer.RTPStreamer:
        obplayer.RTPStreamer.quit()
    if obplayer.YoutubeStreamer:
        obplayer.YoutubeStreamer.quit()


"""
def start_streamer(name, clsname):
    exec("from .{0} import {1}".format(name, clsname))
    streamer = eval(name)()
    streamer.start()
    return streamer
"""
