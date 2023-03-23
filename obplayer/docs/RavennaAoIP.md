# Audio over IP 

Livewire, RTP and Ravenna are Aoip (Audio over IP) formats based heavily on existing internet standards. AES67 is an amalgamation of different Aoip standards intended as a common denominator to allow interoperability between dissimilar devices from various manufactures to support different parts of it. The protocols involved are:

1) RTP (Real Time Protocol)

2) SDP (Session Description Protocol)

3) RTSP & SIP (Real Time Streaming Protocol & Session Initiation Protocol)

4) mDNS-SD / Zeroconf (Service Discovery)

1) RTP sends the actual audio data over the network. It's a binary format on top of UDP. These Aoiop standards use multicast to send the data, which is a form of broadcasting packets on a network. It uses PTP protocol to synchronize all the streams rather than having a separate sync connection. PTP (Precision Time Protocol) is similar to NTP, but is much more accurate. The ptpd package is available on most linux computers. To achieve the low latencies needed for broadcasting, each RTP packet contains only 1ms of audio, which means *tons* of packets. This can be too many packets for some routers, including the WRT54G2 we have been testing with, so that must be kept in mind when specifying equipment.

2) In order to set up an RTP stream, you need to know the parameters to use: what encoding format, sample rate, channels, what UDP port to listen on, etc. That's where SDP comes in. SDP is not a network protocol but just a particularly formatted block of text, like:

v=0

a=clock-domain:PTPv2 0

a=type:multicast

m=audio 5004 RTP/AVP 96

c=IN IP4 239.192.0.102/0

a=rtpmap:96 L24/48000/2

3) There needs to be a way to pass the SDP block from one computer to another. Livewire and Ravenna use RTSP, while AES67 uses SIP (but also allows RTSP?). Both protocols are similar to HTTP and neither actually sends or receives audio data. SIP is more commonly used in the telephony/VoIP industry. Gstreamer has an RTSP client and an RTSP server, but nothing for SIP.

The convention is that the device sending audio out creates an RTSP server, and devices receiving audio in will connect to an RTSP server as a client to fetch the appropriate SDP.

Connect Axia xNode using the RTSP client in gstreamer to another element which reads in an SDP file and sets up the RTP pipeline. Added a new media type to obplayer to play SDP files which is able to connect to and play the xNode's audio.

A separate RTSP server (now part of obplayer) can be configured with Livewire xNode devices to connect. Sends audio from the OBPlayer to the Livewire xNode devices and out of the physical analog output on the device. Integrated this RTSP server into obplayer. It is similar to the icecast streamer, where a separate Pulse audio input reads the data which gets sent out (to allow other microphones and audio sources to be mixed in before sending)

4) In order to get the Livewire xNode devices to connect to our RTSP server, it has to be told the url to access to be able to detect RTSP servers on the network. That's were mDNS-SD comes in. It is also known as Zeroconf, or Bonjour on Apple devices. It's similar to DNS, but it works on a local network and does not need a central DNS server.

The avahi suite of software, which is installed by default on many linux computers, provides this service. It runs in the background responding to queries. OBPlayer “advertises” our RTSP server on the network. Livewire xNode devices have a window that opens listing all the audio devices on the network that it can detect. Under the Output tab, our RTSP output is listed and selectable. 

## Configuring Player for Ravenna 

Development code has split the audio/visualization tab into a '''Sources Tab''' and an '''Outputs Tab'''.  On the Sources tab, you'll notice two new sections for AoIP input (RTSP or SDP) and RTP input.

These have been implemented similarly to the linein module.  Each has a priority, such that the highest enable priority item will play. For the 'pass through' alerting box setup, we normally disable the scheduler and fallback player, and the next highest priority source (the line in) would play instead.  The AoIP source has a priority of 20, the RTP source has a priority of 15, and the line in source has a priority of 10.  So if they were all enabled, the AoIP source would attempt to play first, followed by the RTP, and then followed by the line in.

AoIP accepts a URI of type '''rtsp://server:port/target''' or '''sdp:///path/to/sdp/file'''.  The RTSP client used here is the default gstreamer one, which I was not able to get working with the xNode, so I don't suspect the RTSP option will work yet.  It should however be possible to use an SDP file.  I've included an example in tools/livewire-example.sdp which receives audio from Livewire port 102 (multicast IP 239.192.0.102).  It can be modified to suit specific needs.  Working on an alternate implementation of RTSP that will work with the xNode.

The RTP module requires more options, and the defaults are the same as those used for the local streamer program.  It is possible however to configure the RTP source to receive audio data from the xNode using a multicast address, the 24-bit PCM encoding, and RTCP disabled.  It's possible to test this with the local_streamer program.  Added command line options to the local streamer to change the encoding and sample rate.  There is a chance it might not work correctly on computers with more than one network adapter.

On the Streaming tab, there are settings to configure an RTSP server in the player, which the xNode connects to in order to receive our audio output.  It works similarly to the icecast streamer, it receives audio from Pulse/JACK and not directly from the player's output.  This allows the audio to be mixed and changed before the final output is sent.  It includes a means of advertising the RTSP server as a Ravenna session on the network, however this does not always work if the target equipment is expecting SIP instead of RTSP.

Also on the Streaming tab is a setting for RTP output.  This can be configured with a multicast address of the form 239.192.0.x where x is the Livewire port number.

Please note that a required part of AoIP implementations is to use PTP (precision time protocol) for clock synchronization between computers on the AoIP network.  This means that the ptpd package must be installed and configured on the player machines.

## Summary

- We can send RTP audio in and out of the Livewire xNode devices.

- We can connect to their RTSP server.

- We can get the Livewire QOR16\xNode devices to connect to our RTSP server, now integrated into OBPlayer.

- We can make our RTSP server appear to the xNode as a Ravenna RTP.

- RTP and RTSP works. SIP is a lower priority. We do not have a SIP implementation until we find a Gstreamer library that implements SIP, then we will be able to support AES67 fully.
