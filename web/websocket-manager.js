// websocket-manager.js
import { GeometryRenderer, Logger } from './geometry-renderer.js';
import { MapboxRenderer } from './mapbox-renderer.js';
import { TopicsPanel } from './topics-panel.js';

// Default WebSocket settings
const MAX_RECONNECT_ATTEMPTS = 5;
const BASE_RECONNECT_TIMEOUT = 1000;  // 1 second

// History limits for different geometry types
const DEFAULT_HISTORY_LIMITS = {
    Point: 1,
    MultiPoint: 1,
    LineString: 1,
    MultiLineString: 1,
    Polygon: 1,
    MultiPolygon: 1,
    GeometryCollection: 1,
    Feature: 1,
    FeatureCollection: 1
};

const TOPICS_STORAGE_KEY = 'cviz_selected_topics';

// Determine the WebSocket URL dynamically based on the current page location
function getWebSocketUrl() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host; // Includes hostname and port if specified

    // Use the same host that's serving the web page, with the path to the WebSocket endpoint
    return `${protocol}//${host}/ws`;
}

function normalizeTopicsInput(input) {
    if (!input) {
        return [];
    }

    let topics = [];
    if (Array.isArray(input)) {
        topics = input;
    } else if (typeof input === 'string') {
        topics = input.split(',');
    } else {
        return [];
    }

    return topics
        .map(topic => {
            if (typeof topic === 'string') {
                return topic.trim();
            }
            if (topic === null || topic === undefined) {
                return '';
            }
            return String(topic).trim();
        })
        .filter(topic => topic.length > 0);
}

export class WebSocketManager {
    constructor(options = {}) {
        // Dynamically determine the WebSocket URL
        const dynamicUrl = getWebSocketUrl();
        Logger.log(`Using dynamic WebSocket URL: ${dynamicUrl}`);

        this.options = {
            serverUrl: dynamicUrl,
            maxReconnectAttempts: MAX_RECONNECT_ATTEMPTS,
            historyLimits: {...DEFAULT_HISTORY_LIMITS},
            rendererOptions: {},
            ...options
        };

        this.autoSubscribeFromHealth = this.options.autoSubscribeFromHealth !== false;
        this.pendingCommands = [];
        this.healthTopics = [];
        this.topicPanel = null;

        const optionTopics = normalizeTopicsInput(this.options.topics || this.options.defaultTopics);
        const globalTopicsSource = typeof window !== 'undefined' ? window.CVIZ_TOPICS : undefined;
        const globalTopics = normalizeTopicsInput(globalTopicsSource);
        const storedTopics = this.loadStoredTopics();
        let initialTopics = optionTopics.length > 0 ? optionTopics : (storedTopics.length > 0 ? storedTopics : globalTopics);
        const queryTopics = this.getTopicsFromQuery();
        if (initialTopics.length === 0 && queryTopics.length > 0) {
            initialTopics = queryTopics;
        } else if (queryTopics.length > 0) {
            initialTopics = queryTopics;
        }
        this.desiredTopics = new Set(initialTopics);

        // Delay initialization to ensure DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }

        // Store decay time for each topic
        this.lifeTimes = {};
        this.historyLimits = {};

        if (this.desiredTopics.size > 0) {
            this.ensureSubscriptionCommandQueued();
        }
    }

    getTopicsFromQuery() {
        if (typeof window === 'undefined' || !window.location) {
            return [];
        }

        try {
            const params = new URLSearchParams(window.location.search);
            if (!params.has('topics')) {
                return [];
            }
            return normalizeTopicsInput(params.get('topics'));
        } catch (error) {
            Logger.warn(`Unable to parse topics from query string: ${error.message}`);
            return [];
        }
    }

