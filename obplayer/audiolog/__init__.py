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

from .audiolog import ObAudioLog
from .uploader import LogUploader

def init():
    obplayer.AudioLog = ObAudioLog()
    if obplayer.Config.setting('audiolog_enable_upload'):
        obplayer.LogUploader = LogUploader()
        obplayer.LogUploader.start()

def quit():
    # stop the audio logger.
    if hasattr(obplayer, 'AudioLog'):
        obplayer.AudioLog.stop()
    if hasattr(obplayer, 'LogUploader'):
        obplayer.LogUploader.stop()
