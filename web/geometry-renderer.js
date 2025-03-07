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
            backgroundColor = 0x555555,
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

        // Create tooltip element
        const tooltip = document.getElementById('tooltip');

        // Append Pixi view to the container
        this.container.appendChild(this.app.view);

        // Containers for different geometry types
        this.geometryContainers = {
            Text: new PIXI.Container(),
            Polygon: new PIXI.Container(),
            PolygonVector: new PIXI.Container(),
            Point2d: new PIXI.Container(),
            LineString: new PIXI.Container()
        };

        // Add containers to the stage
        Object.values(this.geometryContainers).forEach(container => {
            this.app.stage.addChild(container);
        });

        // Store coordinate transformation function
        this.coordinateTransform = coordinateTransform;

        // Resize handling
        window.addEventListener('resize', () => this.resize());
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
        return { x, y };
    }

    getTopicColor(topic, dataType) {
        // First, check if topic has a specific style
        if (TOPIC_STYLES[topic]) {
            return TOPIC_STYLES[topic].color;
        }
        
        // Fallback to default color for data type
        return TOPIC_STYLES.default[dataType] || 0xffffff;
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
                graphics.interactive = true;
                graphics.cursor = 'pointer';
                graphics.on('mouseover', () => {
                    graphics.alpha = 0.5;
                });
            }
        }

        // Add metadata
        graphics.topic = topic;
        return graphics;
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

        // Close the polygon
        graphics.closePath();
        graphics.endFill();

        // Add metadata for potential interaction
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
    }

    // Add a geometry to the appropriate container
    addGeometry(type, geometry, topic) {
        if (!this.geometryContainers[type]) {
            Logger.warn(`Container for type ${type} not found`);
            return;
        }
        
        if (geometry) {
            this.geometryContainers[type].addChild(geometry);
        }
    }
}