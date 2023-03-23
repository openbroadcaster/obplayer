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

from obplayer.httpadmin.httpadmin import obplayer, ObHTTPAdmin


class HTTPAdminThread (obplayer.ObThread):
    def try_run(self):
        obplayer.HTTPAdmin = ObHTTPAdmin()
        obplayer.HTTPAdmin.serve_forever()

    def stop(self):
        if obplayer.HTTPAdmin:
            obplayer.HTTPAdmin.shutdown()

def init():
    # run our admin web server.
    if obplayer.Config.args.disable_http is False:
        HTTPAdminThread().start()

def quit():
    pass

