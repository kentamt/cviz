// geometry-renderer.js
import * as PIXI from 'https://cdnjs.cloudflare.com/ajax/libs/pixi.js/7.2.4/pixi.mjs';

// Configuration for topic-specific styling
export const TOPIC_STYLES = {
    // Default fallback colors
    default: {
        Polygon: 0x00ff00,      // Bright Green
        PolygonVector: 0xff00ff, // Magenta
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

        // For visualisation
        this.historyLimits = {};
        this.lifeTimes = {};

        // Containers for different geometry types
        this.geometryContainers = {
            Text: new PIXI.Container(),
            Polygon: new PIXI.Container(),
            PolygonVector: new PIXI.Container(),
            Point2d: new PIXI.Container(),
            LineString: new PIXI.Container()
        };

        // Manage geometries for each topic
        this.geometries = {
            Text: {},
            Polygon: {},
            PolygonVector: {},
            Point2d: {},
            LineString: {}
        };


        // Storage for original geometry data
        this.geometryData = {
            Text: {},
            Polygon: {},
            PolygonVector: {},
            Point2d: {},
            LineString: {}
        };

        // Set z-index for containers
        this.geometryContainers.Text.zIndex = 100;
        this.geometryContainers.Polygon.zIndex = 90;
        this.geometryContainers.PolygonVector.zIndex = 100;
        this.geometryContainers.Point2d.zIndex = 70;
        this.geometryContainers.LineString.zIndex = 60;

        // Add containers to the stage
        Object.values(this.geometryContainers).forEach(container => {
            this.app.stage.addChild(container);
        });

        // Store coordinate transformation function
        this.coordinateTransform = coordinateTransform;

        // Resize handling
        window.addEventListener('resize', () => this.resize());
    }


    processGeometryData(data) {

        const type = data.data_type;
        const topic = data.topic || 'default';

        // Add life time to the geometry if there exists a life time for the topic
        if (data.life_time) {
            this.lifeTimes[topic] = data.life_time;
        }else{
            this.lifeTimes[topic] = 0;  // no life time limit
        }

        // Add history limit to the geometry if there exists a history limit for the topic
        if (data.history_limit) {
            this.historyLimits[topic] = data.history_limit;
        }else{
            // TODO: Implement this
            this.historyLimits[topic] = this.options.historyLimits[type];
        }
        
        Logger.debug(`Processing ${type} data for topic: ${topic}`);
        
        // Get color for the topic
        const color = this.getTopicColor(topic, type);

        // Create geometry based on type
        let geometry;
        if (type === "Polygon") {
            geometry = this.drawPolygon(data.points, color, topic);
        } else if (type === "PolygonVector") {
            geometry = this.drawPolygonVector(data.polygons, color, topic);
        } else if (type === "Point2d") {
            geometry = this.drawPoint(data.point, color, topic, 2);
        } else if (type === "LineString") {
            geometry = this.drawLineString(data.points, color, topic);
        } else if (type === "Text") {
            geometry = this.drawText(data.text, data.position, color, topic);
        }

        // Add geometry to renderer
        if (geometry) {
            this.addGeometry(type, geometry, topic);
        }

        // Initialize topic array if not exists
        if (!this.geometries[type][topic]) {
            this.geometries[type][topic] = [];
        }
        if (!this.geometryData[type][topic]) {
            this.geometryData[type][topic] = [];
        }

        // Manage geometry history
        this.geometries[type][topic].push(geometry);
        this.geometryData[type][topic].push({data, color, topic});
        this.manageGeometryHistory(type, topic);

    }

    manageGeometryHistory(type, topic) {
        // the number of geometries to keep in history
        const historyLimit = this.historyLimits[topic];

        // if (this.geometries[type][topic].length > historyLimit) {
        while (this.geometries[type][topic].length > historyLimit) {

            // remove the oldest geometry
            const oldGeometry = this.geometries[type][topic].shift();            

            // remove geometry object
            if (oldGeometry && !oldGeometry.destroyed) {
                this.geometryContainers[type].removeChild(oldGeometry);
                oldGeometry.destroy({ children: true });
            }
        }

        while (this.geometryData[type][topic].length > historyLimit) {
            this.geometryData[type][topic].shift();
        }

        // life time of the geometry
        // TODO: set life_time in the data, e.g. data.life_time = 1
        // const lifeTime = 1
        // console.log(this.lifeTimes[topic]);
        // const lifeTime = this.lifeTimes[topic];
        // if (lifeTime) {
        //     console.log('Setting timeout');
        //     setTimeout(() => {
        //         if (geometry.destroyed) {
        //             return;
        //         }
        //         console.log('Removing geometry');
        //         this.geometryContainers[type].removeChild(geometry);
        //         geometry.destroy({ children: true });
        //         this.geometries[type][topic].shift();


        //     }, lifeTime * 1000);
        // }

    }

    
    size() {
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
        return { x, y };
    }

    // Update the coordinate transform
    updateCoordinateTransform(transformFunction) {
        console.log('Updating coordinate transform');
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

    // Add a method to redraw all stored geometries
    redrawAllGeometries() {

        // Clear all containers first
        Object.keys(this.geometryContainers).forEach(type => {
            this.geometryContainers[type].removeChildren();
        });

        // Redraw each type of geometry
        Object.keys(this.geometryData).forEach(type => {
            // topic loop
            Object.keys(this.geometryData[type]).forEach(topic => {
                this.geometryData[type][topic].forEach(item => {
                    let geometry;

                    const data = item.data;
                    const color = item.color;
                    const topic = item.topic;
                    const lineWidth = 2;  // TODO: set line width in the data
                    const radius = 5;    // TODO: set radius in the data

                    switch(type) {
                        case 'Text':
                            geometry = this.drawText(data.text, data.position, color, topic);
                            break;
                        case 'Polygon':
                            geometry = this.drawPolygon(data.points, color, topic);
                            break;
                        case 'PolygonVector':
                            geometry = this.drawPolygonVector(data.polygons, "#0000ff", topic);
                            break;
                        case 'Point2d':
                            geometry = this.drawPoint(data.point, color, topic, radius);
                            break;
                        case 'LineString':
                            geometry = this.drawLineString(data.points, color, topic, lineWidth);
                            break;
                    }
                
                    if (geometry) {
                        this.addGeometry(type, geometry, item.topic);
                        this.geometries[type][item.topic].push(geometry);
                    }

                this.manageGeometryHistory(type, topic);

            });});
        });
    }
    
    drawText(text, position, color, topic) {
        const transformedPos = this.transformCoordinates(position.x, position.y);

        const style = new PIXI.TextStyle({
            fill: color,
            fontSize: 12
        });

        const textObj = new PIXI.Text(text, style);
        textObj.x = transformedPos.x;
        textObj.y = transformedPos.y;

        // Add metadata for potential interaction
        textObj.topic = topic;

        return textObj;
    }

    drawPolygon(points, color, topic) {
        if (points.length < 3) return null;
        const alpha = 0.2;
        const graphics = new PIXI.Graphics();

        graphics.beginFill(color, alpha);
        graphics.lineStyle(2, color, 1);

        // Transform and draw first point
        const firstPoint = this.transformCoordinates(points[0].x, points[0].y);
        graphics.moveTo(firstPoint.x, firstPoint.y);

        // Draw lines to subsequent points
        for (let i = 1; i < points.length; i++) {
            const point = this.transformCoordinates(points[i].x, points[i].y);
            graphics.lineTo(point.x, point.y);
        }
1
        // Close the polygon
        graphics.closePath();
        graphics.endFill();

        // Add metadata for potential interaction
        graphics.topic = topic;
        
        return graphics;
    }

    drawPolygonVector(polygons, color, topic) {
   
        const alpha = 0.2;
        const graphics = new PIXI.Graphics();
        
        for (const polygon of polygons) {
            graphics.beginFill(color, alpha);
            graphics.lineStyle(2, color, 1);
            
            if (polygon.points && polygon.points.length > 0) {
                const firstPoint = this.transformCoordinates(polygon.points[0].x, polygon.points[0].y);
             
                // Move to first point
                graphics.moveTo(firstPoint.x, firstPoint.y);
    
                // Draw lines to subsequent points
                for (let i = 1; i < polygon.points.length; i++) {
                    const point = this.transformCoordinates(polygon.points[i].x, polygon.points[i].y);
                    graphics.lineTo(point.x, point.y);
                }
        
                // Close the polygon
                graphics.closePath();
                graphics.endFill();

                // interactive
                // graphics.interactive = true;
                // graphics.cursor = 'pointer';
                // graphics.on('mouseover', () => {
                //     graphics.alpha = 0.5;
                // });
            }
        }

        // Add metadata
        graphics.topic = topic;
        return graphics;
    }
    


    drawPoint(point, color, topic, radius = 5) {

        const transformedPoint = this.transformCoordinates(point.x, point.y);
        
        const graphics = new PIXI.Graphics();
        graphics.beginFill(color, 0.5);
        graphics.drawCircle(transformedPoint.x, transformedPoint.y, radius);
        graphics.endFill();

        // Add metadata for potential interaction
        graphics.topic = topic;

        return graphics;
    }

    drawLineString(points, color, topic, lineWidth = 2) {
        if (points.length < 2) return null;

        const graphics = new PIXI.Graphics();
        graphics.lineStyle(lineWidth, color, 1);

        // Transform and draw first point
        const firstPoint = this.transformCoordinates(points[0].x, points[0].y);
        graphics.moveTo(firstPoint.x, firstPoint.y);

        // Draw lines to subsequent points
        for (let i = 1; i < points.length; i++) {
            const point = this.transformCoordinates(points[i].x, points[i].y);
            graphics.lineTo(point.x, point.y);
        }

        // Add metadata for potential interaction
        graphics.topic = topic;

        return graphics;
    }

    // Clear geometries for a specific type or topic
    clear(type, topic) {
        console.log('Clearing geometries');
        
        const container = this.geometryContainers[type];
        
        if (!container) {
            Logger.warn(`Container for type ${type} not found`);
            return;
        }
        
        // Remove geometries matching the topic (or all if no topic specified)
        for (let i = container.children.length - 1; i >= 0; i--) {
            const child = container.children[i];
            if (!topic || child.topic === topic) {
                container.removeChild(child);
                child.destroy();
            }
        }
        // Also clear stored data
        if (this.geometryData[type]) {
            if (topic) {
                this.geometryData[type][topic] = this.geometryData[type][topic].filter(item => item.topic !== topic);
            } else {
                this.geometryData[type][topic] = [];
            }
        }
    }

    // Add a geometry to the appropriate container
    addGeometry(type, geometry, topic) {

        // 
        if (!this.geometryContainers[type]) {
            Logger.warn(`Container for type ${type} not found`);
            return;
        }
        
        // Add PIXI object to the container
        if (geometry) {
            this.geometryContainers[type].addChild(geometry);
        }

        // Add metadata for potential interaction
        if (geometry) {

             // Initialize topic array if not exists
            if (!this.geometries[type][topic]) {
                this.geometries[type][topic] = [];
            }   
            this.geometries[type][topic].push(geometry);

        }
    }
}
