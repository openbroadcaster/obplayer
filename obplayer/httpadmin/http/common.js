Site = new Object();

Site.fullscreen = function()
{
  $('#command_fullscreen').text(Site.t('Miscellaneous', 'Fullscreen'));

  $.post('/command/fstoggle',{},function(response)
  {
    $('#command_fullscreen').text(Site.t('Miscellaneous', 'Fullscreen ('+response.fullscreen+')'));
  },'json');
}

Site.restart = function(extra)
{
  var postvars = {};
  if (extra) postvars['extra'] = extra;

  if (extra == 'defaults' && !confirm("Are you sure you want to reset all settings to their default values?"))
    return;

  $('#command_restart').text(Site.t('Miscellaneous', 'Restarting') + '...');

  $.post('/command/restart',postvars,function(response)
  {
    $('#command_restart').attr('onclick','');
    Site.restartInterval = setInterval(Site.restartCountdown, 1000);
  },'json');
}

Site.restartCountdownCount = 6;
Site.restartCountdown = function()
{
  Site.restartCountdownCount--;
  $('#command_restart').text(Site.t('Miscellaneous', 'Restarting') + ' ('+Site.restartCountdownCount+')');

  if(Site.restartCountdownCount==0)
  {
    clearInterval(Site.restartInterval);
    location.reload(true);
  }

}

Site.save = function(section)
{

  var postfields = {};

  $('#notice').hide();
  $('#error').hide();

  $('#content-'+section+' .settings input').add('#content-'+section+' .settings select').each(function(index,element)
  {
    if($(element).attr('name')=='save') return; // ignore 'save' button.
    if($(element).hasClass('nosave')) return; // ignore fields marked as nosave

    if($(element).attr('type')=='checkbox') var value = ($(element).is(':checked') ? 1 : 0);
    else var value = $(element).val();

    if ($(element).attr('name') != 'alerts_geocode' && $(element).attr('name') != 'alerts_selected_indigenous_languages') {
        // Handle blank non setting dropdown that the dropdown
        // plugin builds.
        if($(element).attr('name') != undefined) {
          postfields[$(element).attr('name')] = value;
        }
    } else {
      var output = '';
      if (value != null) {
        value.forEach((item) => {
          if (value.slice(-1)[0] != item) {
            output = output + item + ','
          } else {
            output = output + item
          }
        });
        postfields[$(element).attr('name')] = output;
      }
      }
  });

  $.post('/save',postfields,function(response)
  {
    if(response.status) $('#notice').text(Site.t('Responses', 'settings-saved-success')).show();
    else {
      var errormsg = Site.t($('#content-'+section).attr('data-tns'), response.error);
      if(errormsg==response.error) Site.t('Responses', response.error);
      $('#error').text(errormsg).show();
    }
  });
}

//Add support for dropdown menu for alerts locations

$(document).ready(function() {
  $.post('/alerts/geocodes_list', {}, function(data, status) {
    if (data != '') {
       $('#alerts_geocode').select2({
         placeholder: data
       });
    } else {
      $('#alerts_geocode').select2({
        placeholder: 'Select an a location'
      });
    }});
});

//Add support for dropdown menu for indigenous languages

$(document).ready(function() {
  $.post('/alerts/indigenous_languages', {}, function(data, status) {
    if (data != '') {
       $('#alerts_selected_indigenous_languages').select2({
         placeholder: data
       });
    } else {
      $('#alerts_selected_indigenous_languages').select2({
        placeholder: ''
      });
    }});
    // Handle the TOS modal actions.
    $('#tos_agree_btn').on('click', (e) => {
      $('#tos_modal').hide();
      $.post('/command/tos_agreed', {}, function(data, status) {
          // No action needed here.
          console.log(status);
        });
      });
    $('#tos_disagree_btn').on('click', (e) => {
      $('#tos_modal').hide();
      window.location.href = "https://openbroadcaster.com";
    });
});

