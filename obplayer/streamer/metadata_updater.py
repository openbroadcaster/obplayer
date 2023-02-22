import requests
from requests.auth import HTTPBasicAuth
import time
import obplayer
import urllib.parse
# NOTE: The threading module is being used due a issue with the obplayer threading system
# not being able to handle a threat thats not running.
import threading

class MetadataUpdater(threading.Thread):
    def __init__(self, protocol='http', host=None, port='8000', username='source', password='', mount=None):
        threading.Thread.__init__(self)
        self._protocol = protocol
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._mount = mount
        self._last_track = None
        self.running = True

    # Sends the current track info to icecast.

    def _post_metadata_update(self, current_track):
        url = 'http://{0}:{1}/admin/metadata?mode=updinfo&mount=/{2}&song={3}'.format(self._host, self._port, self._mount, urllib.parse.quote(current_track))
        req = requests.get(url, auth=(self._username, self._password))
        if req.status_code == 200:
            return True
        else:
            return False

    # Gets the current track playing now, and returns it.
    def _get_currently_playing(self):
        try:
            requests = obplayer.Player.get_requests()
            select_keys = ['artist', 'title']
            artist = requests['audio']['artist']
            title = requests['audio']['title']
            return artist + ' - ' + title
        except Exception as e:
            # handle catching a time while nothing is playing.
            return self._last_track

    def run(self):
        # sleep for 4 seconds to make sure the stream was on the
        # server before handling the first update request.
        time.sleep(4)
        while self.running:
            new_track = self._get_currently_playing()
            if new_track != None:
                if new_track != self._last_track:
                    self._last_track = new_track
                    if self._post_metadata_update(self._last_track) == False:
                        obplayer.Log.log('The request to update the now playing track fai\'ld! This mostly likly means your password for your stream is wrong, or that your server is having issues.', 'error')
                    else:
                        obplayer.Log.log('"{0}" has been sent to icecast via title streaming.'.format(self._last_track), 'debug')
            time.sleep(4)

    def stop(self):
        obplayer.ObThread.stop(self)
        self.running = False
