---
layout: default
title: index
---

* TOC
{:toc}


## About OBPlayer
{:toc}

OBPlayer is a stable and secure UNIX-based media streaming playout application that can operate standalone or controlled over an IP network by a managing OBServer instance. It can be installed remotely at a transmitter site, in the studio or as a virtual headless process with an OBServer on same machine. A standalone Emergency Alerting CAP Player supporting audio, image and video.

+ Partial Support For IPAWS CAP Profile Version 1.0

## CLI Operation

cd /usr/share/obplayer/

bash obplayer_check

Do not run as sudo or root

optional arguments:

  -h, --help            show this help message and exit
  
  -f, --fullscreen      start fullscreen (default: False)
  
  -m, --minimize        start minimized (default: False)
  
  -r, --reset           reset show, media, and priority broadcast databases (default: False)
  
  -H, --headless        run headless (audio only) (default: False)
  
  -d, --debug           print log messages to stdout (default: False)
  
  -c  --configdir       CONFIGDIR specifies an alternate data directory (default: ['~/.openbroadcaster'])
  
  --disable-http        disables the http admin (default: False)
  
  --http-port           sets the port number used for the http server. (default=None)

## Debian Installs

Start:    sudo service obplayer start

Stop:     sudo service obplayer stop

Restart:  sudo service obplayer restart

OpenBroadcaster Player
https://openbroadcaster.com/

Copyright 2012-2020 OpenBroadcaster, Inc.

Licensed under GNU AGPLv3. See COPYING.
