var gmap, pos, defaultwindow;
var markers = []; 
var counter = 0;
var openedMarkerID;
function initMap() {
    gmap = new google.maps.Map(document.getElementById('map'), {
        center: {
            lat: -34.397,
            lng: 150.644
        },
        zoom: 15
    });
    defaultwindow = new google.maps.InfoWindow({
        content: '<div>' +
            '<ul>' +
            '<li>Detail 1</li>' +
            '<li>Detail 2</li>' +
            '<li>Detail 3</li>' +
            '</ul>' +
            '</div>' +
            '<div>' +
            '<img src="/static/resources/default/trash-icon.jpg"/>' +
            '</div>'+
            '<button onclick="removemarker()" class="btnSmall">Remove</button'
    });
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function (position) {
            pos = {
                lat: position.coords.latitude,
                lng: position.coords.longitude
            };
            gmap.setCenter(pos);
            addMarker(1);
        });
    }
}


function addMarker(id) {

    
    var incident;
    var user;
    $.ajax({
        async:false,
        type:"GET",
        url:"/pins?pin=" + id,
        timeout: 60000,
        success: function (data) {
            incident = data;
        }
    });
    $.ajax({
        async:false,
        type:"GET",
        url:""
    })

    var latlong = {
        lat: incident.lat,
        lng: incident.lon
    }
    var test = incident.image_before;
    console.log(test);
    console.log(`message is ${test}`);
    var infowindow = new google.maps.InfoWindow({
        content: '<div>' +
        '<ul>' +
        '<li>Date Created: ' + 
        `${incident.date_created}` +
        '</li>' +
        '<li>Detail 2</li>' +
        '<li>Detail 3</li>' +
        '</ul>' +
        '</div>' +
        '<div>' +
        '<img src=' + 
        `/static/resources/user-content/${incident.uploader}/${incident.image_before}` + 
        '/>' +
        '</div>'+
        '<button onclick="removemarker()" class="btnSmall">Remove</button'
    });

    var marker = new google.maps.Marker({
        position: latlong,
        map: gmap,
        animation: google.maps.Animation.DROP,
        title: "Trash #00000",
        icon: '/static/resources/default/markers/red_markerA.png',
        id: counter
    });
    marker.addListener('click', function () {
        infowindow.open(gmap, marker);
    })
    markers.push(marker)
    counter++;
    marker.addListener('click', function () {
        infowindow.open(gmap, marker);
        openedMarkerID = marker.id;
    })
}

function addRandomMarker(colour) {
    var max = .005;
    var min = -.005;
    var newPos = {
        lat: pos.lat + Math.random() * (+max - +min),
        lng: pos.lng + Math.random() * (+max - +min)
    }
    var marker = new google.maps.Marker({
        map: gmap,
        position: newPos,
        icon: '/static/resources/default/markers/' + colour,
        id: counter

    });
    markers.push(marker)
    counter++;
    marker.addListener('click', function () {
        defaultwindow.open(gmap, marker);
        openedMarkerID = marker.id;
    })
}

function removemarker(){
    var marker = markers[openedMarkerID];
    marker.setMap(null);
}