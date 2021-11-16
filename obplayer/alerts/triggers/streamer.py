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


class StreamerTrigger (object):
    def __init__(self):
        pass

    def alert_cycle_init(self):
        pass

    def alert_cycle_each(self, alert, alert_media, processor):
        pass

    def alert_cycle_start(self):
        if hasattr(obplayer, 'Streamer'):
            obplayer.Log.log("starting icecast streamer for alert cycle", 'alerts')
            obplayer.Streamer.start()

    def alert_cycle_stop(self):
        if hasattr(obplayer, 'Streamer'):
            obplayer.Log.log("stopping icecast streamer after alert cycle", 'alerts')
            obplayer.Streamer.stop()


