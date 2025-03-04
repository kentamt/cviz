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

class GeometryRenderer {
    constructor(ctx, canvas) {
        this.ctx = ctx;
        this.canvas = canvas;
        this.colors = ["#00ff00", "#00ffff", "#ff0000", "#ffff00", "#ff00ff", "#ff8800"];
    }

    flipY(y) {
        return this.canvas.height - y;
    }

    drawPolygon(points, color) {
        if (points.length < 3) return;
        
        this.ctx.fillStyle = color;
        this.ctx.lineWidth = 1;
        
        this.ctx.beginPath();
        this.ctx.moveTo(points[0].x, this.flipY(points[0].y));
        
        for (let i = 1; i < points.length; i++) {
            this.ctx.lineTo(points[i].x, this.flipY(points[i].y));
        }
        
        this.ctx.closePath();
        this.ctx.fill();
        this.ctx.stroke();
    }

    drawPoint(point, color, radius = 5) {
        this.ctx.beginPath();
        this.ctx.fillStyle = color;
        this.ctx.arc(point.x, this.flipY(point.y), radius, 0, 2 * Math.PI);
        this.ctx.fill();
    }

    drawLineString(points, color, lineWidth = 2) {
        if (points.length < 2) return;
        
        this.ctx.strokeStyle = color;
        this.ctx.lineWidth = lineWidth;
        
        this.ctx.beginPath();
        this.ctx.moveTo(points[0].x, this.flipY(points[0].y));
        
        for (let i = 1; i < points.length; i++) {
            this.ctx.lineTo(points[i].x, this.flipY(points[i].y));
        }
        
        this.ctx.stroke();
    }
}

class WebSocketManager {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.geometries = {
            Polygon: [],
            Point2d: [],
            LineString: []
        };
        this.setupCanvas();
        this.connectWebSocket();
        this.num_keep = 1;
    }

    setupCanvas() {
        this.canvas = document.getElementById("myCanvas");
        this.ctx = this.canvas.getContext("2d", { alpha: false });
        
        // Resize canvas
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;

        // Disable anti-aliasing
        this.ctx.imageSmoothingEnabled = false;

        // Create renderer
        this.renderer = new GeometryRenderer(this.ctx, this.canvas);

        // Event listeners
        window.addEventListener("resize", () => this.resizeCanvas());
    }

    resizeCanvas() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
        this.redrawCanvas();
    }

    drawBackground() {
        this.ctx.fillStyle = "#101010";
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    }

    redrawCanvas() {
        requestAnimationFrame(() => {
            this.drawBackground();
            
            // Draw Polygons
            this.geometries.Polygon.forEach((points, index) => {
                this.renderer.drawPolygon(points, this.renderer.colors[index % this.renderer.colors.length]);
            });

            // Draw Points
            this.geometries.Point2d.forEach((point, index) => {
                this.renderer.drawPoint(point, this.renderer.colors[index % this.renderer.colors.length]);
            });

            // Draw LineStrings
            this.geometries.LineString.forEach((points, index) => {
                this.renderer.drawLineString(points, this.renderer.colors[index % this.renderer.colors.length]);
            });
        });
    }

    validateGeometryData(data) {
        const validTypes = {
            Polygon: (data) => (
                data && 
                data.data_type === "Polygon" && 
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
                data.point && 
                typeof data.point.x === 'number' && 
                typeof data.point.y === 'number'
            ),
            LineString: (data) => (
                data && 
                data.data_type === "LineString" && 
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
                    
                    // Manage number of geometries
                    if (type === "Polygon") {
                        this.geometries.Polygon.push(data.points);
                        if (this.geometries.Polygon.length > this.num_keep) this.geometries.Polygon.shift();
                    } else if (type === "Point2d") {
                        this.geometries.Point2d.push(data.point);
                        if (this.geometries.Point2d.length > this.num_keep) this.geometries.Point2d.shift();
                    } else if (type === "LineString") {
                        this.geometries.LineString.push(data.points);
                        if (this.geometries.LineString.length > this.num_keep) this.geometries.LineString.shift();
                    }
                    
                    this.redrawCanvas();
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

// Initialize WebSocket manager when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new WebSocketManager();
});