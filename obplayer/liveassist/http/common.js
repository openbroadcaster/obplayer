LA = new Object();

LA.station_override = function() {
    const btn = $('.override-btn');
    const action = btn.text();
    if (action == 'Start') {
      $.post('/inter_station_ctrl/start', {}, function (response, status) {
        if (status == 'success') {
            btn.text('Stop');
            btn.removeClass('override-start');
            btn.addClass('override-stop');
        } else {
          $('#notice').text(Site.t('Responses', 'linein_override_failed_action')).show();
        }
      });
    } else {
      $.post('/inter_station_ctrl/stop', {}, function (response, status) {
        if (status == 'success') {
          btn.text('Start');
          btn.removeClass('override-start');
          btn.addClass('override-stop');
        } else {
          alert('Linein override failed to run!');
        }
      });
  }
}

LA.windowResize = function()
{
  // $('#main-playlist').resizable({
  //   handles: 'e',
  //   minWidth: 300,
  //   maxWidth: $(window).width()-5 - ( $('#main-mixer').is(':visible') ? $('#main-mixer').width() : 0 ),
  //   resize: LA.mainResize
  // });

  LA.mainResize();
}

LA.mainResize = function()
{
  $('#main-buttons').width( $(window).width() - $('#main-playlist').width() - 48 - ( $('#main-mixer').is(':visible') ? $('#main-mixer').width() : 0 ));
  $('#main-buttons > div').toggle($('#main-buttons').width()>20)
}

LA.sliderChangeLock = false;
LA.sliderChangeStart = function(event, ui)
{
  LA.sliderChangeLock = true;
}
LA.sliderChangeStop = function(event, ui)
{
  LA.sliderChangeLock = false;

  if(LA.currentPlayMode=='playlist' && LA.currentTrackNumber>-1)
    LA.changePlaylistTrack(LA.currentTrackNumber,$('#control-track_position').slider('value'));

  else if(LA.currentPlayMode=='group' && LA.currentTrackNumber>-1 && LA.currentGroupNumber>-1)
    LA.changeGroupTrack(LA.currentGroupNumber,LA.currentTrackNumber,$('#control-track_position').slider('value'));
}

LA.init = function()
{

  LA.updateShow();
  LA.updateStatus();

  // updateTimes
  LA.updateTimes();

  // set tick interval
  setInterval(LA.tick,250);

  // hook up slider change

  // hook up play/pause buttons

  // set vu meter interval
  setInterval(function ()
  {
    $.post('/info/levels', null, LA.updateVuMeter, 'json').fail(LA.showNotConnected);
  }, 1000);

}

LA.showEndTime = false;
LA.updateShowLock = 0;
LA.updateShow = function()
{

  if(LA.updateShowLock > 0) return;

  // waiting for 3 things to complete before we are allowed to run again.
  LA.updateShowLock = 4;

  setTimeout(function()
  {

    // clear playlist and button items
    $('#main-playlist-tracks').html('');
    $('#main-buttons > div').html('');

    // update show name
    $.post('/info/show_name', {}, function(response)
    {
      LA.updateShowLock--;

      $('#info-show_name').text(response.value);
    },'json').fail(LA.showNotConnected);

    // get playlist items and populate
    $.post('/info/playlist', {}, function(response)
    {
      LA.updateShowLock--;

      var count = 0;
      $(response).each(function(index,track)
      {
        $('#main-playlist-tracks').append('<div class="track" id="track-'+count+'"></div>');

        var $track = $('#track-'+count);

        if(track.media_type=='breakpoint')
          $track.text('Breakpoint');
        else
        {
          $track.text(track.artist+' - '+track.title);
          $track.append('<span class="duration">'+LA.friendlyDuration(track.duration)+'</span>');
          $track.attr('data-artist',track.artist);
          $track.attr('data-title',track.title);
          $track.attr('data-duration',track.duration);
        }

        $track.attr('data-id',count);

        $track.dblclick(LA.trackDoubleClick);

        $track.prepend('<span class="status"></span>');

        $track.attr('data-type',track.media_type);

        count++;
      });
    },'json');

    // update button items and populate
    // get playlist items and populate
    $.post('/info/liveassist_groups', {}, function(response)
    {
      LA.updateShowLock--;

      var group_count = 0;

      //$('#main-buttons > div').css('min-width',response.length*240+'px');

      $(response).each(function(index,group)
      {

        $('#main-buttons > div').append('<ul class="column" id="group-'+group_count+'"></ul>');

        var $group = $('#group-'+group_count);

        $group.append('<li class="heading"><span></span></li>');
        $group.find('.heading > span').text(group.name);

        var track_count = 0;

        $.each(group.items, function(index,track)
        {

          $group.append('<li class="button" id="group-'+group_count+'-item-'+track_count+'"><span></span></li>');

          var $track = $('#group-'+group_count+'-item-'+track_count);
          $track.find('span').html(track.artist+' - '+track.title+'<br>'+LA.friendlyDuration(track.duration));
          $track.attr('data-type',track.media_type);
          $track.attr('data-artist',track.artist);
          $track.attr('data-title',track.title);
          $track.attr('data-duration',track.duration);
          $track.attr('data-id',track_count);
          $track.attr('data-group',group_count);

          $track.dblclick(LA.buttonDoubleClick);

          $track.prepend('<span class="status"></span>');

          track_count++;

        });

        group_count++;
      });

      $('#main-buttons > div').show();
      //$('#main-buttons').width(Math.round($(window).width()/2));

      LA.windowResize();

    },'json');


    // update show end time
    $.post('/info/show_end', {}, function(response)
    {
      LA.updateShowLock--;

      if(response.value==0) // no show, try again in 2 seconds.
      {
        $('#info-show_end').text('');
        LA.showEndTime = 0;
        setTimeout(LA.updateShow,2000);
      }

      else
      {
        LA.showEndTime = response.value;
        if(response.value!=0) $('#info-show_end').text(LA.friendlyTime(response.value));
      }
    }, 'json');

    // get button items and poplulate

  }, 500);

}

