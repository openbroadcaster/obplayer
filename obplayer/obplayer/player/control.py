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
import os.path
import threading
import traceback

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import GObject, Gst, GstVideo

Gst.init(None)

from . import pipes
from . import outputs

if sys.version.startswith('3'):
    unicode = str


class ObPlayer (object):
    def __init__(self):
        self.request_update = threading.Event()
        self.lock = threading.Lock()
        self.thread = None

        self.controllers = [ ]
        self.requests = { }
        self.outputs = { }
        self.patches = { }
        self.pipes = { }
        self.audio_levels = None
        self.audio_levels_timestamp = 0
        self.audio_silence = 0

        self.player_init()

    def player_init(self):
        self.outputs = { }
        self.outputs['audio'] = outputs.ObAudioOutputBin()
        if not obplayer.Config.headless:
            self.outputs['visual'] = outputs.ObVideoOutputBin()
        else:
            self.outputs['visual'] = outputs.ObFakeOutputBin()

        self.patches = { }
        for output in self.outputs.keys():
            self.patches[output] = None

        self.requests = { }
        for request in self.outputs.keys():
            self.requests[request] = None

        self.pipes = { }
        self.pipes['audio'] = pipes.ObAudioPlayBinPipeline('audio-playbin', self, obplayer.Config.setting('audio_out_visualization'))
        self.pipes['video'] = pipes.ObPlayBinPipeline('video-playbin', self)
        self.pipes['testsignal'] = pipes.ObTestSignalPipeline('test-signal', self)
        self.pipes['image'] = pipes.ObImagePipeline('image-pipeline', self)
        self.pipes['break'] = pipes.ObBreakPipeline('audio-break', self)
        self.pipes['linein'] = pipes.ObLineInPipeline('line-input', self)
        self.pipes['rtp'] = pipes.ObRTPInputPipeline('rtp-input', self)
        self.pipes['remote_audio'] = pipes.ObRemoteInputPipeline('remote_audio', self)
        self.pipes['rtsp'] = pipes.ObRTSPInputPipeline('rtsp-input', self)
        self.pipes['sdp'] = pipes.ObSDPInputPipeline('sdp-input', self)

        def silence_request(self, present_time, media_class):
            obplayer.Log.log("player has no requests to play; outputting silence", 'player')
            self.add_request(media_type='break', duration=3600)

        self.silencectrl = self.create_controller('silence', priority=1, allow_requeue=False)
        self.silencectrl.set_request_callback(silence_request)

    def start_player(self):
        self.thread = obplayer.ObThread('PlayerThread', target=self.try_run)
        self.thread.start()

    def player_quit(self):
        for pipe_name in self.pipes.keys():
            self.pipes[pipe_name].quit()

    def media_type_to_class(self, media_type):
        """
        if media_type in [ 'video', 'testsignal' ]:
            return 'audio/visual'
        elif media_type in [ 'audio', 'linein', 'break', 'rtp', 'rtsp', 'sdp' ]:
            return 'audio'
        elif media_type in [ 'image' ]:
            return 'visual'
        """
        if media_type not in self.pipes:
           raise Exception("unknown media type request: " + str(media_type))
        return '/'.join(self.pipes[media_type].min_class)

    @staticmethod
    def file_uri(file_location, filename=None):
        if filename:
            file_location = os.path.join(file_location, filename)
        if not file_location.startswith('/'):
            file_location = os.path.join(os.getcwd(), file_location)
        return 'file://' + file_location

    def create_controller(self, name, priority, default_play_mode=None, allow_overlay=False, allow_requeue=True):
        ctrl = ObPlayerController(self, name, priority, default_play_mode, allow_overlay, allow_requeue)
        for i in range(len(self.controllers)):
            if self.controllers[i].priority < ctrl.priority:
                self.controllers.insert(i, ctrl)
                return ctrl
        self.controllers.append(ctrl)
        return ctrl

    def try_run(self):
        #self.player_init()     # this was moved to the start_player method because with the new mediaclass thing, you can't add requests until the player is initialized
        self.request_update.set()
        while not self.thread.stopflag.wait(0.1):
            try:
                present_time = time.time()

                # stop any requests that have reached their end time and restore any outputs that may have been usurped by the now stopped request
                restore = False
                for output in self.requests.keys():
                    if self.requests[output] is not None and present_time > self.requests[output]['end_time']:
                        self.stop_request(output)
                        self.request_update.set()
                        restore = True
                if restore:
                    self.restore_outputs()

                #print(str(time.time()) + ": Current State (" + str(time.time()) + "): " + repr(self.request_update.is_set()) + " | " + (self.requests['audio']['filename'] if self.requests['audio'] is not None else "No astream") + " | " + (self.requests['visual']['filename'] if 'visual' in self.requests and self.requests['visual'] is not None else "No vstream"))
                #test = time.time()

                # get a list of output names sorted by the priority of the currently playing request
                priority_list = sorted([ (self.requests[output]['priority'] if self.requests[output] else 0, output) for output in self.requests.keys() ], key=lambda pair: pair[0], reverse=True)

                req = None
                while len(priority_list) > 0:
                    #print(str(time.time()) + ": Trying to fill in outputs: " + repr(priority_list))
                    remaining_outputs = [ pair[1] for pair in priority_list ]

                    req = self.get_request(present_time, priority_list[0][0], remaining_outputs, allow_query=self.request_update.is_set())

                    # if we found a request, then execute it, otherwise set req to the current highest priority request
                    if req:
                        self.execute_request(req, output_limit=remaining_outputs)
                    else:
                        req = self.requests[priority_list[0][1]]

                    if not req:
                        # if there was no request found and no existing requests to check, then exit the loop
                        break
                    else:
                        # if the current request is to be played exclusively, then exit the loop
                        if req['play_mode'] == 'exclusive':
                            break

                        # remove all outputs that the currently playing request is using (they cannot be overidden by a lower priority request, so we wont check them)
                        class_list = req['media_class'].split('/')
                        priority_list = [ pair for pair in priority_list if pair[1] not in class_list ]

                #print("----- It took: " + str(time.time() - test))
                #print(str(time.time()) + ": Current State (" + str(time.time()) + "): " + repr(self.request_update.is_set()) + " | " + (self.requests['audio']['filename'] if self.requests['audio'] is not None else "No astream") + " | " + (self.requests['visual']['filename'] if 'visual' in self.requests and self.requests['visual'] is not None else "No vstream"))

                # if the updated flag was set, then clear it
                if self.request_update.is_set():
                    self.request_update.clear()

                # call the update functions
                with self.lock:
                    for ctrl in self.controllers:
                        if ctrl.next_update and present_time > ctrl.next_update:
                            ctrl.next_update = 0
                            ctrl.call_player_update(present_time)

            except:
                obplayer.Log.log("exception in " + self.thread.name + " thread", 'error')
                obplayer.Log.log(traceback.format_exc(), 'error')
                time.sleep(2)

        self.player_quit()

    def get_request(self, present_time, priority, output_list, allow_query=False):
        with self.lock:
            for ctrl in self.controllers:
                if ctrl.priority <= priority:
                    break

                req = ctrl.get_request(present_time, '/'.join(output_list), allow_query=allow_query)
                if req is not None:
                    return req

                if ctrl.allow_overlay is False and ctrl.has_requests():
                    break

        return None

    def execute_request(self, req, output_limit=None):
        self.audio_levels = None
        request_pipe = self.pipes[req['media_type']]

        stop_list = [ ]
        if req['play_mode'] == 'exclusive':
            stop_list = [ output for output in output_limit if self.requests[output] ]
        elif req['controller'].allow_overlay is False:
            stop_list = [ output for output in output_limit if self.requests[output] and self.requests[output]['controller'] != req['controller'] ]

        if len(stop_list) > 0:
            self.repatch_outputs('/'.join(stop_list), None)

        max_list = [ output for output in request_pipe.max_class if output in output_limit ]
        min_list = [ output for output in req['media_class'].split('/') if output in output_limit ]

        patch_list = [ output for output in max_list if output in min_list or self.requests[output] is None ]
        patch_class = '/'.join(patch_list)

        # NOTE this should never happen
        if patch_class == '':
            print("Bloody Murder!!")
            print(repr(req))
            print("Audio Request:")
            print(repr(self.requests['audio']))
            print("Visual Request:")
            print(repr(self.requests['visual']))
            print("")

        obplayer.Log.log("now playing track %s: %s - %s (id: %d file: %s duration: %ss type: '%s' source: %s)" % (
            str(req['order_num'] + 1) if type(req['order_num']) == int and req['order_num'] >= 0 else '?',
            unicode(req['artist']).encode('ascii', 'replace').decode('ascii'),
            unicode(req['title']).encode('ascii', 'replace').decode('ascii'),
            req['media_id'],
            unicode(os.path.basename(req['uri'])).encode('ascii', 'replace').decode('ascii'),
            str(req['duration']),
            req['media_type'],
            req['controller'].name
        ), 'player')

        # change the patches as needed
        self.repatch_outputs(patch_class, req['media_type'])

        # set up and play the request
        request_pipe.stop('by execute request')
        request_pipe.set_request(req)
        request_pipe.start()

        if req['onstart']:
            req['onstart']()

        if outputs.Overlay and req['overlay_text']:
            outputs.Overlay.set_message(req['overlay_text'])

        # record the currently playing requests in the requests table (only the minimum set, so that other requests can use those outputs)
        for output in min_list:
            self.requests[output] = req

        # write entry into play log.
        playlog_notes = 'resuming at ' + str(time.time() - req['start_time']) + 's'
        obplayer.PlaylogData.add_entry(req['media_id'], req['artist'], req['title'], time.time(), req['controller'].name, playlog_notes)

    def stop_request(self, output):
        if self.requests[output] == None:
            return

        req = self.requests[output]
        request_pipe = self.pipes[req['media_type']]
        request_pipe.stop('by stop request')

        if outputs.Overlay and req['overlay_text']:
            outputs.Overlay.set_message('')

        if req['onend']:
            req['onend']()

        for name in self.requests.keys():
            if self.requests[name] == req:
                self.requests[name] = None

    def repatch_outputs(self, media_class, media_type):
        #print("Repatching " + media_class + " to pipe " + str(media_type))

        output_list = media_class.split('/')
        for pipe in self.pipes.keys():
            if pipe != media_type:
                unpatch_list = [ output for output in output_list if self.patches[output] == pipe ]
                if len(unpatch_list) > 0:
                    if set(unpatch_list) == self.pipes[pipe].mode:
                        self.pipes[pipe].stop('by repatch outputs')
                        """
                        requeued = [ ]
                        for output in unpatch_list:
                            if self.requests[output] and self.requests[output] not in requeued:
                                requeued.push(self.requests[output])
                                self.requests[output]['controller'].requeue_request(self.requests[output])
                                print("*** Requeued request " + repr(self.requests[output]))
                        """
                        if self.requests[unpatch_list[0]]:
                            self.requests[unpatch_list[0]]['controller'].requeue_request(self.requests[unpatch_list[0]])
                            #print("*** Requeued request " + repr(self.requests[unpatch_list[0]]))
                        else:
                            # TODO requeue any request for which we stop the pipe
                            #print("*** We didn't requeue " + repr(unpatch_list[0]))
                            pass

                    self.pipes[pipe].unpatch('/'.join(unpatch_list))

        if media_type is not None:
            for output in [ output for output in output_list if self.patches[output] == media_type ]:
                if self.requests[output]:
                    self.requests[output]['controller'].requeue_request(self.requests[output])
                    break
            patch_list = [ output for output in output_list if self.patches[output] != media_type ]
            if len(patch_list) > 0:
                self.pipes[media_type].patch('/'.join(patch_list))
        for output in output_list:
            self.patches[output] = media_type
            self.requests[output] = None

    def restore_outputs(self):
        self.audio_levels = None
        for output in self.requests.keys():
            if self.requests[output] is not None:
                # TODO you should maybe use the output caps instead of the media_class
                class_list = self.requests[output]['media_class'].split('/')
                patch_list = [ output for output in class_list if self.requests[output] is None ]
                if len(patch_list) > 0:
                    patch_list.sort()
                    self.repatch_outputs('/'.join(patch_list), self.patches[output])
                    for class_name in patch_list:
                        self.requests[class_name] = self.requests[output]
                    if outputs.Overlay:
                        outputs.Overlay.set_message(self.requests[output]['overlay_text'])

    def add_inter_tap(self, name):
        with self.lock:
            if self.patches['audio']:
                audio_state = self.pipes[self.patches['audio']].is_playing()
                self.pipes[self.patches['audio']].stop()

            if self.patches['visual']:
                visual_state = self.pipes[self.patches['visual']].is_playing()
                self.pipes[self.patches['visual']].stop()

            obplayer.Player.outputs['audio'].add_inter_tap(name + ':audio')
            obplayer.Player.outputs['visual'].add_inter_tap(name + ':video')
            if self.patches['audio'] and audio_state:
                self.pipes[self.patches['audio']].start()
            if self.patches['visual'] and visual_state and self.patches['audio'] != self.patches['visual']:
                self.pipes[self.patches['visual']].start()

    def get_controller_requests(self, ctrl):
        return [ output for output in self.requests.keys() if self.requests[output] != None and self.requests[output]['controller'] == ctrl ]

    def controller_request_is_playing(self, ctrl):
        for output in self.get_controller_requests(ctrl):
            media_type = self.requests[output]['media_type']
            request_pipe = self.pipes[media_type]
            if media_type != 'break' and request_pipe.is_playing():
                return True
        return False

    def stop_controller_requests(self, ctrl):
        for output in self.requests.keys():
            if self.requests[output] != None and self.requests[output]['controller'] == ctrl:
                self.stop_request(output)

    def get_requests(self):
        requests = { }
        for output in self.requests.keys():
            if self.requests[output] != None:
                requests[output] = self.requests[output].copy()
        return requests

    def get_audio_levels(self):
        if self.audio_levels is None or time.time() - self.audio_levels_timestamp > 2:
            return [ -1000.0, -1000.0 ]
        return self.audio_levels


