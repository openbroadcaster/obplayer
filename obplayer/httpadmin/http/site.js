const restartCountdownCount = [6,5,4,3,2,1];

class Site {
  constructor() {
    document.addEventListener('DOMContentLoaded', (e) => {
    sessionStorage.setItem('current_view', 'status');
    this.messages_container = document.getElementsByClassName('messages')[0];
    this.content_container = document.getElementById('content_container');
    this.updateStatusInfo();
    setInterval(this.updateStatusInfo, 500);
    // document.body.addEventListener('click', e => {
    //   e.preventDefault();
    //   let modals = document.getElementsByClassName('modal');

    //   for (let i = 0; i < modals.length; i++) {
    //       console.log(modals[0]);
    //       modals[0].style.display = 'none';
    //   }
    // });
    let nav_items = Array.from(document.getElementsByClassName('nav-link'));
    nav_items.forEach(nav_item => {
      nav_item.removeAttribute('disabled');
      nav_item.addEventListener('click', (e) => {
        let items = Array.from(document.getElementsByClassName('nav-link'));
        items.forEach(item => {
          item.classList.remove('selected');
        });
        e.target.classList.add('selected');
        e.preventDefault();
        let url = e.target.getAttribute('data-href');
        this.Handle_Nav(url);
      });
    });
    if (document.getElementById('logs-open') != null) {
      this.logs_open_btn = document.getElementById('logs-open');
      this.logs_open_btn.addEventListener('click', () => this.Open_Window('logs.html'));
    }
    if (typeof(document.getElementById('maintenance_btn')) != undefined && document.getElementById('maintenance_btn') != null) {
        document.getElementById('maintenance_btn').addEventListener('click', e => {
        e.preventDefault();
        $.post('/toggle_scheduler',{},function(response) {
          let ele = document.getElementById('maintenance_btn');
          if(response.status) {
            if (response.enabled) {
              ele.classList.remove('btn-danger');
              ele.classList.add('btn-primary');
            } else {
              ele.classList.remove('btn-primary');
              ele.classList.add('btn-danger');
            }
          } else ele.innerText = 'Error!';
        },'json');
      });
    }
    if (typeof(document.getElementById('override_btn')) != undefined && document.getElementById('override_btn') != null) {
        document.getElementById('override_btn').addEventListener('click', e => {
        e.preventDefault();
        const btn = document.getElementById('override_btn');
        if (btn.classList.contains('btn-primary')) {
          $.post('/inter_station_ctrl/start', {}, function (response, status) {
            if (status == 'success') {
                btn.classList.remove('btn-primary');
                btn.classList.add('btn-danger');
            } else {
              translate('Responses', 'linein_override_failed_action',translate_cb, false);
            }
          });
        } else {
          $.post('/inter_station_ctrl/stop', {}, function (response, status) {
            if (status == 'success') {
              btn.classList.remove('btn-danger');
              btn.classList.add('btn-primary');
            } else {
              alert('Linein override failed to run!');
              Show_Alert('Linein override failed to run!', 'danger');
            }
          });
        }
      });
    }
    if (typeof(document.getElementById('command_fullscreen')) != undefined) {
      this.command_fullscreen_btn = document.getElementById('command_fullscreen');
      this.command_fullscreen_btn.addEventListener('click', e => {
        e.preventDefault();
        let ele = e.target;
        $.post('/command/fstoggle',{},function(response)
        {
          if(response.status) {
            ele.innerText = `Fullscreen (${response.fullscreen})`;
          } else ele.innerText = 'Error!';
        },'json');
      });
    }
    if (typeof(document.getElementById('command_restart')) != undefined && document.getElementById('command_restart') != null) {
      this.command_restart_btn = document.getElementById('command_restart');
      this.command_restart_btn.addEventListener('click', (e) => {
        e.preventDefault();
        this.command_restart_btn.disabled = true;
        this.command_restart_btn.innerText = 'Restarting...';
        this.Send_Request('/command/restart');
        this.display_timer();
        setInterval(this.display_timer, 1000);
        setTimeout(() => {
          this.check_for_server_connection();
        }, 6000);
      });
    } else {
      window.reload();
    }
    if (typeof(document.getElementById('open_streams_btn')) != undefined && document.getElementById('open_streams_btn') != null) {
      document.getElementById('open_streams_btn').addEventListener('click', e => {
        e.preventDefault();
        this.Open_Stream_Players_Modal();
    });
    }
  });
}

