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
import threading


class ObPlaylist (object):
    def __init__(self, show_id):
        self.pos = 0
        self.playlist = obplayer.RemoteData.get_show_media(show_id)
        if self.playlist == None:
            self.playlist = [ ]

    def size(self):
        return len(self.playlist)

    def current_pos(self):
        if self.pos >= len(self.playlist):
            return len(self.playlist) - 1
        return self.pos

    def current(self):
        if self.pos >= len(self.playlist):
            return None
        return self.playlist[self.pos]

    def increment(self):
        self.pos += 1
        if self.pos >= len(self.playlist):
            return False
        return True

    def decrement(self):
        self.pos -= 1
        if self.pos < 0:
            self.pos = 0
            return False
        return True

    def set(self, pos):
        self.pos = pos
        if self.pos < 0:
            self.pos = 0
        elif self.pos > len(self.playlist):
            self.pos = len(self.playlist)

    def is_finished(self):
        if self.pos >= len(self.playlist):
            return True
        return False

    def is_last(self):
        if self.pos + 1 >= len(self.playlist):
            return True
        return False

    def next_start(self):
        if self.pos + 1 >= len(self.playlist):
            return None
        return self.playlist[self.pos + 1]['offset']

    def advance_to_current(self, present_offset, media_type=None):
        for i in range(self.pos, len(self.playlist)):
            if present_offset >= self.playlist[i]['offset'] and present_offset <= self.playlist[i]['offset'] + self.playlist[i]['duration'] and (not media_type or media_type == self.playlist[i]['media_type']):
                self.pos = i
                return True
        self.pos = len(self.playlist)
        return False


