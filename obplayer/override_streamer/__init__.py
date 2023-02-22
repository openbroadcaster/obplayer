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
import requests
import time
import subprocess
import json

class Streamer(obplayer.ObThread):
    def __init__(self):
        obplayer.ObThread.__init__(self, 'Obremote_station_override')
        #self.ctrl = obplayer.Player.create_controller('remote station override', priority=99, allow_requeue=False, default_play_mode='overlap')
        self.ctrl = obplayer.Player.create_controller('remote station override', priority=99)
        self.ffmpeg = None
        self.stream_active = False
        self.running = True
        self.daemon = True
        self.self_sending_override = False
        self.req_count = 0

    def start_override(self, url):
        print('Starting Override...')
        self.ffmpeg = subprocess.Popen(['ffmpeg', '-loglevel', 'quiet', '-re', '-i', url, '-c:a', 'libopus', '-f', 'rtp', 'rtp://127.0.0.1:5000'], stdout=subprocess.PIPE)
        self.ctrl.add_request(media_type='remote_audio', start_time=time.time() + 4, duration=31536000, uri="rtp://127.0.0.1:5000")

    def stop_override(self):
        if self.ffmpeg != None:
            #print('Ending Override...')
            self.ffmpeg.kill()
            self.ffmpeg = None
        self.ctrl.stop_requests()
        self.ctrl.add_request(media_type='break', duration=1)

    def check_stream_status(self, stats_url, stream_url):
        try:
            req = requests.get(stats_url)
        except requests.exceptions.ConnectionError as e:
            # if we get more than three errors during a request to icecast,
            # we will stop logging the issue.
            if self.req_count <= 3:
                self.req_count =+ 1
                obplayer.Log.log('Couldn\'t connect to the icecast server for remote override. This message will only repeat three times after system startup.'  + '\nerror: ' + str(e), 'error')
                return False
            else:
                self.req_count =+ 1
                return False
        if req.status_code == 200:
            try:
                data = json.loads(req.content.decode())
                try:
                    if data['icestats'].get('source') != None:
                        if isinstance(data['icestats']['source'], (list)):
                            for stream in data['icestats']['source']:
                                #print(stream)
                                if stream_url == stream['listenurl'].replace('127.0.0.1', 'localhost'):
                                    return True
                        else:
                            if data['icestats']['source']['listenurl'] == stream_url.replace('127.0.0.1', 'localhost'):
                                return True
                    return False
                except Exception as e:
                    for stream in data['icestats']['source']:
                        if stream_url == stream['listenurl'].replace('127.0.0.1', 'localhost'):
                            return True
            except Exception as e:
                #print(e)
                return False
        else:
            return False

    def background(self):
        streams = []
        current_priority = 0
        mountpoints = obplayer.Config.setting('station_override_monitored_streams').split(',')
        for i, mountpoint in enumerate(mountpoints):
            data = mountpoint.split(':')
            ip = data[1].replace('//', '')
            port = data[2].replace('//', '').split('/')[0]
            mountpoint = data[2].replace('//', '').split('/')[1]
            stream_url = 'http://{0}:{1}/{2}'.format(ip, port, mountpoint)
            streams.append({
                'ip': ip,
                'port': port,
                'mountpoint': mountpoint,
                'stream_url': stream_url,
                'priority': i
            })
        #print(streams)
        while self.running:
            for stream in streams:
                ip = stream['ip']
                port = stream['port']
                mountpoint = stream['port']
                stream_url = stream['stream_url']
                stream_priority = stream['priority']
                if self.check_stream_status('http://{0}:{1}/status-json.xsl'.format(ip, port), stream_url):
                    #print('Override stream Found...')
                    if self.stream_active == False:
                        self.stream_active = True
                        # Check if stream check override already active remote stream.
                        if current_priority >= stream_priority:
                            self.start_override(stream_url)
                            current_priority = stream_priority
                else:
                    if self.stream_active:
                        self.stop_override()
                        current_priority = 0
                    self.stream_active = False
            time.sleep(6)


    def try_run(self):
        try:
            self.background()
        except Exception as e:
            print(e)
            raise

    def stop(self):
        self.running = False

def init():
    streamer = Streamer()
    streamer.start()

def quit():
    pass
