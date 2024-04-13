#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Copyright 2012-2024 OpenBroadcaster, Inc.

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

gi.require_version("Gtk", "3.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import GObject, Gtk, Gdk, GdkX11, GdkPixbuf, Pango, PangoCairo
import cairo

import ctypes
import ctypes.util
import cairo
import sys
import threading
import time

pycairo_dll = ctypes.pydll.LoadLibrary(cairo._cairo.__file__)

cairo_dll = ctypes.pydll.LoadLibrary(ctypes.util.find_library("cairo"))
cairo_dll.cairo_reference.restype = ctypes.c_void_p
cairo_dll.cairo_reference.argtypes = (ctypes.c_void_p,)


class ObOverlay(object):
    def __init__(self):
        self.message = None
        self.message_surface = None
        # self.scroll_enable = False
        # self.scroll_pos = 0.0
        # self.scroll_wrap = 1.0
        self.scroll_start_time = None
        self.scroll_per_second = None
        self.chars_per_second = obplayer.Config.setting("alert_crawl_speed") / 60
        self.lock = threading.Lock()
        # GObject.timeout_add(50, self.overlay_scroll_timer)

    """
    def overlay_scroll_timer(self):
        with self.lock:
            self.scroll_pos -= 0.015
            if self.scroll_pos <= 0.0:
                self.scroll_pos = self.scroll_wrap
        GObject.timeout_add(50, self.overlay_scroll_timer)
    """

    def set_message(self, msg):
        if msg:
            # self.scroll_enable = True
            with self.lock:
                if msg and self.message != msg:
                    # self.scroll_pos = 0.05
                    self.scroll_start_time = time.time()
                    self.message = msg
                    self.message_surface = None  # force recreation of the surface
        else:
            pass
            # self.scroll_enable = False

    def draw_overlay(self, context, width, height):

        # do we need to create our message surface?
        if self.message and not self.message_surface:
            print("draw overlay")
            # Temporary surface to calculate text dimensions
            temp_surface = cairo.ImageSurface(
                cairo.FORMAT_ARGB32, 10, 10
            )  # Small surface for measurement
            temp_context = cairo.Context(temp_surface)
            temp_context.set_source_rgb(1, 0, 0)

            # Set up the text attributes
            layout = PangoCairo.create_layout(temp_context)
            font = Pango.font_description_from_string(
                "Sans Condensed " + str(0.090 * height)
            )
            layout.set_font_description(font)
            layout.set_text(self.message, -1)

            # Measure the text
            text_width, text_height = layout.get_pixel_size()

            # Create an off-screen surface with the calculated dimensions
            message_surface = cairo.ImageSurface(
                cairo.FORMAT_ARGB32, text_width, text_height
            )
            context = cairo.Context(message_surface)
            context.set_source_rgb(1, 0, 0)

            # Draw the text on the new surface
            context.set_source_rgb(1, 1, 1)  # White text
            PangoCairo.update_layout(context, layout)
            PangoCairo.show_layout(context, layout)

            average_char_width = text_width / len(self.message)
            self.scroll_per_second = average_char_width * self.chars_per_second

            self.message_surface = message_surface

        if self.message_surface:
            # Draw the red background
            context.set_source_rgb(1, 0, 0)  # Red background
            context.rectangle(
                0, 0.55 * height, width, 0.15 * height
            )  # Cover the entire surface
            context.fill()

            # Calculate the position to start copying from for the scrolling text
            start_x = (
                width - (time.time() - self.scroll_start_time) * self.scroll_per_second
            )

            # Create a pattern from the message surface
            pattern = cairo.SurfacePattern(self.message_surface)
            pattern.set_extend(cairo.EXTEND_NONE)  # Prevent repeating the pattern

            # Use the pattern, adjusting for the scroll position
            context.save()
            context.translate(
                start_x, 0.55 * height
            )  # Adjust for the current scroll position
            context.set_source(pattern)
            context.paint()  # Paint the text pattern over the red background
            context.restore()

            # If the message has completed its crawl, reset state (remove message surface and message)
            if start_x < -1 * self.message_surface.get_width():
                self.message_surface = None
                self.message = None

    """
    def draw_overlay(self, context, width, height):
        if self.scroll_enable and self.message:
            context.set_source_rgb(1, 0, 0)
            context.rectangle(0, 0.55 * height, width, 0.15 * height)
            context.fill()
            layout = PangoCairo.create_layout(context)
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
    """

    # pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size("/home/trans/Downloads/kitty.jpg", width, height)
    # Gdk.cairo_set_source_pixbuf(context, pixbuf, 0, 0)
    # context.stroke()
