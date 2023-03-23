
  var configuration = { "iceServers": [{ "url": "stun:stun.l.google.com:19302" }] };
  var pc = new RTCPeerConnection(configuration);

  pc.onicecandidate = function (evt) {
    console.log(JSON.stringify({ "candidate": evt.candidate }));
  };

  var pc2 = new RTCPeerConnection();

  if (navigator.getUserMedia) {
    navigator.getUserMedia({ audio: true, video: false },
      function (stream) {
        //var video = document.querySelector('video');
        //video.src = window.URL.createObjectURL(stream);
        //video.onloadedmetadata = function(e) {
        //  video.play();
        //};

        //var audioTracks = stream.getAudioTracks();
        var audio = document.querySelector('#local-audio');
        stream.onended = function() {
          console.log('Stream ended');
        };
	window.stream = stream;
        audio.srcObject = stream;

        pc.addStream(stream);
	pc.addIceCandidate(new RTCIceCandidate({ candidate: "a=candidate:1 1 UDP 2130706431 192.168.1.102 1816 typ host" }));
        pc.createOffer(function (desc) {
          pc.setLocalDescription(desc);
          console.log("Offer");
          console.log(desc.sdp, JSON.stringify(desc));

          pc2.setRemoteDescription(desc);
          pc2.createAnswer(function (desc2) {
            console.log("Answer");
            console.log(desc2.sdp, JSON.stringify(desc2));
            pc.setRemoteDescription(new RTCSessionDescription(desc2));

            $.post('/command/open_stream', { 'sdp': desc.sdp, 'sdpanswer': desc2.sdp }, function () {
              console.log("Got it");
            });

          },
          function (err) {
            console.log("The following error occured: " + err.toString());
          }, { mandatory: { OfferToReceiveAudio: true, OfferToReceiveVideo: false } });


        },
        function (err) {
          console.log("The following error occured: " + err.toString());
        }, { audio: true });



      },
      function (err) {
        console.log("The following error occured: " + err.name);
      }
    );
  } else {
    console.log("getUserMedia not supported");
  }
