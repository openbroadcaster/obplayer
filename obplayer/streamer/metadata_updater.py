import requests
from requests.auth import HTTPBasicAuth
import time
import obplayer
import urllib.parse
import json
import copy

# NOTE: The threading module is being used due a issue with the obplayer threading system
# not being able to handle a threat thats not running.
import threading


class MetadataUpdater(threading.Thread):
    def __init__(
        self,
        protocol="http",
        host=None,
        port="8000",
        username="source",
        password="",
        mount=None,
        mode="basic",
    ):
        threading.Thread.__init__(self)
        self._protocol = protocol
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._mount = mount
        self._json = mode == "json"
        self._last_track = None
        self.running = True

    # Sends the current track info to icecast.

    def _post_metadata_update(self, current_track):
        url = "http://{0}:{1}/admin/metadata?mode=updinfo&mount=/{2}&song={3}".format(
            self._host, self._port, self._mount, urllib.parse.quote(current_track)
        )
        req = requests.get(url, auth=(self._username, self._password))
        if req.status_code == 200:
            return True
        else:
            return False

    # Gets the current track playing now, and returns it.
    def _get_currently_playing(self):
        try:
            requests = obplayer.Player.get_requests()
            # create a new dict "track"
            track = {}

            # add the artist, title, and media_id to the dict
            track["mediaId"] = requests["audio"]["media_id"]
            track["artist"] = requests["audio"]["artist"]
            track["title"] = requests["audio"]["title"]
            track["duration"] = requests["audio"]["duration"]
            track["startTime"] = requests["audio"]["start_time"]

            # return track in json format
            return track
        except Exception as e:
            # handle catching a time while nothing is playing.
            return self._last_track

    def run(self):
        # sleep for 4 seconds to make sure the stream was on the
        # server before handling the first update request.
        time.sleep(4)
        sleep_time = time.time()
        while self.running:
            new_track = self._get_currently_playing()
            if new_track != None:
                # update if outputting json and it's been more than 3s since last update, or if the track has changed.
                if (
                    (self._json and time.time() - sleep_time >= 3)
                    or self._last_track is None
                    or new_track != self._last_track
                ):

                    # update values for next time
                    sleep_time = time.time()

                    # copy the new track to the last track (copy needed to avoid reference)
                    self._last_track = new_track.copy()

                    # handle output in json string format
                    if self._json:
                        # use start time to generate current play time position, then delete start time from dict.
                        new_track["time"] = round(
                            time.time() - new_track["startTime"], 2
                        )
                        stream_title = json.dumps(new_track)

                    # handle output in "artist - title" format
                    else:
                        stream_title = "{0} - {1}".format(
                            new_track["artist"], new_track["title"]
                        )

                    # send the request to update the now playing track
                    if self._post_metadata_update(stream_title) == False:
                        obplayer.Log.log(
                            "The request to update the now playing track failed! This most likely means your password for your stream is wrong, or that your server is having issues.",
                            "error",
                        )
                    else:
                        obplayer.Log.log(
                            '"{0}" has been sent to icecast via title streaming.'.format(
                                stream_title
                            ),
                            "debug",
                        )

            # frequent polling to catch track changes quickly
            time.sleep(0.25)

    def stop(self):
        obplayer.ObThread.stop(self)
        self.running = False
