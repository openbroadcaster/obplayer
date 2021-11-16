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

from obplayer.liveassist.liveassist import *

LiveAssist = None

class LiveAssistThread (obplayer.ObThread):
    def try_run(self):
        obplayer.LiveAssist = ObLiveAssist()
        obplayer.LiveAssist.serve_forever()

    def stop(self):
        if hasattr(obplayer, 'LiveAssist') and obplayer.LiveAssist:
            obplayer.LiveAssist.shutdown()

def init():
    if not obplayer.Config.setting('scheduler_enable'):
        obplayer.Log.log("error starting liveassist.  The scheduler must be enabled in order to use the liveassist interface, but it is currently disabled in the settings", 'error')
        return

    if obplayer.Config.setting('live_assist_enable'):
        LiveAssistThread().start()

def quit():
    pass

