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

#import obplayer

import gi
from gi.repository import GObject

import dbus
import avahi
from dbus.mainloop.glib import DBusGMainLoop

service_name = "AudioOut@ObPlayer"
service_type = "_rtsp._tcp"
service_subtype = "_ravenna_session._sub._rtsp._tcp"
service_port = 8554

domain = ""     # Domain to publish on, default to .local
host = ""       #obsource.local" # Host to publish records for, default to localhost

group = None        #our entry group
rename_count = 12   # Counter so we only rename after collisions a sensible number of times

def add_service():
    global group, service_name, service_type, service_port, serviceTXT, domain, host
    if group is None:
        group = dbus.Interface(
                bus.get_object( avahi.DBUS_NAME, server.EntryGroupNew()),
                avahi.DBUS_INTERFACE_ENTRY_GROUP)
        group.connect_to_signal('StateChanged', entry_group_state_changed)

    #print("Adding service '%s' of type '%s' ..." % (service_name, service_type))

    group.AddService(
            avahi.IF_UNSPEC,
            avahi.PROTO_UNSPEC,
            dbus.UInt32(0),
            service_name, service_type,
            domain, host,
            dbus.UInt16(service_port),
            [])
    group.AddServiceSubtype(
            avahi.IF_UNSPEC,
            avahi.PROTO_UNSPEC,
            dbus.UInt32(0),
            service_name, service_type,
            domain,
            service_subtype)
    group.Commit()

def remove_service():
    global group

    if not group is None:
        group.Reset()

def server_state_changed(state):
    if state == avahi.SERVER_COLLISION:
        #print("WARNING: Server name collision")
        remove_service()
    elif state == avahi.SERVER_RUNNING:
        add_service()

def entry_group_state_changed(state, error):
    global service_name, server, rename_count

    #print("state change: %i" % state)

    if state == avahi.ENTRY_GROUP_ESTABLISHED:
        #print("Service established.")
        pass
    elif state == avahi.ENTRY_GROUP_COLLISION:

        rename_count = rename_count - 1
        if rename_count > 0:
            name = server.GetAlternativeServiceName(name)
            print("WARNING: Service name collision, changing name to '%s' ..." % name)
            remove_service()
            add_service()

        else:
            print("ERROR: No suitable service name found after %i retries, exiting." % n_rename)
            main_loop.quit()
    elif state == avahi.ENTRY_GROUP_FAILURE:
        print("Error in group state changed", error)
        main_loop.quit()
        return




if __name__ == '__main__':
    DBusGMainLoop( set_as_default=True )

    main_loop = GObject.MainLoop()
    bus = dbus.SystemBus()

    server = dbus.Interface(
            bus.get_object( avahi.DBUS_NAME, avahi.DBUS_PATH_SERVER ),
            avahi.DBUS_INTERFACE_SERVER )

    server.connect_to_signal( "StateChanged", server_state_changed )
    server_state_changed( server.GetState() )


    try:
        main_loop.run()
    except KeyboardInterrupt:
        pass

    if not group is None:
        group.Free()

 