Site.injectAlert = function()
{
  test_alert=$('#test_alert_select').val();

  $.post('/alerts/inject_test',{'alert':test_alert},function(response)
  {
    if(response.status) $('#notice').text(Site.t('Responses', 'alerts-inject-success')).show();
    else $('#error').text(Site.t('Responses', response.error)).show();
  },'json');
}

Site.replayAlert = function(id)
{
  $.post('/alerts/replay',{'identifier':id},function(response)
  {
    if(response.status) $('#notice').text(Site.t('Responses', 'alerts-cancel-success')).show();
    else $('#error').text(Site.t('Responses', response.error)).show();
  },'json');
}

Site.cancelAlert = function()
{
  var ids = [ ];

  $('#active-alerts input').each(function(index,element)
  {
    if($(element).is(':checked'))
      ids.push($(element).attr('name'));
  });

  if(ids.length>0){
    $.post('/alerts/cancel',{'identifier[]':ids},function(response)
    {
      if(response.status) $('#notice').text(Site.t('Responses', 'alerts-cancel-success')).show();
      else $('#error').text(Site.t('Responses', response.error)).show();
    },'json');
  }
}

Site.updateAlertInfo = function()
{
  if ($('#tabs .tab[data-content="alerts"]').hasClass('selected')){
    $.post('/alerts/list',{},function(response,status)
    {
      if(response.active.length){
	var alerts = response.active;
	var existing = $('#active-alerts');
	var alert_list = [ ];
	alert_list.push('<tr data-tns="Alerts Tab"><th class="fit" data-t>Cancel</th><th data-t>Sender</th><th data-t>Times Played</th><th data-t>Headline</th><th data-t>Replay Message</th></tr>');
	for(var key in alerts){
	  var row;
	  row = '<tr>';
	  row += '<td class="fit"><input type="checkbox" name="'+alerts[key].identifier+'" value="1" '+ ( $(existing).find('[name="'+alerts[key].identifier+'"]').is(':checked') ? 'checked' : '' ) +'/></td>';
	  row += '<td>'+alerts[key].sender+'<br />'+alerts[key].identifier+'<br />'+alerts[key].sent+'</td>';
	  row += '<td class="center">' + alerts[key].played + '</td>';
	  row += '<td><div class="headline" data-id="'+alerts[key].identifier+'">'+alerts[key].headline+'</div><div>'+alerts[key].description+'</div></td>';
    row += '<td class="fit"><button onclick="Site.replayAlert(\'' + alerts[key].identifier + '\')">Replay</button></td>';
    row += '</tr>';
	  alert_list.push(row);
	}
	$('#active-alerts').html(alert_list);
        Site.translateHTML($('#active-alerts'));
      }
      else{
	$('#active-alerts').html($('<tr><td>').html(Site.t('Alerts Tab', "No Active Alerts")));
      }

      if(response.expired.length){
	var alerts = response.expired;
	var alert_list = [ ];
	alert_list.push('<tr data-tns="Alerts Tab"><th data-t>Sender</th><th data-t>Times Played</th><th data-t>Description</th></tr>');
	for(var key in alerts){
	  var row;
	  row = '<tr>';
	  row += '<td>'+alerts[key].sender+'<br />'+alerts[key].identifier+'<br />'+alerts[key].sent+'</td>';
	  row += '<td class="center">'+alerts[key].played+'</td>';
	  row += '<td><div class="headline" data-id="'+alerts[key].identifier+'">'+alerts[key].headline+'</div><div>'+alerts[key].description+'</div></td>';
	  row += '</tr>';
	  alert_list.push(row);
	}
	$('#expired-alerts').html(alert_list);
        Site.translateHTML($('#expired-alerts'));
      }
      else{
	$('#expired-alerts').html($('<tr><td>').html(Site.t('Alerts Tab', "No Expired Alerts")));
      }

      // display the last time a heartbeat was received
      if(response.last_heartbeat==0){
	$('#alerts-last-heartbeat').html('('+Site.t('Alert Tab', 'none received')+')');
	$('#alerts-last-heartbeat').css('color','red');
      }
      else{
	var elapsed = (Date.now() / 1000) - response.last_heartbeat;
	$('#alerts-last-heartbeat').html(Site.friendlyDuration(elapsed) + " min");
	if(elapsed>150) $('#alerts-last-heartbeat').css('color','red');
	else $('#alerts-last-heartbeat').css('color','black');
      }

      // display the next time alerts will be played
      var next_check = response.next_play - (Date.now() / 1000);
      $('#alerts-next-play').html(Site.friendlyDuration(next_check >= 0 ? next_check : 0) + " min");
    },'json').error(function()
    {
      $('#alerts-last-heartbeat').html("");
      $('#alerts-next-play').html("");

      $('#active-alerts').html('<span style="color: red; font-weight: bold;">('+Site.t('Responses', 'player-connection-lost')+'</span>');
      $('#expired-alerts').html('<span style="color: red; font-weight: bold;">('+Site.t('Responses', 'player-connection-lost')+')</span>');
    });
  }
}


