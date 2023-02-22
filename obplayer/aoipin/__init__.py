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

def init():
    def aoip_in_request(self, present_time, media_class):
        uri = obplayer.Config.setting('aoip_in_uri')
        if uri.startswith('rtsp:'):
            self.add_request(media_type='rtsp', uri=uri, duration=31536000)        # duration = 1 year (ie. indefinitely)
        elif uri.startswith('rtspa:'):
            self.add_request(media_type='rtspa', uri=uri.replace('rtspa', 'rtsp'), duration=31536000)        # duration = 1 year (ie. indefinitely)
        elif uri.startswith('sdp:///'):
            self.add_request(media_type='sdp', uri=uri[6:], duration=31536000)        # duration = 1 year (ie. indefinitely)
        else:
            obplayer.Log.log("invalid aoip uri: " + uri, 'error')

    ctrl = obplayer.Player.create_controller('aoipin', priority=20, allow_requeue=False)
    ctrl.set_request_callback(aoip_in_request)

def quit():
    pass

