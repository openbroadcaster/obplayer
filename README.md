# OpenBroadcaster Player

## Project Overview

OpenBroadcaster Player (OBPlayer) is an open-source media playback and broadcasting tool for radio stations and media professionals. It works with OBServer to play scheduled media but can also function as a standalone or network-controlled player. Designed for continuous broadcasting, OBPlayer syncs with OBServer to update schedules, media, and priority broadcasts. If the schedule has gaps, it plays a default playlist. If that fails, it switches to Fallback Media Mode, then to analog input bypass, and finally to a test signal as a last resort. OBPlayer always prioritizes valid Common Alerting Protocol (CAP) messages.

## Key Features
- Multi-format media playback (audio, video, images)
- Live assist web interface
- Support for multiple streaming protocols
- Configurable outputs
- Remote override capabilities
- Integrated logging and monitoring
- Automatic fallback mechanisms
- Emergency alert (CAP) prioritization

## Supported Configurations
- Headless OBPlayer (CLI process)
- GTK Desktop application

## Dependencies

### Core Dependencies
- Python 3.7+
- GStreamer 1.0+
- GTK 3.x
- inotify
- requests
- gi (GObject Introspection)
- FFmpeg


## Installation
OBPlayer is designed to run on Linux Ubuntu 24.04. Installation scripts and containerized versions are available:
- [Reference Installer](https://github.com/pikaspace/openbroadcaster-reference-installer/blob/main/ubuntu-noble-obplayer.sh)
- [Containerized Version](https://github.com/btelliot/openbroadcaster-containers)

## Core Modules

### `Scheduler/` 
- Manages media scheduling and playlists
- Handles show timing, transitions, and priority content
- Fallback content management

### `Player/` 
- GStreamer-based media playback engine
- Supports audio/video pipelines, transitions, and multiple outputs
- Includes playback logging and error recovery

### `HTTPAdmin/`
- Web dashboard for managing and monitoring the player
- Provides secure configuration, alert management, and playback control

### `LiveAssist/` 
- Web-based control interface for real-time playback and microphone input
- Playlist management and playback control

### `Streamer/` 
- Handles output streaming with protocols like Icecast and RTMP
- Manages stream encoding and network connectivity


## Priority System

1. **Highest Priority**
   - Emergency alerts (CAP)
   - Station override signals
   - Live assist input

2. **Normal Priority**
   - Scheduled content
   - Regular playlists
   - Advertisements

3. **Fallback Priority**
   - Default playlist
   - Fallback media
   - Test signal

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

OpenBroadcaster Player is released under the GNU Affero General Public License v3.0.

## Support

- GitHub Issues: https://github.com/openbroadcaster/obplayer/issues
- Support Website: https://support.openbroadcaster.com/