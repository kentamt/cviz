// geometry-renderer.js
import * as PIXI from 'https://cdnjs.cloudflare.com/ajax/libs/pixi.js/7.2.4/pixi.mjs';

// Configuration for topic-specific styling
export const TOPIC_STYLES = {
    // Default fallback colors
    default: {
        Point: 0x00ffff,         // Cyan
        MultiPoint: 0x00aaff,    // Light Blue
        LineString: 0xff0000,    // Bright Red
        MultiLineString: 0xaa0000, // Dark Red
        Polygon: 0x00ff00,       // Bright Green
        MultiPolygon: 0x00aa00,  // Dark Green
        GeometryCollection: 0xff00ff, // Magenta
        Feature: 0xffffff,       // White
        FeatureCollection: 0xffff00 // Yellow
    },

    // Topic-specific color overrides
    "boundary": { color: 0x0055ff, type: "LineString" },
    "agent": { color: 0x00ffff, type: "Polygon" },
    "obstacle": { color: 0xff8800, type: "Polygon" },
    "trajectory": { color: 0x333333, type: "LineString" },
    "observation": { color: 0xffcc00, type: "Point" }
};

// Logging wrapper
export const Logger = {
    log: (message) => console.log(`🌐 ${message}`),
    error: (message) => console.error(`❌ ${message}`),
    warn: (message) => console.warn(`⚠️ ${message}`),
    debug: (message) => console.debug(`🐞 ${message}`)
};

export class GeometryRenderer {
    constructor(options = {}) {
        const {
            containerId = 'pixi-container',
            width = window.innerWidth,
            height = window.innerHeight,
            backgroundColor = 0x111111,
            coordinateTransform = null // Function to transform coordinates if needed
        } = options;

        Logger.debug('Initializing GeometryRenderer');

        // Explicit check for PIXI
        if (!PIXI || !PIXI.Application) {
            throw new Error('Pixi.js not loaded correctly');
        }

        // Create a container for the Pixi application if it doesn't exist
        this.container = document.getElementById(containerId);
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = containerId;
            document.body.appendChild(this.container);
        }

        // Create PIXI application
        try {
            this.app = new PIXI.Application({
                width: width,
                height: height,
                backgroundColor: backgroundColor,
                backgroundAlpha: 0.5,
                resolution: window.devicePixelRatio || 1,
                autoDensity: true,
                antialias: true
            });
        } catch (error) {
            Logger.error('Failed to create PIXI Application:', error);
            throw error;
        }
        this.app.stage.sortableChildren = true;

        // Append Pixi view to the container
        this.container.appendChild(this.app.view);

        // For visualization
        this.historyLimits = {};
        this.lifeTimes = {};

        // Containers for different geometry types (GeoJSON types)
        this.geometryContainers = {
            Point: new PIXI.Container(),
            MultiPoint: new PIXI.Container(),
            LineString: new PIXI.Container(),
            MultiLineString: new PIXI.Container(),
            Polygon: new PIXI.Container(),
            MultiPolygon: new PIXI.Container(),
            GeometryCollection: new PIXI.Container(),
            Feature: new PIXI.Container(),
            FeatureCollection: new PIXI.Container()
        };

        // Manage geometries for each topic
        this.geometries = {
            Point: {},
            MultiPoint: {},
            LineString: {},
            MultiLineString: {},
            Polygon: {},
            MultiPolygon: {},
            GeometryCollection: {},
            Feature: {},
            FeatureCollection: {}
        };

        // Storage for original geometry data
        this.geometryData = {
            Point: {},
            MultiPoint: {},
            LineString: {},
            MultiLineString: {},
            Polygon: {},
            MultiPolygon: {},
            GeometryCollection: {},
            Feature: {},
            FeatureCollection: {}
        };

        // Set z-index for containers
        this.geometryContainers.Point.zIndex = 80;
        this.geometryContainers.MultiPoint.zIndex = 80;
        this.geometryContainers.LineString.zIndex = 60;
        this.geometryContainers.MultiLineString.zIndex = 60;
        this.geometryContainers.Polygon.zIndex = 50;
        this.geometryContainers.MultiPolygon.zIndex = 50;
        this.geometryContainers.GeometryCollection.zIndex = 70;
        this.geometryContainers.Feature.zIndex = 90;
        this.geometryContainers.FeatureCollection.zIndex = 90;

