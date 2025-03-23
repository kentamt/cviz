// Fixed mapbox-renderer.js
import 'https://api.mapbox.com/mapbox-gl-js/v2.15.0/mapbox-gl.js';

// Configuration for topic-specific styling
export const TOPIC_STYLES = {
    // Default fallback colors
    default: {
        Point: '#00ffff',         // Cyan
        MultiPoint: '#00aaff',    // Light Blue
        LineString: '#ff0000',    // Bright Red
        MultiLineString: '#aa0000', // Dark Red
        Polygon: '#00ff00',       // Bright Green
        MultiPolygon: '#00aa00',  // Dark Green
        GeometryCollection: '#ff00ff', // Magenta
        Feature: '#ffffff',       // White
        FeatureCollection: '#ffff00' // Yellow
    },

    // Topic-specific color overrides
    "boundary": { color: '#0055ff', type: "LineString" },
    "agent": { color: '#00ffff', type: "Polygon" },
    "obstacle": { color: '#ff8800', type: "Polygon" },
    "trajectory": { color: '#333333', type: "LineString" },
    "observation": { color: '#ffcc00', type: "Point" }
};

// Helper for logging
export const Logger = {
    log: (message) => console.log(`🗺️ ${message}`),
    error: (message) => console.error(`❌ ${message}`),
    warn: (message) => console.warn(`⚠️ ${message}`),
    debug: (message) => console.debug(`🐞 ${message}`)
};

export class MapboxRenderer {
    constructor(options = {}) {
        const {
            containerId = 'map-container',
            mapboxToken = '',
            initialCenter = [0.1278, 51.5074], // London
            initialZoom = 10,
            mapStyle = 'mapbox://styles/mapbox/dark-v11'
        } = options;

        Logger.debug('Initializing MapboxRenderer');

        // Check if mapboxgl is loaded
        if (!window.mapboxgl) {
            throw new Error('Mapbox GL JS not loaded correctly');
        }

        // Create container if it doesn't exist
        this.container = document.getElementById(containerId);
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = containerId;
            document.body.appendChild(this.container);
        }

        // Fix 1: Ensure container has proper CSS for interaction
        this.container.style.width = '100%';
        this.container.style.height = '100%';
        this.container.style.position = 'absolute';
        this.container.style.top = '0';
        this.container.style.left = '0';
        this.container.style.pointerEvents = 'auto';
        this.container.style.touchAction = 'manipulation';

        // Set Mapbox access token if not already set
        if (mapboxToken && mapboxToken.length > 0) {
            window.mapboxgl.accessToken = mapboxToken;
        } else if (!window.mapboxgl.accessToken) {
            throw new Error('Mapbox access token is required. Please provide it in the constructor options or set it globally.');
        }

        Logger.log(`Initializing map with token: ${window.mapboxgl.accessToken.substring(0, 10)}...`);

        // Fix 2: Create Mapbox map with explicit interaction options
        try {
            // Use a simple configuration first without custom handlers
            this.map = new window.mapboxgl.Map({
                container: containerId,
                style: mapStyle,
                center: initialCenter,
                zoom: initialZoom,
                attributionControl: false,  // We'll add this manually later
                interactive: true           // Most important flag for all interactions
            });

            // Fix 3: Add interactive controls after basic initialization
            this.map.dragPan.enable();
            this.map.scrollZoom.enable();
            this.map.doubleClickZoom.enable();
            this.map.touchZoomRotate.enable();

            // Add a visible attribution control
            this.map.addControl(new window.mapboxgl.AttributionControl({
                compact: true
            }), 'bottom-right');

            // Add navigation controls (zoom buttons)
            this.map.addControl(new window.mapboxgl.NavigationControl(), 'top-right');

            // Add scale control
            this.map.addControl(new window.mapboxgl.ScaleControl({
                maxWidth: 100,
                unit: 'metric'
            }), 'bottom-left');

            // Fix 4: Improved cursor feedback
            this.map.getCanvas().style.cursor = 'grab';

            this.map.on('mousedown', () => {
                this.map.getCanvas().style.cursor = 'grabbing';
            });

            this.map.on('mouseup', () => {
                this.map.getCanvas().style.cursor = 'grab';
            });

        } catch (error) {
            Logger.error('Failed to create Mapbox map:', error);
            throw error;
        }

