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
import obplayer.alerts

import pycurl

import xml.dom.minidom

import os
import re
import time
import hashlib
import shutil
import sys
import json
import calendar
import threading
import traceback
import requests


MIN_SERVER_VERSION = '4.1.1-20150507'


if sys.version.startswith('3'):
    import urllib.parse as urllib
    unicode = str
    def strascii(text):
        return text
else:
    import urllib
    def strascii(text):
        return unicode(text).encode('ascii', 'xmlcharrefreplace')


# Given XML element, gets text within that element.
def xml_get_text(element):
    nodelist = element.childNodes
    rc = ''
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc = rc + node.data
    return rc


# Get direct children.  Like getElementsByTagName, but only with direct children.
def xml_get_direct_children(node, tagName):
    children = []
    for e in node.childNodes:
        if e.nodeType == e.ELEMENT_NODE and e.nodeName == tagName:
            children.append(e)
    return children


def xml_get_tag_value(node, tagName, default=''):
    child = xml_get_direct_children(node, tagName)
    if len(child) <= 0:
        return default
    return xml_get_text(child[0])


def xml_get_media_item(node):
    media_item = {}

    media_item['id'] = xml_get_tag_value(node, 'id', 0)
    media_item['filename'] = xml_get_tag_value(node, 'filename')
    media_item['title'] = xml_get_tag_value(node, 'title')
    media_item['artist'] = xml_get_tag_value(node, 'artist')
    media_item['order'] = xml_get_tag_value(node, 'order')
    media_item['offset'] = xml_get_tag_value(node, 'offset')
    media_item['duration'] = xml_get_tag_value(node, 'duration')
    media_item['type'] = xml_get_tag_value(node, 'type')
    media_item['file_hash'] = xml_get_tag_value(node, 'hash')
    media_item['file_size'] = xml_get_tag_value(node, 'filesize')
    media_item['file_location'] = xml_get_tag_value(node, 'location')
    media_item['approved'] = xml_get_tag_value(node, 'approved')
    media_item['archived'] = xml_get_tag_value(node, 'archived')

    return media_item


def xml_get_tags(element, tag):
    children = [ ]
    for node in element.childNodes:
        if node.nodeType == node.ELEMENT_NODE and node.nodeName == tag:
            children.append(node)
    return children


def xml_get_tag_values(element, tag):
    values = [ ]
    for child in xml_get_tags(element, tag):
        values.append(xml_get_text(child))
    return values


def xml_get_first_tag_value(element, tag, default=None):
    children = xml_get_tags(element, tag)
    if len(children) <= 0:
        return default
    return xml_get_text(children[0])



class VersionUpdateThread (obplayer.ObThread):
    def try_run(self):
        if obplayer.Config.version:
            obplayer.Sync.version_update()
        self.remove_thread()


class SyncShowsThread (obplayer.ObThread):
    def run(self):
        self.synctime = int(60 * obplayer.Config.setting('sync_freq'))
        while True:
            try:
                obplayer.Sync.sync_shows()
            except:
                obplayer.Log.log("exception in " + self.name + " thread", 'error')
                obplayer.Log.log(traceback.format_exc(), 'error')

            if self.stopflag.wait(self.synctime):
                break

    # TODO this is temporary until you can have Sync check the stop flags directly
    def stop(self):
        obplayer.ObThread.stop(self)
        obplayer.Sync.quit = True


class SyncPlaylogThread (obplayer.ObThread):
    def run(self):
        if not obplayer.Config.setting('sync_playlog_enable'):
            self.remove_thread()
            return

        self.synctime = int(60 * obplayer.Config.setting('sync_freq_playlog'))
        while not self.stopflag.wait(self.synctime):
            try:
                obplayer.Sync.sync_playlog()
            except:
                obplayer.Log.log("exception in " + self.name + " thread", 'error')
                obplayer.Log.log(traceback.format_exc(), 'error')

    def stop(self):
        obplayer.ObThread.stop(self)
        obplayer.Sync.quit = True


class SyncEmergThread (obplayer.ObThread):
    def run(self):
        self.synctime = int(60 * obplayer.Config.setting('sync_freq_priority'))
        while not self.stopflag.wait(self.synctime):
            try:
                obplayer.Sync.sync_priority_broadcasts()
            except:
                obplayer.Log.log("exception in " + self.name + " thread", 'error')
                obplayer.Log.log(traceback.format_exc(), 'error')

    def stop(self):
        obplayer.ObThread.stop(self)
        obplayer.Sync.quit = True


