import os
import obplayer

class TranslateSystem(object):
    def __init__(self):
        self.lang = 'default'
        self.strings = self._read_in_strings()

    def _read_in_strings(self):
        strings = { '': { } }

        self.load_strings('default', strings)
        self.load_strings(obplayer.Config.setting('http_admin_language'), strings)

        return strings

    def load_strings(self, lang, strings):
        namespace = ''
        for (dirname, dirnames, filenames) in os.walk(os.path.join('obplayer/translate/strings', lang)):
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

    def t(self, namespace, element):
        try:
            return self.strings[namespace][element]
        except KeyError:
            return element