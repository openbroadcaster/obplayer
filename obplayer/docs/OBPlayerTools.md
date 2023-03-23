# OBPlayer Tools

## CLI Options

Bash script "obplayer_check" starts the player and checks for existing instances and not start if already running

Bash script "obplayer_loop" runs in an infinite loop to restart in case it unexpectedly terminates (crashes) or is shutdown via the web dashboard

obplayer -d prints log messages to console

obplayer -f or obplayer--fullscreen on startup. (obplayer_loop -f also works)

obplayer -h help (displays command-line options)

obplayer -H starts headless, no desktop GUI

obplayer -m starts screen minimized

obplayer -r restarts fresh, clearing out Playlist\Schedule\Media cache 

obplayer -c CONFIGDIR, –configdir Specifies an alternate data directory (default: [’~/.openbroadcaster’])

obplayer – disable-updater Disables the OS updater

obplayer – disable-http Disables the http admin dashboard

## Trigger FallBack Media

To get fallback media to play by causing simulated network problems, remove the default playlist, disable Scheduler.

1. start obplayer application with "./obplayer -r"

2. immediately quit before it has a chance to sync

3. start obplayer again but this time with just "./obplayer"

## Test video playback via gstreamer

~~~~
gst-launch-1.0 playbin2 uri="file:///absolute/path/to/file"
~~~~
