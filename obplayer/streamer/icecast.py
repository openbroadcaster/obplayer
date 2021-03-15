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
import time
import threading
import traceback

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst

from .base import ObGstStreamer

import uuid
from .metadata_updater import MetadataUpdater


class ObIcecastStreamer (ObGstStreamer):
    def __init__(self, streamer_icecast_ip, streamer_icecast_port, streamer_icecast_password,
        streamer_icecast_mount, streamer_icecast_streamname, streamer_icecast_description,
        streamer_icecast_url, streamer_icecast_public, streamer_icecast_bitrate, enable_title_streaming=False):
        self.icecast_ip = streamer_icecast_ip
        self.icecast_port = streamer_icecast_port
        self.icecast_password = streamer_icecast_password
        self.icecast_mount = streamer_icecast_mount
        self.icecast_streamname = streamer_icecast_streamname
        self.icecast_description = streamer_icecast_description
        self.icecast_url = streamer_icecast_url
        self.icecast_public = streamer_icecast_public
        self.icecast_bitrate = streamer_icecast_bitrate
        self._metadata_updater_thread = None
        self.mode = obplayer.Config.setting('streamer_0_icecast_mode')
        ObGstStreamer.__init__(self, 'icecast_' + uuid.uuid4().hex)

        if obplayer.Config.setting('streamer_0_icecast_mode') == 'audio':
            if enable_title_streaming:
                self._metadata_updater_thread = MetadataUpdater(host=self.icecast_ip, port=self.icecast_port, username='source',
                                                                password=self.icecast_password, mount=self.icecast_mount)
            self.make_audio_pipe()
        else:
            self.make_video_pipe(obplayer.Config.setting('streamer_0_icecast_mode'))
            title_streaming = False

    def make_audio_pipe(self):
        self.audiopipe = [ ]

        audio_input = obplayer.Config.setting('streamer_audio_in_mode')
        if audio_input == 'alsa':
            self.audiosrc = Gst.ElementFactory.make('alsasrc', 'audiosrc')
            alsa_device = obplayer.Config.setting('streamer_audio_in_alsa_device')
            if alsa_device != '':
                self.audiosrc.set_property('device', alsa_device)

        elif audio_input == 'jack':
            self.audiosrc = Gst.ElementFactory.make('jackaudiosrc', 'audiosrc')
            self.audiosrc.set_property('connect', 0)  # don't autoconnect ports.
            name = obplayer.Config.setting('streamer_audio_in_jack_name')
            self.audiosrc.set_property('client-name', name if name else 'obplayer')

        elif audio_input == 'oss':
            self.audiosrc = Gst.ElementFactory.make('osssrc', 'audiosrc')

        elif audio_input == 'pulse':
            self.audiosrc = Gst.ElementFactory.make('pulsesrc', 'audiosrc')
            self.audiosrc.set_property('client-name', 'obplayer-streamer-to-icecast')

        elif audio_input == 'test':
            self.audiosrc = Gst.ElementFactory.make('fakesrc', 'audiosrc')

        elif audio_input == 'intersink':
            print(self.name)
            obplayer.Player.add_inter_tap(self.name)
            self.audiosrc = Gst.ElementFactory.make('interaudiosrc')
            self.audiosrc.set_property('channel', self.name + ':audio')
            #self.audiosrc.set_property('buffer-time', 8000000000)
            #self.audiosrc.set_property('latency-time', 8000000000)

        else:
            self.audiosrc = Gst.ElementFactory.make('autoaudiosrc', 'audiosrc')

        self.audiopipe.append(self.audiosrc)

        caps = Gst.ElementFactory.make('capsfilter')
        caps.set_property('caps', Gst.Caps.from_string("audio/x-raw,channels=2,channel-mask=(bitmask)0x3"))
        self.audiopipe.append(caps)

        self.audiopipe.append(Gst.ElementFactory.make("queue2"))

        """
        self.level = Gst.ElementFactory.make("level", "level")
        self.level.set_property('message', True)
        self.level.set_property('interval', int(1.0 * Gst.SECOND))
        self.audiopipe.append(self.level)

        self.selector = Gst.ElementFactory.make("valve", "selector")
        self.selector.set_property('drop', True)
        self.is_dropping = True
        self.pipeline.get_bus().add_signal_watch()
        self.pipeline.get_bus().connect('message::element', self.detect_silence)
        self.audiopipe.append(self.selector)
        """

        self.audiopipe.append(Gst.ElementFactory.make("audioconvert"))

        self.encoder = Gst.ElementFactory.make("lamemp3enc")
        if self.icecast_bitrate != 0:
            self.encoder.set_property('target', 1)
            self.encoder.set_property('bitrate', self.icecast_bitrate)
            self.encoder.set_property('cbr', True)
        self.audiopipe.append(self.encoder)

        self.audiopipe.append(Gst.ElementFactory.make("queue2"))

        self.shout2send = Gst.ElementFactory.make("shout2send", "shout2send")
        '''
        self.shout2send.set_property('ip', obplayer.Config.setting('streamer_icecast_ip'))
        self.shout2send.set_property('port', int(obplayer.Config.setting('streamer_icecast_port')))
        self.shout2send.set_property('password', obplayer.Config.setting('streamer_icecast_password'))
        self.shout2send.set_property('mount', obplayer.Config.setting('streamer_icecast_mount'))
        self.shout2send.set_property('streamname', obplayer.Config.setting('streamer_icecast_streamname'))
        self.shout2send.set_property('description', obplayer.Config.setting('streamer_icecast_description'))
        self.shout2send.set_property('url', obplayer.Config.setting('streamer_icecast_url'))
        self.shout2send.set_property('public', obplayer.Config.setting('streamer_icecast_public'))
        '''
        self.shout2send.set_property('ip', self.icecast_ip)
        self.shout2send.set_property('port', int(self.icecast_port))
        self.shout2send.set_property('password', self.icecast_password)
        self.shout2send.set_property('mount', self.icecast_mount)
        self.shout2send.set_property('streamname', self.icecast_streamname)
        self.shout2send.set_property('description', self.icecast_description)
        self.shout2send.set_property('url', self.icecast_url)
        self.shout2send.set_property('public', self.icecast_public)
        self.audiopipe.append(self.shout2send)

        #self.elements.append(ObRtpOutput())

        self.build_pipeline(self.audiopipe)

    def make_video_pipe(self, res):
        if res == 'video320x200':
            video_res = '320x200'
        elif res == 'video640x480':
            video_res = '640x480'
        elif res == 'video1280x720':
            video_res = '1280x720'
        elif res == 'video1920x1080':
            video_res = '1920x1080'
        else:
            video_res = '0x0'
        obplayer.Player.add_inter_tap(self.name)

        self.audiopipe = [ ]

        self.interaudiosrc = Gst.ElementFactory.make('interaudiosrc')
        self.interaudiosrc.set_property('channel', self.name + ':audio')
        #self.interaudiosrc.set_property('buffer-time', 8000000000)
        #self.interaudiosrc.set_property('latency-time', 8000000000)
        self.audiopipe.append(self.interaudiosrc)

        caps = Gst.ElementFactory.make('capsfilter')
        caps.set_property('caps', Gst.Caps.from_string("audio/x-raw,channels=2,channel-mask=(bitmask)=0x3"))
        self.audiopipe.append(caps)

        self.audiopipe.append(Gst.ElementFactory.make("queue2"))

        self.audiopipe.append(Gst.ElementFactory.make("audioconvert"))
        self.audiopipe.append(Gst.ElementFactory.make("audioresample"))

        caps = Gst.ElementFactory.make('capsfilter')
        #caps.set_property('caps', Gst.Caps.from_string("audio/x-raw,channels=2,rate=44100"))
        caps.set_property('caps', Gst.Caps.from_string("audio/x-raw,channels=2,rate=48000"))
        self.audiopipe.append(caps)

        #self.encoder = Gst.ElementFactory.make("lamemp3enc")
        #self.encoder = Gst.ElementFactory.make("opusenc")
        self.encoder = Gst.ElementFactory.make("vorbisenc")
        self.audiopipe.append(self.encoder)

        self.audiopipe.append(Gst.ElementFactory.make("queue2"))

        self.build_pipeline(self.audiopipe)


        self.videopipe = [ ]

        """
        self.videopipe.append(Gst.ElementFactory.make("udpsrc"))
        self.videopipe[-1].set_property('port', 5500)
        self.videopipe[-1].set_property('caps', Gst.Caps.from_string("application/x-rtp"))

        self.videopipe.append(Gst.ElementFactory.make("queue2"))
        self.videopipe.append(Gst.ElementFactory.make("rtpvp9depay"))
        #self.videopipe.append(Gst.ElementFactory.make("vp9dec"))
        #self.videopipe.append(Gst.ElementFactory.make("videotestsrc"))
        #self.videopipe.append(Gst.ElementFactory.make("videoconvert"))
        #self.videopipe.append(Gst.ElementFactory.make("videorate"))
        #self.videopipe.append(Gst.ElementFactory.make("queue2"))
        #self.videopipe.append(Gst.ElementFactory.make("theoraenc"))
        """

        """
        self.lock = threading.Lock()
        self.microphone_queue = []
        self.appsrc = Gst.ElementFactory.make('appsrc')
        self.appsrc.set_property('is-live', True)
        self.appsrc.set_property('format', 3)
        #self.appsrc.set_property('caps', Gst.Caps.from_string("audio/x-raw,channels=1,rate=" + str(self.rate) + ",format=S16LE,layout=interleaved"))
        self.appsrc.set_property('caps', Gst.Caps.from_string("video/x-raw,format=RGBA,width=384,height=288,framerate=30/1"))
        self.blocksize = 384 * 288 * 4
        self.appsrc.connect("need-data", self._cb_need_data)
        self.videopipe.append(self.appsrc)
        #self.videopipe.append(Gst.ElementFactory.make("videoparse"))
        self.videopipe.append(Gst.ElementFactory.make("queue2"))
        self.videopipe.append(Gst.ElementFactory.make("videoconvert"))
        self.videopipe.append(Gst.ElementFactory.make("vp9enc"))
        """

        self.intervideosrc = Gst.ElementFactory.make('intervideosrc')
        self.intervideosrc.set_property('channel', self.name + ':video')
        self.videopipe.append(self.intervideosrc)

        self.videopipe.append(Gst.ElementFactory.make("queue2"))

        #self.videopipe.append(Gst.ElementFactory.make("videotestsrc"))
        #self.videopipe[-1].set_property('is-live', True)

        self.videopipe.append(Gst.ElementFactory.make("videorate"))
        self.videopipe.append(Gst.ElementFactory.make("videoconvert"))
        self.videopipe.append(Gst.ElementFactory.make("videoscale"))

        caps = Gst.ElementFactory.make('capsfilter', "videocapsfilter")
        #caps.set_property('caps', Gst.Caps.from_string("video/x-raw,width=384,height=288,framerate=15/1"))
        #caps.set_property('caps', Gst.Caps.from_string("video/x-raw,width=100,height=75,framerate=15/1"))
        #caps.set_property('caps', Gst.Caps.from_string("video/x-raw,width=384,height=288,framerate=15/1"))
        caps.set_property('caps', Gst.Caps.from_string("video/x-raw,width={0},height={1},framerate=24/1,pixel-aspect-ratio=1/1". format(video_res.split('x')[0], video_res.split('x')[1])))
        self.videopipe.append(caps)

        #self.videopipe.append(Gst.ElementFactory.make("vp8enc"))
        #self.videopipe.append(Gst.ElementFactory.make("vp9enc"))
        self.videopipe.append(Gst.ElementFactory.make("theoraenc"))
        #self.videopipe.append(Gst.ElementFactory.make("x264enc"))
        #self.videopipe[-1].set_property('target-bitrate', 128000)

        self.videopipe.append(Gst.ElementFactory.make("queue2"))

        self.build_pipeline(self.videopipe)


        self.commonpipe = [ ]

        self.commonpipe.append(Gst.ElementFactory.make("oggmux"))
        #self.commonpipe.append(Gst.ElementFactory.make("webmmux"))
        #self.commonpipe[-1].set_property('streamable', True)

        self.commonpipe.append(Gst.ElementFactory.make("queue2"))

        self.shout2send = Gst.ElementFactory.make("shout2send", "shout2send")
        self.shout2send.set_property('ip', self.icecast_ip)
        self.shout2send.set_property('port', int(self.icecast_port))
        self.shout2send.set_property('password', self.icecast_password)
        self.shout2send.set_property('mount', self.icecast_mount)
        self.shout2send.set_property('streamname', self.icecast_streamname)
        self.shout2send.set_property('description', self.icecast_description)
        self.shout2send.set_property('url', self.icecast_url)
        self.shout2send.set_property('public', self.icecast_public)
        self.shout2send.set_property('async', False)
        self.shout2send.set_property('sync', False)
        self.shout2send.set_property('qos', True)
        self.commonpipe.append(self.shout2send)

        #self.commonpipe.append(Gst.ElementFactory.make("filesink"))
        #self.commonpipe[-1].set_property('location', "/home/trans/test.webm")

        self.build_pipeline(self.commonpipe)

        self.audiopipe[-1].link(self.commonpipe[0])
        self.videopipe[-1].link(self.commonpipe[0])

    def queue_data(self, data):
        with self.lock:
            self.microphone_queue.append(data)

    def _cb_need_data(self, unused, userdata):
        with self.lock:
            if len(self.microphone_queue):
                data = self.microphone_queue.pop(0)
            else:
                #data = bytearray(self.blocksize)
                raw = bytearray(self.blocksize)
                data = Gst.Buffer.new_allocate(None, len(raw), None)
                data.fill(0, raw)
                data.dts = Gst.CLOCK_TIME_NONE
                data.pts = Gst.CLOCK_TIME_NONE
                data.duration = Gst.CLOCK_TIME_NONE
        #if self.encoder:
        #    data = self.encoder.decode_buffer(data)
        #print("Decoded: " + str(len(data)) + " " + repr(data[:20]))
        #gbuffer = Gst.Buffer.new_allocate(None, len(data), None)
        #gbuffer.fill(0, data)
        #ret = self.appsrc.emit('push-buffer', gbuffer)
        ret = self.appsrc.emit('push-buffer', data)

    def detect_silence(self, bus, message, *args):
        peak = message.get_structure().get_value('peak')
        if peak[0] < -28:
            if not self.is_dropping:
                self.is_dropping = True
                self.selector.set_property('drop', True)
                print("now dropping buffers")
        else:
            if self.is_dropping:
                self.is_dropping = False
                self.selector.set_property('drop', False)
                print("now outputting buffers")
        return True

    def start_title_streaming(self):
        if self._metadata_updater_thread != None:
            self._metadata_updater_thread.start()

    def stop_title_streaming(self):
        if self._metadata_updater_thread != None:
            self._metadata_updater_thread.running = False
            self._metadata_updater_thread = None