    init() {
        try {
            // Choose the renderer based on options or detect if we're using the map version
            if (this.options.rendererOptions.mapboxToken || this.options.rendererOptions.useMapbox) {
                Logger.log('Using MapboxRenderer');
                this.renderer = new MapboxRenderer(this.options.rendererOptions);
            } else {
                Logger.log('Using GeometryRenderer');
                this.renderer = new GeometryRenderer(this.options.rendererOptions);
            }
        } catch (error) {
            Logger.error(`Detailed renderer initialization error: ${error.message}`);
            Logger.error(`Error stack: ${error.stack}`);

            // Create a user-friendly error display
            const errorDiv = document.createElement('div');
            errorDiv.style.color = 'red';
            errorDiv.style.padding = '20px';
            errorDiv.style.backgroundColor = '#ffee00';
            errorDiv.innerHTML = `
                <h2>Renderer Initialization Failed</h2>
                <p>There was an error setting up the graphics renderer:</p>
                <pre>${error.message}</pre>
                <p>Possible causes:
                    - Pixi.js not loaded correctly
                    - Browser compatibility issues
                    - Missing dependencies
                </p>
            `;
            document.body.appendChild(errorDiv);

            return;
        }

        this.ws = null;
        this.reconnectAttempts = 0;
        this.geometries = {
            Point: {},
            MultiPoint: {},
            LineString: {},
            MultiLineString: {},
            Polygon: {},
            MultiPolygon: {},
            GeometryCollection: {},
            Feature: {},
            FeatureCollection: {}
        };

        // Log network information before connecting
        this.logNetworkInfo();

        // Delay connection slightly to ensure everything is ready
        setTimeout(() => {
            this.connectWebSocket();
        }, 1000);

        this.topicPanel = new TopicsPanel(this);
        this.topicPanel.updateSelection(this.desiredTopics);
    }

    logNetworkInfo() {
        Logger.log("--- Network Information ---");
        Logger.log(`Page URL: ${window.location.href}`);
        Logger.log(`WebSocket URL: ${getWebSocketUrl()}`);
        Logger.log(`Navigator online: ${navigator.onLine}`);

        // Try to fetch the server health endpoint
        fetch('/health')
           .then(response => response.json())
           .then(data => {
                Logger.log(`Server health check: ${JSON.stringify(data)}`);

               if (Array.isArray(data.topics)) {
                   this.healthTopics = data.topics;
                   if (this.autoSubscribeFromHealth && this.desiredTopics.size === 0 && this.healthTopics.length > 0) {
                       this.setTopics(this.healthTopics);
                   }
                    if (this.topicPanel) {
                        this.topicPanel.setTopics(data.available_topics || this.healthTopics);
                    }
               }
            })
            .catch(error => {
                Logger.error(`Server health check failed: ${error.message}`);
            });
    }

    connectWebSocket() {
        Logger.log(`Connecting to ${getWebSocketUrl()}...`);

        try {
            this.ws = new WebSocket(getWebSocketUrl());

            // Track connection timeout
            const connectionTimeout = setTimeout(() => {
                if (this.ws && this.ws.readyState !== WebSocket.OPEN) {
                    Logger.error("WebSocket connection timeout");
                    this.ws.close();
                }
            }, 5000);

            this.ws.onopen = () => {
                clearTimeout(connectionTimeout);
                Logger.log("WebSocket connected successfully!");
                this.reconnectAttempts = 0;

                 const hadPending = this.pendingCommands.length > 0;
                 this.flushPendingCommands();

                 if (!hadPending) {
                     if (this.desiredTopics.size > 0) {
                         this.sendSubscriptionUpdate();
                     } else if (this.autoSubscribeFromHealth && this.healthTopics.length > 0) {
                         this.setTopics(this.healthTopics);
                     }
                 }
            };

            this.ws.onerror = (error) => {
                clearTimeout(connectionTimeout);
                const errorMsg = error.message || "Unknown error";
                Logger.error(`WebSocket error: ${errorMsg}`);

                // Get more details about the error if possible
                let detailedError = "No additional details available";
                if (error.target) {
                    detailedError = `ReadyState: ${error.target.readyState}`;
                }

                Logger.error(`WebSocket detailed error: ${detailedError}`);
            };

            this.ws.onclose = (event) => {
                clearTimeout(connectionTimeout);
                Logger.warn(`WebSocket closed. Code: ${event.code}, Reason: ${event.reason || "No reason provided"}`);
                this.ensureSubscriptionCommandQueued();
                this.reconnect();
            };

            this.ws.onmessage = (event) => {
                this.handleMessage(event);
            };
        } catch (error) {
            Logger.error(`WebSocket creation error: ${error.message}`);
            this.reconnect();
        }
    }

