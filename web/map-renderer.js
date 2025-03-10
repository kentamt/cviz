// map-renderer.js
import * as PIXI from 'https://cdnjs.cloudflare.com/ajax/libs/pixi.js/7.2.4/pixi.mjs';
import { GeometryRenderer, Logger } from './geometry-renderer.js';
import { WebSocketManager } from './websocket-manager.js';

export class MapRenderer {
    constructor(options = {}) {
        const {
            initialCenter = { lat: 51.497494, lon: -0.173037 }, // Default: London
            initialZoom = 16,
            tileSize = 256,
            containerId = 'map-container',
            tileServer = 'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
            // satellite imagery
            // tileServer = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            wsOptions = {}
        } = options;

        this.center = initialCenter;
        this.zoom = initialZoom;
        this.tileSize = tileSize;
        this.tileServer = tileServer;
        
        // Create map container
        this.container = document.getElementById(containerId);
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = containerId;
            document.body.appendChild(this.container);
        }
        
        // Create PIXI application
        this.app = new PIXI.Application({
            width: window.innerWidth,
            height: window.innerHeight,
            backgroundColor: 0x111111
        });
        this.container.appendChild(this.app.view);
        
        // Create containers
        this.tileContainer = new PIXI.Container();
        this.markerContainer = new PIXI.Container();
        this.app.stage.addChild(this.tileContainer);
        this.app.stage.addChild(this.markerContainer);
        
        // Set up coordinate transform function for the renderer
        const transformFunction = (x, y) => {
            return this.transformCoordinates(x, y);
        };
        
        // Initialize WebSocket manager with our custom renderer
        this.wsManager = new WebSocketManager({
            ...wsOptions,
            rendererOptions: {
                containerId: 'geometry-container',
                coordinateTransform: transformFunction
            }
        });
        
        // Store the geometry renderer
        this.geometryRenderer = this.wsManager.renderer;

        // Initial map loading
        this.loadTiles();
        
        // Set up interaction
        this.setupInteraction();
    }
    
    // Convert lon/lat to pixel coordinates
    lonLatToPixel(lon, lat, zoom) {
        const x = ((lon + 180) / 360) * Math.pow(2, zoom) * this.tileSize;
        const latRad = lat * Math.PI / 180;
        const y = ((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * Math.pow(2, zoom) * this.tileSize;
        return { x, y };
    }
    
    // Transform coordinates from lon/lat to screen pixels
    transformCoordinates(lon, lat) {
        const geoPoint = this.lonLatToPixel(lon, lat, this.zoom);
        const centerPixel = this.lonLatToPixel(this.center.lon, this.center.lat, this.zoom);
        
        const x = geoPoint.x - centerPixel.x + this.app.renderer.width / 2;
        const y = geoPoint.y - centerPixel.y + this.app.renderer.height / 2;

        return { x, y };
    }

    // Update the transform in the geometry render to match the canvas
    updateGeometryTransform() {
        if (this.geometryRenderer) {
            const transformFunction = (x, y) => {
                return this.transformCoordinates(x, y);
            };
            this.geometryRenderer.updateCoordinateTransform(transformFunction);
        }
    }

    
    // Load map tiles based on current center and zoom
    loadTiles() {
        this.tileContainer.removeChildren();

        const centerPixel = this.lonLatToPixel(this.center.lon, this.center.lat, this.zoom);
        const tileX = Math.floor(centerPixel.x / this.tileSize);
        const tileY = Math.floor(centerPixel.y / this.tileSize);

        const range = 3; // number of tiles around center tile

        for (let dx = -range; dx <= range; dx++) {
            for (let dy = -range; dy <= range; dy++) {
                const x = tileX + dx;
                const y = tileY + dy;

                const url = this.tileServer
                    .replace('{z}', this.zoom)
                    .replace('{x}', x)
                    .replace('{y}', y);
                const tile = PIXI.Sprite.from(url);

                tile.x = (x * this.tileSize) - centerPixel.x + (this.app.renderer.width / 2);
                tile.y = (y * this.tileSize) - centerPixel.y + (this.app.renderer.height / 2);

                this.tileContainer.addChild(tile);
            }
        }
    }
    
    // Set up mouse and keyboard interaction
    setupInteraction() {
        // Mouse drag handling
        let dragging = false;
        let lastMouse = null;

        this.app.view.addEventListener('mousedown', e => {
            dragging = true;
            lastMouse = { x: e.clientX, y: e.clientY };
        });

        this.app.view.addEventListener('mousemove', e => {
            if (!dragging) return;

            const dx = e.clientX - lastMouse.x;
            const dy = e.clientY - lastMouse.y;
            lastMouse = { x: e.clientX, y: e.clientY };

            const scale = (this.tileSize * Math.pow(2, this.zoom));
            const lonPerPixel = 360 / scale;
            const latPerPixel = 360 / (scale * Math.cos(this.center.lat * Math.PI / 180));

            this.center.lon -= dx * lonPerPixel;
            this.center.lat += dy * latPerPixel;

            this.loadTiles();
            this.updateGeometryTransform();
        });

        this.app.view.addEventListener('mouseup', () => {
            dragging = false;
        });

        // Keyboard navigation
        document.addEventListener('keydown', e => {
            const diff_angle = 360 / (this.tileSize * Math.pow(2, this.zoom));
            const step_size = 10;
            
            if (e.key === 'ArrowLeft') {
                this.center.lon -= step_size * diff_angle;
                this.loadTiles();
                this.updateGeometryTransform();
            }
            if (e.key === 'ArrowRight') {
                this.center.lon += step_size * diff_angle;
                this.loadTiles();
                this.updateGeometryTransform();
            }
            if (e.key === 'ArrowUp') {
                this.center.lat += step_size * diff_angle * Math.cos(this.center.lat * Math.PI / 180);
                this.loadTiles();
                this.updateGeometryTransform();
            }
            if (e.key === 'ArrowDown') {
                this.center.lat -= step_size * diff_angle * Math.cos(this.center.lat * Math.PI / 180);
                this.loadTiles();
                this.updateGeometryTransform();
            }
        });

        // Zoom with mouse wheel
        this.app.view.addEventListener('wheel', e => {
            e.preventDefault();
            const delta = Math.sign(e.deltaY);
            if (delta > 0) {
                this.zoom = Math.max(this.zoom - 1, 2);
            } else {
                this.zoom = Math.min(this.zoom + 1, 19);
            }
            this.loadTiles();
            this.updateGeometryTransform();
        });

        // Keyboard zoom
        document.addEventListener('keydown', e => {
            if (e.key === '=') {
                this.zoom = Math.min(this.zoom + 1, 19);
                this.loadTiles();
                this.updateGeometryTransform();
            } else if (e.key === '-') {
                this.zoom = Math.max(this.zoom - 1, 2);
                this.loadTiles();
                this.updateGeometryTransform();
            }
        });
    }
}