import obplayer
import time
import inotify.adapters
import requests
import json
import base64

class LogUploader(obplayer.ObThread):
    def __init__(self):
        obplayer.ObThread.__init__(self, "Log Uploader")
        self.daemon = True
        self.running = True

    def upload_file(self, file_path):
        session = requests.session()
        #login_data = json.dumps({'username': obplayer.Config.setting('audiolog_upload_user', True), 'password': obplayer.Config.setting('audiolog_upload_password', True)})
        server_url = obplayer.Config.setting('sync_url', True).replace('remote.php', '')
        # This means we are logged in.
        with open(file_path, 'rb') as file:
            req = session.post('{0}/upload.php'.format(server_url), data=file)
            if req.status_code == 200:
                # The file uploaded to the server.
                # It still needs things a like title though.
                data = req.json()
                #print(data)
                if data['media_supported'] == False:
                    obplayer.Log.log("Audio log uploaded failed due to a media not supported error. Please enable ogg support in the server.", 'audiolog')
                    return None
                log_date = time.strftime("%c", time.localtime())
                metadata = {"media": [{"local_id":"2", "artist": "OBPlayer logs", "title": "Station Audio Log ({0} Local)".format(log_date), "album":"Station audio log", "year": time.strftime("%Y", time.localtime()), "country_id":"231","category_id":"10","language_id":"54","genre_id":"999","comments":"","is_copyright_owner":"0","is_approved":"1","status":"public","dynamic_select":"0","file_id": data['file_id'],"file_key": data['file_key'],"advanced_permissions_users":[],"advanced_permissions_groups":[]}]}
                file_data = json.dumps(metadata)
                req = session.post('{0}/api.php'.format(server_url), data={'appkey':obplayer.Config.setting('audiolog_upload_appkey', True), 'c':'media', 'a': 'save', 'd': file_data})
                if req.status_code == 200:
                    obplayer.Log.log("Audio log uploaded at {0}".format(log_date), 'audiolog')
                else:
                   obplayer.Log.log("Got status code {0} from api call for server media save.".format(req.status_code), 'audiolog')
            else:
                obplayer.Log.log("Got status code {0} from api call for server media upload.".format(req.status_code), 'audiolog')

    def run(self):
        i = inotify.adapters.Inotify()

        i.add_watch(obplayer.Config.datadir + '/audiologs')
        while self.running:
            for event in i.event_gen(yield_nones=False):
                (_, type_names, path, filename) = event

                if type_names[0] == 'IN_CLOSE_WRITE':
                    print("PATH=[{}] FILENAME=[{}] EVENT_TYPES={}".format(
                        path, filename, type_names))
                    self.upload_file(path + '/' + filename)

    def stop(self):
        self.running = False
