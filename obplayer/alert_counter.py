import obplayer
import pickle
import os

"""
Copyright 2012-2022 OpenBroadcaster, Inc.

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

class Alert_Counter(object):
    def __init__(self):
        self.datadir = obplayer.ObData.get_datadir()
        self.data_file = self.datadir + '/.alerts'
        self.alerts = {'local_tests': [], 'advisorys': [], 'broadcast_intrusive': []}

        #load data from last use.
        if os.access(self.data_file, os.F_OK):
            with open(self.data_file, 'rb') as file:
                self.alerts = pickle.load(file)


    def add_alert(self, alert_id, alert_type):
        if self.is_already_logged(alert_id):
            obplayer.Log.log("alert already logged: {0}.".format(alert_id), 'alert counter')
        else:
            if alert_type == 'Local Test Alert':
                self.alerts['local_tests'].append(alert_id)
            elif alert_type == 'Advisory Alert':
                self.alerts['advisorys'].append(alert_id)
            elif alert_type == 'Broadcast Intrusive Alert':
                self.alerts['broadcast_intrusive'].append(alert_id)
            else:
                obplayer.Log.log("couldn't log alert: {0} with type {1}!".format(alert_id, alert_type), 'alerts')
        self.save_data()

    def is_already_logged(self, alert_id):
        alert_types = ['local_tests', 'advisorys', 'broadcast_intrusive']
        for alert_type in alert_types:
            for alert in self.alerts[alert_type]:
                if alert_id == alert:
                    return True
        return False

    def get_number_of_alerts(self, alert_type):
        if alert_type == 'local_test':
            return len(self.alerts['local_tests'])
        elif alert_type == 'advisory':
            return len(self.alerts['advisorys'])
        elif alert_type == 'broadcast_intrusive':
            return len(self.alerts['broadcast_intrusive'])
        else:
            return None

    def save_data(self):
        data = pickle.dumps(self.alerts)
        #print(data)
        with open(self.data_file, 'wb') as file:
            file.write(data)
