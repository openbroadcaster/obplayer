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

import apsw
import os
import os.path
import re
import traceback
import subprocess


class ObData (object):
    datadir = os.path.expanduser('~/.openbroadcaster')

    @classmethod
    def set_datadir(cls, name):
        cls.datadir = os.path.expanduser(name)

        if os.access(cls.datadir, os.F_OK) == False:
            os.mkdir(cls.datadir)

        if os.access(cls.datadir + '/alerts', os.F_OK) == False:
            os.mkdir(cls.datadir + '/alerts')

        # Build the folders to support indigenous alert messages.
        if os.access(cls.datadir + '/indigenous', os.F_OK) == False:
            os.mkdir(cls.datadir + '/indigenous')
        indigenous_languages = ['atikamekw', 'chipewyin', 'cree', 'innu',
        'inuktitut', 'kawawachikamach-naskapi', 'mikmaq', 'ojibwe']
        for language in indigenous_languages:
            if os.access(cls.datadir + '/indigenous/{0}'.format(language), os.F_OK) == False:
                os.mkdir(cls.datadir + '/indigenous/{0}'.format(language))

        if os.access(cls.datadir + '/audiologs', os.F_OK) == False:
            os.mkdir(cls.datadir + '/audiologs')

        if os.access(cls.datadir + '/lineinlogs', os.F_OK) == False:
            os.mkdir(cls.datadir + '/lineinlogs')

        if os.access(cls.datadir + '/offair-audiologs', os.F_OK) == False:
            os.mkdir(cls.datadir + '/offair-audiologs')

        if os.access(cls.datadir + '/media', os.F_OK) == False:
            os.mkdir(cls.datadir + '/media')

        if os.access(cls.datadir + '/logs', os.F_OK) == False:
            os.mkdir(cls.datadir + '/logs')

        if os.access(cls.datadir + '/fallback_media', os.F_OK) == False:
            os.mkdir(cls.datadir + '/fallback_media')

        if os.access(cls.datadir + '/news_feed_override', os.F_OK) == False:
            os.mkdir(cls.datadir + '/news_feed_override')

    @classmethod
    def get_datadir(cls, subdir=None):
        if subdir:
            return os.path.join(cls.datadir, subdir)
        return cls.datadir


    def __init__(self):
        self.db = None

    def open_db(self, filename):
        return apsw.Connection(filename)

    def table_exists(self, table):
        for row in self.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name = ? UNION ALL SELECT name FROM sqlite_temp_master WHERE type IN ('table','view') AND name = ?", (table, table)):
            return True
        return False

    def empty_table(self, table):
        self.execute("DELETE from " + table)

    def execute(self, query, bindings=None):
        return self.db.cursor().execute(query, bindings)

    # run query, return dict.
    def query(self, query, bindings=None):
        cursor = self.db.cursor().execute(query, bindings)

        try:
            cols = cursor.getdescription()
        except apsw.ExecutionCompleteError:
            return [ ]

        return_array = [ ]
        for row in cursor:
            rowdata = { col[0] : row[i] for (i, col) in enumerate(cols) }
            return_array.append(rowdata)
        return return_array

    def escape(self, text):
        return text.replace("'", "''")

    def row_addedit(self, table, data):
        column_list = []
        value_list = []

        for (key, value) in data.items():
            column_list.append("'" + self.escape(str(key)) + "'")
            value_list.append("'" + self.escape(str(value)) + "'")

        # this is INSERT or REPLACE, so if we have (for example) ID set in data, then it will edit. Otherwise it will insert.
        # Other unique keys may cause replace (edit) so be careful.
        self.execute("INSERT or REPLACE into " + table + " ( " + ','.join(column_list) + " ) VALUES ( " + ','.join(value_list) + " )")
        return self.db.last_insert_rowid()



