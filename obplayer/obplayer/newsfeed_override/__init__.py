import obplayer
from .override import *

def init():
    obplayer.newsfeed_override = Override_Thread()
    obplayer.newsfeed_override.start()

def quit():
    obplayer.newsfeed_override.stop()
