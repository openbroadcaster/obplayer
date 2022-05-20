---
layout: default
title: index
---

* TOC
{:toc}


## About the Player
{:toc}

OBPlayer is a stable and secure UNIX-based media streaming playout application that can operate as a standalone player or controlled over a network by a managing OBServer instance. It can be installed remotely at a transmitter site, in the studio or as a virtual headless process on a server.

OBPlayer is built with rules based intelligence to continue broadcasting no matter what happens. It functions by continually syncing with OBServer, looking for updated schedules, media, and priority broadcasts. If there is a blank spot in the schedule, it falls back to a Default Playlist. If that fails, it goes into Fallback Media Mode. If that fails, it plays from the analog input bypass. Finally, it will play a test signal as a last resort.

OBPlayer will always play valid CAP (Common Alerting Protocol) Alerts at the highest priority.

OBPlayer can be run in a variety of configurations:

+ Headless OBPlayer (Virtual Process)
+ LIVE Assist with Mobile HTML5 Touch Screen interface
+ GTK desktop application for a Digital Video Screen.
+ Standalone Emergency Alerting CAP Player supporting audio, image and video
+ Coming Soon Support For IPAWS CAP Profile Version 1.0

OpenBroadcaster Player
http://www.openbroadcaster.com/

Copyright 2012-2018 OpenBroadcaster, Inc.

Licensed under GNU AGPLv3. See COPYING.