Site.updateStatusInfo = function()
{
  if($('#tabs .tab[data-content="status"]').hasClass('selected')){
    $.post('/status_info',{},function(response,status)
    {
      $('#show-summary-time').html(Site.friendlyTime(response.time));
      $('#show-summary-uptime').html(response.uptime);

      if(response.show){
	$('#show-summary-type').html(Site.t('Status Show Type', response.show.type));
	$('#show-summary-id').html(response.show.id);
	$('#show-summary-name').html(response.show.name);
	$('#show-summary-description').html(response.show.description);
	$('#show-summary-last-updated').html(Site.friendlyTime(response.show.last_updated));
      }

      if(response.audio){
	$('#audio-summary-media-type').html(Site.t('Status Media Type', response.audio.media_type));
	$('#audio-summary-order-num').html(response.audio.order_num);
	$('#audio-summary-media-id').html(response.audio.media_id);
	$('#audio-summary-artist').html(response.audio.artist);
	$('#audio-summary-title').html(response.audio.title);
	$('#audio-summary-duration').html(Site.friendlyDuration(response.audio.duration));
	$('#audio-summary-end-time').html(Site.friendlyTime(response.audio.end_time));
	Site.drawAudioMeter(response.audio_levels);
      }

      if(response.visual){
	$('#visual-summary-media-type').html(Site.t('Status Media Type', response.visual.media_type));
	$('#visual-summary-order-num').html(response.visual.order_num);
	$('#visual-summary-media-id').html(response.visual.media_id);
	$('#visual-summary-artist').html(response.visual.artist);
	$('#visual-summary-title').html(response.visual.title);
	$('#visual-summary-duration').html(Site.friendlyDuration(response.visual.duration));
	$('#visual-summary-end-time').html(Site.friendlyTime(response.visual.end_time));
      }
      Site.formatLogs(response.logs);
    },'json').error(function()
    {
      $('#log-data').html('<span style="color: red; font-weight: bold;">(' + Site.t('Responses', 'player-connection-lost') + ')</span>');
    });
  }
}

//  Check override status and update button text.

if ($('#tabs .tab[data-content="outputs"]').hasClass('selected')) {
  const updateStationOverrideBtnInterval = setInterval(Site.updateStationOverrideBtn, 1000);
}

Site.updateStationOverrideBtn = function() {
  const btn = $('.audio-override-btn');
  $.post('/inter_station_ctrl/is_live', {}, function (response, status) {
    if (response == 'True') {
      btn.text('Stop');
    } else {
      btn.text('Start');
    }
  });
}

Site.updateMapInfo = function()
{
  if($('#tabs .tab[data-content="location"]').hasClass('selected'))
  {
    map.invalidateSize();
  }
}

