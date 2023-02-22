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
gi.require_version('Gtk', '3.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import GObject, Gtk, Gdk, GdkX11, GdkPixbuf, Pango, PangoCairo
import cairo

import ctypes
import ctypes.util
import cairo
import sys
import threading

pycairo_dll = ctypes.pydll.LoadLibrary(cairo._cairo.__file__)
pycairo_dll.PycairoContext_FromContext.restype = ctypes.py_object
pycairo_dll.PycairoContext_FromContext.argtypes = (ctypes.c_void_p, ctypes.py_object, ctypes.py_object)

cairo_dll = ctypes.pydll.LoadLibrary(ctypes.util.find_library('cairo'))
cairo_dll.cairo_reference.restype = ctypes.c_void_p
cairo_dll.cairo_reference.argtypes = (ctypes.c_void_p,)

def cairo_context_from_gi(gicr):
    #assert isinstance(gicr, GObject.GBoxed)
    offset = sys.getsizeof(object())  # size of PyObject_HEAD
    # Pull the "boxed" pointer off out and use it as a cairo_t*
    cr_ptr = ctypes.c_void_p.from_address(id(gicr) + offset)
    cr = pycairo_dll.PycairoContext_FromContext(cr_ptr, cairo.Context, None)
    # Add a new ref because the pycairo context will attempt to manage this
    cairo_dll.cairo_reference(cr_ptr)
    return cr


class ObOverlay (object):
    def __init__(self):
        self.message = None
        self.scroll_enable = False
        self.scroll_pos = 0.0
        self.scroll_wrap = 1.0
        self.lock = threading.Lock()
        GObject.timeout_add(50, self.overlay_scroll_timer)

    def overlay_scroll_timer(self):
        with self.lock:
            self.scroll_pos -= 0.015
            if self.scroll_pos <= 0.0:
                self.scroll_pos = self.scroll_wrap
        GObject.timeout_add(50, self.overlay_scroll_timer)

    def set_message(self, msg):
        if msg:
            self.scroll_enable = True
            with self.lock:
                if self.message != msg:
                    self.scroll_pos = 0.05
                self.message = msg
        else:
            self.scroll_enable = False

    def draw_overlay(self, context, width, height):
        context = cairo_context_from_gi(context)

        if self.scroll_enable and self.message:
            #print str(width) + " x " + str(height)
            #context.scale(width, height)
            #context.scale(width / 100, height / 100)
            #context.scale(100, 100)
            #context.set_source_rgb(1, 0, 0)
            #context.paint_with_alpha(1)
            #context.select_font_face("Helvetica")
            #context.set_font_face(None)
            #context.set_font_size(0.05)
            #context.move_to(0.1, 0.1)
            #context.show_text("Hello World")
            #context.rectangle(0, height * 0.60, width, 30)
            #context.rectangle(0, 0.60, 1, 0.1)

            context.set_source_rgb(1, 0, 0)
            context.rectangle(0, 0.55 * height, width, 0.15 * height)
            context.fill()

            #context.scale(1.0 / width, 1.0 / height)
            #context.translate(0, height * 0.60)

            layout = PangoCairo.create_layout(context)
            #font = Pango.FontDescription("Arial " + str(0.090 * height))
            #font.set_family("Sans")
            #font.set_size(0.090 * height)
            #font.set_size(25)
            #font.set_stretch(Pango.Stretch.ULTRA_CONDENSED)
            font = Pango.font_description_from_string("Sans Condensed " + str(0.090 * height))
            layout.set_font_description(font)
            layout.set_text(self.message, -1)

            context.save()
            (layout_width, layout_height) = layout.get_pixel_size()
            self.scroll_wrap = 1.0 + (float(layout_width) / float(width))
            pos = (self.scroll_pos * width) - layout_width
            context.set_source_rgb(1, 1, 1)
            context.translate(pos, 0.55 * height)
            PangoCairo.update_layout(context, layout)
            PangoCairo.show_layout(context, layout)
            context.restore()

            #context.set_line_width(0.1)
            #context.move_to(0, 0)
            #context.line_to(1, 0)
            #context.stroke()

        #pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size("/home/trans/Downloads/kitty.jpg", width, height)
        #Gdk.cairo_set_source_pixbuf(context, pixbuf, 0, 0)
        #context.stroke()

