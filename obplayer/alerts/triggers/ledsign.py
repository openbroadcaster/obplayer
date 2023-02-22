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
import serial
import subprocess
import traceback


class LEDSignTrigger (object):
    def __init__(self):
        #self.trigger_sign = obplayer.Config.setting('led_sign_enable')
        self.sign_serial_file = obplayer.Config.setting('led_sign_serial_file')
        self.sign_timedisplay = obplayer.Config.setting('led_sign_timedisplay')
        self.trigger_serial_sign = None
        self.sign_initialize()

    def alert_cycle_init(self):
        with open('/tmp/textfile', 'w') as f:
            f.write('')

    def alert_cycle_each(self, alert, alert_media, processor):
        #prim_text = alert_media['primary']['overlay_text']
        alert_info = alert.get_first_info(processor.language_primary)
        severity = alert_info.severity.lower()
	if alert_info.description:
            if obplayer.Config.setting('alerts_truncate'):
                parts = alert_info.description.split('\n\n', 1)
                message_text = parts[0].replace('\n', ' ').replace('\r', '')
            else:
                message_text = alert_info.description
	else:
	    message_text = ' '
        head_text = alert_info.headline
        sign_message = head_text + ':' + message_text + '........'
        if severity == 'moderate':
            with open('/tmp/textfile', 'a') as f:
                f.write('\x1C3')
        elif severity == "minor":
            with open('/tmp/textfile', 'a') as f:
                f.write('\x1C2')
        else:
            with open('/tmp/textfile', 'a') as f:
                f.write('\x1C1')
            
        if sign_message:
            with open('/tmp/textfile', 'a') as f:
                f.write(sign_message + '\n')

        if alert_media['secondary']:
            secd_info = alert.get_first_info(processor.language_secondary)
            head_text = secd_info.headline
	    if secd_info.description:
                if obplayer.Config.setting('alerts_truncate'):
                    parts = secd_info.description.split('\n\n', 1)
                    message_text = parts[0].replace('\n', ' ').replace('\r', '')
                else:
                    message_text = secd_info.description
	    else:
		message_text = ' '
            s = head_text + ':' + message_text + '........'
	    #Encoding for cp863 works best for Canadian French
            sign_message = s.encode('cp863')
            if sign_message:
                with open('/tmp/textfile','a') as f:
                    f.write(sign_message + '\n')

    def alert_cycle_start(self):
        self.sign_write_message()

    def alert_cycle_stop(self):
        self.sign_clear_message()


    def sign_initialize(self):
        try:
            obplayer.Log.log("initializing LED sign " + self.sign_serial_file, 'alerts')
            
            serial_sign = serial.Serial(self.sign_serial_file, baudrate=9600)
            self.sign_set_date()
            self.sign_set_time()
            self.sign_run_demo()
            if self.sign_timedisplay:
                 self.sign_display_time()

        except:
            obplayer.Log.log("failed to initalize serial LED sign", 'alerts')
            obplayer.Log.log(traceback.format_exc(), 'error')

    def sign_set_time(self):
        self.trigger_serial_sign = serial.Serial(self.sign_serial_file, baudrate=9600)
        self.trigger_serial_sign.write("\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
        self.trigger_serial_sign.write("\x01Z00\x02\x45\x20")
        loc_time = time.localtime
        self.trigger_serial_sign.write(time.strftime("%H%M", time.localtime()))
        self.trigger_serial_sign.write("\x04")
        self.trigger_serial_sign.close()

    def sign_set_date(self):
        self.trigger_serial_sign = serial.Serial(self.sign_serial_file, baudrate=9600)
        self.trigger_serial_sign.write("\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
        self.trigger_serial_sign.write("\x01Z00\x02\x45\x3B")
        loc_time = time.localtime
        self.trigger_serial_sign.write(time.strftime("%m%d%y", time.localtime()))
        self.trigger_serial_sign.write("\x04")
        self.trigger_serial_sign.close()

    def sign_reset(self):
        self.trigger_serial_sign = serial.Serial(self.sign_serial_file, baudrate=9600)
        self.trigger_serial_sign.write("\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
        self.trigger_serial_sign.write("\x01Z00\x02AA")
        self.trigger_serial_sign.write("\x1B b")
        self.trigger_serial_sign.write(" ")
        self.trigger_serial_sign.write("\x04")
        self.trigger_serial_sign.close()

    def sign_display_time(self):
        self.trigger_serial_sign = serial.Serial(self.sign_serial_file, baudrate=9600)
        self.trigger_serial_sign.write("\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
        self.trigger_serial_sign.write("\x01Z00\x02AA")
        self.trigger_serial_sign.write("\x1B b\x1C2\x0B\x31\x20\x13")
        self.trigger_serial_sign.write("")
        self.trigger_serial_sign.write("\x04")
        self.trigger_serial_sign.close()

    def sign_run_demo(self):
        self.trigger_serial_sign = serial.Serial(self.sign_serial_file, baudrate=9600)
        self.trigger_serial_sign.write("\x00\x00\x00\x00\x00\x00")
        self.trigger_serial_sign.write("\x01Z00\x02AA")
        self.trigger_serial_sign.write("\x1B\x30\x61\x15\x1A\x33\x1C9")
        message = obplayer.Config.setting('led_sign_init_message')
        self.trigger_serial_sign.write(message) 
        #self.trigger_serial_sign.write("\x1B\x30\x6E\x56") #DDAD message
        self.trigger_serial_sign.write("\x04")  
        time.sleep(7)
        self.sign_reset()

    def sign_write_message(self):
        try:
            obplayer.Log.log("sent message to LED sign on serial port " + self.sign_serial_file, 'alerts')
            if self.trigger_serial_sign:
                self.trigger_serial_sign.close()

            self.trigger_serial_sign = serial.Serial(self.sign_serial_file,baudrate=9600)
            self.trigger_serial_sign.write('\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
            with open('/tmp/textfile') as f:
                 message = f.read()
            self.trigger_serial_sign.write("\x01Z00") #SOH type, address(0=all signs)
            self.trigger_serial_sign.write("\x02AA") #STX
            #command codes (See p80 alphasign protocol doc)
            # fill display, RTL,slowest, standard 7 hi character set
            self.trigger_serial_sign.write("\x1B\x30\x61\x15\x1A\x33") 
            self.trigger_serial_sign.write(message) #message!
            self.trigger_serial_sign.write("\x04") # EOT
            self.trigger_serial_sign.close()

        except:
            obplayer.Log.log("failed to send message LED sign on serial port " + self.sign_serial_file, 'alerts')
            obplayer.Log.log(traceback.format_exc(), 'error')

    def sign_clear_message(self):
        try:
            obplayer.Log.log("sent clear to LED sign on serial port " + self.sign_serial_file, 'alerts')
            if self.trigger_serial_sign:
                self.trigger_serial_sign.close()
                 
            if self.sign_timedisplay:
                self.sign_display_time()
            else:
                self.sign_reset()

        except:
            obplayer.Log.log("failed to send message LED sign on serial port " + self.sign_serial_file, 'alerts')
            obplayer.Log.log(traceback.format_exc(), 'error')




