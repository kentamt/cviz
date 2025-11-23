// Complete fixed map-renderer.js
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

        // Create map container with proper styles
        this.container = document.getElementById(containerId);
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = containerId;
            document.body.appendChild(this.container);
        }

        // Fix 1: Ensure container has proper styles for interaction
        this.container.style.width = '100%';
        this.container.style.height = '100%';
        this.container.style.position = 'absolute';
        this.container.style.top = '0';
        this.container.style.left = '0';
        this.container.style.pointerEvents = 'auto';
        this.container.style.touchAction = 'manipulation';

        // Simple debugging panel that won't interfere with map interactions
        this.debugInfo = document.createElement('div');
        this.debugInfo.style.position = 'absolute';
        this.debugInfo.style.bottom = '50px';
        this.debugInfo.style.left = '10px';
        this.debugInfo.style.background = 'rgba(0,0,0,0.7)';
        this.debugInfo.style.color = 'white';
        this.debugInfo.style.padding = '10px';
        this.debugInfo.style.fontFamily = 'monospace';
        this.debugInfo.style.zIndex = '1000';
        this.debugInfo.style.pointerEvents = 'none'; // Critical: Don't block map events
        this.debugInfo.innerHTML = '<div>Map initializing...</div>';
        document.body.appendChild(this.debugInfo);

        // Store map configuration
        this.initialCenter = initialCenter;
        this.initialZoom = initialZoom;
        this.mapStyle = mapStyle;
        this.mapboxToken = mapboxAccessToken;

        // Fix 3: Initialize WebSocket and map with improved timing
        this.initializeMapAndWebSocket(wsOptions);

        // Setup keyboard events for zooming
        this.setupKeyboardControls();

        // Set up window resize handler
        window.addEventListener('resize', () => {
            this.resize();
        });
    }

    initializeMapAndWebSocket(wsOptions) {
        // Initialize WebSocket manager with our Mapbox renderer options
        const rendererOptions = {
            containerId: 'map-container', // Use the same container for map
            mapboxToken: this.mapboxToken,
            initialCenter: this.initialCenter,
            initialZoom: this.initialZoom,
            mapStyle: this.mapStyle,
            useMapbox: true  // Ensure this flag is set to use MapboxRenderer
        };

        // Create the MapboxRenderer first
        try {
            // Create renderer directly instead of through WebSocketManager
            this.mapboxRenderer = new MapboxRenderer(rendererOptions);

            // Wait for the map to be ready before setting up WebSocket
            if (this.mapboxRenderer.map) {
                this.mapboxRenderer.map.once('load', () => {
                    this.onMapLoaded();

                    // Now initialize the WebSocket manager
                    this.wsManager = new WebSocketManager({
                        ...wsOptions,
                        rendererOptions: {
                            ...rendererOptions,
                            mapInstance: this.mapboxRenderer.map // Pass the map instance
                        }
                    });
                });

                // Also check if map is already loaded
                if (this.mapboxRenderer.map.loaded()) {
                    this.onMapLoaded();
                }
            }
        } catch (error) {
            console.error("Error initializing map:", error);
            this.debugInfo.innerHTML = `<div>Error: ${error.message}</div>`;
        }
    }

    onMapLoaded() {
        // Map is loaded and ready
        this.debugInfo.innerHTML = '<div>Map loaded!</div>';

        // Verify that map interaction handlers are enabled
        if (this.mapboxRenderer && this.mapboxRenderer.map) {
            const map = this.mapboxRenderer.map;

            // Explicitly enable interaction handlers
            if (map.dragPan && !map.dragPan.isEnabled()) {
                map.dragPan.enable();
                console.log("Explicitly enabled drag pan");
            }

            if (map.scrollZoom && !map.scrollZoom.isEnabled()) {
                map.scrollZoom.enable();
                console.log("Explicitly enabled scroll zoom");
            }

            // Get current interaction state
            const dragEnabled = map.dragPan && map.dragPan.isEnabled();
            const zoomEnabled = map.scrollZoom && map.scrollZoom.isEnabled();

            // Update debug info
            this.debugInfo.innerHTML += `
                <div>Drag enabled: ${dragEnabled ? 'Yes' : 'No'}</div>
                <div>Zoom enabled: ${zoomEnabled ? 'Yes' : 'No'}</div>
            `;

            // Update debug info on map move events
            map.on('move', () => {
                this.updateDebugInfo();
            });
        }
    }

    setupKeyboardControls() {
        // Set up keyboard controls for map navigation
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

            // Add arrow keys for direct panning
            const panAmount = 100; // pixels to pan

            if (e.key === 'ArrowLeft') {
                this.mapboxRenderer.map.panBy([-panAmount, 0], { animate: true });
            }
            if (e.key === 'ArrowRight') {
                this.mapboxRenderer.map.panBy([panAmount, 0], { animate: true });
            }
            if (e.key === 'ArrowUp') {
                this.mapboxRenderer.map.panBy([0, -panAmount], { animate: true });
            }
            if (e.key === 'ArrowDown') {
                this.mapboxRenderer.map.panBy([0, panAmount], { animate: true });
            }
        });
    }

    resize() {
        // Resize the map when the window size changes
        if (this.mapboxRenderer && this.mapboxRenderer.map) {
            this.mapboxRenderer.map.resize();
            console.log("Resized map");
        }
    }

    updateDebugInfo() {
        // Don't update if map isn't initialized
        if (!this.mapboxRenderer || !this.mapboxRenderer.map) {
            this.debugInfo.innerHTML = "<div>Map not initialized yet</div>";
            return;
        }

        const center = this.mapboxRenderer.map.getCenter();
        const zoom = this.mapboxRenderer.map.getZoom();
        const bounds = this.mapboxRenderer.map.getBounds();

        // Get interaction state
        const dragEnabled = this.mapboxRenderer.map.dragPan &&
                           this.mapboxRenderer.map.dragPan.isEnabled() ?
                           "Yes" : "No";
        const zoomEnabled = this.mapboxRenderer.map.scrollZoom &&
                           this.mapboxRenderer.map.scrollZoom.isEnabled() ?
                           "Yes" : "No";

        this.debugInfo.innerHTML = `
            <div>Center: ${center.lng.toFixed(4)}, ${center.lat.toFixed(4)}</div>
            <div>Zoom: ${zoom.toFixed(2)}</div>
            <div>Drag: ${dragEnabled}</div>
            <div>Zoom: ${zoomEnabled}</div>
        `;
    }

    resetView() {
        // Reset the view to initial center and zoom
        if (!this.mapboxRenderer || !this.mapboxRenderer.map) return;

        this.mapboxRenderer.map.flyTo({
            center: this.initialCenter,
            zoom: this.initialZoom,
            essential: true // This makes the animation happen even if user interaction is disabled
        });

        console.log("Reset view to initial state");
        this.updateDebugInfo();
    }

    centerOn(lng, lat, zoom = null) {
        // Center the map on specific coordinates
        if (!this.mapboxRenderer || !this.mapboxRenderer.map) return;

        this.mapboxRenderer.map.flyTo({
            center: [lng, lat],
            zoom: zoom || this.mapboxRenderer.map.getZoom(),
            essential: true
        });

        console.log(`Centered map on [${lng}, ${lat}]`);
        this.updateDebugInfo();
    }

    addDebugMarker(lng, lat, color = '#ff0000') {
        // Add a visible marker to the map for debugging
        if (!this.mapboxRenderer || !this.mapboxRenderer.map) return;

        // Let the renderer add the actual marker
        this.mapboxRenderer.addDebugMarker(lng, lat, color);
        console.log(`Added debug marker at [${lng}, ${lat}]`);
    }

    setTopics(topics) {
        if (this.wsManager && typeof this.wsManager.setTopics === 'function') {
            this.wsManager.setTopics(topics);
        }
    }

    subscribeToTopics(topics) {
        if (this.wsManager && typeof this.wsManager.subscribeToTopics === 'function') {
            this.wsManager.subscribeToTopics(topics);
        }
    }

    unsubscribeFromTopics(topics) {
        if (this.wsManager && typeof this.wsManager.unsubscribeFromTopics === 'function') {
            this.wsManager.unsubscribeFromTopics(topics);
        }
    }

    clearTopic(topic) {
        if (this.mapboxRenderer && typeof this.mapboxRenderer.clearTopic === 'function') {
            this.mapboxRenderer.clearTopic(topic);
        }
    }
}