  Get_Page(name, cb) {
    //fetch(`${window.location}${name}`)
    fetch(`${name}`)
    .then(data => data.text())
    .then(html => {
      this.content_container.innerHTML = html;
      //translate();
      if (cb) {
        cb();
      }
    })
    .catch(err => {
      console.log(err);
    });
  }

  Handle_Nav(url) {
    console.log(`Switching pages to: ${url}`);
    if (url != '#') {
      // Handle clearing of alert boxes when changing pages.
      Clear_Alert();
      let current_view = url.replace('.html', '').replace(window.location, '').replace('./', '');
      sessionStorage.setItem('current_view', current_view);
      this.Get_Page(url, () => {
        switch(current_view) {
          case 'admin':
            this.handle_save_btns(document.getElementsByClassName('save_btn'), 'admin');
            document.getElementById('update-check').addEventListener('click', (e) => {
              e.preventDefault();
              this.Player_Update('check');
            });
            document.getElementById('update-player').addEventListener('click', (e) => {
              e.preventDefault();
              this.Player_Update('install');
            });
            document.getElementById('hard-restart-btn').addEventListener('click', (e) => {
              e.preventDefault();
              this.restart('hard');
            });
            document.getElementById('icecast_config_editor_open_btn').addEventListener('click', e => {
              e.preventDefault();
              $('#icecast_config_modal').show();
            });
            document.getElementById('icecast_config_editor_save_btn').addEventListener('click', e => {
              this.Handle_Icecast_Config_Save(e);
            });
            document.getElementById('icecast_config_editor_exit_btn').addEventListener('click', e => {
              e.preventDefault();
              $('#icecast_config_modal').hide();
            });
          break;
          case 'alerts':
            setInterval(this.UpdateAlertInfo, 2000);
            this.handle_save_btns(document.getElementsByClassName('save_btn'), 'alerts');
            $.post('/alerts/geocodes_list', {}, function(response) {
              if (response != '') {
                 $('#alerts_geocode').select2({
                   placeholder: response
                 });
              } else {
                $('#alerts_geocode').select2({
                  placeholder: 'Select an a location'
                });
            }});
            // TODO: Handle displaying the current languages that are already
            // selected on page load.
            if (document.getElementById('alerts_selected_indigenous_languages') != undefined) {
              $('#alerts_selected_indigenous_languages').select2({
                placeholder: 'Select an a language'
              });
            }
            document.getElementById('alerts_inject_button').addEventListener('click', e => {
              e.preventDefault();
              let test_alert = $('#test_alert_select').val();

              $.post('/alerts/inject_test',{'alert':test_alert},function(response)
              {
                if(response.status) {
                  translate('Responses', 'alerts-inject-success',translate_cb, false);
                }
                else {
                  translate('Responses', response.error,translate_cb, true);
                }
              },'json');
            });
            document.getElementById('alerts_cancel_button').addEventListener('click', e => {
              e.preventDefault();
              let ids = [];
              $('#active-alerts input').each(function(index,element)
              {
                if($(element).is(':checked'))
                  ids.push($(element).attr('name'));
              });

              if(ids.length>0){
                $.post('/alerts/cancel',{'identifier[]':ids},function(response)
                {
                  if(response.status) translate('Responses', 'alerts-cancel-success',translate_cb, false);
                  else translate('Responses', response.error,translate_cb, false);
                },'json');
              }
            });
          break;
          case 'sync':
            this.handle_save_btns(document.getElementsByClassName('save_btn'), 'sync');
            const maintenance_btn = document.getElementById('toggle-maintenance-btn');
            let maintenance_status = document.getElementById('toggle-maintenance-status');
            document.getElementById('sync_media_mode').addEventListener('change', e => {
              let mode = e.target.value;
              const backup = document.getElementById('sync_backup');
              const local = document.getElementById('sync_local');
              backup.style.visibility = 'hidden';
              backup.style.height = '0%';
              local.style.visibility = 'hidden';
              local.style.height = '0%';

              if (mode == 'backup') {
                backup.style.visibility = 'visible';
                backup.style.height = '100%';
                local.style.visibility = 'visible';
                local.style.height = '100%';
              } else if (mode == 'local') {
                backup.style.visibility = 'hidden';
                backup.style.height = '0%';
                local.style.visibility = 'visible';
                local.style.height = '100%';
              } else {
                backup.style.visibility = 'hidden';
                backup.style.height = '0%';
                local.style.visibility = 'hidden';
                local.style.height = '0%';
              }
            });
            if (maintenance_btn != undefined) {
              maintenance_btn.addEventListener('click', e => {
                e.preventDefault();
                maintenance_btn.disabled = true;
                maintenance_status.innerText = 'Loading...';
                $.post('/toggle_scheduler',{},function(response)
                {
                  maintenance_btn.disabled = false;
                  if(response.status) {
                    if (response.enabled) {
                      maintenance_status.innerText = 'Disabled';
                    } else {
                      maintenance_status.innerText = 'Enabled';
                    }
                  } else maintenance_status.innerText = 'Error!';
                },'json');
              });
            }
          break;
          case 'sources':
            this.handle_save_btns(document.getElementsByClassName('save_btn'), 'sources');
            document.getElementById('audio_in_mode_select').addEventListener('change', e => {
              const alsa = document.getElementById('audio_in_alsa_device_row');
              const jack = document.getElementById('audio_in_jack_name_row');
              let mode = e.target.value;
              if (mode == 'alsa') {
                alsa.style.display = 'block';
                jack.style.display = 'none';
              } else if (mode == 'jack') {
                alsa.style.display = 'none';
                jack.style.display = 'block';
              } else {
                alsa.style.display = 'none';
                jack.style.display = 'none';
              }
            });
          break;
          case 'outputs':
            this.handle_save_btns(document.getElementsByClassName('save_btn'), 'outputs');
            document.getElementById('audio_out_mode_select').addEventListener('change', e => {
              e.preventDefault();
              const alsa = document.getElementById('audio_out_alsa_device_row');
              const jack = document.getElementById('audio_out_jack_name_row');
              const stream1 = document.getElementById('audio_out_shout2send_ip_row');
              const stream2 = document.getElementById('audio_out_shout2send_port_row');
              const stream3 = document.getElementById('audio_out_shout2send_mount_row'); 
              const stream4 = document.getElementById('audio_out_shout2send_password_row');
              alsa.style.display = 'none';
              jack.style.display = 'none';
              stream1.style.display = 'none';
              stream2.style.display = 'none';
              stream3.style.display = 'none';
              stream4.style.display = 'none';

              switch(e.target.value) {
                case 'alsa':
                  alsa.style.display = 'block';
                break;
                case 'jack':
                  jack.style.display = 'block';
                break;
                // See TODO in page this event comes from.
                case 'shout2send':
                  jack.style.display = 'block';
                break;
              }
            })
          break;
          case 'streaming':
            this.handle_save_btns(document.getElementsByClassName('save_btn'), 'streamer');
            document.getElementById('streamer_audio_in_mode_select').addEventListener('change', e => {
              e.preventDefault();
              const alsa = document.getElementById('streamer_audio_in_alsa_device_row');
              const jack = document.getElementById('streamer_audio_in_jack_name_row');
              alsa.style.display = 'none';
              jack.style.display = 'none';

              if (e.target.value == 'alsa') {
                alsa.style.display = 'block';
                jack.style.display = 'none';
              } else if(e.target.value == 'jack') {
                alsa.style.display = 'none';
                jack.style.display = 'block';
              } else {
                alsa.style.display = 'none';
                jack.style.display = 'none';
              }
            });
          break;
          case 'http_admin':
            this.handle_save_btns(document.getElementsByClassName('save_btn'), 'http');
            if (document.getElementById('http_admin_secure') != undefined) {
              const http_admin_secure = document.getElementById('http_admin_secure');
              const http_admin_sslcert_rows = document.getElementsByClassName('http_admin_sslcert_row');

              http_admin_secure.addEventListener('click', e => {
                if (e.target.checked) {
                  for (let i = 0; i < http_admin_sslcert_rows.length; i++) {
                    let row = http_admin_sslcert_rows[i];
                    row.style.display = 'block';
                  }
                } else {
                  for (let i = 0; i < http_admin_sslcert_rows.length; i++) {
                    let row = http_admin_sslcert_rows[i];
                    row.style.display = 'none';
                  }
                }
              });
            }
          break;
          case 'live_assist':
            this.handle_save_btns(document.getElementsByClassName('save_btn'), 'liveassist');
            document.getElementById('live_assist_mic_mode_select').addEventListener('change', e => {
              e.preventDefault();
              const alsa = document.getElementById('live_assist_mic_alsa_device_row');
              const jack = document.getElementById('live_assist_mic_jack_name_row');
              alsa.style.display = 'none';
              jack.style.display = 'none';

              if (e.target.value == 'alsa') {
                alsa.style.display = 'block';
                jack.style.display = 'none';
              } else if(e.target.value == 'jack') {
                alsa.style.display = 'none';
                jack.style.display = 'block';
              } else {
                alsa.style.display = 'none';
                jack.style.display = 'none';
              }
            });
            document.getElementById('live_assist_monitor_mode_select').addEventListener('change', e => {
              e.preventDefault();
              const alsa = document.getElementById('live_assist_monitor_alsa_device_row');
              const jack = document.getElementById('live_assist_monitor_jack_name_row');
              alsa.style.display = 'none';
              jack.style.display = 'none';

              if (e.target.value == 'alsa') {
                alsa.style.display = 'block';
                jack.style.display = 'none';
              } else if(e.target.value == 'jack') {
                alsa.style.display = 'none';
                jack.style.display = 'block';
              } else {
                alsa.style.display = 'none';
                jack.style.display = 'none';
              }
            });
          break;
          case 'location_map':
            init_map();
            this.handle_save_btns(document.getElementsByClassName('save_btn'), 'location');
          break;
        }
      });
    } else {
      location.reload();
    }
  }

