// canvas-app.js - For canvas-based application (no map)
// import { WebSocketManager } from './websocket-manager.js';

// // Initialize WebSocket manager with default settings
// const canvasApp = new WebSocketManager({
//     serverUrl: 'ws://127.0.0.1:6789',
//     rendererOptions: {
//         backgroundColor: 0x101010,
//         width: window.innerWidth,
//         height: window.innerHeight
//     }
// });

// // Export for debugging or external use
// window.canvasApp = canvasApp;

import { CanvasRenderer } from './canvas-renderer.js';

const canvasApp = new CanvasRenderer({
    width: window.innerWidth,
    height: window.innerHeight,
    initialViewport: { x: -500, y: -500, width: 1000, height: 1000 },
    backgroundColor: 0x222222,
    gridSize: 50,
    showGrid: true,
    wsOptions: {
        serverUrl: "ws://127.0.0.1:8000/ws"
    }
});

window.canvasApp = canvasApp;