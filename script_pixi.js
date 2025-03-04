import * as PIXI from './node_modules/pixi.js/dist/pixi.mjs';

// Debugging and connection settings
const SERVER_URL = "ws://127.0.0.1:6789";
const MAX_RECONNECT_ATTEMPTS = 5;
const BASE_RECONNECT_TIMEOUT = 1000;  // 1 second

// Logging wrapper
const Logger = {
    log: (message) => console.log(`🌐 ${message}`),
    error: (message) => console.error(`❌ ${message}`),
    warn: (message) => console.warn(`⚠️ ${message}`)
};

// Configuration for topic-specific styling
const TOPIC_STYLES = {
    // Default fallback colors
    default: {
        Polygon: 0x00ff00,      // Bright Green
        Point2d: 0x00ffff,       // Cyan
        LineString: 0xff0000     // Bright Red
    },
    
    // Topic-specific color overrides
    "polygon_car": { color: 0x0000ff, type: "Polygon" },     // Blue
    "polygon_truck": { color: 0xff8800, type: "Polygon" },   // Orange
    "point_gps": { color: 0x00ff00, type: "Point2d" },       // Bright Green
    "point_landmark": { color: 0xff00ff, type: "Point2d" },  // Magenta
    "line_path": { color: 0xffff00, type: "LineString" },    // Yellow
    "line_boundary": { color: 0x00ffff, type: "LineString" } // Cyan
};

class GeometryRenderer {
    constructor() {
        // Ensure PIXI is loaded
        if (!PIXI) {
            throw new Error('Pixi.js not loaded');
        }

        // Create a container for the Pixi application
        this.container = document.createElement('div');
        this.container.id = 'pixi-container';
        document.body.appendChild(this.container);

        // Initialize Pixi application
        this.app = new PIXI.Application({
            width: window.innerWidth,
            height: window.innerHeight,
            backgroundColor: 0x101010,
            resolution: window.devicePixelRatio || 1,
            autoDensity: true
        });

        // Append Pixi view to the container
        this.container.appendChild(this.app.view);

        // Containers for different geometry types
        this.geometryContainers = {
            Polygon: new PIXI.Container(),
            Point2d: new PIXI.Container(),
            LineString: new PIXI.Container()
        };

        // Add containers to the stage
        Object.values(this.geometryContainers).forEach(container => {
            this.app.stage.addChild(container);
        });

        // Resize handling
        window.addEventListener('resize', () => this.resize());
    }

    resize() {
        // Ensure the renderer exists before resizing
        if (this.app?.renderer) {
            this.app.renderer.resize(window.innerWidth, window.innerHeight);
        }
    }

    getTopicColor(topic, dataType) {
        // First, check if topic has a specific style
        if (TOPIC_STYLES[topic]) {
            return TOPIC_STYLES[topic].color;
        }
        
        // Fallback to default color for data type
        return TOPIC_STYLES.default[dataType] || 0xffffff;
    }

    drawPolygon(points, color, topic) {
        if (points.length < 3) return null;

        const graphics = new PIXI.Graphics();
        graphics.beginFill(color, 0.7);
        graphics.lineStyle(2, color, 1);

        // Move to first point
        graphics.moveTo(points[0].x, this.flipY(points[0].y));

        // Draw lines to subsequent points
        for (let i = 1; i < points.length; i++) {
            graphics.lineTo(points[i].x, this.flipY(points[i].y));
        }

        // Close the polygon
        graphics.closePath();
        graphics.endFill();

        // Add metadata for potential interaction
        graphics.topic = topic;

        return graphics;
    }

    drawPoint(point, color, topic, radius = 5) {
        const graphics = new PIXI.Graphics();
        graphics.beginFill(color, 0.7);
        graphics.drawCircle(point.x, this.flipY(point.y), radius);
        graphics.endFill();

        // Add metadata for potential interaction
        graphics.topic = topic;

        return graphics;
    }

    drawLineString(points, color, topic, lineWidth = 2) {
        if (points.length < 2) return null;

        const graphics = new PIXI.Graphics();
        graphics.lineStyle(lineWidth, color, 1);

        // Move to first point
        graphics.moveTo(points[0].x, this.flipY(points[0].y));

        // Draw lines to subsequent points
        for (let i = 1; i < points.length; i++) {
            graphics.lineTo(points[i].x, this.flipY(points[i].y));
        }

        // Add metadata for potential interaction
        graphics.topic = topic;

        return graphics;
    }