  Open_Window(page) {
    window.open(page, '_blank', "width=600, height=600, scrollbars=1, menubar=0, toolbar=0, titlebar=0");
  }

  Send_Request(url, data = null, res_type = 'json', callback = null) {
    let options = {'method': 'POST'};
    if (data != null) {
      options = {'method': 'POST', 'body': data}
    }
    fetch(url, options)
    .then(res => {
      console.log(`request: ${url}. was successful.`);
      if (res_type == 'json') {
        res.json();
      }
    })
    .then(data => {
      console.log(`request: ${url}. data: ${data}`);
      callback(data);
    })
    .catch(err => console.error(`request: ${url}. was failed with error message ${err}`))
  }

  updateStatusInfo() {
    let current_view = sessionStorage.getItem('current_view', null);
    if(current_view == 'status'){
      $.post('/status_info', {}, res => {
        //console.log(res);
        $('#show-summary-time').html(friendlyTime(res.time));
        $('#show-summary-uptime').html(res.uptime);
        if(res.show){
          //$('#show-summary-type').html(translate('Status Show Type', res.show.type));
          $('#show-summary-type').html(res.show.type);
          $('#show-summary-id').html(res.show.id);
          $('#show-summary-name').html(res.show.name);
          $('#show-summary-description').html(res.show.description);
          $('#show-summary-last-updated').html(friendlyTime(res.show.last_updated));
        }
        if(res.audio){
          translate('Status Media Type', res.audio.media_type, (msg, err) => {
            $('#audio-summary-media-type').html(msg);
          }, false);
          $('#audio-summary-order-num').html(res.audio.order_num);
          $('#audio-summary-media-id').html(res.audio.media_id);
          $('#audio-summary-artist').html(res.audio.artist);
          $('#audio-summary-title').html(res.audio.title);
          $('#audio-summary-duration').html(friendlyDuration(res.audio.duration));
          $('#audio-summary-end-time').html(friendlyTime(res.audio.end_time));
          drawAudioMeter(res.audio_levels);
        }
        if(res.visual){
          $('#visual-summary-media-type').html(res.visual.media_type);
          translate('Status Media Type', res.visual.media_type, (msg, err) => {
            $('#visual-summary-media-type').html(msg);
          }, false);
          $('#visual-summary-order-num').html(res.visual.order_num);
          $('#visual-summary-media-id').html(res.visual.media_id);
          $('#visual-summary-artist').html(res.visual.artist);
          $('#visual-summary-title').html(res.visual.title);
          $('#visual-summary-duration').html(friendlyDuration(res.visual.duration));
          $('#visual-summary-end-time').html(friendlyTime(res.visual.end_time));
        }

        formatLogs(res.logs);
      }, 'json').fail(err => {
        document.getElementById('log-data').innerText = 'The connection to the player was lost! The web client will keep trying to reconnect.';
      });
    }
  }