class ObRtpOutput (Gst.Bin):
    def __init__(self):
        Gst.Bin.__init__(self)

        """
        self.encoder = Gst.ElementFactory.make("opusenc")
        self.add(self.encoder)

        self.payloader = Gst.ElementFactory.make("rtpopuspay")
        self.add(self.payloader)
        """

        self.capsfilter = Gst.ElementFactory.make('capsfilter')
        self.capsfilter.set_property('caps', Gst.Caps.from_string("audio/x-raw,channels=2,rate=44100,format=S16LE,layout=interleaved"))
        self.add(self.capsfilter)

        self.payloader = Gst.ElementFactory.make("rtpL16pay")
        self.add(self.payloader)

        self.rtpbin = Gst.ElementFactory.make("rtpbin")
        self.add(self.rtpbin)

        self.udp_rtp = Gst.ElementFactory.make("udpsink")
        self.udp_rtp.set_property('host', '192.168.1.248')
        self.udp_rtp.set_property('port', 4000)
        self.add(self.udp_rtp)

        self.udp_rtcp = Gst.ElementFactory.make("udpsink")
        self.udp_rtcp.set_property('host', '192.168.1.248')
        self.udp_rtcp.set_property('port', 4001)
        self.udp_rtcp.set_property('sync', False)
        self.udp_rtcp.set_property('async', False)
        self.add(self.udp_rtcp)

        # link elements
        self.sinkpad = Gst.GhostPad.new('sink', self.capsfilter.get_static_pad('sink'))
        self.add_pad(self.sinkpad)

        self.capsfilter.link(self.payloader)
        #self.encoder.link(self.payloader)

        """
        self.rtp_sink = self.rtpbin.get_request_pad('send_rtp_sink_0')
        self.payloader.get_static_pad('src').link(self.rtp_sink)
        self.rtp_src = self.rtpbin.get_request_pad('send_rtp_src_0')
        self.rtp_src.link(self.udp_rtp.get_static_pad('sink'))

        self.rtcp_src = self.rtpbin.get_request_pad('send_rtcp_src_0')
        self.rtcp_src.link(self.udp_rtcp.get_static_pad('sink'))
        """

        self.payloader.link_pads('src', self.rtpbin, 'send_rtp_sink_0')
        self.rtpbin.link_pads('send_rtp_src_0', self.udp_rtp, 'sink')

        self.rtpbin.link_pads('send_rtcp_src_0', self.udp_rtcp, 'sink')