    handleMessage(event) {
        try {
            const data = JSON.parse(event.data);

            // Check if this is a GeoJSON message
            if (this.isGeoJSONMessage(data)) {
                this.processGeoJSONMessage(data);
            }
            // Check if this is a legacy format message that needs conversion
            else if (this.isLegacyFormatMessage(data)) {
                const geoJSON = this.convertLegacyToGeoJSON(data);
                if (geoJSON) {
                    this.processGeoJSONMessage({
                        data_type: 'GeoJSON',
                        topic: data.topic,
                        history_limit: data.history_limit,
                        life_time: data.life_time,
                        geojson: geoJSON
                    });
                }
            } else {
                Logger.warn("Unknown message format received:", data);
            }
        } catch (error) {
            Logger.error(`Message parsing error: ${error.message}`, error.stack);
        }
    }

    isGeoJSONMessage(data) {
        // Check if the message is already in GeoJSON format
        return data.data_type === 'GeoJSON' ||
            (data.geojson && data.geojson.type &&
                ['Point', 'MultiPoint', 'LineString', 'MultiLineString',
                    'Polygon', 'MultiPolygon', 'GeometryCollection',
                    'Feature', 'FeatureCollection'].includes(data.geojson.type));
    }

    isLegacyFormatMessage(data) {
        // Check if the message is in the legacy format (needs conversion)
        return data.data_type && ['Polygon', 'PolygonVector', 'Point2d',
            'LineString', 'LineStringVector', 'Text'].includes(data.data_type);
    }

    convertLegacyToGeoJSON(data) {
        // Convert legacy format to GeoJSON
        try {
            switch (data.data_type) {
                case 'Polygon':
                    return this.convertPolygonToGeoJSON(data);
                case 'PolygonVector':
                    return this.convertPolygonVectorToGeoJSON(data);
                case 'Point2d':
                    return this.convertPointToGeoJSON(data);
                case 'LineString':
                    return this.convertLineStringToGeoJSON(data);
                case 'LineStringVector':
                    return this.convertLineStringVectorToGeoJSON(data);
                case 'Text':
                    return this.convertTextToGeoJSON(data);
                default:
                    Logger.warn(`Unknown legacy data type: ${data.data_type}`);
                    return null;
            }
        } catch (error) {
            Logger.error(`Error converting legacy format to GeoJSON: ${error.message}`);
            return null;
        }
    }

    convertPolygonToGeoJSON(data) {
        if (!data.points || !Array.isArray(data.points)) {
            return null;
        }

        // Convert points to GeoJSON coordinates format
        const coordinates = [data.points.map(p => [p.x, p.y])];

        // Close the polygon if needed (first point = last point)
        if (coordinates[0].length > 0 &&
            (coordinates[0][0][0] !== coordinates[0][coordinates[0].length - 1][0] ||
                coordinates[0][0][1] !== coordinates[0][coordinates[0].length - 1][1])) {
            coordinates[0].push([...coordinates[0][0]]);
        }

        // Create properties object from any additional fields
        const properties = {...data};
        delete properties.data_type;
        delete properties.points;
        delete properties.topic;

        // Return GeoJSON polygon
        return {
            type: 'Polygon',
            coordinates,
            properties
        };
    }

    convertPolygonVectorToGeoJSON(data) {
        if (!data.polygons || !Array.isArray(data.polygons)) {
            return null;
        }

        // Convert to GeoJSON MultiPolygon or FeatureCollection
        if (data.polygons.length === 0) {
            return {
                type: 'MultiPolygon',
                coordinates: [],
                properties: {}
            };
        }

        // Create a FeatureCollection with polygon features
        const features = data.polygons.map((polygon, index) => {
            // Convert polygon points to coordinates
            const coordinates = [polygon.points.map(p => [p.x, p.y])];

            // Close the polygon if needed
            if (coordinates[0].length > 0 &&
                (coordinates[0][0][0] !== coordinates[0][coordinates[0].length - 1][0] ||
                    coordinates[0][0][1] !== coordinates[0][coordinates[0].length - 1][1])) {
                coordinates[0].push([...coordinates[0][0]]);
            }

            return {
                type: 'Feature',
                geometry: {
                    type: 'Polygon',
                    coordinates
                },
                properties: {
                    id: polygon.id || `polygon_${index}`,
                    color: data.color || polygon.color,
                    ...polygon.properties
                }
            };
        });

        // Create properties object from any additional fields
        const properties = {...data};
        delete properties.data_type;
        delete properties.polygons;
        delete properties.topic;

        return {
            type: 'FeatureCollection',
            features,
            properties
        };
    }

