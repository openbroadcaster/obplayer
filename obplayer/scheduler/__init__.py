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

from .scheduler import ObScheduler
from .sync import ObSync, VersionUpdateThread, SyncShowsThread, SyncEmergThread, SyncMediaThread, SyncPlaylogThread, Sync_Alert_Media_Thread
from .priority import ObPriorityBroadcaster
from .data import ObRemoteData

#Sync = None
#Scheduler = None

def init():
    #global Sync, Scheduler

    obplayer.Sync = ObSync()
    obplayer.Scheduler = ObScheduler()
    obplayer.PriorityBroadcaster = ObPriorityBroadcaster()
    obplayer.RemoteData = ObRemoteData()

    # reset show/show_media tables, priority tables
    if obplayer.Config.args.reset:
        obplayer.Log.log('resetting show, media, and priority data', 'data')
        obplayer.RemoteData.empty_table('shows')
        obplayer.RemoteData.empty_table('shows_media')
        obplayer.RemoteData.empty_table('groups')
        obplayer.RemoteData.empty_table('group_items')
        obplayer.RemoteData.empty_table('priority_broadcasts')
        obplayer.RemoteData.empty_table('alert_media')

    # report the player version number to the server if possible
    VersionUpdateThread().start()

    # if resetting the databases, run our initial sync.  otherwise skip and setup other sync interval timers.
    if obplayer.Config.args.reset:
        obplayer.Sync.sync_shows(True)
        obplayer.Sync.sync_priority_broadcasts()
        obplayer.Sync.sync_media()
        if obplayer.Config.setting('alerts_broadcast_message_in_indigenous_languages'):
            obplayer.Sync.sync_alert_media()

    # Start sync threads
    SyncShowsThread().start()
    SyncEmergThread().start()
    SyncMediaThread().start()
    SyncPlaylogThread().start()
    if obplayer.Config.setting('alerts_broadcast_message_in_indigenous_languages'):
        Sync_Alert_Media_Thread().start()

def quit():
    # backup our main db to disk.
    if hasattr(obplayer, 'RemoteData') and obplayer.Main.exit_code == 0:
        obplayer.RemoteData.backup()
