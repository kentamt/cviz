// websocket-manager.js
import { GeometryRenderer, Logger } from './geometry-renderer.js';

// Default WebSocket settings
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
            serverUrl: dynamicUrl || options.serverUrl,
            maxReconnectAttempts: MAX_RECONNECT_ATTEMPTS,
            historyLimits: { ...DEFAULT_HISTORY_LIMITS },
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
        // Add a new entry for each topic to set a decay time
        // i.e. this.decayTimes['topic_name'] = 1000;  // sec
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
            <div><strong>Connection URL:</strong> <span id="ws-url">${this.options.serverUrl}</span></div>
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
        document.getElementById('ws-url').textContent = this.options.serverUrl;
        
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
        const testWs = new WebSocket(this.options.serverUrl);
        
        testWs.onopen = () => {
            Logger.log("Test connection succeeded!");
            this.updateDebugPanel("Test connection successful");
            testWs.close();
        };
        
        testWs.onerror = (error) => {
            Logger.error(`Test connection failed: ${error.message || "Unknown error"}`);
            this.updateDebugPanel("Test connection failed", error.message || "Unknown error");
        };
        
        this.updateDebugPanel("Testing connection...");
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
        Logger.log(`WebSocket URL: ${this.options.serverUrl}`);
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
        Logger.log(`Connecting to ${this.options.serverUrl}...`);
        this.updateDebugPanel("Connecting...");

        try {
            this.ws = new WebSocket(this.options.serverUrl);
            
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
            this.updateDebugPanel(`Reconnecting in ${timeout/1000}s (${this.reconnectAttempts + 1}/${this.options.maxReconnectAttempts})`);
            
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