#############################
#
# Player Controller
#
#############################

class ObPlayerController (object):
    def __init__(self, player, name, priority, default_play_mode=None, allow_overlay=False, allow_requeue=True):
        if default_play_mode is None:
            default_play_mode = 'exclusive'
        self.player = player
        self.name = name
        self.enabled = True
        self.priority = priority
        self.default_play_mode = default_play_mode
        self.allow_requeue = allow_requeue
        self.allow_overlay = allow_overlay

        self.lock = threading.Lock()
        self.queue = [ ]
        self.next_update = 0
        self.hold_requests_flag = False

        # TODO you could have a list of failed requests, where the request is automatically added (auto limit to say 5 entries)
        self.failed = [ ]

    def enable(self):
        self.enabled = True
        self.call_player_request(time.time())

    def disable(self):
        self.enabled = False
        self.clear_queue()

    # media_type can be: audio, video, image, linein, break, testsignal
    # play_mode can be:  exclusive, overlap
    def add_request(self, media_type, start_time=None, end_time=None, uri='', duration=0.0, offset=0, media_id=0, order_num=-1, artist='unknown', title='unknown', play_mode=None, overlay_text=None, onstart=None, onend=None):
        if not self.enabled:
            return

        # if uri was explicitly set to None, then don't add this request (media might be missing)
        if uri is None:
            return None

        # calculate start time and end time based on given info
        if start_time is None:
            start_time = self.get_requests_endtime()
        if end_time is not None:
            duration = end_time - start_time
        else:
            end_time = start_time + duration

        if play_mode is None:
            play_mode = self.default_play_mode

        req = {
            'controller' : self,
            'priority' : self.priority,
            'media_class' : self.player.media_type_to_class(media_type),

            'media_type' : media_type,
            'start_time' : start_time,
            'end_time' : end_time,
            'uri' : uri,
            'duration' : duration,
            'offset' : offset,
            'media_id' : media_id,
            'order_num' : order_num,
            'artist' : artist,
            'title' : title,
            'play_mode' : play_mode,
            'overlay_text' : overlay_text,
            'onstart' : onstart,
            'onend' : onend
        }

        self.insert_request(req)

    def insert_request(self, req):
        with self.lock:
            index = len(self.queue)
            for i in range(len(self.queue)):
                if self.queue[i]['start_time'] > req['start_time']:
                    index = i
                    break
            self.queue.insert(index, req)

    def requeue_request(self, req):
        if self.allow_requeue is True:
            with self.lock:
                for (i, queued) in enumerate(self.queue):
                    if queued == req:
                        #print("We totally didn't requeue!")
                        return
                        #self.queue.pop(i)
            #print("Requeuing request from [" + self.name + "] for (Duration: " + str(req['duration']) + ") [" + req['media_type'] + "] " + req['filename'])
            self.insert_request(req)
        else:
            # if requeues are not allowed and we are requeuing, then the player wont be playing the currently queued requests,
            # and we should get rid of them all, so that the player always calls the controllers to get new requests
            obplayer.Log.log("Clearing queue for source " + self.name + " (" + str(len(self.queue)) + " items)", 'debug')
            self.clear_queue()

    def clear_queue(self):
        with self.lock:
            self.queue = [ ]

    def has_requests(self):
        if len(self.queue) > 0 or len(self.player.get_controller_requests(self)) > 0:
            return True
        return False

    def request_is_playing(self):
        return self.player.controller_request_is_playing(self)

    def stop_requests(self):
        self.clear_queue()
        self.player.stop_controller_requests(self)

    def get_request(self, present_time, media_class, allow_query=False):
        if self.hold_requests_flag is True:
            return None
        index = self.find_current_request(present_time, media_class)
        if index is None and allow_query is True:
            self.call_player_request(present_time, media_class)
            index = self.find_current_request(present_time + 1, media_class)                # the plus one is because the new request's start time will be slight after present_time

        if index is None:
            return None

        with self.lock:
            req = self.queue[index]
            self.queue = self.queue[index+1:]
        return req

    def find_current_request(self, present_time, media_class):
        output_list = media_class.split('/')
        with self.lock:
            for (i, req) in enumerate(self.queue):
                if present_time >= req['start_time'] and present_time < req['end_time']:
                    class_list = req['media_class'].split('/')
                    for output in output_list:
                        if output in class_list:
                            return i
        return None

    def get_requests_endtime(self):
        start_time = time.time()
        for output in self.player.get_controller_requests(self):
            req = self.player.requests[output]
            if req['end_time'] > start_time:
                start_time = req['end_time']

        with self.lock:
            for req in self.queue:
                if req['end_time'] > start_time:
                    start_time = req['end_time']
        return start_time

    def adjust_request_times(self, start_time):
        if len(self.queue) <= 0:
            return

        with self.lock:
            diff = start_time - self.queue[0]['start_time']
            for req in self.queue:
                req['start_time'] += diff
                req['end_time'] += diff

    def hold_requests(self, value):
        self.hold_requests_flag = value

    def set_request_callback(self, func):
        self.do_player_request = func

    def set_update_callback(self, func):
        self.do_player_update = func

    def set_next_update(self, t):
        with self.lock:
            self.next_update = t

    def get_next_update(self):
        return self.next_update

    def call_player_request(self, present_time, media_class):
        try:
            return self.do_player_request(self, present_time, media_class)
        except:
            obplayer.Log.log("exception while calling do_player_request() on " + self.name, 'error')
            obplayer.Log.log(traceback.format_exc(), 'error')

    def call_player_update(self, present_time):
        try:
            return self.do_player_update(self, present_time)
        except:
            obplayer.Log.log("exception while calling do_player_update() on " + self.name, 'error')
            obplayer.Log.log(traceback.format_exc(), 'error')

    # called by the player to ask the controller what it wants to happen
    @staticmethod
    def do_player_request(ctrl, present_time, media_class):
        pass

    @staticmethod
    # called by the player to let the controller check things
    def do_player_update(ctrl, present_time):
        pass
