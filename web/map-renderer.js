// map-renderer.js
import { MapboxRenderer, Logger } from './mapbox-renderer.js';
import { WebSocketManager } from './websocket-manager.js';

export class MapRenderer {
    constructor(options = {}) {
        const {
            containerId = 'map-container',
            initialCenter = [0.1278, 51.5074], // London coordinates: longitude, latitude
            initialZoom = 10,
            mapStyle = 'mapbox://styles/mapbox/dark-v11',
            mapboxAccessToken = 'pk.YOUR_MAPBOX_TOKEN_HERE', // Replace with your Mapbox token
            wsOptions = {}
        } = options;

        // Create map container
        this.container = document.getElementById(containerId);
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = containerId;
            this.container.style.width = '100%';
            this.container.style.height = '100%';
            document.body.appendChild(this.container);
        } else {
            // Ensure the container has proper dimensions
            this.container.style.width = '100%';
            this.container.style.height = '100%';
        }

        // Debug information panel
        this.debugInfo = document.createElement('div');
        this.debugInfo.style.position = 'absolute';
        this.debugInfo.style.top = '10px';
        this.debugInfo.style.left = '10px';
        this.debugInfo.style.background = 'rgba(0,0,0,0.7)';
        this.debugInfo.style.color = 'white';
        this.debugInfo.style.padding = '10px';
        this.debugInfo.style.fontFamily = 'monospace';
        this.debugInfo.style.zIndex = '1000';
        document.body.appendChild(this.debugInfo);

        // Store map configuration
        this.initialCenter = initialCenter;
        this.initialZoom = initialZoom;
        this.mapStyle = mapStyle;
        this.mapboxToken = mapboxAccessToken;

        // Initialize WebSocket manager with our Mapbox renderer
        this.wsManager = new WebSocketManager({
            ...wsOptions,
            rendererOptions: {
                containerId: 'geometry-container',
                mapboxToken: this.mapboxToken,
                initialCenter: this.initialCenter,
                initialZoom: this.initialZoom,
                mapStyle: this.mapStyle,
                // Ensure this flag is set to use MapboxRenderer
                useMapbox: true
            }
        });

        // Store the Mapbox renderer instance
        this.mapboxRenderer = this.wsManager.renderer;

        // Set up window resize handler
        window.addEventListener('resize', () => {
            this.resize();
        });

        // Setup keyboard events for zooming
        this.setupKeyboardControls();

        // Update debug information
        this.updateDebugInfo();
    }

    resize() {
        // Mapbox handles resizing automatically for the most part,
        // but we can trigger a map resize event if needed
        if (this.mapboxRenderer && this.mapboxRenderer.map) {
            this.mapboxRenderer.map.resize();
        }
    }

    // Update debug information
    updateDebugInfo() {
        if (!this.mapboxRenderer || !this.mapboxRenderer.map) {
            this.debugInfo.innerHTML = "<div>Map not initialized yet</div>";
            return;
        }

        const center = this.mapboxRenderer.map.getCenter();
        const zoom = this.mapboxRenderer.map.getZoom();
        const bounds = this.mapboxRenderer.map.getBounds();

        this.debugInfo.innerHTML = `
            <div>Center: ${center.lng.toFixed(4)}, ${center.lat.toFixed(4)}</div>
            <div>Zoom: ${zoom.toFixed(2)}</div>
            <div>Bounds: [${bounds.getWest().toFixed(2)}, ${bounds.getSouth().toFixed(2)}, 
                       ${bounds.getEast().toFixed(2)}, ${bounds.getNorth().toFixed(2)}]</div>
        `;
    }

    // Setup keyboard controls for zooming, panning, etc.
    setupKeyboardControls() {
        document.addEventListener('keydown', (e) => {
            // Don't do anything if the map is not initialized
            if (!this.mapboxRenderer || !this.mapboxRenderer.map) return;

            // Zoom in with '=' or '+' key
            if (e.key === '=' || e.key === '+') {
                this.mapboxRenderer.map.zoomIn();
                this.updateDebugInfo();
            }

            // Zoom out with '-' key
            if (e.key === '-') {
                this.mapboxRenderer.map.zoomOut();
                this.updateDebugInfo();
            }

            // Reset view with 'r' key
            if (e.key === 'r') {
                this.resetView();
            }
        });
    }

    // Add a debug marker at specific coordinates
    addDebugMarker(lng, lat, color = '#ff0000') {
        if (!this.mapboxRenderer || !this.mapboxRenderer.map) return;

        this.mapboxRenderer.addDebugMarker(lng, lat, color);
        console.log(`Debug marker added at [${lng}, ${lat}]`);
    }

    // Reset the map view to the initial settings
    resetView() {
        if (!this.mapboxRenderer || !this.mapboxRenderer.map) return;

        this.mapboxRenderer.map.flyTo({
            center: this.initialCenter,
            zoom: this.initialZoom,
            essential: true
        });

        console.log("Map view reset to initial state");
        this.updateDebugInfo();
    }

    // Center the map on specific coordinates
    centerOn(lng, lat, zoom = null) {
        if (!this.mapboxRenderer || !this.mapboxRenderer.map) return;

        this.mapboxRenderer.map.flyTo({
            center: [lng, lat],
            zoom: zoom || this.mapboxRenderer.map.getZoom(),
            essential: true
        });

        console.log(`Map centered on [${lng}, ${lat}]`);
        this.updateDebugInfo();
    }
}