class ObConfigData (ObData):

    def __init__(self):
        ObData.__init__(self)

        self.headless = False
        self.args = None
        self.version = open('VERSION').read().strip()
        srcpath = os.path.dirname(os.path.dirname(obplayer.__file__))
        branch = subprocess.Popen('cd "{0}" && git branch'.format(srcpath), stdout=subprocess.PIPE, shell=True)
        (branchoutput, _) = branch.communicate()
        branchname = 'master'
        for name in branchoutput.decode('utf-8').split('\n'):
            if name.startswith('*'):
                branchname = name.strip('* ')
                break
        self.branch = branchname

        self.db = self.open_db(self.datadir + '/settings.db')

        if not self.table_exists('settings'):
            self.execute("CREATE TABLE settings (id INTEGER PRIMARY KEY, name TEXT, value TEXT, type TEXT)")
            self.execute("CREATE UNIQUE INDEX name_index on settings(name)")

        self.check_defaults()

        self.settings_cache = {}
        self.settings_type = {}

        rows = self.query("SELECT name,value,type FROM 'settings'")
        for row in rows:
            value = row['value']
            datatype = row['type']
            if datatype == 'int':
                value = int(value)
            elif datatype == 'float':
                value = float(value)
            elif datatype == 'bool':
                value = bool(int(value))
            else:
                value = str(value)
            self.settings_cache[row['name']] = value
            self.settings_type[row['name']] = datatype

        # keep track of settings as they have been edited.
        # they don't take effect until restart, but we want to keep track of them for subsequent edits.
        self.settings_edit_cache = self.settings_cache.copy()

        if not self.setting("video_out_enable"):
            self.headless = True

    def validate_settings(self, settings):
        for (setting_name, setting_value) in settings.items():
            error = self.validate_setting(setting_name, setting_value, settings)
            if error:
                return error
        return None

    def is_int(self, value):
        if re.match('^[0-9]+$', str(value)):
            return True
        else:
            return False

    def validate_setting(self, setting_name, setting_value, settings=None):

        # if we don't have a batch of settings we're checking, use our settings cache.
        if settings == None:
            settings = self.settings_cache

        try:
            self.settings_cache[setting_name]
        except:
            return 'One or more setting names were not valid. ' + setting_name

        # disabled for now - this was locking the UI while waiting to timeout (if network problems)
        # try:
        # urllib.urlopen(settings['sync_url']);
        # except IOError:
        # error = 'The SYNC URL you have provided does not appear to be valid.';

        if setting_name == 'sync_device_id' and self.is_int(setting_value) == False:
            return 'sync_device_id_invalid'

        if setting_name == 'sync_buffer' and self.is_int(setting_value) == False:
            return 'sync_buffer_invalid'

        if setting_name == 'sync_showlock' and self.is_int(setting_value) == False:
            return 'sync_showlock_invalid'

        if setting_name == 'sync_freq' and self.is_int(setting_value) == False:
            return 'sync_freq_invalid'

        if setting_name == 'sync_freq_priority' and self.is_int(setting_value) == False:
            return 'sync_freq_priority_invalid'

        if setting_name == 'sync_freq_playlog' and self.is_int(setting_value) == False:
            return 'sync_freq_playlog_invalid'

        if setting_name == 'streamer_icecast_bitrate' and (self.is_int(setting_value) == False or int(setting_value) not in [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320]):
            return 'streamer_icecast_bitrate_invalid'

        if setting_name == 'offair_audiolog_icecast_bitrate' and (self.is_int(setting_value) == False or int(setting_value) not in [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320]):
            return 'streamer_icecast_bitrate_invalid'

        url_regex = re.compile(
                r'^(?:http|ftp)s?://' # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
                r'localhost|' #localhost...
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
                r'(?::\d+)?' # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        if setting_name == 'sync_url' and setting_value and url_regex.match(setting_value) == None:
            return 'sync_url_invalid'

        if setting_name == 'alerts_naad_stream1' and url_regex.match(setting_value) == None:
            return 'alerts_naad_stream1_invalid'

        if setting_name == 'alerts_naad_stream2' and url_regex.match(setting_value) == None:
            return 'alerts_naad_stream2_invalid'

        if setting_name == 'alerts_naad_archive1' and url_regex.match(setting_value) == None:
            return 'alerts_naad_archive1_invalid'

        if setting_name == 'alerts_naad_archive2' and url_regex.match(setting_value) == None:
            return 'alerts_naad_archive2_invalid'

        #if setting_name == 'alerts_trigger_serial_file' and setting_value and not os.path.exists(setting_value):
        #    return 'alerts_trigger_serial_file_invalid'

        geocode_regex = re.compile(r'^\s*(|\d+(|\s*,\s*\d+)*)$', re.IGNORECASE)
        if setting_name == 'alerts_geocode' and geocode_regex.match(setting_value) == None:
            return 'alerts_geocode_invalid'

        if setting_name == 'alerts_leadin_delay' and int(setting_value) <= 0:
            return 'alerts_leadin_delay_invalid'

        if setting_name == 'alerts_leadout_delay' and int(setting_value) <= 0:
            return 'alerts_leadout_delay_invalid'

        if setting_name == 'fallback_media' and os.access(setting_value, os.F_OK) == False:
            return 'fallback_media_invalid'

        if setting_name == 'local_media' and settings['sync_mode'] != 'remote' and setting_value != '' and os.access(setting_value, os.F_OK) == False:
            return 'local_media_invalid'

        if setting_name == 'http_admin_port' and self.is_int(setting_value) == False:
            return 'http_admin_port_invalid'

        if setting_name == 'http_admin_secure' and int(setting_value) and os.access(settings['http_admin_sslcert'], os.F_OK) == False:
            return 'http_admin_sslcert_invalid'

        if setting_name == 'http_admin_password' and not setting_value:
            return 'http_password_blank'

        if setting_name == 'http_readonly_password' and not setting_value:
            return 'http_password_blank'

        if setting_name == 'live_assist_port' and settings['live_assist_enable'] and settings['live_assist_port'] == settings['http_admin_port']:
            return 'live_assist_port_invalid'

        lat_regex = re.compile(r'^[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?)$')
        if setting_name == 'location_latitude' and lat_regex.match(setting_value) == None:
            return 'location_latitude_invalid'

        lng_regex = re.compile(r'[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)$')
        if setting_name == 'location_longitude' and lng_regex.match(setting_value) == None:
            return 'location_longitude_invalid'

        streams_regex = re.compile(r'^\s+$')
        if setting_name == 'station_override_monitored_streams' and streams_regex.match(setting_value):
            return 'station_override_monitored_streams_invalid'

        if setting_name == 'station_override_server_admin_username' and 'station_override_server_admin_username' == '':
            return 'station_override_passwords_invalid'

        return None

    """
    def set(self, setting_name, setting_value):
        settings = {}
        settings[setting_name] = setting_value
        self.save_settings(settings)
    """

    # make sure we have all our required settings. if not, add setting with default value.
    def check_defaults(self):
        self.add_setting('audio_out_mode', 'auto', 'text')
        self.add_setting('audio_out_alsa_device', 'default', 'text')
        self.add_setting('audio_out_jack_name', '', 'text')
        self.add_setting('audio_out_shout2send_ip', '127.0.0.1', 'text')
        self.add_setting('audio_out_shout2send_port', '8000', 'int')
        self.add_setting('audio_out_shout2send_mount', 'stream', 'text')
        self.add_setting('audio_out_shout2send_password', 'hackme', 'text')
        self.add_setting('audio_out_visualization', '0', 'bool')
        self.add_setting('gst_init_callback', '', 'text')

        self.add_setting('audiolog_enable', '0', 'bool')
        self.add_setting('audiolog_purge_files', '0', 'bool')

        self.add_setting('video_out_enable', '0', 'bool')
        self.add_setting('video_out_mode', 'auto', 'text')
        self.add_setting('video_out_resolution', 'default', 'text')

        self.add_setting('images_transitions_enable', '0', 'bool')
        self.add_setting('images_width', '640', 'int')
        self.add_setting('images_height', '480', 'int')
        self.add_setting('images_framerate', '15', 'int')

        self.add_setting('overlay_enable', '0', 'bool')

        self.add_setting('streamer_enable', '0', 'bool')
        self.add_setting('streamer_audio_in_mode', 'intersink', 'text')
        self.add_setting('streamer_audio_in_alsa_device', 'default', 'text')
        self.add_setting('streamer_audio_in_jack_name', '', 'text')
        for i in range(2):
            i = str(i)
            if i != "1":
                self.add_setting('streamer_' + i + '_icecast_enable', '1', 'bool')
            else:
                self.add_setting('streamer_' + i + '_icecast_enable', '0', 'bool')
            self.add_setting('streamer_' + i + '_icecast_mode', 'audio', 'text')
            self.add_setting('streamer_' + i + '_icecast_bitrate', '0', 'int')
            self.add_setting('streamer_' + i + '_icecast_ip', '127.0.0.1', 'text')
            self.add_setting('streamer_' + i + '_icecast_port', '8000', 'int')
            self.add_setting('streamer_' + i + '_icecast_mount', 'stream_' + i, 'text')
            self.add_setting('streamer_' + i + '_icecast_password', 'hackme', 'text')
            self.add_setting('streamer_' + i + '_icecast_streamname', '', 'text')
            self.add_setting('streamer_' + i + '_icecast_description', '', 'text')
            self.add_setting('streamer_' + i + '_icecast_url', '', 'text')
            self.add_setting('streamer_' + i + '_icecast_public', '0', 'bool')
            self.add_setting('streamer_play_on_startup', '1', 'bool')

        self.add_setting('streamer_rtsp_enable', '0', 'bool')
        self.add_setting('streamer_rtsp_port', '8554', 'int')
        self.add_setting('streamer_rtsp_clock_rate', '48000', 'text')
        self.add_setting('streamer_rtsp_allow_discovery', '0', 'bool')

        self.add_setting('streamer_rtp_enable', '0', 'bool')
        self.add_setting('streamer_rtp_port', '5004', 'int')
        self.add_setting('streamer_rtp_address', '', 'text')
        self.add_setting('streamer_rtp_encoding', 'L24', 'text')
        self.add_setting('streamer_rtp_clock_rate', '48000', 'text')
        self.add_setting('streamer_rtp_enable_rtcp', '1', 'bool')

        self.add_setting('streamer_youtube_enable', '0', 'bool')
        self.add_setting('streamer_youtube_key', '', 'text')
        self.add_setting('streamer_youtube_mode', '240p', 'text')

        self.add_setting('station_override_server_ip', '', 'text')
        self.add_setting('station_override_server_port', '', 'text')
        self.add_setting('station_override_server_password', '', 'text')
        self.add_setting('station_override_server_mountpoint', '', 'text')
        self.add_setting('station_override_server_bitrate', '0', 'int')
        self.add_setting('station_override_monitored_streams', 'http://localhost:8000/local', 'text')
        self.add_setting('station_override_enabled', '0', 'bool')

        self.add_setting('scheduler_enable', '0', 'bool')
        self.add_setting('sync_device_id', '1', 'int')
        self.add_setting('sync_device_password', '', 'text')
        self.add_setting('sync_url', '', 'text')
        self.add_setting('sync_buffer', '24', 'int')
        self.add_setting('sync_showlock', '20', 'int')
        self.add_setting('sync_playlog_enable', '0', 'bool')
        self.add_setting('sync_freq', '2', 'int')
        self.add_setting('sync_freq_priority', '1', 'int')
        self.add_setting('sync_freq_playlog', '3', 'int')
        self.add_setting('sync_mode', 'remote', 'text')
        self.add_setting('sync_copy_media_to_backup', '0', 'bool')
        self.add_setting('remote_media', self.datadir + '/media', 'text')
        self.add_setting('local_media', '', 'text')
        self.add_setting('newsfeed_override_enabled', '0', 'bool')

        self.add_setting('fallback_enable', '1', 'bool')
        self.add_setting('fallback_media', self.datadir + '/fallback_media', 'text')

        self.add_setting('audio_in_enable', '0', 'bool')
        self.add_setting('audio_output_volume', '0.5', 'float')
        self.add_setting('audio_in_mode', 'auto', 'text')
        self.add_setting('audio_in_alsa_device', 'default', 'text')
        self.add_setting('audio_in_jack_name', '', 'text')

        self.add_setting('audio_in_disable_on_silence', '0', 'bool')
        self.add_setting('audio_in_prioritize_above_scheduler', '0', 'bool')
        self.add_setting('audio_in_log', '0', 'bool')
        self.add_setting('audio_in_enable_time', '1', 'int')
        self.add_setting('audio_in_disable_time', '10', 'int')
        self.add_setting('audio_in_threshold', '-28', 'int')

        self.add_setting('aoip_in_enable', '0', 'bool')
        self.add_setting('aoip_in_uri', '', 'text')

        self.add_setting('rtp_in_enable', '0', 'bool')
        self.add_setting('rtp_in_port', '5004', 'int')
        self.add_setting('rtp_in_address', '', 'text')
        self.add_setting('rtp_in_encoding', 'OPUS', 'text')
        self.add_setting('rtp_in_clock_rate', '48000', 'text')
        self.add_setting('rtp_in_enable_rtcp', '1', 'bool')

        self.add_setting('testsignal_enable', '1', 'bool')

        self.add_setting('http_admin_port', '23233', 'int')
        self.add_setting('http_admin_username', 'admin', 'text')
        self.add_setting('http_admin_password', 'admin', 'text')
        self.add_setting('http_readonly_username', 'user', 'text')
        self.add_setting('http_readonly_password', 'user', 'text')
        self.add_setting('http_readonly_allow_restart', '1', 'bool')
        self.add_setting('show_ssl_settings', '0', 'bool')
        self.add_setting('show_sdr_streaming_logging_settings', '0', 'bool')
        self.add_setting('show_indigenous_alert_settings', '0', 'bool')
        self.add_setting('show_station_remote_override_settings', '0', 'bool')
        self.add_setting('show_alert_ledin_settings', '0', 'bool')
        self.add_setting('http_admin_secure', '0', 'bool')
        self.add_setting('http_admin_sslreq', '0', 'bool')
        self.add_setting('http_admin_sslcert', '', 'text')
        self.add_setting('http_admin_sslkey', '', 'text')
        self.add_setting('http_admin_sslca', '', 'text')
        self.add_setting('http_admin_title', 'OpenBroadcaster Player Dashboard', 'text')
        self.add_setting('http_admin_language', 'en', 'text')

        self.add_setting('http_show_sync', '1', 'bool')
        self.add_setting('http_show_streaming', '1', 'bool')
        self.add_setting('http_show_alerts', '1', 'bool')
        self.add_setting('http_show_location', '1', 'bool')
        self.add_setting('http_show_liveassist', '1', 'bool')

        self.add_setting('live_assist_enable', '0', 'bool')
        self.add_setting('live_assist_port', '23456', 'int')
        self.add_setting('live_assist_mic_enable', '0', 'bool')
        self.add_setting('live_assist_mic_mode', 'auto', 'text')
        self.add_setting('live_assist_mic_alsa_device', 'default', 'text')
        self.add_setting('live_assist_mic_jack_name', '', 'text')
        self.add_setting('live_assist_monitor_mode', 'auto', 'text')
        self.add_setting('live_assist_monitor_alsa_device', 'default', 'text')
        self.add_setting('live_assist_monitor_jack_name', '', 'text')

        self.add_setting('alerts_enable', '0', 'bool')
        self.add_setting('alerts_location_type', 'CA', 'text')
        self.add_setting('alerts_aws_voices_enable', '0', 'bool')
        self.add_setting('aws_access_key_id', '', 'text')
        self.add_setting('aws_secret_access_key', '', 'text')
        self.add_setting('aws_region_name', 'us-west-1', 'text')
        self.add_setting('alerts_location_type', 'CA', 'text')
        self.add_setting('alerts_play_leadin_enable', '0', 'bool')
        self.add_setting('alerts_alert_start_audio', self.datadir + '/media/' + 'L/' + 'leadin_message.mp3', 'text')
        self.add_setting('leadin_audio_file_type', '.mp3', 'text')
        self.add_setting('leadin_audio_file', '.mp3', 'text')
        self.add_setting('alerts_language_primary', 'english', 'text')
        self.add_setting('alerts_language_secondary', 'french', 'text')
        self.add_setting('alerts_voice_primary', 'en', 'text')
        self.add_setting('alerts_voice_secondary', 'fr', 'text')
        self.add_setting('alerts_geocode', '10,11,12,13,24,35,46,47,48,59,60,61,62', 'text')
        self.add_setting('alerts_broadcast_message_in_indigenous_languages', '0', 'bool')
        self.add_setting('alerts_selected_indigenous_languages', '', 'text')
        self.add_setting('alerts_repeat_interval', '30', 'int')
        self.add_setting('alerts_repeat_times', '0', 'int')
        self.add_setting('alerts_leadin_delay', '1', 'int')
        self.add_setting('alerts_leadout_delay', '1', 'int')
        self.add_setting('alerts_naad_stream1', "http://streaming1.naad-adna.pelmorex.com:8080", 'text')
        self.add_setting('alerts_naad_stream2', "http://streaming2.naad-adna.pelmorex.com:8080", 'text')
        self.add_setting('alerts_naad_archive1', "http://capcp1.naad-adna.pelmorex.com", 'text')
        self.add_setting('alerts_naad_archive2', "http://capcp2.naad-adna.pelmorex.com", 'text')
        self.add_setting('alerts_truncate', '0', 'bool')
        self.add_setting('alerts_play_moderates', '0', 'bool')
        self.add_setting('alerts_play_tests', '0', 'bool')
        self.add_setting('alerts_trigger_serial', '0', 'bool')
        self.add_setting('alerts_trigger_serial_file', '/dev/ttyS0', 'text')
        self.add_setting('alerts_trigger_streamer', '0', 'bool')
        self.add_setting('alerts_purge_files', '1', 'bool')

        self.add_setting('location_enable', '0', 'bool')
        self.add_setting('location_longitude', '-134.18537', 'float')
        self.add_setting('location_latitude', '60.27434', 'float')

        self.add_setting('offair_audiolog_enable', '0', 'bool')
        self.add_setting('offair_audiolog_icecast_ip', 'localhost', 'text')
        self.add_setting('offair_audiolog_icecast_port', '8000', 'int')
        self.add_setting('offair_audiolog_icecast_mountpoint', 'fm_audio', 'text')
        self.add_setting('offair_audiolog_icecast_password', 'hackme', 'text')
        self.add_setting('offair_audiolog_icecast_bitrate', '128', 'int')
        self.add_setting('offair_audiolog_feq', '88.0', 'float')

        self.add_setting('led_sign_enable', '0', 'bool')
        self.add_setting('led_sign_serial_file', '/dev/ttyS1', 'text')
        self.add_setting('led_sign_timedisplay', '0', 'bool')
        self.add_setting('led_sign_init_message', '', 'text')

    def add_setting(self, name, value, datatype=None):

        check_setting = self.query("SELECT name,value,type from 'settings' WHERE name = '" + self.escape(name) + "'")
        if len(check_setting):
            return

        data = {}
        data['name'] = name
        data['value'] = value

        if datatype != None:
            data['type'] = datatype

        self.row_addedit('settings', data)

    def setting(self, name, use_edit_cache=False):
        settings = self.settings_edit_cache if use_edit_cache else self.settings_cache
        try:
            return settings[name]
        except:
            return False

    # save our settings into the database. update settings_edit_cache to handle subsequent edits.
    def save_settings(self, settings):
        for (name, value) in settings.items():
            dataType = self.settings_type[name]
            if dataType == 'int':
                self.settings_edit_cache[name] = int(value)
            elif dataType == 'float':
                self.settings_edit_cache[name] = float(value)
            elif dataType == 'bool':
                self.settings_edit_cache[name] = bool(int(value))
            else:
                self.settings_edit_cache[name] = str(value)

            self.query('UPDATE settings set value="' + self.escape(str(value)) + '" where name="' + self.escape(name) + '"')

    def list_settings(self, hidepasswords=False):
        result = { }
        for (name, value) in self.settings_cache.items():
            if not hidepasswords or not name.endswith('_password'):
                result[name] = value
        return result
