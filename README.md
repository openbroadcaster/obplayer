#  OpenBroadcaster Multimedia Playout

## Overview 

OBPlayer is a stable and secure UNIX-based media streaming playout application that can operate as a standalone player or controlled over a network by a managing OBServer. It can be installed remotely at a transmitter site, in the studio or as multiple virtual headless processes. OBPlayer is built with rules based intelligence to continue broadcasting no matter what happens. It functions by continually syncing with OBServer, looking for updated schedules, media, and priority broadcasts. If there is a blank spot in the schedule, it falls back to a Default Playlist. If that fails, it goes into Fallback Media Mode. If that fails, it plays from the analog input bypass. Finally, it will play a test signal as a last resort. OBPlayer will always play valid CAP (Common Alerting Protocol) Alerts at the highest priority.

OBPlayer can be run in a variety of configurations:

+ Headless OBPlayer (CLI Process)
+ LIVE Assist with Mobile HTML5 Touch Screen interface
+ GTK desktop application for a Digital Display and output to CATV
+ Standalone Emergency Alerting CAP Player supporting audio, image and video
+ Support For IPAWS CAP Profile Version 1.0 via [Alert-Hub](https://www.alert-hub.org/)

## Installation

To install OBPlayer, you should have a basic understanding of the Linux shell terminal. Once installed, every aspect of your station is managed via OBPlayer's web interface.

Follow our [Install instructions](https://github.com/openbroadcaster/obplayer/blob/main/install.txt) and Post Installation [Troubleshooting guide](https://support.openbroadcaster.com/troubleshooting#post-installation-obplayer-troubleshooting) for instructions on how to setup on your own hardware.

## Support

If you need help with OpenBroadcaster, the first place you should visit is our [Support](https://support.openbroadcaster.com/) page, which features solutions to a number of commonly encountered issues and questions.

## FAQ

Users have sent us [Frequently Asked Questions](https://openbroadcaster.com/knowledge/frequently-asked-questions) and asked common technical questions.

## Documentation

Documentation and user guides can be found in the project's [Support](https://support.openbroadcaster.com) website: 

## Change Log

Visit our [Change Log](https://openbroadcaster.com/resource/change-log) and project history.

## API Access

All of the functionality and metadata in OBServer, (Media, Playlists,Scheduling) is available through our [Documented API](https://docs.openbroadcaster.com/)

## New feature requests

You can visit our GitHub [Issues](https://github.com/openbroadcaster/obplayer/issues) pages to submit a new feature request or comment on existing projects.

## Bug and error reports

We rely exclusively on our GitHub [Issues](https://github.com/openbroadcaster/obplayer/issues) to diagnose, track and update these reports. First, check to make sure the issue you're experiencing isn't already reported. If it is, you can subscribe to the existing ticket for updates on the issue's progress. If your issue or request isn't already reported, click the "New Issue" button to create it. Make sure to follow the template provided, as it asks important details that are very important to our team.

## Contributing

Contributions are more than welcome! You can help us improve OpenBroadcaster by either contributing to the core OBServer or OBPlayer, creating a new module or extending language translations and self help guides. 

Any help is welcome, big or small. We are all learning together.

See our [Contributing Guide](https://github.com/openbroadcaster/.github/blob/main/docs/CONTRIBUTING.md) to learn how to get involved.

Please check out the various GIT projects and components on [OpenBroadcaster](https://github.com/openbroadcaster)

## Releases and Versioning

See our [Releases Guide](https://github.com/openbroadcaster/.github/blob/main/docs/RELEASES.md) 

## Code of Conduct

We abide by our [Code of Conduct](https://github.com/openbroadcaster/.github/blob/main/docs/CODE_OF_CONDUCT.md) and feel strongly about open, appreciative, and empathetic people joining us. 

## Support OpenBroadcaster

OpenBroadcaster will always be available free of charge. OpenBroadcaster is built and maintained by passionate volunteers and broadcasters, so there may be some delays in getting back to you. We make the best effort possible to resolve issues and answer questions. If you find the software support the project. Your support is greatly appreciated.

Copyright 2012-2024 OpenBroadcaster Inc.

Licensed under GNU AGPLv3.  See COPYING.