Site.formatLogs = function(lines)
{
  var scroll = false;
  var logdiv = $('#log-data')[0];
  var log_level = $('#log_level').val();

  if(logdiv.scrollTop == logdiv.scrollTopMax) scroll=true;
  if (log_level == 'normal') {
    lines = lines.normal;
  } else if (log_level == 'debug') {
    lines = lines.debug;
  } else if (log_level == 'alert') {
    lines = lines.alerts;
  }
  $('#log-data').html('');
  $('#log-data').html(lines.join('<br />\n'));
  if(scroll) logdiv.scrollTop = logdiv.scrollHeight;
}

Site.drawAudioMeter = function(levels)
{
  var canvas = $('#audio-levels')[0];
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


// convert seconds to friendly duration
Site.friendlyDuration = function(secs)
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

// convert unix timestamp (in seconds) to friendly time
Site.friendlyTime = function(timestamp)
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

Site.updateIntervals = function ()
{
  if (document.hidden) {
    if (Site.updateAlertInfoInterval) {
      clearInterval(Site.updateAlertInfoInterval);
      Site.updateAlertInfoInterval = null;
    }

    if (Site.updateStatusInfoInterval) {
      clearInterval(Site.updateStatusInfoInterval);
      Site.updateStatusInfoInterval = null;
    }

    if (Site.updateStationOverrideBtnInterval) {
      clearInterval(Site.updateStationOverrideBtnInterval);
      Site.updateStationOverrideBtnInterval = null;
    }
  }
  else {
    if (Site.updateAlertInfoInterval)
      clearInterval(Site.updateAlertInfoInterval);
    Site.updateAlertInfoInterval = setInterval(Site.updateAlertInfo, 2000);

    if (Site.updateStatusInfoInterval)
      clearInterval(Site.updateStatusInfoInterval);
    Site.updateStatusInfoInterval = setInterval(Site.updateStatusInfo, 1000);
    if (Site.updateStationOverrideBtnInterval)
      clearInterval(Site.updateStationOverrideBtnInterval);
    const updateStationOverrideBtnInterval = setInterval(Site.updateStationOverrideBtn, 1000);
  }

}


Site.loadStrings = function (cb)
{
  $.post('/strings', {}, function (response)
  {
    Site.strings = response;
    if (cb)
        cb();
  }, 'json');
}

Site.translateHTML = function( $element )
{
  $namespaces = $element.find('[data-tns]');

  // include this if it also has data-tns (would not be picked up using find)
  if( $element.attr('data-tns') !== undefined ) $namespaces = $namespaces.add($element);

  // sort namespaces by number of parents desc (work from inside out)
  $namespaces.sort(function(a, b)
  {
    return $(a).parents().length > $(b).parents().length ? -1 : 1;
  });

  // translate data-t items in namespace
  $namespaces.each(function(index,namespace)
  {

    var tns = $(namespace).attr('data-tns');

    // is this namespace a single thing to translate?
    if( $(namespace).attr('data-t') !== undefined )
      $strings = $(namespace);

    // if not, find child elements with data-t.
    else $strings = $(namespace).find('[data-t]');

    $strings.each(function(index,string) {
      $(string).text(Site.t(tns,$(string).text()));
      if($(string).attr('placeholder') !== undefined) $(string).attr('placeholder', Site.t(tns,$(string).attr('placeholder')));
      if($(string).attr('title') !== undefined) $(string).attr('title', Site.t(tns,$(string).attr('title')));
      $(string).removeAttr('data-t'); // remove data-t so we don't end up translating again.
    });

    //$(namespace).removeAttr('data-tns');

  });

}


// translate based on namespace, name. returns name (which should be human readable ish at least) if no translation found.
Site.translate = function(namespace,name,data)
{

  // don't have first argument? huh.
  if(typeof(namespace)=='undefined') return '';

  // don't have second argument, and first arg is a string? then we just pass it back.
  if(typeof(namespace)=='string' && typeof(name)=='undefined') return namespace;

  // don't have second argument, but first is an array/object? arguments were passed as an array instead maybe.
  if(typeof(namespace)=='object' && typeof(name)=='undefined')
  {
    var tmp = namespace;

    if(tmp.length==0) return '';

    if(tmp.length==1) return tmp[0];

    if(tmp.length>=2)
    {
      namespace = tmp[0];
      name = tmp[1];
    }

    if(tmp.length>=3)
    {
      data = tmp[2];
    }
  }

  if(!Site.strings) return;
  if(typeof(Site.strings[namespace])=='undefined') return name;
  if(typeof(Site.strings[namespace][name])=='undefined') return name;

  var string = Site.strings[namespace][name];

  // if we have a singular data item passed as a string, make it an array.
  if(typeof(data)=='string') data = [data];

  string = string.replace(/(\\)?%([0-9])+/g,function(match_string,is_escaped,data_index) {

    // is this escaped? also data_index = 0 is not valid.
    if(is_escaped || data_index==0) return '%'+data_index;

    // do we have a data at the data_index?
    if(!data || !data[data_index-1]) return '';

    // we have everything we need, do replace.
    return data[data_index-1];
  });

  return string;
}

Site.t = Site.translate;


$(document).ready(function()
{

  Site.loadStrings(function () {
    Site.translateHTML($(document.body));

    $('table.settings input').each(function ()
    {
      $(this).parent().parent().first().attr('title', $(this).attr('title'));
    });
  });

  $('#logs-open').on('click', function (e) {
    window.open('/logs.html', '_blank', "width=600, height=600, scrollbars=1, menubar=0, toolbar=0, titlebar=0");
  });

  // hide some home page (setting list) settings, if not applicable.
  if($('#sync_mode_value').text()=='remote') $('.local_media_location').hide();
  if($('#sync_mode_value').text()!='backup') $('.backup_media').hide();
  if($('#https_setting').text()=='False') $('.ssl_certificate').hide();

  $('.tab').click(function()
  {
    $('#content > div').hide();
    $('#content-'+$(this).attr('data-content')).show();

    $('.tab').removeClass('selected');
    $(this).addClass('selected');

    if($(this).attr('data-content')=='alerts') Site.updateAlertInfo();
    if($(this).attr('data-content')=='status') Site.updateStatusInfo();
    if($(this).attr('data-content')=='location') Site.updateMapInfo();
  });

  $('#sync_media_mode').change(function()
  {
    $('.sync_display_adjust').hide().find('input').addClass('nosave');
    $('.sync_display_adjust.sync_'+$('#sync_media_mode').val()).show().find('input').removeClass('nosave');
  });
  $('#sync_media_mode').change();

  $('#audio_out_mode_select').change(function()
  {
    if($('#audio_out_mode_select').val()=='alsa') $('#audio_out_alsa_device_row').show();
    else $('#audio_out_alsa_device_row').hide();

    if($('#audio_out_mode_select').val()=='jack') $('#audio_out_jack_name_row').show();
    else $('#audio_out_jack_name_row').hide();

    if($('#audio_out_mode_select').val()=='shout2send') {
      $('#audio_out_shout2send_ip_row').show();
      $('#audio_out_shout2send_port_row').show();
      $('#audio_out_shout2send_mount_row').show();
      $('#audio_out_shout2send_password_row').show();
    }
    else {
      $('#audio_out_shout2send_ip_row').hide();
      $('#audio_out_shout2send_port_row').hide();
      $('#audio_out_shout2send_mount_row').hide();
      $('#audio_out_shout2send_password_row').hide();
    }
  });
  $('#audio_out_mode_select').change();

  $('#audiolog_enable').change(function()
  {
    if($(this).is(':checked')) $('#audiolog_purge_files_row').show();
    else $('#audiolog_purge_files_row').hide();
  });
  $('#audiolog_enable').change();

  $('#audio_in_mode_select').change(function()
  {
    if($('#audio_in_mode_select').val()=='alsa') $('#audio_in_alsa_device_row').show();
    else $('#audio_in_alsa_device_row').hide();

    if($('#audio_in_mode_select').val()=='jack') $('#audio_in_jack_name_row').show();
    else $('#audio_in_jack_name_row').hide();
  });
  $('#audio_in_mode_select').change();

  $('#streamer_audio_in_mode_select').change(function()
  {
    if($('#streamer_audio_in_mode_select').val()=='alsa') $('#streamer_audio_in_alsa_device_row').show();
    else $('#streamer_audio_in_alsa_device_row').hide();

    if($('#streamer_audio_in_mode_select').val()=='jack') $('#streamer_audio_in_jack_name_row').show();
    else $('#streamer_audio_in_jack_name_row').hide();
  });
  $('#streamer_audio_in_mode_select').change();

  $('#http_admin_secure').change(function()
  {
    if($(this).is(':checked')) $('.http_admin_sslcert_row').show();
    else $('.http_admin_sslcert_row').hide();
  });
  $('#http_admin_secure').change();

  document.addEventListener('visibilitychange', Site.updateIntervals);
  Site.updateIntervals();
  Site.updateAlertInfo();
  Site.updateStatusInfo();
  $('#log_level').change(Site.updateStatusInfo);

  $('#import-settings').submit(function (event)
  {
    event.preventDefault();
    console.log(this);
    $.ajax( {
      url: '/import_settings',
      type: 'POST',
      data: new FormData(this),
      processData: false,
      contentType: false,
      success: function (response) {
        $('#notice').hide();
        $('#error').hide();

        if(response.status) $('#notice').html(Site.t('Responses', response.notice)).show();
        else $('#error').html(Site.t('Responses', response.error)).show();
      }
    });
  });

  $('#import_leadin_audio').submit(function (event)
  {
    event.preventDefault();
    console.log(this);
    $.ajax( {
      url: '/import_leadin_audio',
      type: 'POST',
      data: new FormData(this),
      processData: false,
      contentType: false,
      success: function (response) {
        $('#notice').hide();
        $('#error').hide();

        if(response.status) $('#notice').html(Site.t('Responses', response.notice)).show();
        else $('#error').html(Site.t('Responses', response.error)).show();
      }
    });
  });

  // Check for button click to open icecast config dialog.
  $('#icecast_config_editor_open_btn').click(function (e) {
    $('#icecast_config_modal').show();
  })

  // Check for button click to save the icecast config settings.
  $('#icecast_config_editor_save_btn').click(function (e) {
    const admin_password = $('#icecast_config_modal_admin_password');
    const source_password = $('#icecast_config_modal_source_password');
    const relay_password = $('#icecast_config_modal_relay_password');
    const icecast_admin_password = $('#icecast_config_modal_admin_password').val();
    const icecast_source_password = $('#icecast_config_modal_source_password').val();
    const icecast_relay_password = $('#icecast_config_modal_relay_password').val();

    if (icecast_admin_password == '' && icecast_source_password == ''
    && icecast_relay_password == '') {
      $('#icecast_config_modal').hide();
      $('#error').text(Site.t('Responses', 'icecast_config_modal_all_fields_blank')).show();
    } else {
      const post_data = {
        'admin': icecast_admin_password,
        'source': icecast_source_password,
        'relay': icecast_relay_password
      };
      $.post('/command/icecast_config_modal_save', post_data, function (response) {
        let admin = response.admin;
        let source = response.source;
        let relay = response.relay;
        admin_password.val(admin);
        source_password.val(source);
        relay_password.val(relay);
      })
    }
  })

  // Check for button click to close the icecast config settings dialog.
  $('#icecast_config_editor_exit_btn').click(function (e) {
    $('#icecast_config_modal').hide();
  })

  $('#update-player').click(function (event)
  {
    $.post('/update_player', {}, function (response) {
      $('#update-output').html($('<pre>').html(response.output));
    }, 'json');
  });

  $('#update-check').click(function (event)
  {
    $.post('/update_check', {}, function (response) {
      if (response.available)
        $('#update-check-output-row').html($('<td>' + Site.t('Admin Tab', 'Latest Version') + '</td><td>' + response.version + '</td>')).show();
      else
        $('#update-check-output-row').html($('<td>' + Site.t('Admin Tab', 'Already up to date') + '</td>')).show();
    }, 'json');
  });

  $('#toggle-scheduler').click(function (event)
  {
    $.post('/toggle_scheduler', {}, function (response) {
      $('#toggle-scheduler-status').html(Site.t('Sync Tab', response.enabled ? 'Enabled' : 'Disabled'));
    }, 'json');
  });
  //$('#toggle-scheduler-time').timepicker({timeFormat: 'hh:mm:ss',showSecond: true});

  $('#alerts_inject_button').click(Site.injectAlert);
  $('#alerts_cancel_button').click(Site.cancelAlert);

  $('#active-alerts, #expired-alerts').delegate('.headline', 'click', function (e) {
    var id = $(this).attr('data-id');
    window.open('/alertdetails.html?id='+id, '_blank', "width=500, height=600, scrollbars=1, menubar=0, toolbar=0, titlebar=0");
  });

  $('input[name="alerts_trigger_serial"]').change(function()
  {
    if($(this).is(':checked')) $('#alerts_trigger_serial_file_row').show();
    else $('#alerts_trigger_serial_file_row').hide();
  });
  $('input[name="alerts_trigger_serial"]').change();

  $('#live_assist_mic_mode_select').change(function()
  {
    if($('#live_assist_mic_mode_select').val()=='alsa') $('#live_assist_mic_alsa_device_row').show();
    else $('#live_assist_mic_alsa_device_row').hide();

    if($('#live_assist_mic_mode_select').val()=='jack') $('#live_assist_mic_jack_name_row').show();
    else $('#live_assist_mic_jack_name_row').hide();
  });
  $('#live_assist_mic_mode_select').change();

  $('#live_assist_monitor_mode_select').change(function()
  {
    if($('#live_assist_monitor_mode_select').val()=='alsa') $('#live_assist_monitor_alsa_device_row').show();
    else $('#live_assist_monitor_alsa_device_row').hide();

    if($('#live_assist_monitor_mode_select').val()=='jack') $('#live_assist_monitor_jack_name_row').show();
    else $('#live_assist_monitor_jack_name_row').hide();
  });
  $('#live_assist_monitor_mode_select').change();


  $('.pulse-volume').change(function () {
    $.post('/pulse/volume', { n: $(this).prop('name'), v: $(this).val() }, function (response) {
    }, 'json');
  });

  $('.pulse-mute').click(function () {
    var $button = $(this);
    $.post('/pulse/mute', { n: $button.prop('name') }, function (response) {
        if (response.m) $button.addClass('mute');
        else $button.removeClass('mute');
    }, 'json');
  });

  $('.pulse-select').change(function () {
    $.post('/pulse/select', { n: $(this).prop('name'), s: $(this).val() }, function (response) {
    }, 'json');
  });

  $('.audio-override-btn').click(function (e) {
    const btn = $('.audio-override-btn');
    const action = btn.text();
    if (action == 'Start') {
      $.post('/inter_station_ctrl/start', {}, function (response, status) {
        if (status == 'success') {
            btn.text('Stop');
        } else {
          $('#notice').text(Site.t('Responses', 'linein_override_failed_action')).show();
        }
      });
    } else {
      $.post('/inter_station_ctrl/stop', {}, function (response, status) {
        if (status == 'success') {
          btn.text('Start');
        } else {
          $('#notice').text(Site.t('Responses', 'linein_override_failed_action')).show();
        }
      });
    }
    //console.log($('.audio-override-btn').html());
  })

  $('#open_streams_btn').click(function (e) {
    $('#stream_players').show();
  });

  $('.modal_close_btn').click(function (e) {
    $('#stream_players').hide();
    let players = $('.audio_player');
    for (var i = 0; i < players.length; i++) {
      let player = players[i];
      if (player.paused == false){
        player.pause();
        let src = player.src;
        player.src = '';
        player.src = src;
      }
    }
    //players.forEach((player) => {
    //  console.log(player);
    //});
  });

});
