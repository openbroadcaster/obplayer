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

from .base import ObGstPipeline
from .breakbin import ObBreakPipeline
from .decodebin import ObPlayBinPipeline, ObAudioPlayBinPipeline, ObDecodeBinPipeline
from .image import ObImagePipeline
from .linein import ObLineInPipeline
from .rtp import ObRTPInputPipeline
from .rtsp import ObRTSPInputPipeline
#from .rtspa import ObRTSPAInputPipeline
from .sdp import ObSDPInputPipeline
from .testsignal import ObTestSignalPipeline
from .remote_audio import ObRemoteInputPipeline