LA.trackDoubleClick = function()
{
  LA.changePlaylistTrack($(this).attr('data-id'),0);
}

LA.buttonDoubleClick = function()
{
  LA.changeGroupTrack($(this).attr('data-group'),$(this).attr('data-id'),0);
}


LA.currentTrackStart = 0;
LA.currentTrackEnd = 0;
LA.currentTrackNumber = -1;
LA.currentGroupNumber = -1;
LA.currentPlayMode = false;

LA.updateStatusLock = 0;

LA.playing = false;

LA.updateStatus = function()
{

  // usually a delay is needed because update status is called right after a track change, etc.
  // need to give the player a little time to make the change.

  if(LA.updateStatusLock > 0) return;

  LA.updateStatusLock = 1;

  setTimeout(function()
  {

    // get status from server
    $.post('/info/play_status', {}, function(response)
    {

      if(response.status=='override')
      {
        $('#info-status').text('Override');
        $('#info-status').attr('data-status','playing');
        LA.playing = true;
      }

      else if(response.status=='playing')
      {
        $('#info-status').text('Playing');
        $('#info-status').attr('data-status','playing');
        LA.playing = true;
      }

      else
      {
        $('#info-status').text('Paused');
        $('#info-status').attr('data-status','paused');
        LA.playing = false;
      }

      $('#main-playlist-tracks .track').add('#main-buttons .button').removeAttr('data-status');

      var $track = false;

      LA.currentPlayMode = response.mode;

      if(response.mode=='group' && response.group_num>=0 && response.group_item_num>=0)
      {
        $track = $('#group-'+response.group_num+'-item-'+response.group_item_num);
        LA.currentGroupNumber = response.group_num;
        LA.currentTrackNumber = response.group_item_num;
      }
      else if(response.mode=='playlist' && response.track>=0)
      {
        $track = $('#track-'+response.track);
        LA.currentGroupNumber = -1;
        LA.currentTrackNumber = response.track;
      }

      if($track)
      {
        $track.attr('data-status',response.status=='playing' ? 'playing' : 'paused');

        $('#info-track_name').text($track.attr('data-artist')+' - '+$track.attr('data-title'));
        LA.currentTrackStart = Date.now()/1000 - response.position;
        LA.currentTrackEnd = parseFloat($track.attr('data-duration')) + LA.currentTrackStart;
      }

      else
      {
        /*
        LA.currentTrackNumber = -1;
        LA.currentGroupNumber = -1;
        LA.currentPlayMode = false;
        LA.currentTrackStart = 0;
        LA.currentTrackEnd = 0;

        $('#info-track_name').html('');
        $('#info-track_time').html('');
        */

        $('#info-track_name').text(response.artist+' - '+response.title);
        LA.currentTrackStart = Date.now()/1000 - response.position;
        LA.currentTrackEnd = response.duration + LA.currentTrackStart;
      }

      LA.updateStatusLock--;

    }, 'json').fail(LA.showNotConnected);

  }, 500);

}

LA.showNotConnected = function ()
{
  $('#info-status').text('not connected');
  $('#info-status').attr('data-status','not-connected');
  $('#info-vu-meter').css('width', '0%');
  LA.playing = false;
}


LA.currentTimeOffset = false;
LA.updateTimes = function()
{
  $.post('/info/current_time',{},function(response)
  {
    LA.currentTimeOffset = (Date.now()/1000) - response.value;
  },'json').fail(LA.showNotConnected);
}

LA.updateVuMeter = function (levels)
{
  var $meter = $('#info-vu-meter .level');
  $meter.css('width', (100 - Math.max(0, 100 + levels[0])) + '%');
  //$meter.css('background', 'linear-gradient(to right, #090, #900 ' + Math.max(0, 100 + levels[0]) + '%' + ', transparent)');
}

