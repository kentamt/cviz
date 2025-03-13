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