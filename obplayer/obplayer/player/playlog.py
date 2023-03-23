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


class ObPlaylogData (obplayer.ObData):

    def __init__(self):
        obplayer.ObData.__init__(self)
        self.db = self.open_db(self.datadir + '/playlog.db')

        if not self.table_exists('playlog'):
            self.execute("CREATE TABLE playlog (id INTEGER PRIMARY KEY, media_id NUMERIC, artist TEXT, title TEXT, datetime NUMERIC, context TEXT, emerg_id NUMERIC, notes TEXT)")

    #
    # Add entry to play log.
    #
    # media_id : id of media being played (to match web app database)
    # artist : name of artist being played (in case information is lost in web app db)
    # title : title of media being played (in case information is lost in web app db)
    # datetime : unix timestamp of play start time (UTC/GMT)
    # context : what is the context of this media being played (should be 'show' or 'emerg')
    # emerg_id : if this is an priority broadcast, what is the priority broadcast id?
    # notes : any misc notes (in particular, offset if play is resumed part-way through).
    #
    def add_entry(self, media_id, artist, title, datetime, context, notes=''):
        if not obplayer.Config.setting('sync_playlog_enable'):
            return

        # TODO this is a hack until we can change things server-side
        if context == 'alerts':
            context = 'emerg'
        elif context in [ 'scheduler', 'linein' ]:
            context = 'show'
        else:
            context = 'fallback'

        self.execute("INSERT INTO playlog VALUES (null, ?, ?, ?, ?, ?, ?, ?)", (media_id, artist, title, datetime, context, str(0), notes))
        return self.db.last_insert_rowid()

    #
    # Get playlog from given timestamp (used for syncing with web app database)
    #
    def get_entries_since(self, timestamp):
        return self.query("SELECT id,media_id,artist,title,datetime,context,emerg_id,notes from playlog WHERE datetime > " + str(timestamp))

    #
    # Remove playlog entries since ID (used after a successful sync with web app database)
    #
    def remove_entries_since(self, entryid):
        self.execute("DELETE from playlog WHERE id <= " + str(entryid))
        return True


