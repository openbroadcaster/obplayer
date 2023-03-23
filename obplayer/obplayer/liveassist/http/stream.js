Stream = new Object();

function ServerConnection(context)
{
  var that = this;

  that.context = context;

  that.connect = function ()
  {
    that.mode = $('#mic-mode').val();
    that.rate = $('#mic-rate').val();
    that.encoding = $('#mic-encoding').val();

    if (that.encoding == 'pcm')
      that.encoder = new PCMEncoder(that.rate);
    else if (that.encoding == 'a-law')
      that.encoder = new AlawEncoder(that.rate);

    that.socket = new WebSocket("ws://"+window.location.hostname+":"+window.location.port+"/stream", "Audio");
    that.socket.binaryType = "arraybuffer";

    that.socket.onopen = function (event)
    {
      console.log("websocket open");
      that.socket.send(JSON.stringify({
        'type': 'negotiate',
        'mode': that.mode,
        'rate': that.rate,
        'encoding': that.encoding,
        'blocksize': that.encoder.blockSize
      }));

      that.merger = that.context.createChannelMerger();

      if (that.mode == 'mic' || that.mode == 'mic+monitor') {
        that.microphone = new MicrophoneAudio(that.context);
        that.transmitter = new AudioTransmitter(that, that.encoder.sampleSize);
        that.microphone.connect(that.transmitter.processor);
        that.transmitter.connect(that.merger);
      }

      if (that.mode == 'monitor' || that.mode == 'mic+monitor') {
        that.receiver = new AudioReceiver(that, that.encoder.sampleSize);
        that.receiver.connect(that.merger);
      }

      that.merger.connect(that.context.destination);
    }

    that.socket.onmessage = function (event)
    {
      //console.log(JSON.stringify(event.data));

      if (event.data instanceof ArrayBuffer) {
        if (that.receiver)
          that.receiver.push_buffer(that.encoder.decodeBuffer(event.data));
      }
      else {
        msg = JSON.parse(event.data);
        Stream.handle_message(msg);
      }
    }

    that.socket.onclose = function (event)
    {
      console.log("websocket closed");
      if (that.receiver)
        that.receiver.disconnect();
      if (that.transmitter)
        that.transmitter.disconnect();
      if (that.microphone)
        that.microphone.disconnect();
      Stream.updateButtonState(false);
    }

    that.socket.onerror = function (event)
    {
      alert("Streaming Connection Lost");
      if (that.socket.readyState == WebSocket.OPEN)
        that.socket.close();
    }
  }

  that.disconnect = function ()
  {
    if (that.socket && that.socket.readyState != WebSocket.CLOSING && that.socket.readyState != WebSocket.CLOSED)
        that.socket.close();
  }

  that.send_audio = function (data)
  {
    if (that.socket && that.socket.readyState != WebSocket.CLOSING && that.socket.readyState != WebSocket.CLOSED)
      that.socket.send(that.encoder.encodeBuffer(data));
  }

  that.send_message = function (data)
  {
    if (that.socket)
      that.socket.send(JSON.stringify(data));
  }

  return that;
}


function AudioTransmitter(server, sampleSize)
{
  var that = this;

  that.server = server;
  that.processor = that.server.context.createScriptProcessor(sampleSize, 1, 1);
  //that.vu_meter = document.getElementById('mixer-vu-meter');

  that.processor.onaudioprocess = function (event)
  {
    var data = event.inputBuffer.getChannelData(0);
    that.server.send_audio(data);
    //$(that.vu_meter).css('width', (Math.max.apply(Math, data) * 100) + '%');
    //event.outputBuffer.getChannelData(0).set(data);
  }

  that.connect = function (destination)
  {
    that.processor.connect(destination);
    //that.processor.connect(that.context.destination);
  }

  that.disconnect = function ()
  {
    that.processor.disconnect();
  }

  return that;
}


