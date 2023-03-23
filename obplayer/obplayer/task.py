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

import threading

import traceback

class ObThread (threading.Thread):
    threads = []

    def __init__(self, name=None, target=None):
        if name is None:
            name = self.__class__.__name__
        threading.Thread.__init__(self, None, None, name)
        ObThread.threads.insert(0, self)
        self.stopflag = threading.Event()
        self.target = target

    def remove_thread(self):
        ObThread.threads.remove(self)

    def start(self):
        obplayer.Log.log("starting thread <%s>" % (str(self.name),), 'debug')
        threading.Thread.start(self)

    def stop(self):
        obplayer.Log.log("stopping thread <%s>" % (str(self.name),), 'debug')
        self.stopflag.set()

    @staticmethod
    def stop_all():
        for t in ObThread.threads:
            t.stop()

    @staticmethod
    def join_all():
        for t in ObThread.threads:
            if t.daemon is False:
                t.join()
                obplayer.Log.log("thread <%s> has joined successfully" % (str(t.name),), 'debug')
            else:
                obplayer.Log.log("thread <%s> is daemon, skipping" % (str(t.name),), 'debug')

    def run(self):
        try:
            if self.target:
                self.target()
            else:
                self.try_run()
        except:
            obplayer.Log.log("exception occurred in thread " + str(self.name) + ":", 'error')
            obplayer.Log.log(traceback.format_exc(), 'error')
        finally:
            del self.target