        // Fix 5: Add debug panel to verify map status
        this.addDebugPanel();

        // Track sources and layers
        this.sources = {}; // Sources added to the map
        this.layers = {};  // Layers added to the map
        this.geometryData = {}; // Store original geometry data
        this.historyLimits = {}; // Store history limits for topics
        this.lifeTimes = {};  // Store lifetime for topics

        // Fix 6: More robust loading event handling
        if (this.map.loaded()) {
            // Map already loaded, initialize now
            this.onMapLoaded();
        } else {
            // Wait for map to load before continuing initialization
            this.map.on('load', () => {
                this.onMapLoaded();
            });
        }

        // Log any errors that occur
        this.map.on('error', (e) => {
            Logger.error('Mapbox map error:', e.error);
            if (this.debugPanel) {
                this.debugPanel.innerHTML += `<br>Error: ${e.error.message || 'Unknown'}`;
            }
        });
    }

    // Fix 7: Centralized loading handler for better timing control
    onMapLoaded() {
        Logger.log('Mapbox map loaded');
        this.mapLoaded = true;

        // Add empty sources for different geometry types
        this.initializeSources();

        // Register map events
        this.registerMapEvents();

        // Verify interaction handlers are enabled
        this.verifyInteractionHandlers();

        // Log map capabilities and state
        Logger.log(`Map initialized with drag capabilities: ${this.map.dragPan.isEnabled()}`);
        Logger.log(`Map initialized with zoom capabilities: ${this.map.scrollZoom.isEnabled()}`);

        // Update debug panel
        this.updateDebugPanel();
    }

    // Fix 8: Add debug panel to verify map status
    addDebugPanel() {
        this.debugPanel = document.createElement('div');
        this.debugPanel.style.position = 'absolute';
        this.debugPanel.style.bottom = '10px';
        this.debugPanel.style.right = '10px';
        this.debugPanel.style.backgroundColor = 'rgba(0,0,0,0.7)';
        this.debugPanel.style.color = 'white';
        this.debugPanel.style.padding = '5px';
        this.debugPanel.style.borderRadius = '3px';
        this.debugPanel.style.fontSize = '12px';
        this.debugPanel.style.fontFamily = 'monospace';
        this.debugPanel.style.zIndex = '1000';
        this.debugPanel.style.pointerEvents = 'none'; // Don't interfere with map
        this.debugPanel.innerHTML = 'Map initializing...';
        document.body.appendChild(this.debugPanel);

        // Update on map move
        if (this.map) {
            this.map.on('move', () => {
                this.updateDebugPanel();
            });
        }
    }

    // Update debug panel with current map state
    updateDebugPanel() {
        if (!this.debugPanel || !this.map) return;

        const center = this.map.getCenter();
        const zoom = this.map.getZoom();

        let dragStatus = "unknown";
        let zoomStatus = "unknown";

        if (this.map.dragPan) {
            dragStatus = this.map.dragPan.isEnabled() ? "enabled" : "disabled";
        }

        if (this.map.scrollZoom) {
            zoomStatus = this.map.scrollZoom.isEnabled() ? "enabled" : "disabled";
        }

        this.debugPanel.innerHTML = `
            Center: ${center.lng.toFixed(4)}, ${center.lat.toFixed(4)}<br>
            Zoom: ${zoom.toFixed(2)}<br>
            Drag: ${dragStatus}<br>
            Scroll: ${zoomStatus}
        `;
    }

    // Fix 9: Verify interaction handlers are enabled
    verifyInteractionHandlers() {
        if (!this.map) return;

        // Ensure dragPan is enabled
        if (this.map.dragPan && !this.map.dragPan.isEnabled()) {
            Logger.warn("DragPan was disabled, enabling it");
            this.map.dragPan.enable();
        }

        // Ensure scrollZoom is enabled
        if (this.map.scrollZoom && !this.map.scrollZoom.isEnabled()) {
            Logger.warn("ScrollZoom was disabled, enabling it");
            this.map.scrollZoom.enable();
        }

        // Ensure doubleClickZoom is enabled
        if (this.map.doubleClickZoom && !this.map.doubleClickZoom.isEnabled()) {
            Logger.warn("DoubleClickZoom was disabled, enabling it");
            this.map.doubleClickZoom.enable();
        }

        // Update the debug panel
        this.updateDebugPanel();
    }

    initializeSources() {
        // Create sources for each geometry type
        const geometryTypes = [
            'Point', 'MultiPoint', 'LineString', 'MultiLineString',
            'Polygon', 'MultiPolygon', 'GeometryCollection',
            'Feature', 'FeatureCollection'
        ];

        geometryTypes.forEach(type => {
            // Create a source for this geometry type
            const sourceId = `source-${type.toLowerCase()}`;
            this.map.addSource(sourceId, {
                type: 'geojson',
                data: {
                    type: 'FeatureCollection',
                    features: []
                }
            });

            this.sources[type] = sourceId;
            this.geometryData[type] = {};

            // Add empty layers for this source based on geometry type
            this.addLayersForGeometryType(type, sourceId);
        });
    }

    addLayersForGeometryType(type, sourceId) {
        switch (type) {
            case 'Point':
            case 'MultiPoint':
                this.addPointLayer(type, sourceId);
                break;

            case 'LineString':
            case 'MultiLineString':
                this.addLineLayer(type, sourceId);
                break;

            case 'Polygon':
            case 'MultiPolygon':
                this.addPolygonLayer(type, sourceId);
                break;

            case 'GeometryCollection':
            case 'Feature':
            case 'FeatureCollection':
                // These handle multiple geometry types
                this.addPointLayer(type, sourceId);
                this.addLineLayer(type, sourceId);
                this.addPolygonLayer(type, sourceId);
                break;
        }
    }

    addPointLayer(type, sourceId) {
        const layerId = `layer-${type.toLowerCase()}-point`;

        this.map.addLayer({
            id: layerId,
            type: 'circle',
            source: sourceId,
            filter: ['==', '$type', 'Point'],
            paint: {
                'circle-radius': ['coalesce', ['get', 'radius'], 3],
                'circle-color': ['coalesce', ['get', 'color'], TOPIC_STYLES.default.Point],
                'circle-opacity': ['coalesce', ['get', 'opacity'], 0.8]
            }
        });

        if (!this.layers[type]) this.layers[type] = [];
        this.layers[type].push(layerId);

        // Add labels for points if they have a label property
        const labelLayerId = `layer-${type.toLowerCase()}-point-label`;

        this.map.addLayer({
            id: labelLayerId,
            type: 'symbol',
            source: sourceId,
            filter: ['all',
                ['==', '$type', 'Point'],
                ['has', 'label']
            ],
            layout: {
                'text-field': ['get', 'label'],
                'text-font': ['Open Sans Regular'],
                'text-size': 12,
                'text-offset': [0, -1.5],
                'text-anchor': 'bottom'
            },
            paint: {
                'text-color': '#ffffff',
                'text-halo-color': '#000000',
                'text-halo-width': 1
            }
        });

        this.layers[type].push(labelLayerId);
    }

    addLineLayer(type, sourceId) {
        const layerId = `layer-${type.toLowerCase()}-line`;

        this.map.addLayer({
            id: layerId,
            type: 'line',
            source: sourceId,
            filter: ['==', '$type', 'LineString'],
            paint: {
                'line-width': ['coalesce', ['get', 'lineWidth'], 2],
                'line-color': ['coalesce', ['get', 'color'], TOPIC_STYLES.default.LineString],
                'line-opacity': ['coalesce', ['get', 'opacity'], 1.0]
            }
        });

        if (!this.layers[type]) this.layers[type] = [];
        this.layers[type].push(layerId);
    }

    addPolygonLayer(type, sourceId) {
        // Add fill layer
        const fillLayerId = `layer-${type.toLowerCase()}-fill`;

        this.map.addLayer({
            id: fillLayerId,
            type: 'fill',
            source: sourceId,
            filter: ['==', '$type', 'Polygon'],
            paint: {
                'fill-color': ['coalesce', ['get', 'color'], TOPIC_STYLES.default.Polygon],
                'fill-opacity': ['coalesce', ['get', 'fillOpacity'], 0.2]
            }
        });

        // Add outline layer
        const outlineLayerId = `layer-${type.toLowerCase()}-outline`;

        this.map.addLayer({
            id: outlineLayerId,
            type: 'line',
            source: sourceId,
            filter: ['==', '$type', 'Polygon'],
            paint: {
                'line-width': ['coalesce', ['get', 'lineWidth'], 2],
                'line-color': ['coalesce', ['get', 'color'], TOPIC_STYLES.default.Polygon],
                'line-opacity': ['coalesce', ['get', 'lineOpacity'], 1.0]
            }
        });

        if (!this.layers[type]) this.layers[type] = [];
        this.layers[type].push(fillLayerId, outlineLayerId);
    }

    registerMapEvents() {
        // Update cursor when hovering over features
        this.map.on('mouseenter', Object.values(this.layers).flat(), () => {
            this.map.getCanvas().style.cursor = 'pointer';
        });

        this.map.on('mouseleave', Object.values(this.layers).flat(), () => {
            this.map.getCanvas().style.cursor = 'grab';
        });

        // Log click events on features
        this.map.on('click', Object.values(this.layers).flat(), (e) => {
            if (e.features && e.features.length > 0) {
                const feature = e.features[0];
                Logger.log(`Clicked on feature: ${JSON.stringify(feature.properties)}`);
            }
        });

        // Fix 10: Add specific handlers for drag events to verify they're working
        this.map.on('dragstart', () => {
            Logger.debug('Drag started');
            if (this.debugPanel) {
                this.debugPanel.innerHTML += '<br>Dragging...';
            }
        });

        this.map.on('dragend', () => {
            Logger.debug('Drag ended');
            this.updateDebugPanel();
        });

        this.map.on('zoom', () => {
            Logger.debug('Zoom event');
            this.updateDebugPanel();
        });
    }

    // Process GeoJSON data and add it to the map
    processGeometryData(data) {
        // Fix 11: More robust check for map readiness
        if (!this.map || !this.mapLoaded) {
            Logger.warn('Map not loaded yet, deferring geometry processing');
            // Queue the data processing for when the map is ready
            setTimeout(() => this.processGeometryData(data), 200);
            return;
        }

        // Extract GeoJSON data
        const geoJSON = data.data_type === 'GeoJSON' ? data : data.geojson;

        if (!geoJSON) {
            Logger.warn('No GeoJSON data found in message');
            return;
        }

        // Get topic from data
        const topic = data.topic || 'default';

        // Handle lifetime and history limits
        if (data.life_time !== undefined) {
            this.lifeTimes[topic] = data.life_time;
        } else if (geoJSON.properties && geoJSON.properties.life_time !== undefined) {
            this.lifeTimes[topic] = geoJSON.properties.life_time;
        } else {
            this.lifeTimes[topic] = 0;  // no life time limit
        }

        // Add history limit to the geometry if specified
        if (data.history_limit !== undefined) {
            this.historyLimits[topic] = data.history_limit;
        } else if (geoJSON.properties && geoJSON.properties.history_limit !== undefined) {
            this.historyLimits[topic] = geoJSON.properties.history_limit;
        } else if (geoJSON.type === 'FeatureCollection' &&
                  geoJSON.features &&
                  geoJSON.features.length > 0 &&
                  geoJSON.features[0].properties &&
                  geoJSON.features[0].properties.history_limit !== undefined) {
            this.historyLimits[topic] = geoJSON.features[0].properties.history_limit;
        } else {
            this.historyLimits[topic] = 1;
        }

        // Get the GeoJSON type
        const geoJSONType = geoJSON.type;

        // Get color from properties or default to topic color
        let color = this.getTopicColor(topic, geoJSONType);

        // Apply any overrides from properties
        if (geoJSON.properties && geoJSON.properties.color) {
            if (typeof geoJSON.properties.color === 'string') {
                color = geoJSON.properties.color;
            }
        }

        // Process GeoJSON based on its type
        this.addGeoJSONToMap(geoJSONType, geoJSON, color, topic);
    }

    addGeoJSONToMap(type, geoJSON, color, topic) {
        // First ensure it's a valid type
        if (!this.sources[type]) {
            Logger.warn(`Unsupported GeoJSON type: ${type}`);
            return;
        }

        // Initialize topic array if it doesn't exist
        if (!this.geometryData[type][topic]) {
            this.geometryData[type][topic] = [];
        }

        // Process and enhance the GeoJSON with visualization properties
        const processedGeoJSON = this.processGeoJSONForVisualization(geoJSON, color);

        // Add to the geometry data storage
        this.geometryData[type][topic].push(processedGeoJSON);

        // Manage history
        this.manageGeometryHistory(type, topic);

        // Update the map source
        this.updateMapSource(type);
    }

    processGeoJSONForVisualization(geoJSON, defaultColor) {
        // Deep clone to avoid modifying original
        const processed = JSON.parse(JSON.stringify(geoJSON));

        // For features and feature collections, ensure color properties are set
        if (processed.type === 'Feature') {
            processed.properties = processed.properties || {};
            if (!processed.properties.color) {
                processed.properties.color = defaultColor;
            }
        } else if (processed.type === 'FeatureCollection') {
            processed.features.forEach(feature => {
                feature.properties = feature.properties || {};
                if (!feature.properties.color) {
                    feature.properties.color = defaultColor;
                }
            });
        } else {
            // For other GeoJSON types, convert to Feature
            const properties = processed.properties || {};
            if (!properties.color) {
                properties.color = defaultColor;
            }

            // Create a Feature with the original geometry
            return {
                type: 'Feature',
                geometry: {
                    type: processed.type,
                    coordinates: processed.coordinates
                },
                properties: properties
            };
        }

        return processed;
    }

    manageGeometryHistory(type, topic) {
        // Get the history limit for this topic
        const historyLimit = this.historyLimits[topic] || 1;

        // Remove old geometries if we exceed the history limit
        while (this.geometryData[type][topic].length > historyLimit) {
            this.geometryData[type][topic].shift();
        }

        // Handle lifetime for temporary geometries
        const lifeTime = this.lifeTimes[topic];
        if (lifeTime > 0 && this.geometryData[type][topic].length > 0) {
            const geometry = this.geometryData[type][topic][this.geometryData[type][topic].length - 1];

            setTimeout(() => {
                // Find and remove the geometry
                const index = this.geometryData[type][topic].indexOf(geometry);
                if (index > -1) {
                    this.geometryData[type][topic].splice(index, 1);
                    this.updateMapSource(type);
                }
            }, lifeTime * 1000);
        }
    }

    updateMapSource(type) {
        // Fix 12: More robust check for map readiness
        if (!this.map || !this.mapLoaded || !this.sources[type]) {
            Logger.warn(`Cannot update source, map or source not ready: ${type}`);
            return;
        }

        // Collect all features for this source
        const features = [];

        // Gather all geometries for each topic
        Object.keys(this.geometryData[type]).forEach(topic => {
            this.geometryData[type][topic].forEach(geometry => {
                if (geometry.type === 'Feature') {
                    features.push(geometry);
                } else if (geometry.type === 'FeatureCollection') {
                    features.push(...geometry.features);
                } else {
                    // Convert regular geometry to feature
                    features.push({
                        type: 'Feature',
                        geometry: {
                            type: geometry.type,
                            coordinates: geometry.coordinates
                        },
                        properties: geometry.properties || {}
                    });
                }
            });
        });

        // Update the source data
        const sourceId = this.sources[type];
        const source = this.map.getSource(sourceId);
        if (source) {
            try {
                source.setData({
                    type: 'FeatureCollection',
                    features: features
                });
            } catch (error) {
                Logger.error(`Error updating source ${sourceId}: ${error.message}`);
            }
        } else {
            Logger.warn(`Source not found: ${sourceId}`);
        }
    }

    getTopicColor(topic, dataType) {
        // First, check if topic has a specific style
        if (TOPIC_STYLES[topic]) {
            return TOPIC_STYLES[topic].color;
        }

        // Fallback to default color for data type
        return TOPIC_STYLES.default[dataType] || '#ffffff';
    }

    // Add a debug marker at specific coordinates
    addDebugMarker(lng, lat, color = '#ff0000') {
        if (!this.mapLoaded) return;

        // Create a marker element
        const el = document.createElement('div');
        el.className = 'debug-marker';
        el.style.width = '20px';
        el.style.height = '20px';
        el.style.borderRadius = '50%';
        el.style.backgroundColor = color;
        el.style.border = '2px solid white';
        el.style.boxShadow = '0 0 5px rgba(0,0,0,0.5)';

        // Add a marker at the specified location
        new window.mapboxgl.Marker(el)
            .setLngLat([lng, lat])
            .addTo(this.map);

        // Also add a popup with coordinates
        new window.mapboxgl.Popup()
            .setLngLat([lng, lat])
            .setHTML(`<div>[${lng.toFixed(5)}, ${lat.toFixed(5)}]</div>`)
            .addTo(this.map);
    }
}