  UpdateAlertInfo() {
    let ele = $('#active-alerts');
    if (ele == undefined) return;

    $.post('/alerts/list',{}, response => 
    {
      if(response.status){
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
	  row += `<td><div><a href="alertdetails.html?id=${alerts[key].identifier}" class="headline" target="_blank" data-id="${alerts[key].identifier}">${alerts[key].headline}</a>${alerts[key].description}</div></td>`;    row += '<td class="fit"><button class="btn btn-primary" onclick="Site.replayAlert(\'' + alerts[key].identifier + '\')">Replay</button></td>';
    row += '</tr>';
	  alert_list.push(row);
	}
	$('#active-alerts').html(alert_list);
        //Site.translateHTML($('#active-alerts'));
      }
      else{
	$('#active-alerts').html($('<tr><td>').html(translate('Alerts Tab', "No Active Alerts")));
      }

      if(response.expired.length){
	var alerts = response.expired;
	var alert_list = [ ];
	alert_list.push('<tr data-tns="Alerts Tab"><th data-t>Sender</th><th data-t>Times Played</th><th data-t>Description</th></tr>');
	for(var key in alerts){
	  var row;
	  row = '<tr>';
	  row += '<td><div>'+ alerts[key].sender+'<br />'+alerts[key].identifier+'<br />'+alerts[key].sent+'</div></td>';
	  row += '<td class="center">'+alerts[key].played+'</td>';
	  row += `<td><div><a href="alertdetails.html?id=${alerts[key].identifier}" class="headline" target="_blank">${alerts[key].description}</div></td>`;
    row += '<td class="fit"><button class="btn btn-primary" onclick="Site.replayAlert(\'' + alerts[key].identifier + '\')">Replay</button></td>';
	  row += '</tr>';
	  alert_list.push(row);
	}
	$('#expired-alerts').html(alert_list);
        Site.translateHTML($('#expired-alerts'));
      }
      else{
	$('#expired-alerts').html($('<tr><td>').html(translate('Alerts Tab', "No Expired Alerts")));
      }

      // display the last time a heartbeat was received
      if(response.last_heartbeat==0){
	$('#alerts-last-heartbeat').html('('+translate('Alert Tab', 'none received')+')');
	$('#alerts-last-heartbeat').css('color','red');
      }
      else{
	var elapsed = (Date.now() / 1000) - response.last_heartbeat;
	$('#alerts-last-heartbeat').html(friendlyDuration(elapsed) + " min");
	if(elapsed>150) $('#alerts-last-heartbeat').css('color','red');
	else $('#alerts-last-heartbeat').css('color','black');
      }

      // display the next time alerts will be played
      var next_check = response.next_play - (Date.now() / 1000);
      $('#alerts-next-play').html(friendlyDuration(next_check >= 0 ? next_check : 0) + " min");
    },'json');//.error(function()
    // {
    //   $('#alerts-last-heartbeat').html("");
    //   $('#alerts-next-play').html("");