LA.tick = function()
{

  // sometimes we are using a local time, sometimes we are using a player time. need to consider offset sometimes.
  var current_time = Date.now()/1000;
  var current_player_time = current_time - LA.currentTimeOffset;

  // update current time using client time and offset
  if(LA.currentTimeOffset!==false)
  {
    $('#info-time').text(LA.friendlyTime(current_time));
  }

  // are we at the end of the show? then update show.
  if(LA.showEndTime>0 && LA.showEndTime <= current_player_time)
  {
    LA.showEndTime = 0;

    LA.updateShow();
    LA.updateStatus();

    return;
  }

  // waiting for show to update.
  if(LA.showEndTime <= current_time)
  {
    return;
  }

  if(LA.playing && LA.currentTrackEnd!=0 && LA.currentTrackEnd <= current_time)
  {
    LA.currentTrackEnd=0;
    LA.updateStatus();

    return;
  }

  // waiting for track to update.
  if(LA.currentTrackEnd <= current_time)
  {
    return;
  }

  // something is updating, wait.
  if(LA.updateShowLock || LA.updateStatusLock || !LA.playing)
  {
    return;
  }

  // update track time
  if(LA.currentTrackNumber>=0 && LA.currentPlayMode)
  {

    if(LA.currentPlayMode == 'playlist')
      var duration = parseFloat($('#track-'+LA.currentTrackNumber).attr('data-duration'));

    else
      var duration = parseFloat($('#group-'+LA.currentGroupNumber+'-item-'+LA.currentTrackNumber).attr('data-duration'));

    var time = Date.now()/1000 - LA.currentTrackStart;
    var remaining = Math.max(duration-time,0);

    if(time>duration) time=duration;

    $('#info-track_time').text(LA.friendlyDuration(time)+'/'+LA.friendlyDuration(duration));
    $('#info-track_remaining').text(LA.friendlyDuration(remaining));

    if(duration>20 && (remaining<20 || remaining/duration<0.05)) $('#info-track_remaining').addClass('attention');
    else $('#info-track_remaining').removeClass('attention');

    var slider_val = time*100/duration;
  }
  else
  {
    $('#info-track_time').text('00:00/00:00');
    $('#info-track_remaining').text('00:00');
    $('#info-track_remaining').removeClass('attention');
    var slider_val = 0;
  }

  if(!LA.sliderChangeLock) $('#control-track_position').slider('value',slider_val);
  // if track at end, early return (need to wait for next track)

  // update remaining times

  // update slider, time on track

}

// convert seconds to friendly duration
LA.friendlyDuration = function(secs)
{

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

LA.play = function()
{
  $.post('/command/play',{},function()
  {
    LA.updateStatus();
  }, 'json').fail(LA.showNotConnected);
}

LA.pause = function()
{
  $.post('/command/pause',{},function()
  {
    LA.updateStatus();
  }, 'json').fail(LA.showNotConnected);
}

LA.next = function()
{
  $.post('/command/next',{},function()
  {
    LA.updateStatus();
  }, 'json').fail(LA.showNotConnected);
}

LA.prev = function()
{
  $.post('/command/prev',{},function()
  {
    LA.updateStatus();
  }, 'json').fail(LA.showNotConnected);
}

LA.changePlaylistTrack = function(track, offset)
{

  $.post('/command/playlist_seek',{'track_num': track, 'position': offset}, function(response)
  {
    LA.updateStatus();
  }, 'json').fail(LA.showNotConnected);

}

LA.changeGroupTrack = function(group, track, offset)
{

  $.post('/command/play_group_item',{'group_num': group, 'group_item_num': track, 'position': offset}, function(response)
  {
    LA.updateStatus();
  }, 'json').fail(LA.showNotConnected);

}

// convert unix timestamp (in seconds) to friendly time
LA.friendlyTime = function(timestamp)
{
  var date = new Date(timestamp*1000);
  var hours = date.getHours();
  var minutes = date.getMinutes();
  var seconds = date.getSeconds();

  if(hours<10) hours = '0'+hours;
  if(minutes<10) minutes = '0'+minutes;
  if(seconds<10) seconds = '0'+seconds;

  return hours+':'+minutes+':'+seconds;
}


LA.toggleMixer = function()
{
  if ($('#main-mixer').is(':hidden')) {
    $('#main-mixer-toggle').html('&raquo;');
    $('#main-mixer').show();
    //$('#main-buttons').css('right', $('#main-mixer').width());
    if (($(window).width() - $('#main-playlist').width()) < $('#main-mixer').width())
      $('#main-playlist').width( $(window).width() - $('#main-mixer').width() - 48 );
    LA.mainResize();
  }
  else {
    $('#main-mixer-toggle').html('&laquo;');
    $('#main-mixer').hide();
    //$('#main-buttons').css('right', 0);
    LA.mainResize();
  }
}


$(function() {

  $('#main-playlist-tracks').disableSelection();
  $('#main-buttons').disableSelection();

  $('#control-track_position').slider({
    change: LA.sliderChange,
    start: LA.sliderChangeStart,
    stop: LA.sliderChangeStop
  });

  $('#main-mixer-toggle').click(function (event) { LA.toggleMixer(); });

  $(window).resize(LA.windowResize);
  LA.windowResize();

  LA.init();
});
