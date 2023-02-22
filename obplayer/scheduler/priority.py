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

import time


class ObPriorityBroadcaster:
    def __init__(self):
        self.ctrl = obplayer.Player.create_controller('priority', priority=75, default_play_mode='overlap', allow_overlay=True)
        #self.ctrl.set_request_callback(self.do_player_request)
        #self.ctrl.set_update_callback(self.do_player_update)
        #self.ctrl.set_next_update(0)

    def do_player_update(self, ctrl, present_time, media_class):
        pass

    def check_update(self):
        present_time = time.time()

        # run through priority broadcasts and play if it's time. don't play while syncing priority since it might be changing data or downloading new data.
        if obplayer.RemoteData.priority_broadcasts != False and obplayer.Sync.priority_sync_running == False:
            for (bindex, broadcast) in obplayer.RemoteData.priority_broadcasts.items():
                if broadcast['next_play'] <= present_time:

                    if obplayer.Sync.check_media(broadcast):

                        obplayer.Log.log('play priority announcement', 'priority')

                        self.ctrl.add_request(
                            media_type = broadcast['media_type'],
                            uri = obplayer.Sync.media_uri(broadcast['file_location'], broadcast['filename']),
                            media_id = broadcast['media_id'],
                            artist = broadcast['artist'],
                            title = broadcast['title'],
                            duration = broadcast['duration'] + 2
                        )

                        play_time = self.ctrl.get_requests_endtime()
                        obplayer.RemoteData.priority_broadcasts[bindex]['next_play'] = play_time + broadcast['duration'] + broadcast['frequency']
                        obplayer.RemoteData.priority_broadcasts[bindex]['last_play'] = play_time

                        # we set this so the show will resume.
                        #self.show_update_time = present_time
                        #break