    // Flip Y coordinate to match typical coordinate system
    flipY(y) {
        return this.app.renderer.height - y;
    }

    // Clear geometries for a specific type or topic
    clear(type, topic) {
        const container = this.geometryContainers[type];
        
        // Remove geometries matching the topic (or all if no topic specified)
        container.children.forEach(child => {
            if (!topic || child.topic === topic) {
                container.removeChild(child);
                child.destroy();
            }
        });
    }

    // Add a geometry to the appropriate container
    addGeometry(type, geometry, topic) {
        if (geometry) {
            this.geometryContainers[type].addChild(geometry);
        }
    }
}

class WebSocketManager {
    constructor() {
        // Delay initialization to ensure DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }

    init() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.geometries = {
            Polygon: {},
            Point2d: {},
            LineString: {}
        };

        // Initialize renderer
        try {
            this.renderer = new GeometryRenderer();
        } catch (error) {
            Logger.error(`Failed to initialize renderer: ${error.message}`);
            return;
        }

        this.connectWebSocket();
    }

    validateGeometryData(data) {
        const validTypes = {
            Polygon: (data) => (
                data && 
                data.data_type === "Polygon" && 
                data.topic &&
                Array.isArray(data.points) && 
                data.points.length > 0 && 
                data.points.every(point => 
                    point && 
                    typeof point.x === 'number' && 
                    typeof point.y === 'number'
                )
            ),
            Point2d: (data) => (
                data && 
                data.data_type === "Point2d" && 
                data.topic &&
                data.point && 
                typeof data.point.x === 'number' && 
                typeof data.point.y === 'number'
            ),
            LineString: (data) => (
                data && 
                data.data_type === "LineString" && 
                data.topic &&
                Array.isArray(data.points) && 
                data.points.length > 1 && 
                data.points.every(point => 
                    point && 
                    typeof point.x === 'number' && 
                    typeof point.y === 'number'
                )
            )
        };

        return validTypes[data.data_type] ? validTypes[data.data_type](data) : false;
    }

    connectWebSocket() {
        Logger.log(`Connecting to ${SERVER_URL}...`);

        this.ws = new WebSocket(SERVER_URL);

        this.ws.onopen = () => {
            Logger.log("WebSocket connected successfully!");
            this.reconnectAttempts = 0;
        };

        this.ws.onerror = (error) => {
            Logger.error(`WebSocket error: ${JSON.stringify(error)}`);
        };

        this.ws.onclose = (event) => {
            Logger.warn(`WebSocket closed. Code: ${event.code}, Reason: ${event.reason}`);
            this.reconnect();
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                if (this.validateGeometryData(data)) {
                    const type = data.data_type;
                    const topic = data.topic;
                    
                    // Initialize topic array if not exists
                    if (!this.geometries[type][topic]) {
                        this.geometries[type][topic] = [];
                    }

                    // Get color for the topic
                    const color = this.renderer.getTopicColor(topic, type);

                    // Create geometry based on type
                    let geometry;
                    if (type === "Polygon") {
                        geometry = this.renderer.drawPolygon(data.points, color, topic);
                    } else if (type === "Point2d") {
                        geometry = this.renderer.drawPoint(data.point, color, topic);
                    } else if (type === "LineString") {
                        geometry = this.renderer.drawLineString(data.points, color, topic);
                    }

                    // Add geometry to renderer
                    if (geometry) {
                        this.renderer.addGeometry(type, geometry, topic);
                    }

                    // Manage geometry history (limit to 10 per topic)
                    this.geometries[type][topic].push(geometry);
                    if (this.geometries[type][topic].length > 10) {
                        const oldGeometry = this.geometries[type][topic].shift();
                        this.renderer.clear(type, topic);
                    }
                } else {
                    Logger.warn("Invalid geometry data received");
                }
            } catch (error) {
                Logger.error(`Message parsing error: ${error}`);
            }
        };
    }

    reconnect() {
        if (this.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
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

// Ensure WebSocket manager is created when script loads
const wsManager = new WebSocketManager();

export default wsManager;