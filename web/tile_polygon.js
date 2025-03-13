import * as PIXI from 'https://cdnjs.cloudflare.com/ajax/libs/pixi.js/7.2.4/pixi.mjs';

const app = new PIXI.Application({
    width: window.innerWidth,
    height: window.innerHeight,
    backgroundColor: 0x111111
});
document.body.appendChild(app.view);

// Containers
const tileContainer = new PIXI.Container();
const polygonContainer = new PIXI.Container();
app.stage.addChild(tileContainer);
app.stage.addChild(polygonContainer);

// Map setup
const tileSize = 256;
let zoom = 14;
let center = { lat: 51.497494, lon: -0.173037 };

// Example polygon coordinates (lon/lat)
const polygons = [
    {
        color: 0xff0055,
        coords: [
            { lon: -0.175, lat: 51.498 },
            { lon: -0.170, lat: 51.498 },
            { lon: -0.170, lat: 51.496 },
            { lon: -0.175, lat: 51.496 }
        ]
    },
    {
        color: 0x00aaff,
        coords: [
            { lon: -0.180, lat: 51.499 },
            { lon: -0.178, lat: 51.500 },
            { lon: -0.176, lat: 51.498 }
        ]
    }
];

// Coordinate conversions
function lonLatToPixel(lon, lat, zoom) {
    const x = ((lon + 180) / 360) * Math.pow(2, zoom) * tileSize;
    const latRad = lat * Math.PI / 180;
    const y = ((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * Math.pow(2, zoom) * tileSize;
    return { x, y };
}

// Load map tiles
function loadTiles() {
    tileContainer.removeChildren();

    const centerPixel = lonLatToPixel(center.lon, center.lat, zoom);
    const tileX = Math.floor(centerPixel.x / tileSize);
    const tileY = Math.floor(centerPixel.y / tileSize);
        const range = 3;

    for (let dx = -range; dx <= range; dx++) {
        for (let dy = -range; dy <= range; dy++) {
            const x = tileX + dx;
            const y = tileY + dy;
            const url = `https://basemaps.cartocdn.com/dark_all/${zoom}/${x}/${y}.png`;
            const tile = PIXI.Sprite.from(url);
            tile.x = (x * tileSize) - centerPixel.x + (app.renderer.width / 2);
            tile.y = (y * tileSize) - centerPixel.y + (app.renderer.height / 2);
            tileContainer.addChild(tile);
        }
    }

    updatePolygons();
}

// Draw and update polygons
function updatePolygons() {
    polygonContainer.removeChildren();
    const centerPixel = lonLatToPixel(center.lon, center.lat, zoom);

    polygons.forEach(poly => {
        const pixiPolygon = new PIXI.Graphics();
        pixiPolygon.beginFill(poly.color, 0.5);
        pixiPolygon.lineStyle(2, poly.color);

        poly.coords.forEach((point, idx) => {
            const pixel = lonLatToPixel(point.lon, point.lat, zoom);
            const x = pixel.x - centerPixel.x + app.renderer.width / 2;
            const y = pixel.y - centerPixel.y + app.renderer.height / 2;

            if (idx === 0) {
                pixiPolygon.moveTo(x, y);
            } else {
                pixiPolygon.lineTo(x, y);
            }
        });

        pixiPolygon.closePath();
        pixiPolygon.endFill();
        polygonContainer.addChild(pixiPolygon);
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

app.view.addEventListener('mouseup', () => dragging = false);

// Zoom interaction
app.view.addEventListener('wheel', e => {
    e.preventDefault();
    const delta = Math.sign(e.deltaY);
    zoom = Math.min(Math.max(zoom - delta, 2), 19);
    loadTiles();
});

// Initial render
loadTiles();