        // Add containers to the stage
        Object.values(this.geometryContainers).forEach(container => {
            this.app.stage.addChild(container);
        });

        // Store coordinate transformation function
        this.coordinateTransform = coordinateTransform;

        // Resize handling
        window.addEventListener('resize', () => this.resize());
    }

    // Process GeoJSON data and render it
    processGeometryData(data) {
        // Extract GeoJSON data
        const geoJSON = data.data_type === 'GeoJSON' ? data : data.geojson;

        if (!geoJSON) {
            Logger.warn('No GeoJSON data found in message');
            return;
        }

        // Get topic from data
        const topic = data.topic || 'default';


         // Add life time to the geometry if specified
        if (data.life_time !== undefined) {
            this.lifeTimes[topic] = data.life_time;
        } else if (geoJSON.properties && geoJSON.properties.life_time !== undefined) {
            this.lifeTimes[topic] = geoJSON.properties.life_time;
        } else {
            this.lifeTimes[topic] = 0;  // no life time limit
        }

        // Add history limit to the geometry if specified
        // First check top-level data
        if (data.history_limit !== undefined) {
            this.historyLimits[topic] = data.history_limit;
        }
        // Then check GeoJSON properties
        else if (geoJSON.properties && geoJSON.properties.history_limit !== undefined) {
            this.historyLimits[topic] = geoJSON.properties.history_limit;
        }
        // For FeatureCollection, check the first feature's properties
        else if (geoJSON.type === 'FeatureCollection' &&
                geoJSON.features &&
                geoJSON.features.length > 0 &&
                geoJSON.features[0].properties &&
                geoJSON.features[0].properties.history_limit !== undefined) {
            this.historyLimits[topic] = geoJSON.features[0].properties.history_limit;
        }
        // Default to 1 if not specified anywhere
        else {
            this.historyLimits[topic] = 1;
        }

        // Process the GeoJSON data based on its type
        const geoJSONType = geoJSON.type;


        // Get color from properties or default to topic color
        let color;
        if (geoJSON.properties && geoJSON.properties.color) {
            // Handle color in various formats
            if (typeof geoJSON.properties.color === 'string') {
                if (geoJSON.properties.color.startsWith('#')) {
                    // Convert hex string to number
                    color = parseInt(geoJSON.properties.color.substring(1), 16);
                } else if (geoJSON.properties.color.startsWith('0x')) {
                    // Already in hex format as string
                    color = parseInt(geoJSON.properties.color, 16);
                }
            } else if (typeof geoJSON.properties.color === 'number') {
                color = geoJSON.properties.color;
            }
        }

        // If no color found, use topic-based color
        if (!color) {
            color = this.getTopicColor(topic, geoJSONType);
        }

        // Create geometry based on GeoJSON type
        let geometry;

        switch (geoJSONType) {
            case 'Point':
                geometry = this.drawGeoJSONPoint(geoJSON, color, topic);
                break;
            case 'MultiPoint':
                geometry = this.drawGeoJSONMultiPoint(geoJSON, color, topic);
                break;
            case 'LineString':
                geometry = this.drawGeoJSONLineString(geoJSON, color, topic);
                break;
            case 'MultiLineString':
                geometry = this.drawGeoJSONMultiLineString(geoJSON, color, topic);
                break;
            case 'Polygon':
                geometry = this.drawGeoJSONPolygon(geoJSON, color, topic);
                break;
            case 'MultiPolygon':
                geometry = this.drawGeoJSONMultiPolygon(geoJSON, color, topic);
                break;
            case 'GeometryCollection':
                geometry = this.drawGeoJSONGeometryCollection(geoJSON, color, topic);
                break;
            case 'Feature':
                geometry = this.drawGeoJSONFeature(geoJSON, color, topic);
                break;
            case 'FeatureCollection':
                geometry = this.drawGeoJSONFeatureCollection(geoJSON, color, topic);
                break;
            default:
                Logger.warn(`Unsupported GeoJSON type: ${geoJSONType}`);
                return;
        }

        // Add geometry to renderer
        if (geometry) {
            // Check if container exists
            if (!this.geometryContainers[geoJSONType]) {
                Logger.warn(`Container for type ${geoJSONType} not found`);
                return;
            }

            // Add PIXI object to the container
            this.geometryContainers[geoJSONType].addChild(geometry);
        }

        // Initialize topic array if not exists
        if (!this.geometries[geoJSONType][topic]) {
            this.geometries[geoJSONType][topic] = [];
        }
        if (!this.geometryData[geoJSONType][topic]) {
            this.geometryData[geoJSONType][topic] = [];
        }

        // Manage geometry history
        this.geometries[geoJSONType][topic].push(geometry);
        this.geometryData[geoJSONType][topic].push({data: geoJSON, color, topic});

        this.manageGeometryHistory(geoJSONType, topic);
    }

    manageGeometryHistory(type, topic) {
        // The number of geometries to keep in history
        const historyLimit = this.historyLimits[topic] || 1;

        while (this.geometries[type][topic].length > historyLimit) {
            // Remove the oldest geometry
            const oldGeometry = this.geometries[type][topic].shift();

            // Remove geometry object
            if (oldGeometry && !oldGeometry.destroyed) {
                this.geometryContainers[type].removeChild(oldGeometry);
                oldGeometry.destroy({children: true});
            }
        }

        while (this.geometryData[type][topic].length > historyLimit) {
            this.geometryData[type][topic].shift();
        }

        // Handle life time if set
        const lifeTime = this.lifeTimes[topic];
        if (lifeTime > 0 && this.geometries[type][topic].length > 0) {
            const geometry = this.geometries[type][topic][this.geometries[type][topic].length - 1];

            setTimeout(() => {
                if (geometry && !geometry.destroyed) {
                    this.geometryContainers[type].removeChild(geometry);
                    geometry.destroy({children: true});

                    // Also remove from arrays
                    const index = this.geometries[type][topic].indexOf(geometry);
                    if (index > -1) {
                        this.geometries[type][topic].splice(index, 1);
                        this.geometryData[type][topic].splice(index, 1);
                    }
                }
            }, lifeTime * 1000);
        }
    }

    resize() {
        // Ensure the renderer exists before resizing
        if (this.app?.renderer) {
            this.app.renderer.resize(window.innerWidth, window.innerHeight);
        }
    }

    // Transform coordinates if a transform function is provided
    transformCoordinates(x, y) {
        if (this.coordinateTransform) {
            return this.coordinateTransform(x, y);
        }
        return {x, y};
    }

    // Update the coordinate transform
    updateCoordinateTransform(transformFunction) {
        this.coordinateTransform = transformFunction;
        this.redrawAllGeometries();
    }

    getTopicColor(topic, dataType) {
        // First, check if topic has a specific style
        if (TOPIC_STYLES[topic]) {
            return TOPIC_STYLES[topic].color;
        }

        // Fallback to default color for data type
        return TOPIC_STYLES.default[dataType] || 0xffffff;
    }

    // Redraw all stored geometries
    redrawAllGeometries() {
        // Clear all containers first
        Object.keys(this.geometryContainers).forEach(type => {
            this.geometryContainers[type].removeChildren();
        });

        // Reset the geometries arrays but keep the stored data
        Object.keys(this.geometries).forEach(type => {
            Object.keys(this.geometries[type]).forEach(topic => {
                this.geometries[type][topic] = [];
            });
        });

        // Redraw each type of geometry
        Object.keys(this.geometryData).forEach(type => {
            // Loop through each topic
            Object.keys(this.geometryData[type]).forEach(topic => {
                // Redraw each saved geometry data
                this.geometryData[type][topic].forEach(item => {
                    const geoJSON = item.data;
                    const color = item.color;

                    let geometry;

                    // Draw based on the GeoJSON type
                    switch (type) {
                        case 'Point':
                            geometry = this.drawGeoJSONPoint(geoJSON, color, topic);
                            break;
                        case 'MultiPoint':
                            geometry = this.drawGeoJSONMultiPoint(geoJSON, color, topic);
                            break;
                        case 'LineString':
                            geometry = this.drawGeoJSONLineString(geoJSON, color, topic);
                            break;
                        case 'MultiLineString':
                            geometry = this.drawGeoJSONMultiLineString(geoJSON, color, topic);
                            break;
                        case 'Polygon':
                            geometry = this.drawGeoJSONPolygon(geoJSON, color, topic);
                            break;
                        case 'MultiPolygon':
                            geometry = this.drawGeoJSONMultiPolygon(geoJSON, color, topic);
                            break;
                        case 'GeometryCollection':
                            geometry = this.drawGeoJSONGeometryCollection(geoJSON, color, topic);
                            break;
                        case 'Feature':
                            geometry = this.drawGeoJSONFeature(geoJSON, color, topic);
                            break;
                        case 'FeatureCollection':
                            geometry = this.drawGeoJSONFeatureCollection(geoJSON, color, topic);
                            break;
                    }

                    // Add to the appropriate container and track it
                    if (geometry) {
                        this.geometryContainers[type].addChild(geometry);
                        this.geometries[type][topic].push(geometry);
                    }
                });
            });
        });
    }
    // Drawing methods for GeoJSON types

    // Point: [longitude, latitude]
    drawGeoJSONPoint(geoJSON, color, topic) {
        if (!geoJSON.coordinates) return null;

        const coords = geoJSON.coordinates;
        const radius = geoJSON.properties?.radius || 2;
        const alpha = geoJSON.properties?.alpha || 0.8;

        const graphics = new PIXI.Graphics();
        graphics.beginFill(color, alpha);

        // Transform coordinates if needed
        const point = this.transformCoordinates(coords[0], coords[1]);
        graphics.drawCircle(point.x, point.y, radius);
        graphics.endFill();

        // Add metadata for potential interaction
        graphics.topic = topic;
        if (geoJSON.properties) {
            graphics.properties = geoJSON.properties;
        }

        return graphics;
    }

    // MultiPoint: Array of [longitude, latitude]
    drawGeoJSONMultiPoint(geoJSON, color, topic) {
        if (!geoJSON.coordinates || !Array.isArray(geoJSON.coordinates)) return null;

        const radius = geoJSON.properties?.radius || 5;
        const alpha = geoJSON.properties?.alpha || 0.8;

        const graphics = new PIXI.Graphics();
        graphics.beginFill(color, alpha);

        // Draw each point
        geoJSON.coordinates.forEach(coords => {
            const point = this.transformCoordinates(coords[0], coords[1]);
            graphics.drawCircle(point.x, point.y, radius);
        });

        graphics.endFill();

        // Add metadata
        graphics.topic = topic;
        if (geoJSON.properties) {
            graphics.properties = geoJSON.properties;
        }

        return graphics;
    }

    // LineString: Array of [longitude, latitude]
    drawGeoJSONLineString(geoJSON, color, topic) {
        if (!geoJSON.coordinates || !Array.isArray(geoJSON.coordinates) || geoJSON.coordinates.length < 2) {
            return null;
        }

        const lineWidth = geoJSON.properties?.lineWidth || 2;
        const alpha = geoJSON.properties?.alpha || 1.0;

        const graphics = new PIXI.Graphics();
        graphics.lineStyle(lineWidth, color, alpha);

        // Transform and draw first point
        const firstPoint = this.transformCoordinates(
            geoJSON.coordinates[0][0],
            geoJSON.coordinates[0][1]
        );
        graphics.moveTo(firstPoint.x, firstPoint.y);

        // Draw lines to subsequent points
        for (let i = 1; i < geoJSON.coordinates.length; i++) {
            const point = this.transformCoordinates(
                geoJSON.coordinates[i][0],
                geoJSON.coordinates[i][1]
            );
            graphics.lineTo(point.x, point.y);
        }

        // Add metadata
        graphics.topic = topic;
        if (geoJSON.properties) {
            graphics.properties = geoJSON.properties;
        }

        return graphics;
    }

    // MultiLineString: Array of LineString coordinate arrays
    drawGeoJSONMultiLineString(geoJSON, color, topic) {
        if (!geoJSON.coordinates || !Array.isArray(geoJSON.coordinates)) {
            return null;
        }

        const lineWidth = geoJSON.properties?.lineWidth || 2;
        const alpha = geoJSON.properties?.alpha || 1.0;

        const graphics = new PIXI.Graphics();
        graphics.lineStyle(lineWidth, color, alpha);

        // Draw each line string
        geoJSON.coordinates.forEach(lineCoords => {
            if (lineCoords.length >= 2) {
                // Transform and draw first point of this line
                const firstPoint = this.transformCoordinates(lineCoords[0][0], lineCoords[0][1]);
                graphics.moveTo(firstPoint.x, firstPoint.y);

                // Draw the rest of the line
                for (let i = 1; i < lineCoords.length; i++) {
                    const point = this.transformCoordinates(lineCoords[i][0], lineCoords[i][1]);
                    graphics.lineTo(point.x, point.y);
                }
            }
        });

        // Add metadata
        graphics.topic = topic;
        if (geoJSON.properties) {
            graphics.properties = geoJSON.properties;
        }

        return graphics;
    }

    // Polygon: Array of rings (first is exterior, rest are holes)
    drawGeoJSONPolygon(geoJSON, color, topic) {
        if (!geoJSON.coordinates || !Array.isArray(geoJSON.coordinates) || geoJSON.coordinates.length === 0) {
            return null;
        }

        const alpha = geoJSON.properties?.fillAlpha || 0.2;
        const lineAlpha = geoJSON.properties?.lineAlpha || 1.0;
        const lineWidth = geoJSON.properties?.lineWidth || 2;

        const graphics = new PIXI.Graphics();

        // Begin fill for the polygon
        graphics.beginFill(color, alpha);
        graphics.lineStyle(lineWidth, color, lineAlpha);

        // Draw exterior ring
        const exteriorRing = geoJSON.coordinates[0];
        if (exteriorRing && exteriorRing.length >= 3) {
            // Move to first point
            const firstPoint = this.transformCoordinates(exteriorRing[0][0], exteriorRing[0][1]);
            graphics.moveTo(firstPoint.x, firstPoint.y);

            // Draw the rest of the exterior ring
            for (let i = 1; i < exteriorRing.length; i++) {
                const point = this.transformCoordinates(exteriorRing[i][0], exteriorRing[i][1]);
                graphics.lineTo(point.x, point.y);
            }

            // Close the exterior ring
            graphics.closePath();
        }

        // Draw interior rings (holes)
        for (let h = 1; h < geoJSON.coordinates.length; h++) {
            const holeRing = geoJSON.coordinates[h];
            if (holeRing && holeRing.length >= 3) {
                // Move to first point of the hole
                const firstHolePoint = this.transformCoordinates(holeRing[0][0], holeRing[0][1]);
                graphics.moveTo(firstHolePoint.x, firstHolePoint.y);

                // Draw the hole
                for (let i = 1; i < holeRing.length; i++) {
                    const point = this.transformCoordinates(holeRing[i][0], holeRing[i][1]);
                    graphics.lineTo(point.x, point.y);
                }

                // Close the hole
                graphics.closePath();
            }
        }

        graphics.endFill();

        // Add metadata
        graphics.topic = topic;
        if (geoJSON.properties) {
            graphics.properties = geoJSON.properties;
        }

        return graphics;
    }

    // MultiPolygon: Array of Polygon coordinate arrays
    drawGeoJSONMultiPolygon(geoJSON, color, topic) {
        if (!geoJSON.coordinates || !Array.isArray(geoJSON.coordinates)) {
            return null;
        }

        const alpha = geoJSON.properties?.fillAlpha || 0.2;
        const lineAlpha = geoJSON.properties?.lineAlpha || 1.0;
        const lineWidth = geoJSON.properties?.lineWidth || 2;

        const graphics = new PIXI.Graphics();

        // Begin fill and line style
        graphics.beginFill(color, alpha);
        graphics.lineStyle(lineWidth, color, lineAlpha);

        // Draw each polygon
        geoJSON.coordinates.forEach(polygonCoords => {
            // Draw exterior ring of this polygon
            const exteriorRing = polygonCoords[0];
            if (exteriorRing && exteriorRing.length >= 3) {
                // Move to first point
                const firstPoint = this.transformCoordinates(exteriorRing[0][0], exteriorRing[0][1]);
                graphics.moveTo(firstPoint.x, firstPoint.y);

                // Draw the rest of the exterior ring
                for (let i = 1; i < exteriorRing.length; i++) {
                    const point = this.transformCoordinates(exteriorRing[i][0], exteriorRing[i][1]);
                    graphics.lineTo(point.x, point.y);
                }

                // Close the exterior ring
                graphics.closePath();
            }

            // Draw interior rings (holes) for this polygon
            for (let h = 1; h < polygonCoords.length; h++) {
                const holeRing = polygonCoords[h];
                if (holeRing && holeRing.length >= 3) {
                    // Move to first point of the hole
                    const firstHolePoint = this.transformCoordinates(holeRing[0][0], holeRing[0][1]);
                    graphics.moveTo(firstHolePoint.x, firstHolePoint.y);

                    // Draw the hole
                    for (let i = 1; i < holeRing.length; i++) {
                        const point = this.transformCoordinates(holeRing[i][0], holeRing[i][1]);
                        graphics.lineTo(point.x, point.y);
                    }

                    // Close the hole
                    graphics.closePath();
                }
            }
        });

        graphics.endFill();

        // Add metadata
        graphics.topic = topic;
        if (geoJSON.properties) {
            graphics.properties = geoJSON.properties;
        }

        return graphics;
    }

    // GeometryCollection: Collection of different geometry objects
    drawGeoJSONGeometryCollection(geoJSON, color, topic) {
        if (!geoJSON.geometries || !Array.isArray(geoJSON.geometries)) {
            return null;
        }

        const container = new PIXI.Container();

        // Draw each geometry in the collection
        geoJSON.geometries.forEach(geometry => {
            // Determine the color for this geometry
            let geometryColor = color;
            if (geometry.properties && geometry.properties.color) {
                if (typeof geometry.properties.color === 'string') {
                    if (geometry.properties.color.startsWith('#')) {
                        geometryColor = parseInt(geometry.properties.color.substring(1), 16);
                    } else if (geometry.properties.color.startsWith('0x')) {
                        geometryColor = parseInt(geometry.properties.color, 16);
                    }
                } else if (typeof geometry.properties.color === 'number') {
                    geometryColor = geometry.properties.color;
                }
            }

            // Draw the geometry based on its type
            let graphicsObject;

            switch (geometry.type) {
                case 'Point':
                    graphicsObject = this.drawGeoJSONPoint(geometry, geometryColor, topic);
                    break;
                case 'MultiPoint':
                    graphicsObject = this.drawGeoJSONMultiPoint(geometry, geometryColor, topic);
                    break;
                case 'LineString':
                    graphicsObject = this.drawGeoJSONLineString(geometry, geometryColor, topic);
                    break;
                case 'MultiLineString':
                    graphicsObject = this.drawGeoJSONMultiLineString(geometry, geometryColor, topic);
                    break;
                case 'Polygon':
                    graphicsObject = this.drawGeoJSONPolygon(geometry, geometryColor, topic);
                    break;
                case 'MultiPolygon':
                    graphicsObject = this.drawGeoJSONMultiPolygon(geometry, geometryColor, topic);
                    break;
            }

            if (graphicsObject) {
                container.addChild(graphicsObject);
            }
        });

        // Add metadata
        container.topic = topic;
        if (geoJSON.properties) {
            container.properties = geoJSON.properties;
        }

        return container;
    }

    // Feature: A geometry with properties
    drawGeoJSONFeature(geoJSON, color, topic) {
        if (!geoJSON.geometry) {
            return null;
        }

        // Determine color from feature properties if available
        let featureColor = color;
        if (geoJSON.properties && geoJSON.properties.color) {
            if (typeof geoJSON.properties.color === 'string') {
                if (geoJSON.properties.color.startsWith('#')) {
                    featureColor = parseInt(geoJSON.properties.color.substring(1), 16);
                } else if (geoJSON.properties.color.startsWith('0x')) {
                    featureColor = parseInt(geoJSON.properties.color, 16);
                }
            } else if (typeof geoJSON.properties.color === 'number') {
                featureColor = geoJSON.properties.color;
            }
        }

        // Create a graphics object for the geometry
        let graphicsObject;

        switch (geoJSON.geometry.type) {
            case 'Point':
                graphicsObject = this.drawGeoJSONPoint(geoJSON.geometry, featureColor, topic);
                break;
            case 'MultiPoint':
                graphicsObject = this.drawGeoJSONMultiPoint(geoJSON.geometry, featureColor, topic);
                break;
            case 'LineString':
                graphicsObject = this.drawGeoJSONLineString(geoJSON.geometry, featureColor, topic);
                break;
            case 'MultiLineString':
                graphicsObject = this.drawGeoJSONMultiLineString(geoJSON.geometry, featureColor, topic);
                break;
            case 'Polygon':
                graphicsObject = this.drawGeoJSONPolygon(geoJSON.geometry, featureColor, topic);
                break;
            case 'MultiPolygon':
                graphicsObject = this.drawGeoJSONMultiPolygon(geoJSON.geometry, featureColor, topic);
                break;
            case 'GeometryCollection':
                graphicsObject = this.drawGeoJSONGeometryCollection(geoJSON.geometry, featureColor, topic);
                break;
        }

        // If we have a valid graphics object
        if (graphicsObject) {
            // Add properties to the graphics object
            graphicsObject.topic = topic;
            graphicsObject.properties = geoJSON.properties || {};

            // Check if we should add a label from properties
            if (geoJSON.properties && geoJSON.properties.label) {
                // Create a label if the feature has one specified
                const labelStyle = new PIXI.TextStyle({
                    fontFamily: 'Arial',
                    fontSize: 12,
                    fill: 0xffffff,
                    strokeThickness: 4,
                    stroke: 0x000000
                });

                const label = new PIXI.Text(geoJSON.properties.label, labelStyle);

                // Position the label based on geometry type
                if (geoJSON.geometry.type === 'Point') {
                    const point = this.transformCoordinates(
                        geoJSON.geometry.coordinates[0],
                        geoJSON.geometry.coordinates[1]
                    );
                    label.x = point.x + 10;
                    label.y = point.y - 10;
                } else if (geoJSON.geometry.type === 'Polygon' || geoJSON.geometry.type === 'MultiPolygon') {
                    // For polygons, calculate centroid for label position
                    const coords = geoJSON.geometry.type === 'Polygon' ?
                        geoJSON.geometry.coordinates[0] :
                        geoJSON.geometry.coordinates[0][0];

                    // Simple centroid calculation (average of all points)
                    let sumX = 0, sumY = 0;
                    coords.forEach(coord => {
                        const point = this.transformCoordinates(coord[0], coord[1]);
                        sumX += point.x;
                        sumY += point.y;
                    });

                    label.x = sumX / coords.length;
                    label.y = sumY / coords.length;
                    label.anchor.set(0.5);
                } else {
                    // For other types, use first point
                    const firstCoord = geoJSON.geometry.type === 'LineString' ?
                        geoJSON.geometry.coordinates[0] :
                        geoJSON.geometry.coordinates[0][0];

                    const point = this.transformCoordinates(firstCoord[0], firstCoord[1]);
                    label.x = point.x;
                    label.y = point.y - 15;
                }

                // Create a container to hold both graphics and label
                const container = new PIXI.Container();
                container.addChild(graphicsObject);
                container.addChild(label);
                container.topic = topic;
                container.properties = geoJSON.properties;

                return container;
            }

            return graphicsObject;
        }

        return null;
    }

    // FeatureCollection: Collection of features
    drawGeoJSONFeatureCollection(geoJSON, color, topic) {
        if (!geoJSON.features || !Array.isArray(geoJSON.features)) {
            return null;
        }

        const container = new PIXI.Container();

        // Draw each feature in the collection
        geoJSON.features.forEach(feature => {
            // Determine the color for this feature
            let featureColor = color;
            if (feature.properties && feature.properties.color) {
                if (typeof feature.properties.color === 'string') {
                    if (feature.properties.color.startsWith('#')) {
                        featureColor = parseInt(feature.properties.color.substring(1), 16);
                    } else if (feature.properties.color.startsWith('0x')) {
                        featureColor = parseInt(feature.properties.color, 16);
                    }
                } else if (typeof feature.properties.color === 'number') {
                    featureColor = feature.properties.color;
                }
            }

            // Draw the feature
            const featureGraphics = this.drawGeoJSONFeature(feature, featureColor, topic);
            if (featureGraphics) {
                container.addChild(featureGraphics);
            }
        });

        // Add metadata
        container.topic = topic;
        if (geoJSON.properties) {
            container.properties = geoJSON.properties;
        }

        return container;
    }
}