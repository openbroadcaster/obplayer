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

import serial
import traceback


class SerialTrigger (object):
    def __init__(self):
        self.trigger_serial = obplayer.Config.setting('alerts_trigger_serial')
        self.trigger_serial_file = obplayer.Config.setting('alerts_trigger_serial_file')
        self.trigger_serial_fd = None
        self.initialize()

    def initialize(self):
        try:
            obplayer.Log.log("initializing serial trigger on port " + self.trigger_serial_file, 'alerts')

            #serial_fd = serial.Serial(self.trigger_serial_file, baudrate=9600)
            #serial_fd.setDTR(False)
            #serial_fd.close()
        except:
            obplayer.Log.log("failed to initalize serial trigger", 'alerts')
            obplayer.Log.log(traceback.format_exc(), 'error')

    def alert_cycle_init(self):
        pass

    def alert_cycle_each(self, alert, alert_media, processor):
        pass

    def alert_cycle_start(self):
        try:
            obplayer.Log.log("asserted DTR on serial port " + self.trigger_serial_file, 'alerts')
            if self.trigger_serial_fd:
                self.trigger_serial_fd.close()
            self.trigger_serial_fd = serial.Serial(self.trigger_serial_file, baudrate=9600)
            self.trigger_serial_fd.setDTR(True)
        except:
            obplayer.Log.log("failed to assert DTR on serial port " + self.trigger_serial_file, 'alerts')
            obplayer.Log.log(traceback.format_exc(), 'error')

    def alert_cycle_stop(self):
        try:
            obplayer.Log.log("resetting DTR on serial port " + self.trigger_serial_file, 'alerts')
            if self.trigger_serial_fd:
                self.trigger_serial_fd.setDTR(False)
                self.trigger_serial_fd.close()
                self.trigger_serial_fd = None
        except:
            obplayer.Log.log("failed to assert DTR on serial port " + self.trigger_serial_file, 'alerts')
            obplayer.Log.log(traceback.format_exc(), 'error')

