// canvas-app.js - For canvas-based application (no map)
import { WebSocketManager } from './websocket-manager.js';

// Initialize WebSocket manager with default settings
const canvasApp = new WebSocketManager({
    serverUrl: 'ws://127.0.0.1:6789',
    rendererOptions: {
        backgroundColor: 0x101010,
        width: window.innerWidth,
        height: window.innerHeight
    }
});

// Export for debugging or external use
window.canvasApp = canvasApp;