    //   $('#active-alerts').html('<span style="color: red; font-weight: bold;">('+translate('Responses', 'player-connection-lost')+'</span>');
    //   $('#expired-alerts').html('<span style="color: red; font-weight: bold;">('+translate('Responses', 'player-connection-lost')+')</span>');
    // });
  }

  Save(section) {

    let postfields = {};

    this.messages_container.innerHTML = '';
  
    $('#content-'+section+' .settings input').add('#content-'+section+' .settings select').each(function(index,element)
    {
      if($(element).attr('name')=='save') return; // ignore 'save' button.
      if($(element).hasClass('nosave')) return; // ignore fields marked as nosave
  
      if($(element).attr('type')=='checkbox') {
        var value = ($(element).is(':checked') ? 1 : 0);
      } else var value = $(element).val();

      if ($(element).attr('name') != 'alerts_geocode' && $(element).attr('name') != 'alerts_selected_indigenous_languages') {
        // Handle blank non setting dropdown that the dropdown
        // plugin builds.
        if($(element).attr('name') != undefined) {
          console.log($(element).attr('name'));
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
      if(response.status) translate('Responses', 'settings-saved-success',translate_cb, false);
      else {
        translate($('#content-'+section).attr('data-tns'), response.error,translate_cb, true);
      }
    });
  }

  handle_save_btns(eles, settings_group) {
    for (let i = 0; i < eles.length; i++) {
      let element = eles[i];
      element.addEventListener('click', (e) => {
        e.preventDefault();
        this.Save(settings_group);
      });
    }
  }

 restart(extra) {
    let postvars = {};
    if (extra) postvars['extra'] = extra;
  
    if (extra == 'defaults' && !confirm("Are you sure you want to reset all settings to their default values?"))
      return;
  
    $('#command_restart').text('Restarting...');
  
    $.post('/command/restart',postvars,function(response)
    {
      document.getElementById('command_restart').disabled = true;
      setTimeout(() => {
        this.check_for_server_connection();
      }, 6000);
    },'json');
  }

  update_password(e) {
    e.preventDefault();
    let password = document.getElementById('http_admin_password').value;
    let password_repeat = document.getElementById('http_admin_password_retype').value;
    let postvars = {'http_admin_password': password, 'http_admin_password_retype': password_repeat};
    $.post('/command/password_change',postvars,function(response)
    {
      if (response.status) {
        
        Show_Alert('Your password has been changed!');
      }
    },'json');
  }

  Player_Update(type='check') {
    if (type == 'check') {
      $.post('/updater/check', {}, function (response) {
        if (response.available)
          $('#update-check-output-row').html($('<td>' + translate('Admin Tab', 'Latest Version') + '</td><td>' + response.version + '</td>')).show();
        else
          $('#update-check-output-row').html($('<td>' + translate('Admin Tab', 'Already up to date') + '</td>')).show();
      }, 'json');
    } else if (type = 'install') {
      $.post('/updater/update', {}, function (response) {
        $('#update-output').html($('<pre>').html(response.output));
      }, 'json');
    }
  }
  
  Open_Stream_Players_Modal() {
    let ele = $('#stream_players');
    ele.show();
    document.getElementById('modal_close_btn').addEventListener('click', e => {
      ele.hide();
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
    });
  }

  Handle_TOS_Agree(e) {
    e.preventDefault();
    $('#tos_modal').hide();
    $.post('/command/tos_agreed', {}, function(data, status) {
        // No action needed here.
        console.log(status);
        if (typeof(document.getElementById('password-change-modal')) != undefined) {
          document.getElementById('password-change-modal').style.display = 'block';
        }
    });
  }

  Handle_TOS_Disagree(e) {
    e.preventDefault();
    $('#tos_modal').hide();
    window.location.href = "https://openbroadcaster.com";
  }

  Handle_Icecast_Config_Save(e) {
    e.preventDefault();
    const admin_password = $('#icecast_config_modal_admin_password');
    const source_password = $('#icecast_config_modal_source_password');
    const relay_password = $('#icecast_config_modal_relay_password');
    const icecast_admin_password = $('#icecast_config_modal_admin_password').val();
    const icecast_source_password = $('#icecast_config_modal_source_password').val();
    const icecast_relay_password = $('#icecast_config_modal_relay_password').val();
    if (icecast_admin_password == '' && icecast_source_password == ''
    && icecast_relay_password == '') {
      $('#icecast_config_modal').hide();
      translate('Responses', 'icecast_config_modal_all_fields_blank', translate_cb, false);
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
  }

  check_for_server_connection() {
    setInterval(() => {
      fetch('/status_info')
      .then(res => {
        location.reload();
      })
      .catch(err => {
        console.log('The server is still down!');
      });
    }, 1000);
  }

  display_timer() {
    if (restartCountdownCount.length > 0) {
      $('#command_restart').text('Restarting...' + restartCountdownCount.shift());
    }
  }
}

site = new Site();