function AudioReceiver(server, sampleSize)
{
  var that = this;

  that.server = server;
  that.processor = that.server.context.createScriptProcessor(sampleSize, 1, 1);
  //that.processor.connect(context.destination);
  that.buffer = new Array();

  that.processor.onaudioprocess = function (event)
  {
    var data = that.buffer.shift() || new Float32Array(sampleSize);
    //var input = event.inputBuffer.getChannelData(0);
    /*
    for (var i = 0; i < input.length; i++) {
      data[i] += input[i];
    }
    */
    event.outputBuffer.getChannelData(0).set(data);
  }

  that.connect = function (destination)
  {
    that.processor.connect(destination);
    //that.processor.connect(that.context.destination);
  }

  that.disconnect = function ()
  {
    that.processor.disconnect();
  }

  that.push_buffer = function (data)
  {
    //console.log("Received " + data.length);
    that.buffer.push(data);

    /*
    var buffer = that.buffer.getChannelData(0);
    for (var i = 0; i < data.length; i++) {
      buffer[i] = data[i];
    }
    */
  }
}


function MicrophoneAudio(context)
{
  var that = this;

  that.context = context;

  that.connect = function (destination)
  {
    navigator.getUserMedia = navigator.getUserMedia || navigator.webkitGetUserMedia || navigator.mozGetUserMedia;

    if (navigator.getUserMedia) {
      navigator.getUserMedia({ audio: true, video: false },
        function (stream) {
          //var audioTracks = stream.getAudioTracks();
          stream.onended = function() {
            console.log('Stream ended');
          };

          that.source = that.context.createMediaStreamSource(stream);
          that.source.connect(destination);
          //that.source.connect(that.context.destination);
        },
        function (err) {
          console.log("The following error occured: " + err.name);
        });
    } else {
      console.log("getUserMedia not supported");
    }
  }

  that.disconnect = function ()
  {
    that.source.disconnect();
  }

  return that;
}


function AudioEncoder(rate)
{
  this.factor = this.getRateFactor(rate);
  this.sampleSize = 2048 * this.factor;
}
AudioEncoder.prototype = {
  getRateFactor: function (rate)
  {
    if (rate == '44100')
      return 1;
    else if (rate == '22050')
      return 2;
    else if (rate == '11025')
      return 4;
  }
}


function PCMEncoder(rate)
{
  AudioEncoder.call(this, rate);
  this.blockSize = (this.sampleSize / this.factor) * 2;
}
PCMEncoder.prototype = new AudioEncoder();

PCMEncoder.prototype.encodeBuffer = function(buffer)
{
  var pcm = new Int16Array(buffer.length / this.factor);
  for (var i = 0, j = 0; i < buffer.length; i++, j += this.factor) {
    pcm[i] = buffer[j] * 32767;
  }
  return pcm;
}

PCMEncoder.prototype.decodeBuffer = function(buffer)
{
  var pcm = new Int16Array(buffer);
  var data = new Float32Array(pcm.length * this.factor);
  for (var i = 0, j = 0; i < pcm.length; i++, j += this.factor) {
    for (var k = 0; k < this.factor; k++) {
      data[j + k] = pcm[i] / 32767;
    }
  }
  return data;
}


function AlawEncoder(rate)
{
  AudioEncoder.call(this, rate);
  this.blockSize = this.sampleSize / this.factor;
}
AlawEncoder.prototype = new AudioEncoder();

AlawEncoder.prototype.encodeBuffer = function(buffer)
{
  var alaw = new Uint8Array(buffer.length / this.factor);
  for (var i = 0, j = 0; i < buffer.length; i++, j += this.factor) {
    var sign = (buffer[j] < 0) ? 0x80 : 0;
    var sample = Math.abs(buffer[j] * 32767);
    var exponent = AlawEncoder.prototype.encodeTable[(sample >> 8) & 0x7f];
    var mantissa = (exponent != 0) ? (sample >> exponent + 3) : (sample >> 4)
    alaw[i] = sign | (exponent << 4) | (mantissa & 0x0f);
  }
  return alaw;
}

AlawEncoder.prototype.decodeBuffer = function(buffer)
{
  var alaw = new Uint8Array(buffer);
  var data = new Float32Array(alaw.length * this.factor);
  for (var i = 0, j = 0; i < alaw.length; i++, j += this.factor) {
    //var sample = AlawEncoder.prototype.decodeTable[alaw[i]];
    var sign = (alaw[i] & 0x80) ? 0x8000 : 0;
    var exponent = (alaw[i] & 0x70) >> 4;
    var mantissa = alaw[i] & 0x0f;
    var sample = (exponent != 0) ? (0x10 | mantissa) << (exponent + 3) : (mantissa << 4);
    if (sign)
      sample *= -1;
    sample /= 32767;
    for (var k = 0; k < this.factor; k++) {
      data[j + k] = sample;
    }
  }
  return data;
}