class ObShow (object):
    def __init__(self):
        self.paused = False
        self.pause_position = 0
        self.auto_advance = True

        self.media_start_time = 0
        self.now_playing = None
        self.next_media_update = 0

        self.show_data = None
        self.playlist = None
        self.groups = None

    @staticmethod
    def find_show(datetime):
        data = obplayer.RemoteData.get_present_show(datetime)
        if not data:
            return None

        # TODO we could possibly have a list of possible show types
        if data['type'] == 'live_assist':
            self = ObLiveAssistShow()
        elif data['type'] == 'advanced':
            self = ObAdvancedShow()
        else:
            self = ObShow()
        self.show_data = data
        self.playlist = ObPlaylist(self.show_data['id'])
        self.groups = obplayer.RemoteData.load_groups(self.show_data['id'])
        return self

    def get_break_media(self, end_time=None, title="show paused break"):
        if end_time == None:
            end_time = self.end_time()
        return {
            'media_type' : 'break',
            'end_time' : end_time,
            'artist' : '[scheduler]',
            'title' : title
        }

    def id(self):
        return self.show_data['id']

    def show_id(self):
        return self.show_data['show_id']

    def name(self):
        return self.show_data['name']

    def start_time(self):
        return self.show_data['start_time']

    def end_time(self):
        return self.show_data['end_time']

    def show_info(self):
        return { key : self.show_data[key] for key in self.show_data if key in [ 'id', 'name', 'description', 'type', 'last_updated' ] }

    def get_playlist(self):
        return self.playlist.playlist

    def get_groups(self):
        return self.groups

    def start_show(self, present_time):
        self.ctrl.stop_requests()

        # find the track that should play at the present time
        self.playlist.advance_to_current(present_time - self.show_data['start_time'])
        obplayer.Log.log("starting at track number " + str(self.playlist.pos), 'scheduler')

        self.play_current(present_time)

    def play_next(self, present_time, media_class=None):
        if self.is_paused() or self.playlist.is_finished():
            self.ctrl.stop_requests()
            self.ctrl.add_request(media_type='break', end_time=self.end_time(), title = "show paused break")
            return False

        #self.ctrl.stop_requests()
        #if present_time >= self.next_media_update - 2:
        if self.playlist.advance_to_current(present_time - self.start_time()):
            self.play_current(present_time)

        if self.ctrl.has_requests():
            return False
        print("This is a bug...")
        self.media_start_time = 0

        # NOTE this usually only happens when a media item fails to play, in which case we don't want to fill the
        # space with a pause, we want to let the fallback player take over
        #self.ctrl.stop_requests()
        #self.ctrl.add_request(media_type='break', end_time=self.end_time(), title = "break (filling spaces)")

    def play_current(self, present_time):
        if self.is_paused():
            self.ctrl.stop_requests()
            self.ctrl.add_request(media_type='break', end_time=self.end_time(), title = "show paused break")
            return False

        media = self.playlist.current()
        if not media or not obplayer.Sync.check_media(media):
            obplayer.Log.log("media not found at position " + str(self.playlist.current_pos()) + ": " + str(media['filename']) if media else '??', 'scheduler')
            next_start = self.playlist.next_start() if media else None
            self.next_media_update = self.start_time() + next_start if next_start else self.end_time()
            #self.ctrl.stop_requests()
            self.ctrl.add_request(media_type='break', duration=2, title="media not found break")
            return False

        offset = present_time - self.show_data['start_time'] - media['offset']
        self.play_media(media, offset, present_time)
        next_start = self.playlist.next_start()
        self.next_media_update = self.start_time() + next_start if next_start else self.end_time()

        return True

    def play_media(self, media, offset, present_time):
        self.now_playing = media
        self.pause_position = 0
        self.media_start_time = present_time - offset

        if media['media_type'] == 'breakpoint':
            obplayer.Log.log("stopping on breakpoint at position " + str(self.playlist.pos), 'scheduler')
            self.playlist.increment()
            self.auto_advance = False
            self.media_start_time = 0
            obplayer.Sync.now_playing_update(self.show_data['show_id'], self.show_data['end_time'], '', '', self.show_data['name'])

            self.ctrl.add_request(media_type = 'break', end_time = self.end_time(), title = "live assist breakpoint", order_num = media['order_num'])

        else:
            # if track does not end in time, use show end_time instead of track duration
            if self.end_time() and self.media_start_time + media['duration'] > self.end_time():
                self.ctrl.add_request(
                    start_time = self.media_start_time,
                    end_time = self.end_time(),
                    media_type = media['media_type'],
                    uri = obplayer.Sync.media_uri(media['file_location'], media['filename']),
                    media_id = media['media_id'],
                    order_num = media['order_num'],
                    artist = media['artist'],
                    title = media['title'],
                )
            else:
                self.ctrl.add_request(
                    start_time = self.media_start_time,
                    media_type = media['media_type'],
                    uri = obplayer.Sync.media_uri(media['file_location'], media['filename']),
                    media_id = media['media_id'],
                    order_num = media['order_num'],
                    artist = media['artist'],
                    title = media['title'],
                    duration = media['duration']
                )

            obplayer.Sync.now_playing_update(self.show_data['show_id'], self.show_data['end_time'], media['media_id'], self.media_start_time + media['duration'], self.show_data['name'])

    def playlist_seek(self, track_num, seek):
        self.playlist.set(track_num)
        self.paused = False
        self.auto_advance = True
        if not self.playlist.is_finished():
            self.ctrl.stop_requests()
            media = self.playlist.current()
            self.play_media(media, media['duration'] * (seek / 100), time.time())

    def play_group_item(self, group_num, group_item_num, seek):
        if self.show_data['type'] != 'live_assist':
            return False

        if group_num < 0 or group_num >= len(self.groups):
            return False
        group = self.groups[group_num]['items']

        if group_item_num < 0 or group_item_num >= len(group):
            return False

        media = group[group_item_num]
        self.ctrl.stop_requests()
        self.play_media(media, media['duration'] * (seek / 100), time.time())
        self.paused = False
        self.auto_advance = False
        return True

    def pause(self):
        if not self.paused:
            self.paused = True
            self.pause_position = time.time() - self.media_start_time
            self.media_start_time = 0
            self.ctrl.stop_requests()
            self.ctrl.add_request(media_type='break', end_time=self.end_time(), title="show paused break")

    def unpause(self):
        if self.paused:
            self.paused = False
            self.ctrl.stop_requests()
            if self.now_playing is None:
                self.play_current(time.time())
            else:
                self.play_media(self.now_playing, self.pause_position, time.time())
                self.pause_position = 0
        elif not self.auto_advance:
            self.auto_advance = True
            self.ctrl.stop_requests()
            self.play_current(time.time())

    def next(self):
        pos = self.playlist.current_pos() + 1
        if pos < self.playlist.size():
            self.playlist_seek(pos, 0)

    def previous(self):
        pos = self.playlist.current_pos() - 1
        if pos >= 0:
            self.playlist_seek(pos, 0)

    def is_paused(self):
        return self.paused or not self.auto_advance

    def position(self):
        if self.media_start_time == 0:
            if self.now_playing == None:
                return 0
            return self.pause_position if self.pause_position else self.now_playing['duration']
        return time.time() - self.media_start_time


