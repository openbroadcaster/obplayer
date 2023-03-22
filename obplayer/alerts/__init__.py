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
from obplayer.alerts.alert import ObAlert, parse_alert_file
from obplayer.alerts.processor import ObAlertProcessor
import os

Processor = None

def init():
    global Processor
    Processor = ObAlertProcessor()

    vol = obplayer.Config.setting("alerts_attention_signal_volume", True)

    if vol != None:
        vol = round(1 / vol, 3)
        print(vol)
        os.system("ffmpeg -y -i obplayer/alerts/data/canadian-attention-signal.mp3 -filter:a \"volume={0}\" /tmp/attn.wav".format(str(vol)))

def quit():
    pass

