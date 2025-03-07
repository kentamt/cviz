import * as PIXI from 'https://cdnjs.cloudflare.com/ajax/libs/pixi.js/7.2.4/pixi.mjs';

// Pixi.js setup
const app = new PIXI.Application({
    width: window.innerWidth,
    height: window.innerHeight,
    backgroundColor: 0x111111
});
document.body.appendChild(app.view);

// Containers
const tileContainer = new PIXI.Container();
const markerContainer = new PIXI.Container();
app.stage.addChild(tileContainer);
app.stage.addChild(markerContainer);

// Tile settings
const tileSize = 256;
let zoom = 16;
let center = { lat: 51.497494, lon: -0.173037 }; // Initial center (London)

// List of markers (lon, lat)
const markers = [
    { lon: -0.173037, lat: 51.497494, color: 0x00ff00 }, // center marker
    { lon: -0.180000, lat: 51.495000, color: 0xff3333 },
    { lon: -0.165000, lat: 51.500000, color: 0xffcc00 }
];

// Coordinate conversions
function lonLatToPixel(lon, lat, zoom) {
    const x = ((lon + 180) / 360) * Math.pow(2, zoom) * tileSize;
    const latRad = lat * Math.PI / 180;
    const y = ((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * Math.pow(2, zoom) * tileSize;
    return { x, y };
}

// Load tiles based on center
function loadTiles() {
    tileContainer.removeChildren();

    const centerPixel = lonLatToPixel(center.lon, center.lat, zoom);
    const tileX = Math.floor(centerPixel.x / tileSize);
    const tileY = Math.floor(centerPixel.y / tileSize);

    const range = 3; // number of tiles around center tile

    for (let dx = -range; dx <= range; dx++) {
        for (let dy = -range; dy <= range; dy++) {
            const x = tileX + dx;
            const y = tileY + dy;

            // const url = `https://basemaps.cartocdn.com/dark_all/${zoom}/${x}/${y}.png`;
            const url = `https://a.basemaps.cartocdn.com/light_all/${zoom}/${x}/${y}.png`;
            const tile = PIXI.Sprite.from(url);

            tile.x = (x * tileSize) - centerPixel.x + (app.renderer.width / 2);
            tile.y = (y * tileSize) - centerPixel.y + (app.renderer.height / 2);

            tileContainer.addChild(tile);
        }
    }

    updateMarkers();
}

// Update marker positions dynamically
function updateMarkers() {
    markerContainer.removeChildren();

    const centerPixel = lonLatToPixel(center.lon, center.lat, zoom);

    markers.forEach(({ lon, lat, color }) => {
        const markerPixel = lonLatToPixel(lon, lat, zoom);
        const x = markerPixel.x - centerPixel.x + app.renderer.width / 2;
        const y = markerPixel.y - centerPixel.y + app.renderer.height / 2;

        const marker = new PIXI.Graphics();
        marker.beginFill(color);
        marker.drawCircle(0, 0, 5);
        marker.endFill();
        marker.x = x;
        marker.y = y;

        markerContainer.addChild(marker);
    });
}

// Interaction (Pan & Zoom)
let dragging = false;
let lastMouse = null;

app.view.addEventListener('mousedown', e => {
    dragging = true;
    lastMouse = { x: e.clientX, y: e.clientY };
});

app.view.addEventListener('mousemove', e => {
    if (!dragging) return;

    const dx = e.clientX - lastMouse.x;
    const dy = e.clientY - lastMouse.y;
    lastMouse = { x: e.clientX, y: e.clientY };

    const scale = (tileSize * Math.pow(2, zoom));
    const lonPerPixel = 360 / scale;
    const latPerPixel = 360 / (scale * Math.cos(center.lat * Math.PI / 180));

    center.lon -= dx * lonPerPixel;
    center.lat += dy * latPerPixel;

    loadTiles();
});

// left arrow, right arrow, up arrow, down arrow
document.addEventListener('keydown', e => {
    const diff_angle = 360 / (tileSize * Math.pow(2, zoom));
    const step_size = 10;
    
    if (e.key === 'ArrowLeft') {
        center.lon -= step_size * diff_angle;
        loadTiles();
    }
    if (e.key === 'ArrowRight') {
        center.lon += step_size * diff_angle;
        loadTiles();
    }
    if (e.key === 'ArrowUp') {
        center.lat += step_size * diff_angle * Math.cos(center.lat * Math.PI / 180);
        loadTiles();
    }
    if (e.key === 'ArrowDown') {
        center.lat -= step_size * diff_angle * Math.cos(center.lat * Math.PI / 180);
        loadTiles();
    }
});


app.view.addEventListener('mouseup', () => {
    dragging = false;
});

function zoomIn() {
    zoom = Math.min(zoom + 1, 19);
    loadTiles();
}

function zoomOut() {
    zoom = Math.max(zoom - 1, 2);
    loadTiles();
}

// Zoom with mouse wheel
app.view.addEventListener('wheel', e => {
    e.preventDefault();
    const delta = Math.sign(e.deltaY);
    if (delta > 0) {
        zoomOut();
    }else {
        zoomIn();
    }
});

// '=' r '-'
document.addEventListener('keydown', e => {
    if (e.key === '=') {
        zoomIn();
    }else if (e.key === '-') {
        zoomOut();
    }
});

// Initial load
loadTiles();
