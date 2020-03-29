import obplayer
import inotify.adapters
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstPbutils', '1.0')
from gi.repository import GObject, Gst, GstPbutils
import os
import time

class Override_Thread(obplayer.ObThread):
    def __init__(self):
        obplayer.ObThread.__init__(self, 'ObNewsFeedAudioOverride')
        self.daemon = True
        self.running = False
        self.i = inotify.adapters.Inotify()
        self.watch_folder = obplayer.Config.datadir + '/news_feed_override'
        self.i.add_watch(self.watch_folder)
        self.ctrl = obplayer.Player.create_controller('news_feed_override', priority=98, allow_requeue=False)

    def run(self):
        self.running = True
        # remove any files in the watch folder on startup.
        for file in os.listdir(self.watch_folder):
            file_path = self.watch_folder + '/' + file
            os.remove(file_path)

        while self.running:
            for event in self.i.event_gen(yield_nones=False):
                (_, type_names, path, filename) = event
                if not 'IN_CLOSE_WRITE' in event[1]:
                    continue
                else:
                    uri = obplayer.Player.file_uri(path, filename)
                    d = GstPbutils.Discoverer()
                    mediainfo = d.discover_uri(uri)
                    duration = mediainfo.get_duration() / float(Gst.SECOND)
                    obplayer.Log.log("playing news feed media file: {0}".format(filename), 'newsfeed_override')
                    self.ctrl.add_request(media_type='audio', uri=uri, duration=duration)
                    time.sleep(duration)
                    obplayer.Log.log("removing news feed media file: {0}".format(filename), 'newsfeed_override')
                    try:
                        os.remove(path + '/' + filename)
                    except Exception as e:
                        obplayer.Log.log("an exception occurred while removing news feed media file: {0}".format(filename), 'newsfeed_override')


    def quit(self):
        self.running = False
