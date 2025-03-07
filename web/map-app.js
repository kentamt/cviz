// map-app.js - For map-based application
import { MapRenderer } from './map-renderer.js';

// Initialize map application with London as default center
const mapApp = new MapRenderer({
    initialCenter: { lat: 51.497494, lon: -0.173037 },
    initialZoom: 16,
    wsOptions: {
        serverUrl: 'ws://127.0.0.1:6789',
        historyLimits: {
            Text: 1,
            Polygon: 1,
            PolygonVector: 1,
            Point2d: 100,
            LineString: 10
        }
    }
});

// Export for debugging or external use
window.mapApp = mapApp;