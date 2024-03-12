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

import gi
from gi.repository import GObject

from datetime import datetime


class ObGui:

    def __init__(self):
        pass

    def create_window(self):

        if obplayer.Config.headless:
            return

        else:
            global Gtk, Gdk, GdkX11, GdkPixbuf, cairo
            gi.require_version("Gtk", "3.0")
            gi.require_version("GdkX11", "3.0")
            from gi.repository import Gtk, Gdk, GdkX11, GdkPixbuf, cairo

        builder = Gtk.Builder()
        builder.add_from_file("obplayer/ui.glade")

        # SET SOME COLORS
        gtk_black = Gdk.Color(0, 0, 0)

        # MAIN WINDOW
        self.gui_window = builder.get_object("main_window")
        self.gui_window.set_title("Openbroadcaster GTK Player")
        self.gui_window.resize(640, 480)
        self.gui_window_fullscreen = False

        # FULLSCREEN TOGGLE
        self.gui_window.connect("key-press-event", self.key_press)

        # MISC WIDGETS
        self.gui_toolbar = builder.get_object("toolbar")
        self.gui_statusbar = builder.get_object("statusbar")

        def do_nothing(one, two):
            pass

        # DRAWING AREA
        """
        self.gui_drawing_area = builder.get_object('drawingarea_slideshow')
        self.gui_drawing_area_alpha = 1
        #self.gui_drawing_area.connect('draw', self.drawing_area_expose)
        self.gui_drawing_area.set_size_request(250, 250)
        self.gui_drawing_area.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
        self.gui_drawing_area.modify_bg(Gtk.StateFlags.NORMAL, gtk_black)
        self.gui_drawing_area.realize()
        """

        self.gui_gst_area = builder.get_object("drawingarea_gst")
        self.gui_gst_area_alpha = 1
        self.gui_gst_area.set_size_request(250, 250)
        self.gui_gst_area.connect("draw", do_nothing)
        self.gui_gst_area.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
        self.gui_gst_area.modify_bg(Gtk.StateFlags.NORMAL, gtk_black)
        self.gui_gst_area.realize()

        try:
            # Test for X11 session.
            self.gst_xid = self.gui_gst_area.get_window().get_xid()
        except AttributeError:
            # Set as wayland session.
            self.gst_xid = "Wayland"
        """
        # TODO note, you changed these to refer to the drawing area instead of the viewport, so it's now a misnomer
        #self.gui_drawing_area_viewport = builder.get_object('drawingarea_slideshow')
        #self.gui_gst_area_viewport = builder.get_object('drawingarea_gst')
        self.gui_drawing_area_viewport = builder.get_object('drawingarea_slideshow_viewport')
        self.gui_gst_area_viewport = builder.get_object('drawingarea_gst_viewport')

        # TODO for some reason this is the issue! why?
        #self.gui_gst_area_viewport.hide()
        #self.gui_drawing_area.hide()

        #self.gui_gst_area_viewport.hide()
        #self.gui_drawing_area_viewport.hide()
        #self.gui_gst_area_viewport.show()

        self.pixbuf = False
        self.pixbuf_original = False
        self.next_pixbuf = False
        self.next_pixbuf_original = False
        """

        # track our fullscreen pointer hide timeout event id.
        self.fullscreen_hide_pointer_id = None

        # connect signals
        builder.connect_signals(self)

        # start minimized?
        if obplayer.Config.args.minimize:
            self.gui_window.iconify()

        # go fullscreen?
        if obplayer.Config.args.fullscreen:
            self.fullscreen_toggle(None)

        # show main window.
        if obplayer.Config.headless == False:
            self.gui_window.show()

    def key_press(self, widget, event):
        if event.keyval == Gdk.KEY_F11:
            self.fullscreen_toggle(None)

    def application_shutdown(self, widget):
        obplayer.Main.quit()

    """
    def change_media_mode(self, mode):
        if obplayer.Config.headless:
            return

        obplayer.Config.setting('audio_out_visualization') == 0
        if mode == 'image' or (mode == 'audio' and obplayer.Config.setting('audio_out_visualization') == 0):
            self.gui_gst_area_viewport.hide()
            # if the image area is not currently visible, then clear what was previous displayed on the image area
            if not self.gui_drawing_area_viewport.is_visible():
                self.pixbuf = False
                self.pixbuf_original = False
            self.gui_drawing_area_viewport.show()

        else:
            self.gui_drawing_area_viewport.hide()
            self.gui_gst_area_viewport.show()
    """

    def fullscreen_toggle(self, widget):
        if obplayer.Config.headless:
            return

        if self.gui_window_fullscreen == False:
            self.gui_window.fullscreen()
            self.gui_window_fullscreen = True
            self.gui_toolbar.hide()
            self.fullscreen_hide_pointer_id = GObject.timeout_add(
                1000, self.fullscreen_hide_pointer
            )

        else:
            self.gui_window.unfullscreen()
            self.gui_window_fullscreen = False
            self.gui_toolbar.show()
            self.fullscreen_show_pointer()

    def fullscreen_hide_pointer(self):
        if self.gui_window_fullscreen != True:
            return
        cursor = Gdk.Cursor.new(Gdk.CursorType.BLANK_CURSOR)
        self.gui_window.get_root_window().set_cursor(cursor)
        self.gui_toolbar.hide()
        self.fullscreen_hide_pointer_id = None
        return False  # GObject.timeout_add for pointer show/hide on fullscreen, using return false to avoid repeated calls.

    def fullscreen_show_pointer(self):
        cursor = Gdk.Cursor.new(Gdk.CursorType.ARROW)
        self.gui_window.get_root_window().set_cursor(cursor)

    def pointer_position_watch(self, widget, event):
        if self.gui_window_fullscreen == False:
            return

        if self.fullscreen_hide_pointer_id != None:
            GObject.source_remove(self.fullscreen_hide_pointer_id)

        self.fullscreen_show_pointer()
        self.fullscreen_hide_pointer_id = GObject.timeout_add(
            3000, self.fullscreen_hide_pointer
        )

        if event.y < 20:
            self.gui_toolbar.show()
        else:
            self.gui_toolbar.hide()

    """
    def pixbuf_resize_to_drawing_area(self, pixbuf):
        org_img_size = (pixbuf.get_width(), pixbuf.get_height())
        org_img_size_ratio = float(org_img_size[0]) / float(org_img_size[1])

        target_img_size = (self.gui_drawing_area.get_allocated_width(), self.gui_drawing_area.get_allocated_height())
        target_img_size_ratio = float(target_img_size[0]) / float(target_img_size[1])

        if org_img_size_ratio >= target_img_size_ratio:
            img_size = (target_img_size[0], org_img_size[1] * (float(target_img_size[0]) / float(org_img_size[0])))
        else:
            img_size = (org_img_size[0] * (float(target_img_size[1]) / float(org_img_size[1])), target_img_size[1])
        return pixbuf.scale_simple(int(img_size[0]), int(img_size[1]), GdkPixbuf.InterpType.BILINEAR)

    def drawing_area_resize_event(self, widget, event):
        if self.pixbuf_original != False:
            self.pixbuf = self.pixbuf_resize_to_drawing_area(self.pixbuf_original)
            self.gui_drawing_area.queue_draw()

    def drawing_area_expose(self, da, event):
        if self.pixbuf != False:
            imgw = self.pixbuf.get_width()
            if imgw < self.gui_drawing_area.get_allocated_width():
                offset_x = int((self.gui_drawing_area.get_allocated_width() - imgw) / 2)
            else:
                offset_x = 0

            imgh = self.pixbuf.get_height()
            if imgh < self.gui_drawing_area.get_allocated_height():
                offset_y = int((self.gui_drawing_area.get_allocated_height() - imgh) / 2)
            else:
                offset_y = 0

            self.cairo = da.get_window().cairo_create()
            Gdk.cairo_set_source_pixbuf(self.cairo, self.pixbuf, offset_x, offset_y)
            self.cairo.paint_with_alpha(self.gui_drawing_area_alpha)
            self.cairo.stroke()
        else:
            try:
                self.cairo.destroy()
            except:
                pass

    def drawing_area_image_update(self, filename=False):
        if obplayer.Config.headless:
            return
        GObject.idle_add(self.drawing_area_image_update_idleadd, filename)

    def drawing_area_image_update_idleadd(self, filename=False):
        if filename != False:
            self.next_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(filename, self.gui_drawing_area.get_allocated_width(), self.gui_drawing_area.get_allocated_height())
            self.next_pixbuf_original = self.next_pixbuf
            self.next_pixbuf = self.pixbuf_resize_to_drawing_area(self.next_pixbuf_original)

        else:
            self.next_pixbuf = False
            self.next_pixbuf_original = False

        if self.pixbuf != False:
            self.drawing_area_transition_mode = 'out'
            GObject.timeout_add(50, self.drawing_area_transition_timer, 'fade')

        else:
            self.gui_drawing_area_alpha = 0
            self.pixbuf = self.next_pixbuf
            self.pixbuf_original = self.next_pixbuf_original
            self.drawing_area_transition_mode = 'in'
            GObject.timeout_add(50, self.drawing_area_transition_timer, 'fade')

    def drawing_area_transition_timer(self, action):
        if action == 'fade':
            if self.drawing_area_transition_mode == 'out' and self.pixbuf != False:
                if self.gui_drawing_area_alpha <= 0:
                    self.drawing_area_transition_mode = 'in'
                    self.pixbuf = self.next_pixbuf
                    self.pixbuf_original = self.next_pixbuf_original

                else:
                    self.gui_drawing_area_alpha -= 0.05
                    self.gui_drawing_area.queue_draw()

            if self.drawing_area_transition_mode == 'in' and self.pixbuf != False:
                if self.gui_drawing_area_alpha >= 1:
                    return False
                else:
                    self.gui_drawing_area_alpha += 0.05

            self.gui_drawing_area.queue_draw()
        return True
    """