class ObLiveAssistShow (ObShow):
    def start_show(self, present_time):
        self.ctrl.stop_requests()

        # if we start the show less than 30 seconds in, then start it, otherwise start paused
        if present_time - self.show_data['start_time'] < 30:
            obplayer.Log.log('starting live assist show', 'scheduler')
        else:
            obplayer.Log.log('starting live assist show paused', 'scheduler')
            self.auto_advance = False
            self.now_playing = self.playlist.current()

        self.play_current(present_time)

    def play_next(self, present_time, media_class=None):
        if self.is_paused() or self.playlist.is_finished():
            self.ctrl.stop_requests()
            self.ctrl.add_request(media_type='break', end_time=self.end_time(), title = "show paused break")
            return False

        if self.ctrl.has_requests():
            return False
        # TODO can you insert a break if the previous track failed to play?
        self.playlist.increment()
        self.play_current(present_time)

    def play_current(self, present_time):
        if self.is_paused():
            self.ctrl.stop_requests()
            self.ctrl.add_request(media_type='break', end_time=self.end_time(), title = "show paused break")
            return False

        media = self.playlist.current()
        if not media or not obplayer.Sync.check_media(media):
            obplayer.Log.log("media not found at position " + str(self.playlist.current_pos()) + ": " + str(media['filename']) if media else '??', 'scheduler')
            #self.ctrl.stop_requests()
            self.ctrl.add_request(media_type='break', duration=2, title="media not found break")
            return False

        self.play_media(media, 0, present_time)
        return True

    def play_group_item(self, group_num, group_item_num, seek):
        if group_num < 0 or group_num >= len(self.groups):
            return False
        group = self.groups[group_num]['items']

        if group_item_num < 0 or group_item_num >= len(group):
            return False

        media = group[group_item_num]
        self.ctrl.stop_requests()
        self.play_media(media, media['duration'] * (seek / 100), time.time())
        self.paused = False
        self.auto_advance = False
        return True


class ObAdvancedShow (ObShow):
    def play_next(self, present_time, media_class=None):
        if self.is_paused() or self.playlist.is_finished():
            self.ctrl.stop_requests()
            self.ctrl.add_request(media_type='break', end_time=self.end_time(), title = "show finished break")
            self.next_media_update = self.end_time()
            return False

        # TODO there is a problem with the first play
        if media_class == 'visual':
            if self.playlist.advance_to_current(present_time - self.start_time(), 'image'):
                self.play_current(present_time)
        elif media_class == 'audio':
            if self.playlist.advance_to_current(present_time - self.start_time(), 'audio'):
                self.play_current(present_time)
        else:
            if self.playlist.advance_to_current(present_time - self.start_time()):
                self.play_current(present_time)



