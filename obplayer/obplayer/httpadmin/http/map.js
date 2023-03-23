var Devices = L.layerGroup();

function init_map()
{
  window.map = new L.map('map');
  var OSMBase = L.tileLayer('https://{s}.tiles.mapbox.com/v3/geoprism.h4g8f1k5/{z}/{x}/{y}.png', { maxZoom: 18 }).addTo(map);
  var currentLat = $("input[name=location_latitude]").val();
  var currentLng = $("input[name=location_longitude]").val();
  var latlng = L.latLng(currentLat,currentLng);

  Device = L.marker(latlng,{
      draggable: true
  });
  Devices.addLayer(Device).addTo(map);
  Device.on('dragend', onDrag);
  map.setView(latlng,9);
}

function onDrag(e)
{
  map.panTo(e.target.getLatLng());
  $("input[name=location_longitude]").val(e.target.getLatLng().lng.toFixed(5))
  $("input[name=location_latitude]").val(e.target.getLatLng().lat.toFixed(5))
}

function updateMap(){
  var newlat = $("input[name=location_latitude]").val();
  var newlng = $("input[name=location_longitude]").val();
  var newLatLng = L.latLng(newlat,newlng);

  Devices.removeLayer(Device);
  Device = L.marker(newLatLng,{draggable: true});
  Device.on('dragend', onDrag);
  Devices.addLayer(Device).addTo(map);
  map.panTo(newLatLng,9);
}

$(document).ready(function () {
  init_map();
});

