
// gets a value from local storage.
// Returns null if no value, otherwise returns the value.

function Get_Data(name) {
  return sessionStorage.getItem(name, null);
}

// sets a value from local storage.

function Set_Data(name, value) {
  sessionStorage.setItem(name, value);
}

function Show_Alert(msg, type='warning') {
document.getElementsByClassName('messages')[0].innerHTML = `
  <div class="alert alert-${type}">${msg}</div>
`;
}

function Clear_Alert(msg, type='warning') {
  document.getElementsByClassName('messages')[0].innerHTML = '';
  }

// Closes modal

function Close_Modal() {
let modal = document.getElementsByClassName('modal')[0];
if (modal != undefined) {
  document.getElementsByClassName('modal')[0].display = 'none';
}
}

// convert unix timestamp (in seconds) to friendly time

function friendlyTime(timestamp) {
let date = new Date(timestamp*1000);
let hours = date.getHours();
let minutes = date.getMinutes();
let seconds = date.getSeconds();

if(hours<10) hours = '0'+hours;
if(minutes<10) minutes = '0'+minutes;
if(seconds<10) seconds = '0'+seconds;

return hours+':'+minutes+':'+seconds;
}

// convert seconds to friendly duration
function friendlyDuration(secs) {

secs = Math.floor(secs);

var hours = Math.floor(secs/60/60);
secs -= hours*60*60;

var minutes = Math.floor(secs/60);
secs -= minutes*60;

var seconds = Math.round(secs);

if(hours<10) hours = '0'+hours;
if(minutes<10) minutes = '0'+minutes;
if(seconds<10) seconds = '0'+seconds;

var friendly_duration = minutes+':'+seconds;
if(hours>0) friendly_duration = hours+':'+friendly_duration;

return friendly_duration;
}

function drawAudioMeter (levels) {
var canvas = $('#audio-levels')[0];
if (canvas == undefined) return;
var c = canvas.getContext('2d');
var channels = levels.length;

c.clearRect(0, 0, canvas.width, canvas.height);

gradient = c.createLinearGradient(0, 0, canvas.width, 0);
gradient.addColorStop(0, "green");
gradient.addColorStop(1, "red");
c.fillStyle = gradient;

for(var i=0; i<channels; i++) {
  //c.fillRect(0, i * (canvas.height / channels), levels[i] * canvas.width, canvas.height / channels);
  c.fillRect(0, i * (canvas.height / channels), canvas.width + (levels[i] * (canvas.width / 100) ), canvas.height / channels);
}
}

function translate(namespace, element, cb, err) {
  $.post('/translate', {'namespace': namespace, 'element': element}, res => {
    if (res.status) {
      cb(res.text, err);
    } else {
      cb(null, err);
    }
  });
}

function translate_cb(msg, err) {
  if (msg != null) {
    if (err) {
      Show_Alert(msg, 'danger');
    } else {
      Show_Alert(msg, 'success');
    }
  }
}

function formatLogs(lines){
var scroll = false;
var logdiv = $('#log-data')[0];
if (logdiv == undefined) return;
var log_level = $('#log_level').val();

if(logdiv.scrollTop == logdiv.scrollTopMax) scroll=true;

for(var i=0; i<lines.length; i++)
{
  lines[i] = lines[i].replace(/\</g,'&lt;');
  lines[i] = lines[i].replace(/\>/g,'&gt;');
  lines[i] = lines[i].replace(/\&/g,'&amp;');

  if(lines[i].search('\\\[error\\\]')>0) lines[i] = '<span style="color: #880000;">'+lines[i]+'</span>';
  else if(lines[i].search('\\\[warning\\\]')>0) lines[i] = '<span style="color: #888800;">'+lines[i]+'</span>';
  else if(lines[i].search('\\\[alerts\\\]')>0) lines[i] = '<span style="color: #880088;">'+lines[i]+'</span>';
  else if(lines[i].search('\\\[priority\\\]')>0) lines[i] = '<span style="color: #880088;">'+lines[i]+'</span>';
  else if(lines[i].search('\\\[player\\\]')>0) lines[i] = '<span style="color: #005500;">'+lines[i]+'</span>';
  else if(lines[i].search('\\\[data\\\]')>0) lines[i] = '<span style="color: #333333;">'+lines[i]+'</span>';
  else if(lines[i].search('\\\[scheduler\\\]')>0) lines[i] = '<span style="color: #005555;">'+lines[i]+'</span>';
  else if(lines[i].search('\\\[sync\\\]')>0) lines[i] = '<span style="color: #000055;">'+lines[i]+'</span>';
  else if(lines[i].search('\\\[sync download\\\]')>0) lines[i] = '<span style="color: #AA4400;">'+lines[i]+'</span>';
  else if(lines[i].search('\\\[admin\\\]')>0) lines[i] = '<span style="color: #333300;">'+lines[i]+'</span>';
  else if(lines[i].search('\\\[live\\\]')>0) lines[i] = '<span style="color: #333300;">'+lines[i]+'</span>';
  else if(lines[i].search('\\[debug\\]')>0)
  {
    if(log_level=='debug') lines[i] = '<span style="color: #008000;">'+lines[i]+'</span>';
    else {
lines.splice(i, 1);
i -= 1;
    }
  }
}
$('#log-data').html(lines.join('<br />\n'));
if(scroll) logdiv.scrollTop = logdiv.scrollHeight;
}