    convertPointToGeoJSON(data) {
        if (!data.point) {
            return null;
        }

        // Create properties object from any additional fields
        const properties = {...data};
        delete properties.data_type;
        delete properties.point;
        delete properties.topic;

        // Return GeoJSON point
        return {
            type: 'Point',
            coordinates: [data.point.x, data.point.y],
            properties
        };
    }

    convertLineStringToGeoJSON(data) {
        if (!data.points || !Array.isArray(data.points)) {
            return null;
        }

        // Convert points to GeoJSON coordinates format
        const coordinates = data.points.map(p => [p.x, p.y]);

        // Create properties object from any additional fields
        const properties = {...data};
        delete properties.data_type;
        delete properties.points;
        delete properties.topic;

        // Return GeoJSON LineString
        return {
            type: 'LineString',
            coordinates,
            properties
        };
    }

    convertLineStringVectorToGeoJSON(data) {
        if (!data.lines || !Array.isArray(data.lines)) {
            return null;
        }

        // Convert to GeoJSON MultiLineString or FeatureCollection
        if (data.lines.length === 0) {
            return {
                type: 'MultiLineString',
                coordinates: [],
                properties: {}
            };
        }

        // Create a FeatureCollection with LineString features
        const features = data.lines.map((line, index) => {
            // Convert line points to coordinates
            const coordinates = line.points.map(p => [p.x, p.y]);

            return {
                type: 'Feature',
                geometry: {
                    type: 'LineString',
                    coordinates
                },
                properties: {
                    id: line.id || `line_${index}`,
                    color: data.color || line.color,
                    ...line.properties
                }
            };
        });

        // Create properties object from any additional fields
        const properties = {...data};
        delete properties.data_type;
        delete properties.lines;
        delete properties.topic;

        return {
            type: 'FeatureCollection',
            features,
            properties
        };
    }

    convertTextToGeoJSON(data) {
        if (!data.text || !data.position) {
            return null;
        }

        // Create properties object including the text
        const properties = {
            ...data,
            label: data.text // Use text as label in GeoJSON
        };
        delete properties.data_type;
        delete properties.text;
        delete properties.position;
        delete properties.topic;

        // Return GeoJSON Point with text in properties
        return {
            type: 'Feature',
            geometry: {
                type: 'Point',
                coordinates: [data.position.x, data.position.y]
            },
            properties
        };
    }