AlawEncoder.prototype.encodeTable = [
  0,1,2,2,3,3,3,3,
  4,4,4,4,4,4,4,4,
  5,5,5,5,5,5,5,5,
  5,5,5,5,5,5,5,5,
  6,6,6,6,6,6,6,6,
  6,6,6,6,6,6,6,6,
  6,6,6,6,6,6,6,6,
  6,6,6,6,6,6,6,6,
  7,7,7,7,7,7,7,7,
  7,7,7,7,7,7,7,7,
  7,7,7,7,7,7,7,7,
  7,7,7,7,7,7,7,7,
  7,7,7,7,7,7,7,7,
  7,7,7,7,7,7,7,7,
  7,7,7,7,7,7,7,7,
  7,7,7,7,7,7,7,7
]

Stream.connect = function ()
{
  if (!Stream.context)
    Stream.context = new (window.AudioContext || window.webkitAudioContext)();

  if (!Stream.server) {
    Stream.server = new ServerConnection(Stream.context);
    Stream.server.connect();
  }
  Stream.updateButtonState(true);

  /*
  buffer = new Uint8Array(256);
  for (var i = 0; i < 256; i++)
    buffer[i] = i;
  enc = new AlawEncoder(22050);
  data = enc.decodeBuffer(buffer);
  data2 = enc.encodeBuffer(data);
  console.log(buffer);
  console.log(data);
  console.log(data2);
  */
}

Stream.disconnect = function ()
{
  if (Stream.server) {
    Stream.server.disconnect();
    Stream.server = undefined;
  }

  //if (context) {
  //  context.close();
  //  context = undefined;
  //}
  Stream.updateButtonState(false);
}

Stream.updateButtonState = function (connected)
{
  if (connected) {
    $('#mic-mode').attr('disabled', true);
    $('#mic-rate').attr('disabled', true);
    $('#mic-encoding').attr('disabled', true);

    $('#mic-connect').attr('disabled', true);
    $('#mic-disconnect').removeAttr('disabled');
  }
  else {
    $('#mic-mode').removeAttr('disabled');
    $('#mic-rate').removeAttr('disabled');
    $('#mic-encoding').removeAttr('disabled');

    $('#mic-connect').removeAttr('disabled');
    $('#mic-disconnect').attr('disabled', true);

  $('#mixer-vu-meter .level').css('width', '100%');
  }
}

Stream.mixerMicChange = function(event, ui)
{
  if (Stream.server) {
    Stream.server.send_message({
      'type': 'volume',
      'volume': $('#mixer-mic .mixer-volume').slider('value')
    });
  }
}

Stream.muteMic = function()
{
  if (Stream.server) {
    Stream.server.send_message({
      'type': 'mute'
    });
  }
}

Stream.handle_message = function (msg)
{

  if (msg.type == 'mic-level') {
    $('#mixer-vu-meter .level').css('width', (100 - Math.max(0, 100 + msg.level[0])) + '%');
  }
  else if (msg.type == 'mic-status') {
    $('#mixer-mic .mixer-volume').slider('value', msg.volume);
    if (msg.mute)
      $('#mixer-mic .mixer-mute').addClass('muted');
    else
      $('#mixer-mic .mixer-mute').removeClass('muted');
  }

}



$(document).ready(function()
{

  Stream.updateButtonState(false);
  $('#mic-connect').click(function () { Stream.connect(); });
  $('#mic-disconnect').click(function () { Stream.disconnect(); });

  $('#mixer-mic .mixer-volume').slider({
    orientation: 'vertical',
    min: 0,
    max: 100,
    step: 1,
    slide: Stream.mixerMicChange
  });
  $('#mixer-mic .mixer-mute').click(function () { Stream.muteMic(); });

  /*
  $('#mixer-something .mixer-volume').slider({
    orientation: 'vertical',
    min: 0,
    max: 100,
    step: 1,
    slide: Stream.mixerMicChange
  });
  $('#mixer-something .mixer-mute').click(function () { Stream.muteMic(); });
  */
});


$(document, window).on('beforeunload', function()
{
  Stream.disconnect();
});
