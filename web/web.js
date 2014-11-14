/* setup google map */
var mapOptions = {
    center: {
        lat: 22.4,
        lng: 114.15
    },
    zoom: 9,
    streetViewControl: false,
    mapTypeId: google.maps.MapTypeId.HYBRID
};
var map = new google.maps.Map(document.getElementById("map-canvas"), mapOptions);

/* stream from websocket */
var ws = new WebSocket("ws://" + location.hostname + ":8888/websocket");

var craft_info = {};

ws.addEventListener("message", function(e){
    var data = JSON.parse(e.data);
    
    var data_keys = Object.keys(data);
    data_keys.forEach(function(key){
        var icao = key;
        var pos = data[key].pos;
        var updated = data[key].updated;
        
        if (icao in craft_info) {
            craft_info[icao].oldCoords.push([craft_info[icao].pos[0], craft_info[icao].pos[1]]);
        }
        
        if (!(icao in craft_info)) {
            craft_info[icao] = {marker: null, polyline: null, oldCoords: []};
        }
        
        if (craft_info[icao].marker) craft_info[icao].marker.setMap(null);
        if (craft_info[icao].polyline) craft_info[icao].polyline.setMap(null);
        
        craft_info[icao].pos = pos;
        craft_info[icao].updated = updated;
        
        craft_info[icao].marker = new google.maps.Marker({
            position: new google.maps.LatLng(pos[0], pos[1]),
            map: map,
            title: icao,
            icon: "img/plane.svg"
        });
        
        var path = [];
        craft_info[icao].oldCoords.forEach(function(latLon){
            path.push(new google.maps.LatLng(latLon[0], latLon[1]));
        });
        
        craft_info[icao].polyline = new google.maps.Marker({
            path: path,
            map: map,
            geodesic: true,
            strokeColor: '#FF0000',
            strokeOpacity: 1.0,
            strokeWeight: 2
        });
    });
});

ws.onopen = function(e) {
    setInterval(function(){
        ws.send(null);
        
        var craft_keys = Object.keys(craft_info);
        craft_keys.forEach(function(key){
            var now = new Date().getTime();
            var updated = craft_info[key].updated * 1000;

            if (now - updated > 20000) {
                delete craft_info[key];
            }
        });
    }, 1000);
};