    queueCommand(payload) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(payload));
            return;
        }

        if (payload.action === 'set_topics') {
            this.pendingCommands = this.pendingCommands.filter(cmd => cmd.action !== 'set_topics');
        }

        this.pendingCommands.push(payload);
    }

    flushPendingCommands() {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            return;
        }

        while (this.pendingCommands.length > 0) {
            const payload = this.pendingCommands.shift();
            this.ws.send(JSON.stringify(payload));
        }
    }

    ensureSubscriptionCommandQueued() {
        if (this.desiredTopics.size === 0) {
            return;
        }

        this.queueCommand({
            action: 'set_topics',
            topics: Array.from(this.desiredTopics)
        });
    }

    setTopics(topics) {
        const normalized = normalizeTopicsInput(topics);
        const previous = new Set(this.desiredTopics);
        this.desiredTopics = new Set(normalized);
        const removed = [...previous].filter(topic => !this.desiredTopics.has(topic));
        this.clearRendererTopics(removed);
        this.filterRendererTopics(this.desiredTopics);
        this.persistTopics();
        if (this.topicPanel) {
            this.topicPanel.updateSelection(this.desiredTopics);
        }
        this.sendSubscriptionUpdate();
    }

    subscribeToTopics(topics) {
        const normalized = normalizeTopicsInput(topics);
        normalized.forEach(topic => this.desiredTopics.add(topic));
        this.persistTopics();
        if (this.topicPanel) {
            this.topicPanel.updateSelection(this.desiredTopics);
        }
        this.sendSubscriptionUpdate();
    }

    unsubscribeFromTopics(topics) {
        const normalized = normalizeTopicsInput(topics);
        const removed = [];
        normalized.forEach(topic => {
            if (this.desiredTopics.has(topic)) {
                this.desiredTopics.delete(topic);
                removed.push(topic);
            }
        });
        this.clearRendererTopics(removed);
        this.persistTopics();
        if (this.topicPanel) {
            this.topicPanel.updateSelection(this.desiredTopics);
        }
        this.sendSubscriptionUpdate();
    }

    sendSubscriptionUpdate() {
        this.ensureSubscriptionCommandQueued();
        this.flushPendingCommands();
    }

    clearRendererTopics(topics) {
        if (!this.renderer || !topics || topics.length === 0) {
            return;
        }

        topics.forEach(topic => {
            if (this.renderer && typeof this.renderer.clearTopic === 'function') {
                this.renderer.clearTopic(topic);
            }
        });

        this.refreshRenderer();
    }

    filterRendererTopics(allowedTopicsSet) {
        if (!this.renderer || !allowedTopicsSet) {
            return;
        }

        if (typeof this.renderer.filterTopics === 'function') {
            this.renderer.filterTopics(allowedTopicsSet);
        } else {
            this.refreshRenderer();
        }
    }

    refreshRenderer() {
        if (!this.renderer) return;

        if (typeof this.renderer.refreshSources === 'function') {
            this.renderer.refreshSources();
        } else if (typeof this.renderer.redrawAllGeometries === 'function') {
            this.renderer.redrawAllGeometries();
        }
    }

    loadStoredTopics() {
        if (typeof window === 'undefined' || !window.localStorage) {
            return [];
        }

        try {
            const stored = window.localStorage.getItem(TOPICS_STORAGE_KEY);
            if (!stored) {
                return [];
            }
            const parsed = JSON.parse(stored);
            return normalizeTopicsInput(parsed);
        } catch (error) {
            Logger.warn(`Failed to load stored topics: ${error.message}`);
            return [];
        }
    }

    persistTopics() {
        if (typeof window === 'undefined' || !window.localStorage) {
            return;
        }

        try {
            window.localStorage.setItem(TOPICS_STORAGE_KEY, JSON.stringify(Array.from(this.desiredTopics)));
        } catch (error) {
            Logger.warn(`Failed to persist topics: ${error.message}`);
        }
    }

    processGeoJSONMessage(data) {
     // If we don't have GeoJSON data but have a regular message
        if (!this.isGeoJSONMessage(data) && data) {
            // Try to extract any top-level history_limit or life_time
            const topLevelData = {
                data_type: 'GeoJSON',
                topic: data.topic,
                geojson: data
            };

            // Copy history_limit if present at the top level
            if (data.history_limit !== undefined) {
                topLevelData.history_limit = data.history_limit;
            }

            // Copy life_time if present at the top level
            if (data.life_time !== undefined) {
                topLevelData.life_time = data.life_time;
            }

            this.renderer.processGeometryData(topLevelData);
        } else {
            this.renderer.processGeometryData(data);
        }
    }

    reconnect() {
        if (this.reconnectAttempts < this.options.maxReconnectAttempts) {
            const timeout = BASE_RECONNECT_TIMEOUT * Math.pow(2, this.reconnectAttempts);

            Logger.warn(`Reconnecting in ${timeout / 1000} seconds... (Attempt ${this.reconnectAttempts + 1})`);

            this.reconnectAttempts++;

            setTimeout(() => {
                this.connectWebSocket();
            }, timeout);
        } else {
            Logger.error("Max reconnection attempts reached. Please check the server.");
        }
    }
}
