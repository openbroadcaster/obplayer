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

import socket
import os
import sys
import time
import signal
import os.path
import traceback
import subprocess
import passlib.hash as hashing
from obplayer.streamer.linein import ObLineinIcecastStreamer


from obplayer.httpadmin import httpserver

def inter_station_ctrl_is_live():
    res = httpserver.Response()
    try:
        if hasattr(obplayer, 'LineinStreamer'):
            res.send_content('text/plain', 'True')
            return res
        else:
            res.send_content('text/plain', 'False')
            return res
    except Exception as e:
            res.send_content('text/plain', '500 error')
            return res

def inter_station_ctrl_toggle(live):
    res = httpserver.Response()
    try:
        if live == False:
            obplayer.LineinStreamer.quit()
            del obplayer.LineinStreamer
        else:
            obplayer.LineinStreamer = ObLineinIcecastStreamer(obplayer.Config.setting('station_override_server_ip'), obplayer.Config.setting('station_override_server_port'),
            obplayer.Config.setting('station_override_server_password'), obplayer.Config.setting('station_override_server_mountpoint'), '', '', '', False, 128)
            obplayer.LineinStreamer.start()
    except Exception as e:
            res.send_content(500, 'text/plain', '500 error')
            return res
    res.send_content('text/plain', '')
    return res

