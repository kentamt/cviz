
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

class WebSocketManager {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.polygons = [];
        this.colors = ["#00ff00", "#00ffff", "#ff0000", "#ffff00", "#ff00ff", "#ff8800"];
        this.setupCanvas();
        this.connectWebSocket();
    }

    setupCanvas() {
        this.canvas = document.getElementById("myCanvas");
        this.ctx = this.canvas.getContext("2d", { alpha: false });
        
        // Resize canvas
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;

        // Disable anti-aliasing
        this.ctx.imageSmoothingEnabled = false;

        // Event listeners
        window.addEventListener("resize", () => this.resizeCanvas());
    }

    resizeCanvas() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
        this.redrawCanvas();
    }

    flipY(y) {
        return this.canvas.height - y;
    }

    drawBackground() {
        this.ctx.fillStyle = "#101010";
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    }

    drawPolygon(points, color) {
        if (points.length < 3) return;
        
        this.ctx.fillStyle = color;
        // this.ctx.strokeStyle = "white";
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

    redrawCanvas() {
        requestAnimationFrame(() => {
            this.drawBackground();
            this.polygons.forEach((points, index) => {
                this.drawPolygon(points, this.colors[index % this.colors.length]);
            });
        });
    }

    validatePolygonData(data) {
        return (
            data && 
            data.data_type === "Polygon" && 
            Array.isArray(data.points) && 
            data.points.length > 0 && 
            data.points.every(point => 
                point && 
                typeof point.x === 'number' && 
                typeof point.y === 'number'
            )
        );
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
                const data_type = data.data_type;
                // show the date type in the console
                console.log(data_type);

                if (this.validatePolygonData(data)) {
                    
                    this.polygons.push(data.points);
                    
                    if (this.polygons.length > 1) this.polygons.shift();
                    
                    this.redrawCanvas();
                } else {
                    Logger.warn("Invalid polygon data received");
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
