// map-app.js
import { MapRenderer } from './map-renderer.js';

const mapApp = new MapRenderer({
    width: window.innerWidth,
    height: window.innerHeight,
    initialCenter: [-0.1278, 51.5074], // London coordinates
    initialZoom: 12,
    mapStyle: 'mapbox://styles/mapbox/dark-v11',

    mapboxAccessToken: 'pk.eyJ1Ijoia2VudGFtdCIsImEiOiJjbThtMHI3NnkxZmk1MmtzZDhzZW5hbHN3In0.taDwurloudkixpwxStqSEw',
    wsOptions: {
        serverUrl: "ws://127.0.0.1:8000/ws"
    }
});

window.mapApp = mapApp;