class ObScheduler:
    def __init__(self):
        self.lock = threading.Lock()

        self.ctrl = obplayer.Player.create_controller('scheduler', priority=50, default_play_mode='overlap', allow_overlay=False)
        self.ctrl.set_request_callback(self.do_player_request)
        self.ctrl.set_update_callback(self.do_player_update)

        self.present_show = None
        self.next_show_update = 0

    def do_player_request(self, ctrl, present_time, media_class):
        self.check_show(present_time)

        if self.present_show is not None:
            self.present_show.play_next(present_time, media_class)

        self.set_next_update()

    def do_player_update(self, ctrl, present_time):
        self.check_show(present_time)

        if self.present_show and present_time > self.present_show.next_media_update:
            self.present_show.play_next(present_time)

        self.set_next_update()

    def set_next_update(self):
        if self.present_show and self.present_show.next_media_update < self.next_show_update:
            self.ctrl.set_next_update(self.present_show.next_media_update)
        else:
            self.ctrl.set_next_update(self.next_show_update)

    def check_show(self, present_time):
        if self.present_show is None or present_time > self.next_show_update:
            self.present_show = ObShow.find_show(present_time)
            next_show_times = obplayer.RemoteData.get_next_show_times(present_time)

            # no show, try again in 1min30secs.  (we add the 30 seconds to let the priority broadcaster update come through first, if applicable.
            if self.present_show is None:
                obplayer.Log.log('no show found.', 'scheduler')

                # update now_playing data.
                obplayer.Sync.now_playing_update('', '', '', '', '')

                # if next show starting in less than 90s, we need to update sooner.
                self.next_show_update = present_time + 90
                if next_show_times and self.next_show_update > next_show_times['start_time']:
                    self.next_show_update = next_show_times['start_time']

            else:
                self.present_show.ctrl = self.ctrl
                obplayer.Log.log('loading show ' + str(self.present_show.show_id()), 'scheduler')

                # update now_playing data
                obplayer.Sync.now_playing_update(self.present_show.show_id(), self.present_show.end_time(), '', '', self.present_show.name())
                # TODO get rid of this?? ^^^  why would i get rid of this, old me?

                # figure out show update time. (lower of next show start time, present show end time).
                self.next_show_update = self.present_show.end_time()
                if next_show_times and self.next_show_update > next_show_times['start_time']:
                    self.next_show_update = next_show_times['start_time']

                self.present_show.start_show(present_time)

                if self.present_show.playlist.is_finished():
                    if next_show_times != None:
                        obplayer.Log.log("this show over. waiting for next show to start in " + str(self.next_show_start - present_time) + " seconds", 'scheduler')
                    else:
                        obplayer.Log.log("this show over. next show not found. will retry after next update.")

    # update show update time after show sync. (if next show starting sooner than previously set, we need to update!)
    # this is already subject to the 'show lock' cutoff time.
    def update_show_update_time(self):
        next_show_times = obplayer.RemoteData.get_next_show_times(time.time())
        if next_show_times and next_show_times['start_time'] < self.next_show_update:
            self.next_show_update = next_show_times['start_time']
            self.set_next_update()

    def get_show_name(self):
        if self.present_show == None:
            return '(no show playing)'
        return self.present_show.name()

    def get_show_info(self):
        if self.present_show == None:
            return None
        return self.present_show.show_info()

    def get_show_end(self):
        if self.present_show == None:
            return 0
        return self.present_show.end_time()

    def get_current_playlist(self):
        playlist = [ ]
        if self.present_show != None:
            for track in self.present_show.get_playlist():
                data = { 'track_id' : track['media_id'], 'artist' : track['artist'], 'title' : track['title'], 'duration' : track['duration'], 'media_type' : track['media_type'] }
                playlist.append(data)
        return playlist

    def get_current_groups(self):
        groups = [ ]
        if self.present_show != None:
            for group in self.present_show.get_groups():
                group_items = [ ]
                for group_item in group['items']:
                    data = { 'id' : group_item['id'], 'artist' : group_item['artist'], 'title' : group_item['title'], 'duration' : group_item['duration'], 'media_type' : group_item['media_type'] }
                    group_items.append(data)
                groups.append({ 'name' : group['name'], 'items' : group_items })
        return groups

    def playlist_seek(self, track_num, seek):
        if self.present_show == None:
            return False

        with self.lock:
            self.present_show.playlist_seek(track_num, seek)
        return True

    def play_group_item(self, group_num, group_item_num, seek):
        if self.present_show == None:
            return False

        with self.lock:
            self.present_show.play_group_item(group_num, group_item_num, seek)
        return True

    def unpause_show(self):
        if self.present_show == None:
            return False

        with self.lock:
            self.present_show.unpause()
        return True

    def pause_show(self):
        if self.present_show == None:
            return False

        with self.lock:
            self.present_show.pause()
        return True

    def next_track(self):
        if self.present_show == None:
            return False

        with self.lock:
            self.present_show.next()
        return True

    def previous_track(self):
        if self.present_show == None:
            return False

        with self.lock:
            self.present_show.previous()
        return True

    def find_group_item_pos(self, group_id):
        if self.present_show == None:
            return False

        groups = self.present_show.get_groups()
        for i in range(0, len(groups)):
            group_items = groups[i]['items']
            for j in range(0, len(group_items)):
                if group_items[j]['id'] == group_id:
                    return (i, j)
        return (0, 0)

    def get_now_playing(self):
        data = { }

        player = self.ctrl.player
        requests = player.get_requests()

        request = None
        for key in requests.keys():
            if not request or requests[key]['priority'] > request['priority']:
                request = requests[key]

        if not request:
            data['status'] = 'override'
            data['artist'] = ''
            data['title'] = ''
            data['duration'] = 0
            data['position'] = 0
            data['track'] = -1
            return data

        if request['controller'] != self.ctrl:
            data['status'] = 'override'
        elif self.ctrl.request_is_playing():
            data['status'] = 'playing'
        else:
            data['status'] = 'stopped'

        data['artist'] = request['artist']
        data['title'] = request['title']
        data['duration'] = request['duration']
        data['position'] = time.time() - request['start_time']

        if self.present_show != None and self.present_show.now_playing != None:
            now_playing = self.present_show.now_playing
            if 'group_id' in now_playing:
                data['mode'] = 'group'
                (data['group_num'], data['group_item_num']) = self.find_group_item_pos(now_playing['id'])
            else:
                data['mode'] = 'playlist'
                data['track'] = self.present_show.playlist.current_pos()

        return data

    def get_audio_levels(self):
        return self.ctrl.player.get_audio_levels()

 
