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

import xml.dom.minidom
import base64
import hashlib
import datetime
import dateutil.tz
import dateutil.parser

import os
import os.path
import sys
import time
import socket

import traceback

import html
import requests
import subprocess

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstPbutils', '1.0')
from gi.repository import GObject, Gst, GstPbutils

import wave
if obplayer.Config.setting('alerts_aws_voices_enable'):
    import boto3
import audioop
import math
import struct

def xml_get_text(element):
    text = ''
    for node in element.childNodes:
        if node.nodeType == node.TEXT_NODE:
            text = text + node.data
    return text

def xml_has_tag(element, tag):
    for node in element.childNodes:
        if node.nodeType == node.ELEMENT_NODE and node.nodeName == tag:
            return True
    return False

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

class Feed (object):
    def __init__(self, xmlcode=None):
        self.known_alerts = []
        if xmlcode != None:
            try:
                xmlcode = xmlcode.replace('cap:', '')
                self.alerts = xml.dom.minidom.parseString(xmlcode)
                #print(xml_get_tags(self.alerts))
            except:
                obplayer.Log.log('error parsing emergency alert xml data', 'error')
                obplayer.Log.log(traceback.format_exc(), 'error')
                print(xmlcode)
                return
    def get_alerts(self):
        alerts = []

        for alert in self.alerts.getElementsByTagName('entry'):
            output = {}
            #print(xml_get_first_tag_value(alert, 'id'))
            #print(self.is_old(xml_get_first_tag_value(alert, 'id')))
            print(self.has_fips(alert, '039025'))
            #print(get_full_alert(xml_get_first_tag_value(alert, 'id')))
            #alert = alert.ObAlert(get_full_alert(xml_get_first_tag_value(alert, 'id')))
            #print(xml_get_tags(alert))
        #     for tag in xml_get_tags(alert):
        #         output[tag] = xml_get_first_tag_value(alert)
        #         output.append({'tags': xml_get_tags(alert), 'values': xml_get_tags(alert)})
        # return alerts
    def is_old(self, id):
        for alert in self.known_alerts:
            if alert['id'] == id:
                return True
        return True

    def has_fips(self, element, fips):
        for geocode in element.getElementsByTagName('geocode'):
            if xml_get_first_tag_value(geocode, 'valueName') == 'SAME':
                if xml_get_first_tag_value(geocode, 'value') == str(fips):
                    return True
        return False