class SyncMediaThread (obplayer.ObThread):
    def run(self):
        self.synctime = int(5)
        while not self.stopflag.wait(self.synctime):
            try:
                obplayer.Sync.sync_media()
            except:
                obplayer.Log.log("exception in " + self.name + " thread", 'error')
                obplayer.Log.log(traceback.format_exc(), 'error')

    def stop(self):
        obplayer.ObThread.stop(self)
        obplayer.Sync.quit = True


class Sync_Alert_Media_Thread(obplayer.ObThread):
    def __init__(self):
        obplayer.ObThread.__init__(self)
        self.daemon = True
        # Download indigenous alert data from server.

    def run(self):
        self.running = True
        while self.running:
            obplayer.Sync.sync_alert_media()
            # Sleeping for sync_freq time
            time.sleep(obplayer.Config.setting('sync_freq'))

    def convert_audio(self, file_path, file_type, filename):
        process = subprocess.Popen(['sox', file_path + '.' + file_type, '-t', 'wav', file_path + '.wav'])
        process.wait()
        if process.poll() != 0:
            obplayer.Log.log('Could not convert file {0} to wav format! Make sure sox is installed.'.format(file_path + file_type), 'error')

    def fetch_alert_media(self, media):
        postfields = {}

        postfields['id'] = obplayer.Config.setting('sync_device_id')
        postfields['pw'] = obplayer.Config.setting('sync_device_password')
        postfields['media_id'] = media['media_id']

        data_request = requests.post(obplayer.Config.setting('sync_url') + "?action=media", data=postfields)

        if data_request.status_code != 200:
            obplayer.Log.log('unable to download alert media id: {0} at this time'.format(media['media_id']), 'error')
        else:
            data = data_request.content
            try:
                # build save path with language name.
                print(obplayer.alert.ObAlert.lang_ref_to_language_name(media['language']))
                save_path = obplayer.RemoteData.datadir + '/indigenous/{0}/'.format(obplayer.alert.ObAlert.lang_ref_to_language_name(media['language']))
                with open(save_path + media['filename'], 'wb') as file:
                    file.write(data)
                # convert all non wav audio to wav
                if media['filename'].endswith('.wav') == False:
                    # strip file ext from filename
                    filename = media['filename'].replace('.ogg', '').replace('.mp3', '').replace('.OGG', '').replace('.MP3', '')
                    self.convert_audio(save_path + media['filename'], media['media_format'], filename)
            except FileNotFoundError as e:
                obplayer.Log.log('unable to download alert media id: {0} at this time'.format(media['media_id']), 'error')

    def stop(self):
        self.running = False
        obplayer.ObThread.stop(self)


