// map-app.js - For map-based application
import { MapRenderer } from './map-renderer.js';

// Get the WebSocket URL dynamically
function getWebSocketUrl() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host; // Includes hostname and port if specified
    return `${protocol}//${host}/ws`;
}

// Initialize map application with appropriate center
// These coordinates are for southern England where the map_swarm_example uses UTM30
const mapApp = new MapRenderer({
    initialCenter: { lat: 51.50, lon: -0.17 },
    initialZoom: 14,
    wsOptions: {
        serverUrl: getWebSocketUrl(),
        historyLimits: {
            Text: 1,
            Polygon: 1,
            PolygonVector: 1,
            Point2d: 100,
            LineString: 10,
            LineStringVector: 1
        }
    }
});

// Export for debugging or external use
window.mapApp = mapApp;