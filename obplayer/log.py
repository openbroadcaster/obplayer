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

MAX_BACKLOG = 2000

#
# OpenBroadcaster Logging Class
# Provides logging for remote application.  Presently logging outputs to stdout only.
#
class ObLog:
    def __init__(self):
        self.datadir = obplayer.ObData.get_datadir()
        self.logbuffer = []
        self.debug = False

        self.logdate = False
        self.logfile = False
        self.alertlogfile = False

        self.lock = threading.Lock()

    def set_debug(self, flag):
        self.debug = flag

    def log(self, message, mtype='error', alert_data=None):

        mstring = '[' + time.strftime('%b %d %Y %H:%M:%S', time.gmtime()) + ' UTC] [' + mtype + '] ' + message

        self.lock.acquire()

        # write to log file. (filename is present date).
        if self.logdate != time.strftime('%Y.%m.%d'):
            self.logdate = time.strftime('%Y.%m.%d')

            if self.logfile != False:
                self.logfile.close()

            if self.alertlogfile != False:
                self.alertlogfile.close()

            self.logfile = open(self.datadir + '/logs/' + self.logdate + '.obplayer.log', 'a', 1)
            self.alertlogfile = open(self.datadir + '/logs/' + self.logdate + '.alerts.obplayer.log', 'a', 1)

        # if alert, log to alerts only log too.
        if mtype == 'alerts':
            self.alertlogfile.write(mstring + '\n')
        if alert_data != None:
            with open(self.datadir + '/' + '.' + 'alert_count.txt', 'w') as file:
                print(str(alert_data.times_played))
                #file.write(alert_data.times_played)
        self.logfile.write(mstring + '\n')

        self.logbuffer.append(mstring)
        if len(self.logbuffer) > MAX_BACKLOG:
            self.logbuffer.pop(0)

        if self.debug:
            print(mstring)

        self.lock.release()

        return True

    def get_log(self):
        return self.logbuffer

    def get_in_hms(seconds):
        hours = int(seconds) / 3600
        seconds -= 3600 * hours
        minutes = seconds / 60
        seconds -= 60 * minutes
        return "%02d:%02d:%02d" % (hours, minutes, seconds)