class ObSync:

    def __init__(self):
        self.quit = False
        self.priority_sync_running = False

    def curl_progress(self, download_t, download_d, upload_t, upload_d):
        if self.quit:
            return True

    def version_update(self):
        if not obplayer.Config.setting('sync_url'):
            return
        obplayer.Log.log('sending player version to server: ' + obplayer.Config.version, 'sync')

        postfields = {}
        postfields['id'] = obplayer.Config.setting('sync_device_id')
        postfields['pw'] = obplayer.Config.setting('sync_device_password')
        postfields['version'] = obplayer.Config.version
        postfields['longitude'] = obplayer.Config.setting('location_longitude')
        postfields['latitude'] = obplayer.Config.setting('location_latitude')

        curl = pycurl.Curl()

        enc_postfields = urllib.urlencode(postfields)

        curl.setopt(pycurl.NOSIGNAL, 1)
        curl.setopt(pycurl.USERAGENT, 'OpenBroadcaster Player')
        curl.setopt(pycurl.URL, obplayer.Config.setting('sync_url') + '?action=version')
        curl.setopt(pycurl.HEADER, False)
        curl.setopt(pycurl.POST, True)
        curl.setopt(pycurl.POSTFIELDS, enc_postfields)

        curl.setopt(pycurl.LOW_SPEED_LIMIT, 10)
        curl.setopt(pycurl.LOW_SPEED_TIME, 300)

        curl.setopt(pycurl.NOPROGRESS, 0)
        curl.setopt(pycurl.PROGRESSFUNCTION, self.curl_progress)

        class CurlResponse:
            def __init__(self):
                self.buffer = u''
            def __call__(self, data):
                self.buffer += data.decode('utf-8')

        curl_response = CurlResponse()
        curl.setopt(pycurl.WRITEFUNCTION, curl_response)

        try:
            curl.perform()
        except:
            obplayer.Log.log("exception in VersionUpdate thread", 'error')
            obplayer.Log.log(traceback.format_exc(), 'error')

        curl.close()

        if curl_response.buffer:
            version = json.loads(curl_response.buffer)
            obplayer.Log.log("server version reported as " + str(version), 'sync')
            if not self.check_min_version(version):
                obplayer.Log.log("minimum server version " + str(MIN_SERVER_VERSION) + " is required. Please update server software before continuing", 'error')
        else:
            obplayer.Log.log("server did not report a version number", 'warning')


    def check_min_version(self, version):
        cv = re.split('[.-]', version)
        mv = re.split('[.-]', MIN_SERVER_VERSION)
        for i in range(0, len(mv)):
            try:
                if int(cv[i]) < int(mv[i]):
                    return False
            except:
                return False
        return True

    #
    # Perform synchronization.
    # if ignore_showlock = true, ignore cutoff time. we're doing a database reset.
    def sync_shows(self, ignore_showlock=False):

        cutoff_time = time.time() + obplayer.Config.setting('sync_showlock') * 60

        syncfiles = {}

        obplayer.Log.log('fetching show data from server', 'sync')

        schedule_xml = self.sync_request('schedule')

        # TODO for debugging purposes, write schedule to file
        #with open(obplayer.ObData.get_datadir() + "/schedules/" + time.strftime('%Y.%m.%d %H:%M:%S') + ".xml", 'w') as f:
        #    f.write(schedule_xml)
        #print(schedule_xml)


        # trying to quit?
        if self.quit:
            return

        try:
            schedule = xml.dom.minidom.parseString(schedule_xml)
        except:
            obplayer.Log.log('unable to sync - possible configuration, server, or network error.', 'error')
            return

        error = schedule.getElementsByTagName('error')
        if len(error) > 0:
            error_msg = xml_get_text(error[0])
            obplayer.Log.log('Unable to sync with server.  (' + error_msg + ')', 'error')
            return

        obplayer.Log.log('writing data to database', 'sync')

        start_times_list = []

        for show in schedule.getElementsByTagName('show'):

            show_id = xml_get_first_tag_value(show, 'id')
            show_type = xml_get_first_tag_value(show, 'type')
            show_date = xml_get_first_tag_value(show, 'date')
            show_time = xml_get_first_tag_value(show, 'time')
            show_name = xml_get_first_tag_value(show, 'name', '')
            show_description = xml_get_first_tag_value(show, 'description', '')
            show_duration = xml_get_first_tag_value(show, 'duration', 0)
            show_last_updated = xml_get_first_tag_value(show, 'last_updated', 0)
            show_media = xml_get_direct_children(show, 'media')[0]

            show_liveassist = xml_get_direct_children(show, 'liveassist_buttons')
            if show_liveassist:
                show_liveassist = show_liveassist[0]

            show_start_datetime = time.strptime(show_date + ' ' + show_time, '%Y-%m-%d %H:%M:%S')
            # show_start_timestamp=time.mktime(show_start_datetime) - time.timezone;
            show_start_timestamp = calendar.timegm(show_start_datetime)

            # only consider shows that are beyond the showlock time (unless ignore_showlock)
            if ignore_showlock or show_start_timestamp - cutoff_time > 0:

                local_show_id = obplayer.RemoteData.show_addedit(show_id, show_name, show_type, show_description, show_start_timestamp, show_duration, show_last_updated)

                start_times_list.append(show_start_timestamp)

                if local_show_id is not False:

                    for media in xml_get_direct_children(show_media, 'item'):
                        media_item = xml_get_media_item(media)
                        obplayer.RemoteData.show_media_add(local_show_id, show_id, media_item)

                    if show_liveassist:

                        obplayer.RemoteData.group_remove_old(local_show_id)
                        for group in xml_get_direct_children(show_liveassist, 'group'):
                            group_name = xml_get_text(xml_get_direct_children(group, 'name')[0])
                            media_list = xml_get_direct_children(group, 'media')[0]
                            group_id = obplayer.RemoteData.group_add(local_show_id, group_name)

                            for media in xml_get_direct_children(media_list, 'item'):
                                media_item = xml_get_media_item(media)
                                obplayer.RemoteData.group_item_add(group_id, media_item)

                        group_id = obplayer.RemoteData.group_add(local_show_id, 'System Requests')
                        obplayer.RemoteData.group_item_add(group_id, { 'id': -1, 'order': 0, 'artist': 'System', 'title': "Station Line-In Audio Source", 'type': 'linein', 'duration': 3600, 'filename': '', 'file_hash': '', 'file_size': 0, 'file_location': '', 'approved': 0, 'archived': 0 })
                        obplayer.RemoteData.group_item_add(group_id, { 'id': -1, 'order': 1, 'artist': 'System', 'title': "Remote RTP Audio Source", 'type': 'rtp', 'duration': 3600, 'filename': '', 'file_hash': '', 'file_size': 0, 'file_location': '', 'approved': 0, 'archived': 0 })
                        #obplayer.RemoteData.group_item_add(group_id, { 'id': -1, 'order': 1, 'artist': 'System', 'title': "Local Streamer Audio Source", 'type': 'sdp', 'duration': 3600, 'filename': 'local_streamer.sdp', 'file_hash': '', 'file_size': 0, 'file_location': os.getcwd() + '/tools', 'approved': 0, 'archived': 0 })

        obplayer.RemoteData.show_remove_deleted(start_times_list, cutoff_time)
        obplayer.RemoteData.show_remove_old()

        obplayer.Scheduler.update_show_update_time()

        self.sync_media_required = True

        # backup database to disk.
        obplayer.RemoteData.backup()

    #
    # Similar to sync, but synchronizes priority broadcast.  Showlock is not used here.
    #
    def sync_priority_broadcasts(self):

        self.priority_sync_running = True

        syncfiles = {}

        obplayer.Log.log('fetching priority broadcast data from server', 'sync')

        broadcasts_xml = self.sync_request('emerg')

        # trying to quit?
        if self.quit:
            return

        try:
            broadcasts = xml.dom.minidom.parseString(broadcasts_xml)
        except:
            obplayer.Log.log('unable to sync (priority broacasts) - possible configuration or server error', 'error')
            return

        error = broadcasts.getElementsByTagName('error')

        if len(error) > 0:
            error_msg = xml_get_text(error[0])
            obplayer.Log.log('Unable to sync with server.  (' + error_msg + ')', 'error')
            return

        # self.log.log('writing data to database');

        # setup our broadcaster id list, used to remove deleted items from db after adding below.
        broadcast_id_list = []

        for broadcast in broadcasts.getElementsByTagName('broadcast'):
            broadcast_id = xml_get_text(broadcast.getElementsByTagName('id')[0])
            broadcast_start = xml_get_text(broadcast.getElementsByTagName('start_timestamp')[0])
            broadcast_end = xml_get_text(broadcast.getElementsByTagName('end_timestamp')[0])
            broadcast_frequency = xml_get_text(broadcast.getElementsByTagName('frequency')[0])
            broadcast_artist = xml_get_text(broadcast.getElementsByTagName('artist')[0])
            broadcast_filename = xml_get_text(broadcast.getElementsByTagName('filename')[0])
            broadcast_title = xml_get_text(broadcast.getElementsByTagName('title')[0])
            broadcast_media_id = xml_get_text(broadcast.getElementsByTagName('media_id')[0])
            broadcast_duration = xml_get_text(broadcast.getElementsByTagName('duration')[0])
            broadcast_media_type = xml_get_text(broadcast.getElementsByTagName('media_type')[0])
            broadcast_file_hash = xml_get_text(broadcast.getElementsByTagName('hash')[0])
            broadcast_file_size = xml_get_text(broadcast.getElementsByTagName('filesize')[0])
            broadcast_file_location = xml_get_text(broadcast.getElementsByTagName('location')[0])
            broadcast_approved = xml_get_text(broadcast.getElementsByTagName('approved')[0])
            broadcast_archived = xml_get_text(broadcast.getElementsByTagName('archived')[0])

            broadcast_id_list.append(broadcast_id)

            obplayer.RemoteData.priority_broadcast_addedit(
                broadcast_id,
                broadcast_start,
                broadcast_end,
                broadcast_frequency,
                broadcast_artist,
                broadcast_title,
                broadcast_filename,
                broadcast_media_id,
                broadcast_duration,
                broadcast_media_type,
                broadcast_file_hash,
                broadcast_file_size,
                broadcast_file_location,
                broadcast_approved,
                broadcast_archived,
                )

        # delete now-removed broadcasts.
        obplayer.RemoteData.priority_broadcast_remove_deleted(broadcast_id_list)

        # update gui, sync media.
        # self.sync_media();
        self.sync_media_required = True

        self.priority_sync_running = False

        obplayer.RemoteData.get_priority_broadcasts()
        obplayer.PriorityBroadcaster.check_update()

    #
    # Sync playlog with server.
    # This makes a request to the server to determine the point from which the playlog is required.
    # Then it sends the playlog from that point.  If server replies with 'success', sync'd entries + older are removed from this app's database.
    #
    def sync_playlog(self):

        obplayer.Log.log('syncing playlog with server', 'sync')

        # determine from what point the server is missing playlog entries.
        status_xml = self.sync_request('playlog_status')

        # trying to quit? sync request was cancelled.
        if self.quit:
            return

        try:
            status = xml.dom.minidom.parseString(status_xml)
            last_timestamp = xml_get_text(status.getElementsByTagName('last_timestamp')[0])
        except:
            obplayer.Log.log('unable to sync (playlog) - possible configuration or server error', 'error')
            return

        entries = obplayer.PlaylogData.get_entries_since(last_timestamp)

        # get DOM implementation to create new XML document.
        impl = xml.dom.minidom.getDOMImplementation()

        doc = impl.createDocument(None, 'obconnect', None)
        playlog = doc.createElement('playlog')
        doc.firstChild.appendChild(playlog)

        highest_id = 0

        for entry in entries:
            xmlentry = doc.createElement('entry')

            media_id_element = doc.createElement('media_id')
            media_id_text = doc.createTextNode(str(entry['media_id']))
            media_id_element.appendChild(media_id_text)
            xmlentry.appendChild(media_id_element)

            artist_element = doc.createElement('artist')
            #artist_text = doc.createTextNode(unicode(entry['artist']).encode('ascii', 'xmlcharrefreplace'))
            artist_text = doc.createTextNode(strascii(entry['artist']))
            artist_element.appendChild(artist_text)
            xmlentry.appendChild(artist_element)

            title_element = doc.createElement('title')
            #title_text = doc.createTextNode(unicode(entry['title']).encode('ascii', 'xmlcharrefreplace'))
            title_text = doc.createTextNode(strascii(entry['title']))
            title_element.appendChild(title_text)
            xmlentry.appendChild(title_element)

            datetime_element = doc.createElement('datetime')
            datetime_text = doc.createTextNode(str(entry['datetime']))
            datetime_element.appendChild(datetime_text)
            xmlentry.appendChild(datetime_element)

            context_element = doc.createElement('context')
            context_text = doc.createTextNode(str(entry['context']))
            context_element.appendChild(context_text)
            xmlentry.appendChild(context_element)

            priority_id_element = doc.createElement('emerg_id')
            priority_id_text = doc.createTextNode(str(entry['emerg_id']))
            priority_id_element.appendChild(priority_id_text)
            xmlentry.appendChild(priority_id_element)

            notes_element = doc.createElement('notes')
            notes_text = doc.createTextNode(str(entry['notes']))
            notes_element.appendChild(notes_text)
            xmlentry.appendChild(notes_element)

            playlog.appendChild(xmlentry)

            # keep track of highest ID, we will remove everything of this ID and lower if post is a success.
            if highest_id < entry['id']:
                highest_id = entry['id']

        postxml = doc.toxml()

        response_xml = self.sync_request('playlog_post', postxml)

        # trying to quit? sync requestes was cancelled.
        if self.quit:
            return

        try:
            post_status = xml.dom.minidom.parseString(response_xml)
            post_status_text = xml_get_text(post_status.getElementsByTagName('status')[0])
        except:
            post_status_text = ''

        if post_status_text == 'success':
            obplayer.PlaylogData.remove_entries_since(highest_id)

        else:
            obplayer.Log.log('unable to submit playlog at this time', 'error')

    sync_media_required = False  # set to true if sync_media should do a sync.
    sync_media_id = False  # this is the id of the file presently being downloaded

    #
    # Sync media files.  This takes a look at show_media and priority_broadcast tables to determine the media required,
    # then downloads that media from the web application.
    #
    def sync_media(self, delete_unused_media=True):

        if self.sync_media_required == False:
            return

        self.sync_media_required = False

        media_required = obplayer.RemoteData.media_required()

        for media_row in media_required:

            media = media_required[media_row]

            if self.check_media(media) == False:
                self.sync_media_file = media['media_id']
                self.fetch_media(media)
                self.sync_media_file = False

        if delete_unused_media == True:
            self.remove_unused_media(obplayer.Config.setting('remote_media'), media_required)

    def fetch_alert_media(self, media):
        postfields = {}

        postfields['id'] = obplayer.Config.setting('sync_device_id')
        postfields['pw'] = obplayer.Config.setting('sync_device_password')
        postfields['media_id'] = media['media_id']

        data_request = requests.post(obplayer.Config.setting('sync_url') + "?action=media", data=postfields)

        if data_request.status_code != 200:
            obplayer.Log.log('unable to download alert media id: {0} at this time'.format(media['media_id']), 'error')
        else:
            data = data_request.content
            try:
                # build save path with language name.
                save_path = obplayer.RemoteData.datadir + '/indigenous/{0}/'.format(obplayer.alerts.ObAlert.lang_ref_to_language_name(media['language']))
                with open(save_path + media['filename'], 'wb') as file:
                    file.write(data)
                # convert all non wav audio to wav
                if media['filename'].endswith('wav') == False:
                    # strip file ext from filename
                    filename = media['filename'].replace('.ogg', '').replace('.mp3', '').replace('.OGG', '').replace('.MP3', '')
                    self.convert_audio(save_path + media['filename'], media['media_format'], filename)
            except FileNotFoundError as e:
                obplayer.Log.log('unable to download alert media id: {0} at this time'.format(media['media_id']), 'error')

    def sync_alert_media(self, delete_unused_media=True):
        media_required = obplayer.RemoteData.alert_media_required()

        for media_row in media_required:

            media = media_required[media_row]

            if self.check_media(media, True, media['language']) == False:
                self.sync_media_file = media['media_id']
                self.fetch_alert_media(media)
                self.sync_media_file = False

        if delete_unused_media == True:
            self.remove_unused_media(obplayer.Config.setting('remote_media'), media_required)

    #
    #
    # uses media['file_location'], media['file_size'], media['filename'] to see if available media is the correct filesize.
    #
    def check_media(self, media, alert_mode=False, alert_language=None):

        if media['media_type'] not in [ 'audio', 'video', 'image' ]:
            return True
        if alert_mode and alert_language != None:
            media_fullpath = obplayer.RemoteData.datadir + '/indigenous/{0}/'.format(alert_language) + media['filename']
        else:
            media_fullpath = obplayer.Config.setting('remote_media') + '/' + media['file_location'][0] + '/' + media['file_location'][1] + '/' + media['filename']

        # TODO provide file hash check (slow) as an option.

        if os.path.exists(media_fullpath):
            localfile_size = os.path.getsize(media_fullpath)
        else:
            localfile_size = False

        if localfile_size == False or localfile_size != media['file_size']:
            return False

        return True

    #
    # removed unusued media from remote media directory. (called recursively)
    #
    def remove_unused_media(self, searchdir, media_required):

        dirlist = os.listdir(searchdir)
        for thisfile in dirlist:

            if os.path.isdir(searchdir + '/' + thisfile):
                self.remove_unused_media(searchdir + '/' + thisfile, media_required)
            else:

                try:
                    media_required[thisfile]
                except:
                    obplayer.Log.log('deleting unused media: ' + searchdir + '/' + thisfile, 'sync')
                    try:
                        os.remove(searchdir + '/' + thisfile)
                    except:
                        obplayer.Log.log('unable to remove media: ' + searchdir + '/' + thisfile, 'error')

    # call sync now playing update in a separate thread.
    def now_playing_update(self, playlist_id, playlist_end, media_id, media_end, show_name):
        if obplayer.Config.setting('sync_playlog_enable'):
            t = threading.Thread(target=self.now_playing_update_thread, args=(playlist_id, playlist_end, media_id, media_end, show_name))
            t.start()

    #
    # Update 'now playing' information
    #
    def now_playing_update_thread(self, playlist_id, playlist_end, media_id, media_end, show_name):

        if not obplayer.Config.setting('sync_url'):
            return

        postfields = {}
        postfields['id'] = obplayer.Config.setting('sync_device_id')
        postfields['pw'] = obplayer.Config.setting('sync_device_password')

        postfields['playlist_id'] = playlist_id
        postfields['media_id'] = media_id
        postfields['show_name'] = show_name

        if playlist_end != '':
            postfields['playlist_end'] = int(round(playlist_end))
        else:
            postfields['playlist_end'] = ''

        if media_end != '':
            postfields['media_end'] = int(round(media_end))
        else:
            postfields['media_end'] = ''

        curl = pycurl.Curl()

        enc_postfields = urllib.urlencode(postfields)

        curl.setopt(pycurl.NOSIGNAL, 1)
        curl.setopt(pycurl.USERAGENT, 'OpenBroadcaster Player')
        curl.setopt(pycurl.URL, obplayer.Config.setting('sync_url') + '?action=now_playing')
        curl.setopt(pycurl.HEADER, False)
        curl.setopt(pycurl.POST, True)
        curl.setopt(pycurl.POSTFIELDS, enc_postfields)
        #curl.setopt(pycurl.FOLLOWLOCATION, 1)

        curl.setopt(pycurl.LOW_SPEED_LIMIT, 10)
        curl.setopt(pycurl.LOW_SPEED_TIME, 60)

        curl.setopt(pycurl.NOPROGRESS, 0)
        curl.setopt(pycurl.PROGRESSFUNCTION, self.curl_progress)

        try:
            curl.perform()
        except:
            obplayer.Log.log("exception in NowPlayingUpdate thread", 'error')
            obplayer.Log.log(traceback.format_exc(), 'error')

        curl.close()

    #
    # Request sync data from web application.
    # This is used by sync (with request_type='schedule') and sync_priority_broadcasts (with request_type='emerg').
    # Function outputs XML response from server.
    #
    def sync_request(self, request_type='', data=False):
        sync_url = obplayer.Config.setting('sync_url')
        if not sync_url:
            obplayer.Log.log("sync url is blank, skipping sync request", 'sync')
            return ''

        curl = pycurl.Curl()

        postfields = {}
        postfields['id'] = obplayer.Config.setting('sync_device_id')
        postfields['pw'] = obplayer.Config.setting('sync_device_password')
        postfields['hbuffer'] = obplayer.Config.setting('sync_buffer')
        if data:
            postfields['data'] = data

        enc_postfields = urllib.urlencode(postfields)

        curl.setopt(pycurl.NOSIGNAL, 1)
        curl.setopt(pycurl.USERAGENT, 'OpenBroadcaster Player')
        curl.setopt(pycurl.URL, sync_url + '?action=' + request_type)
        curl.setopt(pycurl.HEADER, False)
        curl.setopt(pycurl.POST, True)
        curl.setopt(pycurl.POSTFIELDS, enc_postfields)

        # some options so that it'll abort the transfer if the speed is too low (i.e., network problem)
        # low speed abort set to 0.01Kbytes/s for 60 seconds).
        curl.setopt(pycurl.LOW_SPEED_LIMIT, 10)
        curl.setopt(pycurl.LOW_SPEED_TIME, 300)

        curl.setopt(pycurl.NOPROGRESS, 0)
        curl.setopt(pycurl.PROGRESSFUNCTION, self.curl_progress)

        class CurlResponse:
            def __init__(self):
                self.buffer = u''
            def __call__(self, data):
                self.buffer += data.decode('utf-8')

        curl_response = CurlResponse()
        curl.setopt(pycurl.WRITEFUNCTION, curl_response)

        try:
            curl.perform()
        #except pycurl.error as error:
        #    (errno, errstr) = error
        #    obplayer.Log.log('network error: ' + errstr, 'error')
        except:
            obplayer.Log.log("exception in sync " + request_type + " thread", 'error')
            obplayer.Log.log(traceback.format_exc(), 'error')

        curl.close()

        return curl_response.buffer

    #
    # Fetch media from web application.  Saves under media directory.
    # media_id : id of the media we want
    # filename : filename to save under.
    #
    def fetch_media(self, media):

        media_id = media['media_id']
        filename = media['filename']
        file_hash = media['file_hash']
        file_size = media['file_size']
        file_location = media['file_location']
        approved = media['approved']
        archived = media['archived']

        #
        # create subdirs in media if required.

        if os.path.isdir(obplayer.Config.setting('remote_media') + '/' + file_location[0]) == False:
            os.mkdir(obplayer.Config.setting('remote_media') + '/' + file_location[0], 0o755)

        if os.path.isdir(obplayer.Config.setting('remote_media') + '/' + file_location[0] + '/' + file_location[1]) == False:
            os.mkdir(obplayer.Config.setting('remote_media') + '/' + file_location[0] + '/' + file_location[1], 0o755)

        fetch_from_http = False

        # what is our desired output file name?

        media_outfilename = obplayer.Config.setting('remote_media') + '/' + file_location[0] + '/' + file_location[1] + '/' + filename

        # determine our sync mode - if local or backup, look in local location first.

        sync_mode = obplayer.Config.setting('sync_mode')
        if sync_mode == 'remote':
            fetch_from_http = True

        if sync_mode == 'local' or sync_mode == 'backup':

            if archived == 1:
                local_media_location = obplayer.Config.setting('local_archive')
            elif approved == 0:
                local_media_location = obplayer.Config.setting('local_uploads')
            else:
                local_media_location = obplayer.Config.setting('local_media')

            # see if local file exists, and if hash matches.

            local_fullpath = local_media_location + '/' + file_location[0] + '/' + file_location[1] + '/' + filename

            # TODO provide hash match (slow) as an option.

            if os.path.exists(local_fullpath):
                local_exists = True
                if os.path.getsize(local_fullpath) == file_size:
                    file_match = True
                else:
                    file_match = False
            else:

                local_exists = False
                file_match = False

            if local_exists and (file_match or sync_mode == 'local'):  # ignoring hash mismatch if source local, there is nothing we can do anyway...
                obplayer.Log.log('copying ' + filename + ' from local', 'sync')
                shutil.copy(local_fullpath, media_outfilename)
            elif sync_mode == 'backup':

                fetch_from_http = True

        if fetch_from_http:

            media_id = str(media_id)

            postfields = str('media_id=' + media_id + '&id=' + str(obplayer.Config.setting('sync_device_id')) + '&pw=' + obplayer.Config.setting('sync_device_password') + '&buffer=' + str(obplayer.Config.setting('sync_buffer')))

            obplayer.Log.log('downloading ' + filename, 'sync download')

            curl = pycurl.Curl()

            outfile = open(media_outfilename, 'wb')

            curl.setopt(pycurl.NOSIGNAL, 1)
            curl.setopt(pycurl.USERAGENT, 'OpenBroadcaster Player')
            curl.setopt(pycurl.URL, obplayer.Config.setting('sync_url') + '?action=media')
            curl.setopt(pycurl.HEADER, False)
            curl.setopt(pycurl.POST, True)
            curl.setopt(pycurl.POSTFIELDS, postfields)
            curl.setopt(pycurl.WRITEFUNCTION, outfile.write)
            curl.setopt(pycurl.LOW_SPEED_LIMIT, 10)
            curl.setopt(pycurl.LOW_SPEED_TIME, 60)

            curl.setopt(pycurl.NOPROGRESS, 0)
            curl.setopt(pycurl.PROGRESSFUNCTION, self.curl_progress)

            # TODO, if a perform fails, then we need to make sure sync will try again shortly (i.e. 90 seconds)
            try:
                curl.perform()
                file_download_complete = True
            except:
                obplayer.Log.log('error fetching media, network or configuration problem.', 'error')
                file_download_complete = False

            outfile.close()
            curl.close()

            # trying to quit? don't copy to backup because we probably aborted the transfer.
            if self.quit:
                return

            # if file download complete and we're on 'backup' mode, copy the downloaded file to our backup repository to keep it up to date.
            # also check to make sure this setting is selected

            if obplayer.Config.setting('sync_copy_media_to_backup') and file_download_complete and sync_mode == 'backup' and os.path.exists(media_outfilename) and os.path.getsize(media_outfilename) == file_size:
                # create our dirs in the backup location if required
                if os.path.isdir(local_media_location + '/' + file_location[0]) == False:
                    os.mkdir(local_media_location + '/' + file_location[0], 0o755)

                if os.path.isdir(local_media_location + '/' + file_location[0] + '/' + file_location[1]) == False:
                    os.mkdir(local_media_location + '/' + file_location[0] + '/' + file_location[1], 0o755)

                obplayer.Log.log('copying downloaded file to backup location', 'sync')

                # copy newly downloaded file to backup
                shutil.copy(media_outfilename, local_fullpath)

    #
    # Check MD5 hash of a given file.
    #
    def file_hash(self, filename):
        fp = file(filename, 'rb')
        return hashlib.md5(fp.read()).hexdigest()

    @staticmethod
    def media_location(file_location):
        if '/' not in file_location:
            # file location specified as 2-character directory code.
            file_location = obplayer.Config.setting('remote_media') + '/' + file_location[0] + '/' + file_location[1]
        elif file_location[0] != '/':
            file_location = os.getcwd() + '/' + file_location
        return file_location

    #
    # expand file location and check that media file exists
    #
    @staticmethod
    def media_uri(file_location, filename):
        if not file_location:
            return ''
        file_location = obplayer.Sync.media_location(file_location)
        if filename and os.path.exists(file_location + '/' + filename) == False:
            obplayer.Log.log('ObPlayer: File ' + file_location + '/' + filename + ' does not exist. Skipping playback', 'error')
            return None
        return 'file://' + file_location + '/' + filename