class ObHTTPAdmin (httpserver.ObHTTPServer):
    def __init__(self):
        self.root = 'obplayer/httpadmin/http'

        self.username = obplayer.Config.setting('http_admin_username')
        self.password_hash = obplayer.Config.setting('http_admin_password_hash')
        self.readonly_username = obplayer.Config.setting('http_readonly_username')
        self.readonly_password_hash = obplayer.Config.setting('http_readonly_password_hash')
        self.readonly_allow_restart = obplayer.Config.setting('http_readonly_allow_restart')
        self.title = obplayer.Config.setting('http_admin_title')

        sslenable = obplayer.Config.setting('http_admin_secure')
        sslreq = obplayer.Config.setting('http_admin_sslreq')
        sslkey = obplayer.Config.setting('http_admin_sslkey')
        sslcert = obplayer.Config.setting('http_admin_sslcert')
        sslca = obplayer.Config.setting('http_admin_sslca')
        if obplayer.custom_http_admin_port != None:
            port = int(obplayer.custom_http_admin_port)
        else:
            port = obplayer.Config.setting('http_admin_port')
        server_address = ('', port)  # (address, port)

        if sslenable:
            httpserver.ObHTTPServer.__init__(self, server_address, sslenable, sslreq, sslkey, sslcert, sslca if sslca else None)
        else:
            httpserver.ObHTTPServer.__init__(self, server_address)

        self.register_routes()
        sa = self.socket.getsockname()
        obplayer.Log.log('serving http(s) on port ' + str(sa[1]), 'admin')


    def log(self, message):
        if not "POST /status_info" in message and not "POST /alerts/list" and not "POST /translate" in message:
            obplayer.Log.log(message, 'debug')

    def form_item_selected(self, setting, value):
        if obplayer.Config.setting(setting, True) == value:
            return ' selected="selected"'
        else:
            return ''

    def form_item_checked(self, setting):
        if obplayer.Config.setting(setting, True):
            return ' checked="checked"'
        else:
            return ''

    def fullscreen_status(self):
        if obplayer.Config.headless:
            return 'N/A'
        elif obplayer.Gui.gui_window_fullscreen:
            return 'On'
        else:
            return 'Off'

    def register_routes(self):
        self.route('/status_info', self.req_status_info)
        self.route('/alerts/list', self.req_alert_list)
        self.route('/alerts/geocodes_list', self.req_geocodes_list)
        self.route('/strings', self.req_strings)
        self.route('/command/restart', self.req_restart)
        self.route('/command/fstoggle', self.req_fstoggle)
        self.route('/command/password_change', self.req_password_change, 'admin')
        self.route('/command/tos_agreed', self.req_tos_agreed)
        self.route('/save', self.req_save, 'admin')
        self.route('/import_settings', self.req_import, 'admin')
        self.route('/export_settings', self.req_export, 'admin')
        self.route('/updater/update', self.req_update, 'admin')
        self.route('/updater/check', self.req_update_check, 'admin')
        self.route('/toggle_scheduler', self.req_scheduler_toggle, 'admin')
        self.route('/alerts/inject_test', self.req_alert_inject, 'admin')
        self.route('/alerts/cancel', self.req_alert_cancel, 'admin')
        self.route('/pulse/volume', self.req_pulse_volume, 'admin')
        self.route('/pulse/mute', self.req_pulse_mute, 'admin')
        self.route('/pulse/select', self.req_pulse_select, 'admin')
        self.route('/translate', self.req_translate, 'admin')
        self.route('/inter_station_ctrl/start', self.req_start_inter_station_ctrl, 'admin')
        self.route('/inter_station_ctrl/stop', self.req_stop_inter_station_ctrl, 'admin')
        self.route('/inter_station_ctrl/is_live', self.req_is_live_inter_station_ctrl, 'admin')

    def req_status_info(self, request):
        proc = subprocess.Popen([ "uptime", "-p" ], stdout=subprocess.PIPE)
        (uptime, _) = proc.communicate()

        requests = obplayer.Player.get_requests()
        select_keys = [ 'media_type', 'end_time', 'filename', 'duration', 'media_id', 'order_num', 'artist', 'title' ]

        data = { }
        data['time'] = time.time()
        data['uptime'] = uptime.decode('utf-8')
        for stream in requests.keys():
            data[stream] = { key: requests[stream][key] for key in requests[stream].keys() if key in select_keys }
        data['audio_levels'] = obplayer.Player.get_audio_levels()
        if hasattr(obplayer, 'scheduler'):
            data['show'] = obplayer.Scheduler.get_show_info()
        data['logs'] = obplayer.Log.get_log()
        return data

    def req_tos_agreed(self, request):
        res = httpserver.Response()
        obplayer.Config.save_settings({'http_admin_tos_ui_agreed': '1'})
        res.send_content('text/plain', '')
        return res

    def req_geocodes_list(self, request):
        data = obplayer.Config.setting('alerts_geocode', True)
        res = httpserver.Response()
        if data:
            res.send_content('text/plain', data)
            return res
        else:
            res.send_content('text/plain', '')
            return res

    def req_start_inter_station_ctrl(self, request):
        return inter_station_ctrl_toggle(True)

    def req_stop_inter_station_ctrl(self, request):
        return inter_station_ctrl_toggle(False)

    def req_is_live_inter_station_ctrl(self, request):
        return inter_station_ctrl_is_live()

    def req_alert_list(self, request):
        if hasattr(obplayer, 'alerts'):
            return obplayer.alerts.Processor.get_alerts()
        return { 'status' : False }

    def req_strings(self, request):
        strings = { '': { } }

        self.load_strings('default', strings)
        self.load_strings(obplayer.Config.setting('http_admin_language'), strings)
        #self.load_strings('fake', strings)
        return strings

    def req_restart(self, request):
        if not self.readonly_allow_restart and not request.access:
            return { 'status' : False, 'error' : "permissions-error-guest" }
        if 'extra' in request.args:
            if request.args['extra'][0] == 'defaults':
                try:
                    os.remove(obplayer.ObData.get_datadir() + '/settings.db')
                except:
                    obplayer.Log.log(traceback.format_exc(), 'error')
            if request.args['extra'][0] == 'hard':
                try:
                    os.remove(obplayer.ObData.get_datadir() + '/data.db')
                except:
                    obplayer.Log.log(traceback.format_exc(), 'error')
            if request.args['extra'][0] == 'hard' or request.args['extra'][0] == 'defaults':
                obplayer.Main.exit_code = 37
        os.kill(os.getpid(), signal.SIGINT)
        return { 'status' : True }

    def req_fstoggle(self, request):
        if not self.readonly_allow_restart and not request.access:
            return { 'status' : False, 'error' : "permissions-error-guest", 'fullscreen' : 'N/A' }

        if obplayer.Config.headless:
            return { 'status' : False, 'fullscreen' : 'N/A' }
        else:
            obplayer.Gui.fullscreen_toggle(None)
            return { 'status' : True, 'fullscreen' : 'On' if obplayer.Gui.gui_window_fullscreen else 'Off' }

    def req_save(self, request):
        if 'http_admin_password' in request.args:
            if request.args['http_admin_password'][0] == '':
                del request.args['http_admin_password']
                del request.args['http_admin_password_retype']
            elif 'http_admin_password_retype' not in request.args or request.args['http_admin_password'][0] != request.args['http_admin_password_retype'][0]:
                return { 'status' : False, 'error' : 'passwords-dont-match' }
            else:
                del request.args['http_admin_password_retype']
                self.password = request.args['http_admin_password'][0]

        unchanged_settings = ['sync_device_password', 'streamer_0_icecast_password', 'streamer_1_icecast_password',
        'streamer_youtube_key']
        removed_settings = []

        for key in request.args:
            setting_name = key
            setting_value = request.args[key][0]

            if setting_name in unchanged_settings:
                # handle unchanged password from being re-saved.
                if setting_value == 'unchanged':
                    removed_settings.append(setting_name)
                    continue

        for setting in removed_settings:
            request.args.pop(setting)

        # run through each setting and make sure it's valid. if not, complain.
        for key in request.args:
            setting_name = key
            setting_value = request.args[key][0]

            error = obplayer.Config.validate_setting(setting_name, setting_value)

            if error != None:
                return { 'status' : False, 'error' : error }

        # we didn't get an errors on validate, so update each setting now.
        settings = { key: value[0] for (key, value) in request.args.items() }
        obplayer.Config.save_settings(settings)

        return { 'status' : True }

    def req_password_change(self, request):
        if 'http_admin_password' in request.args and request.args['http_admin_password'][0] != '':
            hash = hashing.bcrypt.hash(request.args['http_admin_password'][0])
            obplayer.Config.save_settings({'http_admin_password_hash': hash, 'http_admin_password_default': 0})
            return { 'status' : True }
        else:
            return { 'status' : False, 'error' : 'error message here' }

    def req_import(self, request):
        content = request.args.getvalue('importfile').decode('utf-8')

        errors = ''
        settings = { }
        for line in content.split('\n'):
            (name, _, value) = line.strip().partition(':')
            name = name.strip()
            # Check folder doesn't exist, and fallback to the current
            # setting in that case.
            if name == 'fallback_media':
                if os.access(value, os.F_OK) == False:
                    continue

            if not name:
                continue

            error = obplayer.Config.validate_setting(name, value)
            if error:
                errors += error + '<br/>'
            else:
                settings[name] = value
                obplayer.Log.log("importing setting '{0}': '{1}'".format(name, value), 'config')

        if errors:
            return { 'status' : False, 'error' : errors }

        obplayer.Config.save_settings(settings)
        return { 'status' : True, 'notice' : "settings-imported-success" }

    def req_export(self, request):
        settings = ''
        for (name, value) in sorted(obplayer.Config.list_settings(hidepasswords=True).items()):
            settings += "{0}:{1}\n".format(name, value if type(value) != bool else int(value))

        res = httpserver.Response()
        res.add_header('Content-Disposition', 'attachment; filename=obsettings.txt')
        res.send_content('text/plain', settings)
        return res

    def req_update(self, request):
        srcpath = os.path.dirname(os.path.dirname(obplayer.__file__))
        proc = subprocess.Popen('cd "' + srcpath + '" && git branch && git pull', stdout=subprocess.PIPE, shell=True)
        (output, _) = proc.communicate()
        return { 'output': output.decode('utf-8') }

    def req_update_check(self, request):
        srcpath = os.path.dirname(os.path.dirname(obplayer.__file__))
        branch = subprocess.Popen('cd "{0}" && git branch'.format(srcpath), stdout=subprocess.PIPE, shell=True)
        (branchoutput, _) = branch.communicate()
        branchname = 'master'
        for name in branchoutput.decode('utf-8').split('\n'):
            if name.startswith('*'):
                branchname = name.strip('* ')
                break

        diff = subprocess.Popen('cd "{0}" && git fetch && git diff origin/{1} --quiet'.format(srcpath, branchname), stdout=subprocess.PIPE, shell=True)
        (output, _) = diff.communicate()

        version = subprocess.Popen('cd "{0}" && git show origin/{1}:VERSION'.format(srcpath, branchname), stdout=subprocess.PIPE, shell=True)
        (output, _) = version.communicate()
        return {
            'available': False if diff.returncode == 0 else True,
            'version': "{0} on {1} branch".format(output.decode('utf-8'), branchname),
            'branches': [ name.strip(' *') for name in branchoutput.decode('utf-8').split('\n') ]
        }

    def req_scheduler_toggle(self, request):
        ctrl = obplayer.Scheduler.ctrl
        if ctrl.enabled:
            ctrl.disable()
        else:
            ctrl.enable()
        return { 'status': True, 'enabled': ctrl.enabled }

    def req_alert_inject(self, request):
        if not hasattr(obplayer, 'alerts'):
            return { 'status' : False, 'error' : "alerts-disabled-error" }

        filename = request.args['alert'][0]
        if '..' in filename or not os.path.exists(filename):
            return { 'status' : False, 'error' : "alerts-invalid-filename" }

        obplayer.alerts.Processor.inject_alert(filename)
        return { 'status' : True }

    def req_alert_cancel(self, request):
        if hasattr(obplayer, 'alerts'):
            for identifier in request.args['identifier[]']:
                obplayer.alerts.Processor.cancel_alert(identifier)
            return { 'status' : True }
        return { 'status' : False, 'error' : "alerts-disabled-error" }

    def req_pulse_volume(self, request):
        if not hasattr(obplayer, 'pulse'):
            return { 'status' : False, 'error' : "pulse-control-disabled" }
        newvol = obplayer.pulse.change_volume(request.args['n'][0], request.args['v'][0])
        return { 'status' : True, 'v': newvol }

    def req_pulse_mute(self, request):
        if not hasattr(obplayer, 'pulse'):
            return { 'status' : False, 'error' : "pulse-control-disabled" }
        mute = obplayer.pulse.mute(request.args['n'][0])
        return { 'status' : True, 'm': mute }

    def req_pulse_select(self, request):
        if not hasattr(obplayer, 'pulse'):
            return { 'status' : False, 'error' : "pulse-control-disabled" }
        obplayer.pulse.select_output(request.args['n'][0], request.args['s'][0])
        return { 'status' : True }

    def req_translate(self, request):
        namespace = request.args['namespace'][0]
        element = request.args['element'][0]
        if namespace == None or element == None:
            return { 'status' : False, 'error' : "" }
        return {'status' : True, 'text': obplayer.Translate.t(namespace, element)}
        

    @staticmethod
    def load_strings(lang, strings):
        namespace = ''
        for (dirname, dirnames, filenames) in os.walk(os.path.join('obplayer/httpadmin/strings', lang)):
            for filename in filenames:
                if filename.endswith('.txt'):
                    with open(os.path.join(dirname, filename), 'rb') as f:
                        while True:
                            line = f.readline()
                            if not line:
                                break
                            if line.startswith(b'\xEF\xBB\xBF'):
                                line = line[3:]
                            (name, _, text) = line.decode('utf-8').partition(':')
                            (name, text) = (name.strip(), text.strip())
                            if name:
                                if text:
                                    strings[namespace][name] = text
                                else:
                                    namespace = name
                                    strings[namespace] = { }
        return strings
