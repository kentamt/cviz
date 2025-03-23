// websocket-manager.js
import { GeometryRenderer, Logger } from './geometry-renderer.js';

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

// Determine the WebSocket URL dynamically based on the current page location
function getWebSocketUrl() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host; // Includes hostname and port if specified

    // Use the same host that's serving the web page, with the path to the WebSocket endpoint
    return `${protocol}//${host}/ws`;
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

        // Create debug element for connection status
        this.createDebugPanel();

        // Delay initialization to ensure DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }

        // Store decay time for each topic
        this.lifeTimes = {};
        this.historyLimits = {};
    }

    createDebugPanel() {
        // Create a debug panel to display connection status
        const debugPanel = document.createElement('div');
        debugPanel.id = 'ws-debug-panel';
        debugPanel.style.position = 'fixed';
        debugPanel.style.bottom = '10px';
        debugPanel.style.right = '10px';
        debugPanel.style.backgroundColor = 'rgba(0,0,0,0.7)';
        debugPanel.style.color = 'white';
        debugPanel.style.padding = '10px';
        debugPanel.style.borderRadius = '5px';
        debugPanel.style.fontFamily = 'monospace';
        debugPanel.style.fontSize = '12px';
        debugPanel.style.zIndex = '9999';
        debugPanel.style.maxWidth = '400px';
        debugPanel.style.maxHeight = '200px';
        debugPanel.style.overflowY = 'auto';

        // Add initial content
        debugPanel.innerHTML = `
            <div><strong>WebSocket Status:</strong> <span id="ws-status">Initializing...</span></div>
            <div><strong>Connection URL:</strong> <span id="ws-url">${getWebSocketUrl()}</span></div>
            <div><strong>Connection Attempts:</strong> <span id="ws-attempts">0</span></div>
            <div><strong>Network Info:</strong> <span id="ws-network">Checking...</span></div>
            <div><strong>Last Error:</strong> <span id="ws-error">None</span></div>
            <button id="ws-test-btn" style="margin-top: 5px; padding: 2px 5px;">Test Connection</button>
        `;

        // Append to document when ready
        if (document.body) {
            document.body.appendChild(debugPanel);
            document.getElementById('ws-test-btn').addEventListener('click', () => this.testConnection());
        } else {
            document.addEventListener('DOMContentLoaded', () => {
                document.body.appendChild(debugPanel);
                document.getElementById('ws-test-btn').addEventListener('click', () => this.testConnection());
            });
        }

        this.debugPanel = debugPanel;
    }

    updateDebugPanel(status, error = null) {
        if (!document.getElementById('ws-status')) return;

        document.getElementById('ws-status').textContent = status;
        document.getElementById('ws-attempts').textContent = this.reconnectAttempts;
        document.getElementById('ws-url').textContent = getWebSocketUrl();

        if (error) {
            document.getElementById('ws-error').textContent = error;
            document.getElementById('ws-error').style.color = 'red';
        }

        // Get network information
        const networkInfo = [];
        if (window.location && window.location.hostname) {
            networkInfo.push(`Page host: ${window.location.hostname}:${window.location.port}`);
        }

        // Check if running in Docker
        fetch('/health')
            .then(response => response.json())
            .then(data => {
                networkInfo.push(`Server health: ${data.status}`);
                document.getElementById('ws-network').innerHTML = networkInfo.join('<br>');
            })
            .catch(err => {
                networkInfo.push(`Server health check failed: ${err.message}`);
                document.getElementById('ws-network').innerHTML = networkInfo.join('<br>');
            });
    }

    testConnection() {
        // Attempt to create a temporary WebSocket connection to test connectivity
        this.updateDebugPanel("Testing connection...");

        // Send a ping request to the health endpoint instead of creating a WebSocket
        fetch('/health')
            .then(response => response.json())
            .then(data => {
                Logger.log("Server health check succeeded:", data);
                this.updateDebugPanel(`Connection test successful: ${JSON.stringify(data)}`);
            })
            .catch(error => {
                Logger.error(`Connection test failed: ${error.message || "Unknown error"}`);
                this.updateDebugPanel("Connection test failed", error.message || "Unknown error");
            });
    }

    init() {
        try {
            this.renderer = new GeometryRenderer(this.options.rendererOptions);
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
                this.updateDebugPanel(`Health OK: ${JSON.stringify(data)}`);
            })
            .catch(error => {
                Logger.error(`Server health check failed: ${error.message}`);
                this.updateDebugPanel("Health check failed", error.message);
            });
    }

    connectWebSocket() {
        Logger.log(`Connecting to ${getWebSocketUrl()}...`);
        this.updateDebugPanel("Connecting...");

        try {
            this.ws = new WebSocket(getWebSocketUrl());

            // Track connection timeout
            const connectionTimeout = setTimeout(() => {
                if (this.ws && this.ws.readyState !== WebSocket.OPEN) {
                    Logger.error("WebSocket connection timeout");
                    this.updateDebugPanel("Connection timeout");
                    this.ws.close();
                }
            }, 5000);

            this.ws.onopen = () => {
                clearTimeout(connectionTimeout);
                Logger.log("WebSocket connected successfully!");
                this.reconnectAttempts = 0;
                this.updateDebugPanel("Connected");
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
                this.updateDebugPanel("Connection error", `${errorMsg} (${detailedError})`);
            };

            this.ws.onclose = (event) => {
                clearTimeout(connectionTimeout);
                Logger.warn(`WebSocket closed. Code: ${event.code}, Reason: ${event.reason || "No reason provided"}`);
                this.updateDebugPanel("Disconnected", `Code: ${event.code}, Reason: ${event.reason || "No reason"}`);
                this.reconnect();
            };

            this.ws.onmessage = (event) => {
                this.handleMessage(event);
            };
        } catch (error) {
            Logger.error(`WebSocket creation error: ${error.message}`);
            this.updateDebugPanel("Creation error", error.message);
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

    processGeoJSONMessage(data) {
        this.renderer.processGeometryData(data);
    }

    reconnect() {
        if (this.reconnectAttempts < this.options.maxReconnectAttempts) {
            const timeout = BASE_RECONNECT_TIMEOUT * Math.pow(2, this.reconnectAttempts);

            Logger.warn(`Reconnecting in ${timeout / 1000} seconds... (Attempt ${this.reconnectAttempts + 1})`);
            this.updateDebugPanel(`Reconnecting in ${timeout / 1000}s (${this.reconnectAttempts + 1}/${this.options.maxReconnectAttempts})`);

            this.reconnectAttempts++;

            setTimeout(() => {
                this.connectWebSocket();
            }, timeout);
        } else {
            Logger.error("Max reconnection attempts reached. Please check the server.");
            this.updateDebugPanel("Failed - max attempts reached");
        }
    }
}