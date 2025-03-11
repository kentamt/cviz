// websocket-manager.js
import { GeometryRenderer, Logger } from './geometry-renderer.js';

// Default WebSocket settings
const DEFAULT_SERVER_URL = "ws://127.0.0.1:8675";
const MAX_RECONNECT_ATTEMPTS = 5;
const BASE_RECONNECT_TIMEOUT = 1000;  // 1 second

// History limits for different geometry types
const DEFAULT_HISTORY_LIMITS = {
    Text: 1,                        
    Polygon: 1,
    PolygonVector: 1,
    Point2d: 100,
    LineString: 1,
    LineStringVector: 1
};

export class WebSocketManager {
    constructor(options = {}) {
        this.options = {
            serverUrl: DEFAULT_SERVER_URL,
            maxReconnectAttempts: MAX_RECONNECT_ATTEMPTS,
            historyLimits: { ...DEFAULT_HISTORY_LIMITS },
            rendererOptions: {},
            ...options
        };

        // Delay initialization to ensure DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }

        // Create geometry renderer to expose to other renderers
        // this.geometryRenderer = new GeometryRenderer(options.rendererOptions);
        
        // Store decay time for each topic
        // Add a new entry for each topic to set a decay time
        // i.e. this.decayTimes['topic_name'] = 1000;  // sec
        this.lifeTimes = {};
        this.historyLimits = {};
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
            Text: {},
            Polygon: {},
            PolygonVector: {},
            Point2d: {},
            LineString: {},
            LineStringVector: {}
        };

        this.connectWebSocket();
    }

    connectWebSocket() {
        Logger.log(`Connecting to ${this.options.serverUrl}...`);

        this.ws = new WebSocket(this.options.serverUrl);

        this.ws.onopen = () => {
            Logger.log("WebSocket connected successfully!");
            this.reconnectAttempts = 0;
        };

        this.ws.onerror = (error) => {
            Logger.error(`WebSocket error: ${JSON.stringify(error)}`);
            Logger.error(`WebSocket error: ${error.message || "Unknown error"}`);
        };

        this.ws.onclose = (event) => {
            Logger.warn(`WebSocket closed. Code: ${event.code}, Reason: ${event.reason}`);
            this.reconnect();
        };

        this.ws.onmessage = (event) => {
            this.handleMessage(event);
        };
    }

    handleMessage(event) {
        try {
            const data = JSON.parse(event.data);
            if (this.validateGeometryData(data)) {
                this.processGeometryData(data);
            } else {
                Logger.warn("Invalid geometry data received:", data);
            }
        } catch (error) {
            Logger.error(`Message parsing error: ${error}`);
        }
    }

    processGeometryData(data) {
        this.renderer.processGeometryData(data);
    }

    validateGeometryData(data) {
        // Basic validation
        if (!data || !data.data_type) {
            return false;
        }

        const validationMap = {
            "Text": this.validateTextData,
            "Polygon": this.validatePolygonData,
            "PolygonVector": this.validatePolygonVectorData,
            "Point2d": this.validatePointData,
            "LineString": this.validateLineStringData,
            "LineStringVector": this.validateLineStringVectorData
        };

        const validator = validationMap[data.data_type];
        return validator ? validator(data) : false;
    }

    validateTextData(data) {
        return data.text && data.position && 
               typeof data.position.x === 'number' && 
               typeof data.position.y === 'number';
    }

    validatePolygonData(data) {
        return Array.isArray(data.points) && 
               data.points.length >= 3 && 
               data.points.every(p => p && typeof p.x === 'number' && typeof p.y === 'number');
    }

    validatePolygonVectorData(data) {
        return data.polygons && Array.isArray(data.polygons);
        // TODO: Add polygon validation
        // && data.polygons.points.length > 0;  # FIXME: This is not working
    }

    validatePointData(data) {
        return data.point && typeof data.point.x === 'number' && 
               typeof data.point.y === 'number';
    }

    validateLineStringData(data) {
        return Array.isArray(data.points) && 
               data.points.length >= 2 && 
               data.points.every(p => p && typeof p.x === 'number' && typeof p.y === 'number');
    }

    validateLineStringVectorData(data) {
        // TODO: Add line string vector validation
        return data.lines && Array.isArray(data.lines);
    }
    
    reconnect() {
        if (this.reconnectAttempts < this.options.maxReconnectAttempts) {
            const timeout = BASE_RECONNECT_TIMEOUT * Math.pow(2, this.reconnectAttempts);
            
            Logger.warn(`Reconnecting in ${timeout/1000} seconds... (Attempt ${this.reconnectAttempts + 1})`);
            
            this.reconnectAttempts++;
            
            setTimeout(() => {
                this.connectWebSocket();
            }, timeout);
        } else {
            Logger.error("Max reconnection attempts reached. Please check the server.");
        }
    }
}
