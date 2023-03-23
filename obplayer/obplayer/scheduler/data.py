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
import obplayer.alerts

import time


class ObRemoteData (obplayer.ObData):

    def __init__(self):
        obplayer.ObData.__init__(self)

        # our main database, stored in memory.
        self.db = self.open_db(':memory:')

        self.verify_backup()

        if not self.table_exists('shows'):
            obplayer.Log.log('shows table not found, creating', 'data')
            self.shows_create_table()

        if not self.table_exists('shows_media'):
            obplayer.Log.log('media table not found, creating', 'data')
            self.shows_media_create_table()

        if not self.table_exists('priority_broadcasts'):
            obplayer.Log.log('priority broadcast table not found, creating', 'data')
            self.priority_broadcasts_create_table()

        if not self.table_exists('groups'):
            obplayer.Log.log('liveassist groups table not found, creating', 'data')
            self.shows_groups_create_table()

        if not self.table_exists('group_items'):
            obplayer.Log.log('liveassist group items table not found, creating', 'data')
            self.shows_group_items_create_table()

        if not self.table_exists('alert_media'):
            obplayer.Log.log('alert media table not found, creating', 'data')
            self.alert_media_create_table()

        self.priority_broadcasts = False

    def backup(self):
        obplayer.Log.log('backup database to disk', 'data')
        backupcon = self.open_db(self.datadir + '/data.db')

        with backupcon.backup('main', self.db, 'main') as backup:
            backup.step()

        backupcon.close()
        obplayer.Log.log('done backing up', 'data')

    def verify_backup(self):
        # load our backup database from file. check integrity.  if the database doesn't exist, it will be created/empty - no problem, tables are checked/created below.
        backup_icheck = []
        backup = self.open_db(self.datadir + '/data.db')
        for row in backup.cursor().execute('PRAGMA integrity_check'):
            backup_icheck.extend(row)

        if '\n'.join(backup_icheck) != 'ok':
            obplayer.Log.log('backup file bad, ignoring.', 'data')

        else:
            obplayer.Log.log('restoring database from file', 'data')
            with self.db.backup('main', backup, 'main') as backup:
                backup.step()
            obplayer.Log.log('done restoring database', 'data')

        backup.close()

    def shows_create_table(self):
        self.execute('CREATE TABLE shows (id INTEGER PRIMARY KEY, show_id INTEGER, name TEXT, type TEXT, description TEXT, datetime NUMERIC UNIQUE, duration NUMERIC, last_updated NUMERIC)')
        self.execute('CREATE UNIQUE INDEX datetime_index on shows (datetime)')

    def shows_media_create_table(self):
        self.execute('CREATE TABLE shows_media (id INTEGER PRIMARY KEY, local_show_id INTEGER, media_id INTEGER, show_id INTEGER, order_num INTEGER, filename TEXT, artist TEXT, title TEXT, offset NUMERIC, duration NUMERIC, media_type TEXT, file_hash TEXT, file_size INT, file_location TEXT, approved INT, archived INT)')
        self.execute('CREATE INDEX local_show_id_index on shows_media (local_show_id)')

    def alert_media_create_table(self):
        self.execute('CREATE TABLE alert_media (media_id INTEGER, filename TEXT, file_hash TEXT, file_size INT, language TEXT, event_name TEXT, media_type TEXT, PRIMARY KEY(media_id))')

    def priority_broadcasts_create_table(self):
        self.execute('CREATE TABLE priority_broadcasts (id INTEGER PRIMARY KEY, start_timestamp INTEGER, end_timestamp INTEGER, frequency INTEGER, filename TEXT, artist TEXT, title TEXT, duration NUMERIC, media_type TEXT, media_id INTEGER, file_hash TEXT, file_size INT, file_location TEXT, approved INT, archived INT)')

    def shows_groups_create_table(self):
        self.execute('CREATE TABLE groups (id INTEGER PRIMARY KEY, local_show_id INTEGER, name TEXT)')
        self.execute('CREATE INDEX groups_local_show_id_index on groups (local_show_id)')

    def shows_group_items_create_table(self):
        self.execute('CREATE TABLE group_items (id INTEGER PRIMARY KEY, group_id INTEGER, media_id INTEGER, order_num INTEGER, filename TEXT, artist TEXT, title TEXT, duration NUMERIC, media_type TEXT, file_hash TEXT, file_size INT, file_location TEXT, approved INT, archived INT)')
        self.execute('CREATE INDEX group_id_index on group_items (group_id)')

    #
    # Given media id, filename, file_hash, file_size, event_name,
    # language and media_type, add entry to show database.  If entry exists, edit if required.
    # Return false if edit not required.  Return lastrowid otherwise.
    def alert_audio_addedit(self, media_id, filename, file_hash, file_size, event_name, media_type, language):
        rows = self.execute("SELECT * from alert_media where media_id=?", (str(media_id),))
        for row in rows:
            # if update not required, return false.
            if int(row[0]) == int(media_id) and str(row[4]) == str(language):
                return False
            else:
                # if we have a match, but update is required, delete entry + associated media.
                self.execute("DELETE from alert_media where media_id=? and language=?", (str(row[0]), str(language),))

        # now add the alert media... (media not added here, but added by sync script)
        self.execute("INSERT or REPLACE into alert_media VALUES (?, ?, ?, ?, ?, ?, ?)", (media_id, filename, file_hash, file_size, language, event_name, media_type))
        return self.db.last_insert_rowid()

    #
    # Given show_id, name, description, datetime, and duration, add entry to show database.  If entry exists, edit if required.
    # Return false if edit not required.  Return lastrowid otherwise.
    #
    def show_addedit(self, show_id, name, show_type, description, datetime, duration, last_updated):
        # determine whether there is already a show in this slot.
        rows = self.execute("SELECT show_id,last_updated,id,duration from shows where datetime=?", (str(datetime),))
        for row in rows:
            # if update not required, return false.
            if int(row[0]) == int(show_id) and int(row[1]) == int(last_updated) and float(row[3]) == float(duration):
                return False
            else:
                # if we have a match, but update is required, delete entry + associated media.
                self.execute("DELETE from shows_media where local_show_id=?", (str(row[2]),))

        # now add the show... (media not added here, but added by sync script)
        self.execute("INSERT or REPLACE into shows VALUES (null, ?, ?, ?, ?, ?, ?, ?)", (show_id, name, show_type, description, str(datetime), duration, str(last_updated)))
        return self.db.last_insert_rowid()

    #
    # Given a list of timestamps, delete all shows with a timestamp not in this list.  (Clean out shows that have been removed).
    # DO NOT remove shows within starting within 'ignore_limit' (since these fall within 'showlock').
    #
    def show_remove_deleted(self, timestamps, ignore_limit):
        id_list_string = ','.join(str(timestamp) for timestamp in timestamps)
        rows = self.query("SELECT id from shows WHERE datetime NOT IN (" + id_list_string + ") and datetime > " + str(ignore_limit))

        for row in rows:
            self.execute("DELETE from shows where id = " + str(row['id']))
            self.execute("DELETE from shows_media where local_show_id = " + str(row['id']))
        return True

    # remove shows that are over, and associated media.
    def show_remove_old(self):
        rows = self.query("SELECT id from shows WHERE (datetime+duration) < " + str(time.time()))

        for row in rows:
            self.execute("DELETE from shows where id = " + str(row['id']))
            self.execute("DELETE from shows_media where local_show_id = " + str(row['id']))
        return True

    #
    # Given broadcast_id, start time, end time ('' for none), frequency, artist, title, filename, media_id, duration, and media type, update priority broadcast database.
    # If row with broadcast_id exists, it will be updated.  Otherwise row will be added.
    #
    def priority_broadcast_addedit(self, broadcast_id, start, end, frequency, artist, title, filename, media_id, duration, media_type, file_hash, file_size, file_location, approved, archived):
        query = "INSERT OR REPLACE into priority_broadcasts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        bindings = (
            broadcast_id,
            start, end,
            frequency,
            filename,
            artist,
            title,
            duration,
            media_type,
            media_id,
            file_hash,
            file_size,
            file_location,
            approved,
            archived)

        self.execute(query, bindings)
        return self.db.last_insert_rowid()

    #
    # Given a list of priority broadcast IDs, remove anything that isn't in there. (they are no longer needed.)
    #
    def priority_broadcast_remove_deleted(self, id_list):
        id_list_string = ','.join(str(broadcast_id) for broadcast_id in id_list)
        self.execute("DELETE from priority_broadcasts WHERE id NOT IN (" + id_list_string + ")")
        return True

    #
    # Given media id, show id, order number, filename, artist, title, duration, and media type, add show media.
    #
    def show_media_add(self, local_show_id, show_id, media_item):
        query = "INSERT into shows_media VALUES (null, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        bindings = (
            str(local_show_id),
            str(media_item['id']),
            show_id,
            media_item['order'],
            media_item['filename'],
            media_item['artist'],
            media_item['title'],
            media_item['offset'],
            media_item['duration'],
            media_item['type'],
            media_item['file_hash'],
            media_item['file_size'],
            media_item['file_location'],
            media_item['approved'],
            media_item['archived'])

        self.execute(query, bindings)
        return self.db.last_insert_rowid()

    def group_remove_old(self, local_show_id):
        rows = self.query("SELECT id from groups WHERE local_show_id = " + str(local_show_id))
        for row in rows:
            self.execute("DELETE from group_items where group_id = " + str(row['id']))
            self.execute("DELETE from groups where id = " + str(row['id']))

    def group_add(self, local_show_id, name):
        self.execute("INSERT into groups VALUES (null, ?, ?)", (str(local_show_id), name))
        return self.db.last_insert_rowid()

    def group_item_add(self, group_id, media_item):
        query = "INSERT into group_items VALUES (null, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        bindings = (
            str(group_id),
            str(media_item['id']),
            media_item['order'],
            media_item['filename'],
            media_item['artist'],
            media_item['title'],
            media_item['duration'],
            media_item['type'],
            media_item['file_hash'],
            media_item['file_size'],
            media_item['file_location'],
            media_item['approved'],
            media_item['archived'])

        self.execute(query, bindings)
        return self.db.last_insert_rowid()

    #
    # Return a dictionary (associate array) of format returned_list[filename]=media_id for all media required by remote.
    # This is based on the entries in shows_media and priority_broadcasts.
    #
    def media_required(self):
        rows = self.execute("SELECT filename,media_id,file_hash,file_location,approved,archived,file_size,media_type from shows_media GROUP by media_id")

        media_list = {}

        for row in rows:
            media_row = self.get_media_from_row(row)
            media_list[media_row['filename']] = media_row

        rows = self.execute("SELECT filename,media_id,file_hash,file_location,approved,archived,file_size,media_type from priority_broadcasts GROUP by media_id")

        for row in rows:
            media_row = self.get_media_from_row(row)
            media_list[media_row['filename']] = media_row

        rows = self.execute("SELECT filename,media_id,file_hash,file_location,approved,archived,file_size,media_type from group_items GROUP by media_id")

        for row in rows:
            media_row = self.get_media_from_row(row)
            media_list[media_row['filename']] = media_row

        return media_list

    def get_media_info(self, media_id):
        for media in self.media_required():
            print(media)
            if media['media_id'] == media_id:
                return media
        return None

    def alert_media_required(self):
        import json, requests, time
        postfields = {}
        postfields['id'] = obplayer.Config.setting('sync_device_id')
        postfields['pw'] = obplayer.Config.setting('sync_device_password')

        data_request = requests.post(obplayer.Config.setting('sync_url').replace('/remote.php', '/modules/alert_languages/remote.php'), data=postfields)
        if data_request.status_code != 200:
            return {}
        data = json.loads(data_request.content.decode('utf-8'))
        for language in obplayer.Config.setting('alerts_selected_indigenous_languages').split(','):
            for media_item in data[2][language]['alerts']:
                media_item['language'] = language
                print(media_item)
                self.alert_audio_addedit(media_item['media_id'], media_item['alert_name'].lower() + '.' + media_item['media_format'],
                media_item['media_hash'], media_item['media_filesize'], media_item['alert_name'], media_item['media_type'], media_item['language'])
        rows = self.execute("SELECT media_id,filename,file_hash,file_size,language,event_name,media_type from alert_media GROUP by media_id")

        media_list = {}

        for row in rows:
            media_row = self.get_alert_media_from_row(row)
            media_list[media_row['filename']] = media_row

        return media_list

    def language_lookup(self, code):
        for item in os.listdir(obplayer.RemoteData.datadir + '/indigenous/'):
            print(item)
        #obplayer.Config.setting('alerts_selected_indigenous_languages')

    def fetch_alert_media(self, media):
        postfields = {}

        postfields['id'] = obplayer.Config.setting('sync_device_id')
        postfields['pw'] = obplayer.Config.setting('sync_device_password')
        postfields['media_id'] = media['media_id']

        data_request = requests.post(obplayer.Config.setting('sync_url') + "?action=media", data=postfields)

        if data_request.status_code != 200:
            obplayer.Log.log('unable to download alert media id: {0} at this time'.format(media['media_id']), 'error')
        else:
            data = data_request.content
            try:
                # build save path with language name.
                save_path = obplayer.RemoteData.datadir + '/indigenous/{0}/'.format(obplayer.alert.ObAlert.lang_ref_to_language_name(media['language']))
                with open(save_path + media['filename'], 'wb') as file:
                    file.write(data)
                # convert all non wav audio to wav
                if media['filename'].endswith('wav') == False:
                    # strip file ext from filename
                    filename = media['filename'].replace('.ogg', '').replace('.mp3', '').replace('.OGG', '').replace('.MP3', '')
                    self.convert_audio(save_path + media['filename'], media['media_format'], filename)
            except FileNotFoundError as e:
                obplayer.Log.log('unable to download alert media id: {0} at this time'.format(media['media_id']), 'error')

    @staticmethod
    def get_media_from_row(row):
        media_row = {}
        media_row['filename'] = row[0]
        media_row['media_id'] = row[1]
        media_row['file_hash'] = row[2]
        media_row['file_size'] = row[6]
        media_row['file_location'] = row[3]
        media_row['approved'] = row[4]
        media_row['archived'] = row[5]
        media_row['media_type'] = row[7]
        return media_row

    @staticmethod
    def get_alert_media_from_row(row):
        media_row = {}
        media_row['media_id'] = row[0]
        media_row['filename'] = row[1]
        media_row['file_hash'] = row[2]
        media_row['file_size'] = row[3]
        media_row['language'] = row[4]
        media_row['event_name'] = row[5]
        media_row['media_type'] = row[6]
        return media_row

    #
    # Given the present time, return the present show (associate array/dictionary).
    #
    def get_present_show(self, present_timestamp):

        rows = self.query("SELECT * from shows where datetime <= " + str(present_timestamp) + " order by datetime desc limit 1")

        for (rindex, row) in enumerate(rows):

            show_start_timestamp = row['datetime']
            show_end_timestamp = show_start_timestamp + float(row['duration'])

            if present_timestamp < show_end_timestamp:
                rows[rindex]['start_time'] = show_start_timestamp
                rows[rindex]['end_time'] = show_end_timestamp
                return rows[rindex]

        return None

    #
    # Given the present time, return the next show.  Returned as associative array/dictionary.
    #
    def get_next_show_times(self, present_timestamp):

        rows = self.query("SELECT datetime,duration from shows where datetime > " + str(present_timestamp) + " order by datetime limit 1")

        for (rindex, row) in enumerate(rows):

            show_start_timestamp = row['datetime']
            show_end_timestamp = show_start_timestamp + float(row['duration'])

            if present_timestamp < show_end_timestamp:
                rows[rindex]['start_time'] = show_start_timestamp
                rows[rindex]['end_time'] = show_end_timestamp
                return rows[rindex]

        return None

    def load_groups(self, local_show_id):

        group_rows = self.query("SELECT * from groups WHERE local_show_id = " + str(local_show_id))

        groups = [ ]
        for group_row in group_rows:
            item_rows = self.query("SELECT * from group_items WHERE group_id = " + str(group_row['id']))

            group_items = [ ]
            for item_row in item_rows:
                group_items.append(item_row)

            groups.append({ 'id' : group_row['id'], 'local_show_id' : group_row['local_show_id'], 'name' : group_row['name'], 'items' : group_items })

        # TODO I've moved this to sync, and only liveassist shows will have these available
        #groups.append({ 'id' : -1, 'local_show_id' : -1, 'name' : 'System Requests', 'items' : [
        #    { 'id': -1, 'artist': 'System', 'title': "Line-In Audio Source", 'media_type': 'linein', 'duration': 3600, 'media_id': -1, 'order_num': -1, 'file_location': '', 'filename': '' },
        #    { 'id': -1, 'artist': 'System', 'title': "RTP Audio Source", 'media_type': 'rtp', 'duration': 3600, 'media_id': -1, 'order_num': -1, 'file_location': '', 'filename': '' }
        #] })
        return groups

    #
    # Get a list of the show media given a show id. Returned as associative array/dictionary.
    #
    def get_show_media(self, local_show_id):
        rows = self.execute("SELECT filename,order_num,duration,media_type,artist,title,media_id,file_location,offset,file_size from shows_media where local_show_id=? order by offset", (str(local_show_id),))

        media = []
        for row in rows:
            media_data = {}
            media_data['filename'] = row[0]
            media_data['order_num'] = int(row[1])
            media_data['offset'] = float(row[8])
            media_data['duration'] = float(row[2])
            media_data['type'] = row[3]
            media_data['artist'] = row[4]
            media_data['title'] = row[5]
            media_data['media_id'] = int(row[6])
            media_data['file_location'] = row[7]
            media_data['media_type'] = row[3]
            media_data['file_size'] = row[9]

            media.append(media_data)

        if len(media) <= 0:
            return None
        else:
            return media

    #
    # Get all present priority broadcasts.  Returned as associative array/dictionary.
    #
    def get_priority_broadcasts(self):

        # TODO previous broadcast array is used to get the next_play play data.
        # will need to record id into broadcast array index to make this easier...

        present_time = time.time()

        rows = self.execute("SELECT id,start_timestamp,end_timestamp,frequency,artist,title,filename,duration,media_type,media_id,file_location,file_size from priority_broadcasts")

        broadcasts = {}

        has_broadcasts = False

        for row in rows:
            data = {}
            data['id'] = row[0]
            data['start'] = row[1]
            data['end'] = row[2]
            data['frequency'] = row[3]
            data['artist'] = row[4]
            data['title'] = row[5]
            data['filename'] = row[6]
            data['duration'] = row[7]
            data['type'] = row[8]
            data['media_type'] = row[8]
            data['media_id'] = row[9]
            data['file_location'] = row[10]
            data['file_size'] = row[11]

            data['next_play'] = False

            # try to get next play time based on previous play time.
            if self.priority_broadcasts != False:

                former_data = self.priority_broadcasts.get(str(data['id']), None)

                if former_data != None:

                    # TODO why are we fetching former data and then using this other record of data...
                    old = self.priority_broadcasts[str(data['id'])]
                    if 'last_play' in old:
                        data['last_play'] = old['last_play']
                    else:
                        data['last_play'] = 0
                    check_next_play = data['last_play'] + data['frequency']

                    if check_next_play >= present_time:
                        data['next_play'] = check_next_play

            # if we don't have a next play time, get it in a more usual way.
            if data['next_play'] == False:
                if data['start'] < present_time:
                    data['next_play'] = present_time
                else:
                    data['next_play'] = data['start']

            has_broadcasts = True

            broadcasts[str(data['id'])] = data

        if has_broadcasts == False:
            self.priority_broadcasts = False
            return False
        else:

            self.priority_broadcasts = broadcasts
            return broadcasts