class ObAlert (object):
    def __init__(self, xmlcode=None, testmode=False):
        self.active = False
        self.max_plays = 0
        self.times_played = 0
        self.previously_important = False
        self.media_info = { }
        self.received_at = time.time()
        self.profile = 'CP-CA'
        self.testmode = testmode

        if xmlcode is not None:
            self.parse_cap_xml(xmlcode)

    def parse_cap_xml(self, xmlcode):
        try:
            alerts = xml.dom.minidom.parseString(xmlcode)
        except:
            obplayer.Log.log('error parsing emergency alert xml data', 'error')
            obplayer.Log.log(traceback.format_exc(), 'error')
            print(xmlcode)
            return

        for alert in alerts.getElementsByTagName('alert'):
            if xml_get_first_tag_value(alert, 'code') == 'profile:CAP-CP:0.4':
                self.profile = 'CP-CA'
            elif xml_get_first_tag_value(alert, 'code') == 'IPAWSv1.0':
                self.profile = 'IPAWS-CAP'
            else:
                self.profile = 'CP-CA'
            self.identifier = xml_get_first_tag_value(alert, 'identifier')
            self.sender = xml_get_first_tag_value(alert, 'sender')
            self.sent = xml_get_first_tag_value(alert, 'sent')
            self.codes = xml_get_tag_values(alert, 'code')
            self.status = xml_get_first_tag_value(alert, 'status', default="").lower()
            self.msgtype = xml_get_first_tag_value(alert, 'msgType', default="").lower()
            self.scope = xml_get_first_tag_value(alert, 'scope', default="").lower()
            self.references = [ ref.split(',') for ref in xml_get_first_tag_value(alert, 'references', default="").split() ]
            self.info = [ ]
            for node in xml_get_tags(alert, 'info'):
                self.info.append(ObAlertInfo(node, False))

            # # Check for indigenous broadcast settings
            if obplayer.Config.setting('alerts_broadcast_message_in_indigenous_languages'):
                for node in xml_get_tags(alert, 'info'):
                    self.info.append(ObAlertInfo(node, True))
                    break
                #self.info.append(ObAlertInfo(xml_get_tags(alert, 'info')[0], True))
            # for info in self.info:
            #     print(info.language)

            self.signatures = [ ]
            for signature in xml_get_tags(alert, 'Signature'):
                self.signatures.append(ObAlertSignature(signature))


    def print_data(self):
        print(self.identifier)
        print(self.sent + " by " + self.sender)
        print("Status: " + self.status + " Type: " + self.msgtype)

        if len(self.info) > 0:
            print(self.info[0].description)

    def get_all_info(self, language):
        infos = [ ]
        lang = self.lang_ref(language)
        if self.profile == 'CP-CA':
            for info in self.info:
                if info.language == lang:
                    infos.append(info)
            return infos
        # NWS Alerts don't include a lang code for a info block
        elif self.profile == 'IPAWS-CAP':
            for info in self.info:
                infos.append(info)
            return infos

    def get_first_info(self, language, bestmatch=True):
        lang = self.lang_ref(language)
        for info in self.info:
            if info.language == lang:
                return info
        if bestmatch and len(self.info) > 0:
            return self.info[0]
        return None

    def test(self):
        for info in self.info:
            for area in info.areas:
                print(area.has_geocode(['1', '10']))

    def has_geocode(self, codes):
        for info in self.info:
            for area in info.areas:
                if area.has_geocode(codes):
                    return True
        return False

    def add_geocode(self, code):
        for info in self.info:
            for area in info.areas:
                area.add_geocode(code)

    def is_expired(self):
        for info in self.info:
            if not info.is_expired():
                return False
        return True

    def broadcast_immediately(self):
        if self.previously_important:
            return True
        for info in self.info:
            if self.profile == 'CP-CA':
                val = info.get_parameter("layer:SOREM:1.0:Broadcast_Immediately")
                if val.lower() == "yes":
                    return True
            else:
                info = self.get_first_info("en-US")
                val = info.severity
                if val.lower() == "severe":
                    return True
        return False

    def minor_change(self):
        for info in self.info:
            val = info.get_parameter("profile:CAP-CP:0.4:MinorChange")
            if val:
                return val
        return None

    def generate_audio(self, language, voice=None, indigenous=False):
        info = self.get_first_info(language, bestmatch=False)
        #print(info.get_message_text(False))
        #print(self.get_first_info('en-CA', bestmatch=False))
        #time.sleep(20)
        if info is None:
            self.media_info[language] = None
            return False
        if indigenous == True:
            # over writting for cg scroll text and logging. TODO: shoud be indigenous text here.
            cg_message_text = self.get_first_info('english', bestmatch=True).get_message_text(False)
        if indigenous == False:
            truncate = not self.broadcast_immediately() and obplayer.Config.setting('alerts_truncate')
            message_text = info.get_message_text(truncate)

        # TODO there needs to be a better way to get the datadir
        location = obplayer.ObData.get_datadir() + "/alerts"
        filename = self.reference(self.sent, self.identifier) + "-" + language + ".wav"
        uri = obplayer.Player.file_uri(location, filename)
        if os.access(location, os.F_OK) == False:
            os.mkdir(location)
        if indigenous == False:
            resources = info.get_resources('audio')
            if resources:
                if resources[0].write_file(os.path.join(location, filename)) is False:
                    return False

            elif message_text:
                self.write_tts_file(os.path.join(location, filename), message_text, voice)
            else:
                return False
        else:
            self.write_indigenous_file(os.path.join(location, filename), self.get_first_info('indigenous', bestmatch=True).get_message_text(False, True))
            # over writting for cg scroll text and logging. TODO: shoud be indigenous text here.
            cg_message_text = self.get_first_info('english', bestmatch=True).get_message_text(False)
            uri = obplayer.Player.file_uri(location, filename)
            #print(uri)
            #time.sleep(20)

        d = GstPbutils.Discoverer()
        mediainfo = d.discover_uri(uri)

        if self.testmode:
            self.alert_type = 'Local Test Alert'
        elif self.broadcast_immediately():
            self.alert_type = 'Broadcast Intrusive Alert'
        else:
            self.alert_type = 'Advisory Alert'

        self.media_info[language] = { }
        if indigenous:
            self.media_info[language]['audio'] = {
                'media_type' : 'audio',
                'artist' : 'Emergency Alert',
                'title' : str(self.identifier),
                'overlay_text' : 'A alert is in effect.',
                'uri' : uri,
                'duration' : (mediainfo.get_duration() / float(Gst.SECOND))
            }
        else:
            self.media_info[language]['audio'] = {
                'media_type' : 'audio',
                'artist' : 'Emergency Alert',
                'title' : str(self.identifier),
                'overlay_text' : message_text,
                'uri' : uri,
                'duration' : (mediainfo.get_duration() / float(Gst.SECOND))#,
                #'alert_type': self.alert_type
            }

        # the NPAS Common Look and Feel guide states that audio content should not be more than 120 seconds
        if self.media_info[language]['audio']['duration'] > 120.0:
            self.media_info[language]['audio']['duration'] = 120.0

        resources = info.get_resources('image')
        if resources:
            filename = self.reference(self.sent, self.identifier) + "-" + language + ".jpg"
            if resources[0].write_file(os.path.join(location, filename)) is False:
                return False
            self.media_info[language]['visual'] = {
                'media_type' : 'image',
                'artist' : 'Emergency Alert',
                'title' : str(self.identifier),
                #'overlay_text' : message_text,
                'uri' : obplayer.Player.file_uri(location, filename),
                'duration' : self.media_info[language]['audio']['duration'],
                #'alert_type': self.alert_type
            }
            self.media_info[language]['audio']['overlay_text'] = None

        return True

    def get_media_info(self, primary_language, primary_voice, secondary_language, secondary_voice, indigenous=False):
        messages = []
        if primary_language not in self.media_info:
            self.generate_audio(primary_language, primary_voice)
        if secondary_language and secondary_language not in self.media_info:
            self.generate_audio(secondary_language, secondary_voice)
        if indigenous != None and indigenous not in self.media_info:
            self.generate_audio('indigenous', primary_voice, True)
        primary_info = self.media_info[primary_language] if primary_language else None
        secondary_info = self.media_info[secondary_language] if secondary_language else None
        indigenous_info = self.media_info['indigenous'] if indigenous else None

        if indigenous_info != None:
            messages.append(indigenous_info)

        if primary_info != None:
            messages.append(primary_info)
        if secondary_info != None:
            messages.append(secondary_info)
        return messages

    def pcm_audio_builder(self, tone, duration, level):
        level = math.pow(10, (float(level) / 20)) * 32767
        phase = 0 * math.pi
        samples = []
        numberOfSumples = int(round(22050 * duration))
        for i in range(numberOfSumples):
            sample = int(level * math.sin((tone * 1 * math.pi * i) / 22050 + phase ))
            samples.append(struct.pack('<h', sample))
        return b''.join(samples)

    def write_indigenous_file(self, path, message_text):
        # Add all needded indigenous messages together.
        frames = [self.pcm_audio_builder(0, 1, -12)]
        try:
            for message in message_text.split('.wav'):
                message = message.strip() + '.wav'
                if message == '.wav':
                    continue
                with wave.open(message, 'rb') as read_only_wf:
                    data = read_only_wf.readframes(read_only_wf.getnframes())
                    channels = read_only_wf.getnchannels()
                    sample_width = read_only_wf.getsampwidth()
                    # If the sample width in bytes isn't 2, convert it.
                    if sample_width != 2:
                        process = subprocess.Popen(['sox', message, '-b', '16', '/tmp/' + 'audio.wav'])
                        process.wait()
                        if process.poll() == 0:
                            with wave.open('/tmp/audio.wav', 'rb') as file:
                                data = file.readframes(file.getnframes())
                            os.remove('/tmp/audio.wav')
                        else:
                            obplayer.Log.log('sox returned a error, or a isn\'t installed.', 'error')
                            pass
                    sample_rate = read_only_wf.getframerate()
                    # Convert to 22050 hz audio if not already 22050hz.
                    if sample_rate != 22050:
                        data = audioop.ratecv(data, 2, 1, sample_rate, 22050, None)[0]

                    # Convert to mono audio if not already mono.
                    if channels != 1:
                        data = audioop.tomono(data, 2, 1, 1)[0]
                    for i in range(2):
                        frames.append(bytes(data))
                        frames.append(self.pcm_audio_builder(0, 1, -12))

            with wave.open(path, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(22050)
                wf.writeframes(b''.join(frames))
                obplayer.Log.log('Writting indigenous alert messages...', 'debug')
        except Exception as e:
            print(e)
            obplayer.Log.log(e, 'error')

    def write_tts_file(self, path, message_text, voice=None):
        if not voice:
            voice = 'en'
            #if language == 'en-CA' or language == 'fr-CA':
        message_text = message_text.rstrip('*')
        #os.system("echo \"%s\" | text2wave > %s/%s" % (message_text[0], location, filename))
        #os.system(u"espeak -v %s -s 130 -w %s/%s \"%s\"" % (voice, location, filename, message_text[0].encode('utf-8')))
        #cmd = u"espeak -v %s -s 130 -w %s/%s " % (voice, location, filename)
        #cmd += u"\"" + message_text[0] + u"\""
        if voice.startswith('aws'):
            print('voice: ' + voice)
            voice = voice.replace('aws-', '')
            polly_client = boto3.Session(
                aws_access_key_id=obplayer.Config.setting('aws_access_key_id'), aws_secret_access_key=obplayer.Config.setting('aws_secret_access_key'),
                region_name=obplayer.Config.setting('aws_region_name')).client('polly')

            try:
                response = polly_client.synthesize_speech(VoiceId=voice,
                                OutputFormat='pcm',
                                Text = "<speak><prosody volume=\"+3dB\"><break time=\"1s\" /> " + message_text + "</prosody></speak>",
                                TextType = "ssml")

                audio_data = response['AudioStream'].read()

                with wave.open(path, 'wb') as file:
                    file.setnchannels(1)
                    file.setsampwidth(2)
                    file.setframerate(16000)
                    file.setcomptype('NONE', 'NONE')
                    file.writeframes(audio_data)
            except Exception as e:
                # if aws errors use espeak
                obplayer.Log.log('AWS error such as network outage, or invaild aws ids/keys in use. error: {0}\nUsing local tts as backup audio.', 'error'.format(e))
                voice = 'en'
                proc = subprocess.Popen([ 'espeak', '-m', '-v', voice, '-s', '140', '--stdout' ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=True)
                message_text = html.escape(message_text).encode('utf-8')
                (stdout, stderr) = proc.communicate(b"...<break time=\"1s\" /> " + message_text)
                proc.wait()

                with open(path, 'wb') as f:
                    f.write(stdout)
        else:
            proc = subprocess.Popen([ 'espeak', '-m', '-v', voice, '-s', '140', '--stdout' ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=True)
            message_text = html.escape(message_text).encode('utf-8')
            (stdout, stderr) = proc.communicate(b"...<break time=\"1s\" /> " + message_text)
            proc.wait()

            with open(path, 'wb') as f:
                f.write(stdout)

    @staticmethod
    def reference(timestamp, identifier):
        reference = timestamp + "I" + identifier
        reference = reference.translate({ ord('-') : ord('_'), ord(':') : ord('_'), ord('+') : ord('p') })
        return reference

    @staticmethod
    def lang_ref(language):
        if language == 'english':
            return 'en-CA'
        elif language == 'indigenous':
            return 'en-CA'
        elif language == 'french':
            return 'fr-CA'
        elif language == 'cree':
            return 'cr-CA'
        elif language == 'inuktitut':
            return 'iu-CA'
        elif language == 'ojibwe':
            return 'oj-CA'
        elif language == 'chipewyan':
            return 'chp-CA'
        elif language == 'mikmaq':
            return 'mic-CA'
        else:
            #raise Exception("Unsupported language: " + language)
            return 'en-US'
    @staticmethod
    def lang_ref_to_language_name(language_code):
        if language_code == 'cr-CA':
            return 'cree'
        elif language_code == 'iu-CA':
            return 'inuktitut'
        elif language_code == 'oj-CA':
            return 'ojibwe'
        elif language_code == 'chp-CA':
            return 'chipewyan'
        elif language_code == 'mic-CA':
            return 'mikmaq'
        else:
            raise Exception("Unsupported language: " + language_code)

    @staticmethod
    def get_indigenous_languages_by_sgcs(sgcs):
        languages = []
        for sgc in sgcs:
            if type(sgc) != str:
                #print('SGC: {0} not string'.format(sgc))
                ObLog.log('SGC: {0} invaild'.format(sgc), 'error')
                continue
            if str(sgc).startswith("47") or str(sgc).startswith("48") or str(sgc).startswith("59") or str(sgc).startswith("61") and "Cree" not in languages:
                if "Cree" not in languages:
                    print("Cree")
                    languages.append("Cree")
            # Check for Woods Cree
            if str(sgc).startswith("46") or str(sgc).startswith("47") and "Cree" not in languages:
                if "Cree" not in languages:
                    print("Cree")
                    languages.append("Cree")
            # Check for Swampy Cree
            if str(sgc).startswith("35") or str(sgc).startswith("46") or str(sgc).startswith("47") and "Cree" not in languages:
                if "Cree" not in languages:
                    print("Cree")
                    languages.append("Cree")
            # Check for Moose Cree
            if str(sgc).startswith("35") and "Cree" not in languages:
                if "Cree" not in languages:
                    print("Cree")
                    languages.append("Cree")
            # Check for Atikamekw
            if str(sgc).startswith("24") and "Atikamekw" not in languages:
                languages.append("Atikamekw")
            #Check for Northern East Cree
            if str(sgc).startswith("24") and "Cree" not in languages:
                if "Cree" not in languages:
                    print("Cree")
                    languages.append("Cree")
            # Check for Southern East Cree
            if str(sgc).startswith("24") and "Cree" not in languages:
                if "Cree" not in languages:
                    print("Cree")
                    languages.append("Cree")
            # Check for Kawawachikamach Naskapi
            if str(sgc).startswith("24") and "Kawawachikamach-Naskapi" not in languages:
                languages.append("Kawawachikamach-Naskapi")
            # Check for Western Innu
            if str(sgc).startswith("24") and "Innu" not in languages:
                languages.append("Innu")
            # Check for Eastern Innu
            if str(sgc).startswith("24") or str(sgc).startswith("10") and "Innu" not in languages:
                languages.append("Innu")
            # Check for Inuktitut
            if str(sgc).startswith("24") or str(sgc).startswith("10") or str(sgc).startswith("46") or str(sgc).startswith("61")\
            and "Inuktitut" not in languages:
                languages.append("Inuktitut")
            # Check for Ojibwe
            if str(sgc).startswith("24") or str(sgc).startswith("35") or str(sgc).startswith("46") or str(sgc).startswith("47") or str(sgc).startswith("59")\
            and "Ojibwe" not in languages:
                languages.append("Ojibwe")
            # Check for Innu
            if str(sgc).startswith("24") or str(sgc).startswith("10") and "Innu" not in languages:
                languages.append("Innu")
            # Check for Chipewyin
            if str(sgc).startswith("47") or str(sgc).startswith("48") or str(sgc).startswith("61") or str(sgc).startswith("46")\
            and "Chipewyin" not in languages:
                languages.append("Chipewyin")
            # Check for Mikmaq
            if str(sgc).startswith("12") or str(sgc).startswith("13") or str(sgc).startswith("11") or str(sgc).startswith("10")\
            and "Mikmaq" not in languages:
                languages.append("Mikmaq")
        return languages

class ObAlertInfo (object):
    def __init__(self, element, indigenous_mode=False):
        self.indigenous_mode = indigenous_mode
        self.parse_info(element)

    def parse_info(self, info):
        if self.indigenous_mode:
            self.language = 'indigenous'
        else:
            self.language = xml_get_first_tag_value(info, 'language', 'en-US')
        self.event = xml_get_first_tag_value(info, 'event')
        self.urgency = xml_get_first_tag_value(info, 'urgency')
        self.severity = xml_get_first_tag_value(info, 'severity')
        self.certainty = xml_get_first_tag_value(info, 'certainty')

        self.effective = xml_get_first_tag_value(info, 'effective')
        self.onset = xml_get_first_tag_value(info, 'onset')
        self.expires = xml_get_first_tag_value(info, 'expires')

        self.categories = xml_get_tag_values(info, 'category')
        self.responsetypes = xml_get_tag_values(info, 'responseType')

        self.sender = xml_get_first_tag_value(info, 'senderName')
        self.headline = xml_get_first_tag_value(info, 'headline')
        self.description = xml_get_first_tag_value(info, 'description')
        self.instruction = xml_get_first_tag_value(info, 'instruction')

        self.parameters = [ ]
        for parameter in xml_get_tags(info, 'parameter'):
            name = xml_get_first_tag_value(parameter, 'valueName')
            val = xml_get_first_tag_value(parameter, 'value')
            if val is not None:
                self.parameters.append([ name, val ])

        self.eventcodes = [ ]
        for eventcode in xml_get_tags(info, 'eventCode'):
            name = xml_get_first_tag_value(eventcode, 'valueName')
            code = xml_get_first_tag_value(eventcode, 'value')
            if code is not None:
                self.eventcodes.append([ name, code ])

        self.areas = [ ]
        for node in xml_get_tags(info, 'area'):
            self.areas.append(ObAlertArea(node))
        for area in self.areas:
            print(area.get_sgcs())
        self.resources = [ ]
        for node in xml_get_tags(info, 'resource'):
            self.resources.append(ObAlertResource(node))

    def is_expired(self):
        if self.expires:
            current = datetime.datetime.now(dateutil.tz.tzlocal())
            expires = dateutil.parser.parse(self.expires)
            if current > expires:
                return True
        return False

    def get_parameter(self, name):
        for param in self.parameters:
            if param[0] == name:
                return param[1]
        return None

    def get_resources(self, typename=None):
        return [ resource for resource in self.resources if not typename or typename in resource.mimetype ]

    def get_message_text(self, truncate=False, indigenous=False):
        if indigenous: self.language = 'indigenous'
        text = self.get_parameter("layer:SOREM:1.0:Broadcast_Text")
        if not text or self.language == 'indigenous':
            #text = self.description if self.description else self.headline
            # CLF Guide 1.2: Appendix D, Section 2.2
            sender = ' ' + self.sender if self.sender else ''
            areadesc = ' ' + ', '.join([ area.description for area in self.areas ])
            #geocodes = [area.geocodes for area in self.areas]
            # for sgc_group in sgcs:
            #     #print(sgc_group)
            #     for sgc in sgc_group:
            output_geocodes = []
            # for geocode_group in geocodes:
            #     for geocode in geocode_group:
            #         #print(geocode[0])
            #         if geocode[0] == 'FIPS6' or geocode[0] == 'SAME' or geocode[0] == 'profile:CAP-CP:Location:0.3':
            #             #print(geocode[1])
            #             output_geocodes.append(geocode[1])
            for area in self.areas:
                output_geocodes = area.get_sgcs() + output_geocodes
            output_geocodes = list(dict.fromkeys(output_geocodes))
            #print(type(output_geocodes))
            #time.sleep(20)
            description = '. ' + self.description if self.description else ''
            instruction = '. ' + self.instruction if self.instruction else ''
            event = ' ' + self.event if self.event else ''
            if self.event == "test":
               event = 'Test Alert'
            if self.language == 'fr-CA':
                text = 'Alerte' + sender + ' - ' + 'Alerte ' + event + areadesc +  instruction
            elif self.language == 'indigenous':
                self.indigenous = ObAlert.get_indigenous_languages_by_sgcs(output_geocodes)
                #print(self.indigenous)
                message_text = ""
                self.indigenous_languages_enabled = obplayer.Config.setting('alerts_selected_indigenous_languages').split(',')
                for indigenous in self.indigenous:
                    # check if language is enabled.
                    if ObAlert.lang_ref(indigenous.lower()) in self.indigenous_languages_enabled:
                        print('lang_ref:', ObAlert.lang_ref(indigenous))
                        # Check to make sure file exists.
                        if os.path.isfile("{0}/indigenous/{1}/{2}.wav".format(obplayer.Config.datadir, indigenous.lower(), self.event.lower())):
                            message_text += '{0}/indigenous/{1}/{2}.wav\n'.format(obplayer.Config.datadir, indigenous.lower(), self.event.lower())
                text = message_text
                print(message_text)
            else:
               text = 'Message From' + sender + '. ' + event + ' For ' + areadesc + description + instruction
        # Always must be indigenous alert audio
        if self.language == 'indigenous':
            self.indigenous = ObAlert.get_indigenous_languages_by_sgcs(output_geocodes)
            message_text = ""
            self.indigenous_languages_enabled = obplayer.Config.setting('alerts_selected_indigenous_languages').split(',')
            for indigenous_language in self.indigenous:
                if ObAlert.lang_ref(indigenous_language.lower()) in self.indigenous_languages_enabled:
                    message_text += '{0}/indigenous/{1}/{2}.wav\n'.format(obplayer.Config.datadir, indigenous_language.lower(), self.event.lower())
            text = message_text
        if self.language != 'indigenous':
            if sys.version.startswith('3'):
                import html
                text = html.unescape(text)
            else:
                text = text.replace('&apos;', "\'").replace('&quot;', '\"').replace('&amp;', '&').replace('&gt;', '>').replace('&lt;', '<').replace('&#xA;', '\n')

            if truncate:
                parts = text.split('\n\n', 1)
                text = parts[0] + ('***' if len(parts) > 1 else '')

        text = text.replace('\n', ' ').replace('\r', '')
        return text


class ObAlertArea (object):
    def __init__(self, element):
        self.parse_area(element)

    def get_sgcs(self, type=None):
        output = []
        if self.geocodes != None:
            for geocode in self.geocodes:
                if geocode[0] == 'SAME' or geocode[0] == 'FIPS6' or geocode[0] == 'profile:CAP-CP:Location:0.3':
                    output.append(geocode[1])
            return output
        else:
            return None

    def parse_area(self, area):
        self.description = xml_get_first_tag_value(area, 'areaDesc')
        self.altitude = xml_get_first_tag_value(area, 'altitude')
        self.ceiling = xml_get_first_tag_value(area, 'ceiling')

        self.polygons = xml_get_tag_values(area, 'polygon')
        self.circles = xml_get_tag_values(area, 'circle')

        self.geocodes = [ ]
        for geocode in xml_get_tags(area, 'geocode'):
            name = xml_get_first_tag_value(geocode, 'valueName')
            code = xml_get_first_tag_value(geocode, 'value')
            if code is not None:
                self.geocodes.append([ name, code ])

    def has_geocode(self, codes):
        for geocode in self.geocodes:
            for code in codes:
                # TODO this is a bit of a hack
                if obplayer.Config.setting('alerts_location_type') == 'US':
                    if geocode[0] == 'SAME' or geocode[0] == 'FIPS6' and geocode[1] == code:
                        return True
                elif obplayer.Config.setting('alerts_location_type') == 'CA':
                    if geocode[0] == 'profile:CAP-CP:Location:0.3' and (geocode[1].startswith(code) or code.startswith(geocode[1])):
                        return True
        return False

    def add_geocode(self, code):
        if obplayer.Config.setting('alerts_location_type') == 'US':
            self.geocodes.append([ 'SAME', code ])
        elif obplayer.Config.setting('alerts_location_type') == 'CA':
            self.geocodes.append([ 'profile:CAP-CP:Location:0.3', code ])


class ObAlertResource (object):
    def __init__(self, element):
        self.parse_resource(element)

    def parse_resource(self, resource):
        self.description = xml_get_first_tag_value(resource, 'resourceDesc')
        self.mimetype = xml_get_first_tag_value(resource, 'mimeType')

        self.size = xml_get_first_tag_value(resource, 'size')
        self.uri = xml_get_first_tag_value(resource, 'uri')

        self.data = None
        derefuri = xml_get_first_tag_value(resource, 'derefUri')
        if derefuri is not None:
            digest = xml_get_first_tag_value(resource, 'digest')
            calculated_digest = hashlib.sha1(derefuri.encode('utf-8')).hexdigest()
            if digest != calculated_digest:
                obplayer.Log.log("emergency alert resource corrupted: " + str(self.uri), 'error')
            else:
                try:
                    self.data = base64.b64decode(derefuri)
                except:
                    obplayer.Log.log("error parsing base64 resource from emergency alert", 'error')

        elif self.uri is not None:
            try:
                obplayer.Log.log("fetching alert resource %s" % (self.uri,), 'alerts')
                r = requests.get(self.uri)

                if r.status_code == requests.codes.ok:
                    self.data = r.content
                else:
                    obplayer.Log.log("error fetching alert resource %s: returned status code %s" % (self.uri, r.status_code), 'alerts')
            #except requests.exceptions.RequestException:
            except:
                obplayer.Log.log("connection error while fetching alert resource %s" % (self.uri,), 'alerts')

    def write_file(self, filename):
        if not self.data:
            return False
        with open(filename, 'wb') as f:
            f.write(self.data)


class ObAlertSignature (object):
    def __init__(self, element):
        self.parse_signature(element)

    def parse_signature(self, signature):
        self.signed_info = xml_get_first_tag_value(signature, 'SignedInfo')
        # TODO finish this, although it's not clear from the cap specs if you're suppose to reject a message that isn't verified or signed



def parse_alert_file(xmlfile):
    with open(xmlfile, 'rb') as f:
        alert = ObAlert(f.read())
    return alert
