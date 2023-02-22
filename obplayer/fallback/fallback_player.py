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

import os
import sys
import time
import magic
import random
import traceback

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstPbutils', '1.0')
from gi.repository import GObject, Gst, GstPbutils

if sys.version.startswith('3'):
    unicode = str


class ObFallbackPlayer (obplayer.player.ObPlayerController):

    def __init__(self):
        self.media = []

        self.media_types = []
        self.image_types = []

        self.media_types.append('audio/x-flac')
        self.media_types.append('audio/flac')
        self.media_types.append('audio/mpeg')
        self.media_types.append('audio/ogg')

        # TODO we're always headless new so we never play images or video??
        #if obplayer.Config.headless == False:
        self.image_types.append('image/jpeg')
        self.image_types.append('image/png')
        self.image_types.append('image/svg+xml')
        self.media_types.append('application/ogg')
        self.media_types.append('video/ogg')
        self.media_types.append('video/x-msvideo')
        self.media_types.append('video/mp4')
        self.media_types.append('video/mpeg')

        self.play_index = 0
        self.image_duration = 15.0

        m = magic.open(magic.MAGIC_MIME)
        m.load()

        for (dirname, dirnames, filenames) in os.walk(unicode(obplayer.Config.setting('fallback_media'))):
            for filename in filenames:
                try:
                    path = os.path.join(dirname, filename)
                    uri = obplayer.Player.file_uri(path)
                    filetype = m.file(path.encode('utf-8')).split(';')[0]

                    if filetype in self.media_types:
                        d = GstPbutils.Discoverer()
                        mediainfo = d.discover_uri(uri)

                        media_type = None
                        for stream in mediainfo.get_video_streams():
                            if stream.is_image():
                                media_type = 'image'
                            else:
                                media_type = 'video'
                                break
                        if not media_type and len(mediainfo.get_audio_streams()) > 0:
                            media_type = 'audio'

                        if media_type:
                            # we discovered some more fallback media, add to our media list.
                            self.media.append([ uri, filename, media_type, float(mediainfo.get_duration()) / Gst.SECOND ])

                    if filetype in self.image_types:
                        self.media.append([ uri, filename, 'image', self.image_duration ])
                except:
                    obplayer.Log.log("exception while loading fallback media: " + dirname + '/' + filename, 'error')
                    obplayer.Log.log(traceback.format_exc(), 'error')

        # shuffle the list
        random.shuffle(self.media)

        self.ctrl = obplayer.Player.create_controller('fallback', priority=25)
        self.ctrl.set_request_callback(self.do_player_request)

    # the player is asking us what to play next
    def do_player_request(self, ctrl, present_time, media_class):
        if len(self.media) == 0:
            return False

        if self.play_index >= len(self.media):
            self.play_index = 0
            random.shuffle(self.media)  # shuffle again to create a new order for next time.

        ctrl.add_request(
            media_type = unicode(self.media[self.play_index][2]),
            uri = unicode(self.media[self.play_index][0]),
            duration = self.media[self.play_index][3],
            order_num = self.play_index,
            artist = u'unknown',
            title = unicode(self.media[self.play_index][1])
        )

        self.play_index = self.play_index + 1

        return True


