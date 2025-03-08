// canvas-renderer.js
import * as PIXI from 'https://cdnjs.cloudflare.com/ajax/libs/pixi.js/7.2.4/pixi.mjs';
import { GeometryRenderer, Logger } from './geometry-renderer.js';
import { WebSocketManager } from './websocket-manager.js';

export class CanvasRenderer {
    constructor(options = {}) {
        const {
            width = window.innerWidth,
            height = window.innerHeight,
            initialViewport = { x: 0, y: 0, width: 1000, height: 1000 }, // Default canvas size in model coords
            containerId = 'canvas-container',
            backgroundColor = 0x111111,
            backgroundAlpha = 1,
            gridSize = 100, // Size of grid cells
            showGrid = true,
            wsOptions = {}
        } = options;

        // Create canvas container
        this.container = document.getElementById(containerId);
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = containerId;
            document.body.appendChild(this.container);
        }
        
        // Debug elements
        this.debugInfo = document.createElement('div');
        this.debugInfo.style.position = 'absolute';
        this.debugInfo.style.top = '10px';
        this.debugInfo.style.left = '10px';
        this.debugInfo.style.background = 'rgba(0,0,0,0.7)';
        this.debugInfo.style.color = 'white';
        this.debugInfo.style.padding = '10px';
        this.debugInfo.style.fontFamily = 'monospace';
        this.debugInfo.style.zIndex = '1000';
        document.body.appendChild(this.debugInfo);
        
        // Canvas viewport settings
        this.viewport = initialViewport;
        this.width = width;
        this.height = height;
        this.showGrid = showGrid;
        this.gridSize = gridSize;
        
        // Create PIXI application
        this.app = new PIXI.Application({
            width: width,
            height: height,
            backgroundColor: backgroundColor,
        });
        this.container.appendChild(this.app.view);
        
        // Create containers
        this.gridContainer = new PIXI.Container();
        this.debugContainer = new PIXI.Container(); // Container for debug elements
        this.app.stage.addChild(this.gridContainer);
        this.app.stage.addChild(this.debugContainer);

        // Set up coordinate transform function for the renderer
        const transformFunction = (x, y) => {
            return this.transformCoordinates(x, y);
        };
        
        // Initialize WebSocket manager with our custom renderer
        this.wsManager = new WebSocketManager({
            ...wsOptions,
            rendererOptions: {
                containerId: 'geometry-container',
                coordinateTransform: transformFunction
            }
        });
        
        // Initial canvas setup
        this.drawGrid();
        
        // Add a test point at (300, 300) to debug
        // this.addDebugPoint(300, 300, 0xff0000);
        
        // Set up interaction
        this.setupInteraction();
        
        // Handle window resize
        window.addEventListener('resize', () => {
            this.resize(window.innerWidth, window.innerHeight);
        });
        
        // Update debug info
        this.updateDebugInfo();
    }
    
    resize(width, height) {
        this.width = width;
        this.height = height;
        this.app.renderer.resize(width, height);
        this.drawGrid();
        this.updateDebugInfo();
    }
    
    // Update debug information
    updateDebugInfo() {
        this.debugInfo.innerHTML = `
            <div>Viewport: x=${this.viewport.x.toFixed(0)}, y=${this.viewport.y.toFixed(0)}, 
                       w=${this.viewport.width.toFixed(0)}, h=${this.viewport.height.toFixed(0)}</div>
            <div>Canvas: ${this.width}x${this.height}</div>
            <div>Point (300,300) should be at screen: ${JSON.stringify(this.transformCoordinates(300, 300))}</div>
        `;
    }
    
    // Add a visible debug point at specified coordinates
    addDebugPoint(x, y, color = 0xff0000, size = 10) {
        this.debugContainer.removeChildren();
        
        // Create a point in model coordinates
        const screenPos = this.transformCoordinates(x, y);
        
        const graphics = new PIXI.Graphics();
        graphics.beginFill(color);
        graphics.drawCircle(screenPos.x, screenPos.y, size);
        graphics.endFill();
        
        // Add crosshair lines for visibility
        graphics.lineStyle(2, color);
        graphics.moveTo(screenPos.x - size*2, screenPos.y);
        graphics.lineTo(screenPos.x + size*2, screenPos.y);
        graphics.moveTo(screenPos.x, screenPos.y - size*2);
        graphics.lineTo(screenPos.x, screenPos.y + size*2);
        
        this.debugContainer.addChild(graphics);
        
        // Add text label
        const text = new PIXI.Text(`(${x},${y})`, {
            fontFamily: 'Arial',
            fontSize: 12,
            fill: color
        });
        text.x = screenPos.x + size + 5;
        text.y = screenPos.y - 10;
        this.debugContainer.addChild(text);
        
        // Logger.log(`Debug point added at model (${x}, ${y}) -> screen (${screenPos.x.toFixed(0)}, ${screenPos.y.toFixed(0)})`);
    }
    
    // Transform coordinates from model space to screen pixels
    transformCoordinates(_x, _y) {
        // Calculate the scale factors
        const scaleX = this.width / this.viewport.width;
        const scaleY = this.height / this.viewport.height;
        
        // Transform the coordinates
        const screenX = (_x - this.viewport.x) * scaleX;
        const screenY = (_y - this.viewport.y) * scaleY;
        // const x = (_x - this.viewport.x) * scaleX;
        // const y = (_y - this.viewport.y) * scaleY;
        
        return { 'x': screenX, 'y': screenY};
    }
    
    // Inverse transform from screen pixels to model space
    inverseTransform(screenX, screenY) {
        const scaleX = this.width / this.viewport.width;
        const scaleY = this.height / this.viewport.height;
        
        const x = (screenX / scaleX) + this.viewport.x;
        const y = (screenY / scaleY) + this.viewport.y;
        
        return { x, y };
    }
    
    // Draw grid lines based on current viewport
    drawGrid() {
        if (!this.showGrid) return;
        
        this.gridContainer.removeChildren();
        
        const graphics = new PIXI.Graphics();
        graphics.lineStyle(1, 0x333333, 1.0);
        
        // Calculate grid start and end points
        const start = this.viewport;
        const end = {
            x: this.viewport.x + this.viewport.width,
            y: this.viewport.y + this.viewport.height
        };
        
        // Calculate grid lines positions
        const startGridX = Math.floor(start.x / this.gridSize) * this.gridSize;
        const startGridY = Math.floor(start.y / this.gridSize) * this.gridSize;
        
        // Draw vertical grid lines
        for (let x = startGridX; x <= end.x; x += this.gridSize) {
            const startPos = this.transformCoordinates(x, start.y);
            graphics.moveTo(startPos.x, 0);
            graphics.lineTo(startPos.x, this.height);
            
            // Add coordinate labels on x-axis
            if (x % (this.gridSize * 5) === 0) {
                const label = new PIXI.Text(x.toString(), { 
                    fontFamily: 'Arial', 
                    fontSize: 10, 
                    fill: 0x666666 
                });
                label.x = startPos.x + 5;
                label.y = 5;
                this.gridContainer.addChild(label);
            }
        }
        
        // Draw horizontal grid lines
        for (let y = startGridY; y <= end.y; y += this.gridSize) {
            const startPos = this.transformCoordinates(start.x, y);
            graphics.moveTo(0, startPos.y);
            graphics.lineTo(this.width, startPos.y);
            
            // Add coordinate labels on y-axis
            if (y % (this.gridSize * 5) === 0) {
                const label = new PIXI.Text(y.toString(), { 
                    fontFamily: 'Arial', 
                    fontSize: 10, 
                    fill: 0x666666 
                });
                label.x = 5;
                label.y = startPos.y + 5;
                this.gridContainer.addChild(label);
            }
        }
        
        // Origin marker
        const origin = this.transformCoordinates(0, 0);
        if (origin.x >= 0 && origin.x <= this.width && 
            origin.y >= 0 && origin.y <= this.height) {
            graphics.beginFill(0x00fff0);
            graphics.drawCircle(origin.x, origin.y, 3);
        }

        // draw arrows
        // x axis; red, y axis; green at origin
        // the length is the same as the grid
        const xEnd = this.transformCoordinates(this.gridSize/2, 0);
        const yEnd = this.transformCoordinates(0, this.gridSize/2);
        graphics.lineStyle(4, 0xff0000);
        graphics.moveTo(origin.x, origin.y);
        graphics.lineTo(xEnd.x, xEnd.y);
        graphics.lineStyle(4, 0x00ff00);
        graphics.moveTo(origin.x, origin.y);
        graphics.lineTo(yEnd.x, yEnd.y);


        
        this.gridContainer.addChild(graphics);
        
        // Refresh our debug point if needed
        // this.addDebugPoint(300, 300, 0xff0000);
    }
    
    // Set up mouse and keyboard interaction
    setupInteraction() {
        // Mouse drag handling
        let dragging = false;
        let lastMouse = null;

        this.app.view.addEventListener('mousedown', e => {
            dragging = true;
            lastMouse = { x: e.clientX, y: e.clientY };
        });

        this.app.view.addEventListener('mousemove', e => {
            // Show coordinates in model space for debugging
            const modelCoords = this.inverseTransform(e.clientX, e.clientY);
            this.debugInfo.innerHTML = `<div>Mouse: screen(${e.clientX}, ${e.clientY}) → model(${modelCoords.x.toFixed(0)}, ${modelCoords.y.toFixed(0)})</div>`;
            
            if (!dragging) return;

            const dx = e.clientX - lastMouse.x;
            const dy = e.clientY - lastMouse.y;
            lastMouse = { x: e.clientX, y: e.clientY };

            // Calculate the movement in model coordinates
            const scaleX = this.viewport.width / this.width;
            const scaleY = this.viewport.height / this.height;
            
            // Move viewport in opposite direction of drag
            this.viewport.x -= dx * scaleX;
            this.viewport.y -= dy * scaleY;

            this.drawGrid();
            this.updateDebugInfo();
        });

        this.app.view.addEventListener('mouseup', () => {
            dragging = false;
        });

        // Keyboard navigation
        document.addEventListener('keydown', e => {
            const panStep = this.viewport.width / 20; // 5% of viewport width
            
            if (e.key === 'ArrowLeft') {
                this.viewport.x -= panStep;
                this.drawGrid();
                this.updateDebugInfo();
            }
            if (e.key === 'ArrowRight') {
                this.viewport.x += panStep;
                this.drawGrid();
                this.updateDebugInfo();
            }
            if (e.key === 'ArrowUp') {
                this.viewport.y -= panStep;
                this.drawGrid();
                this.updateDebugInfo();
            }
            if (e.key === 'ArrowDown') {
                this.viewport.y += panStep;
                this.drawGrid();
                this.updateDebugInfo();
            }
            
            // Reset view with 'r' key
            if (e.key === 'r') {
                this.resetView();
                this.updateDebugInfo();
            }
            
            // Center on point (300,300) with 'c' key
            if (e.key === 'c') {
                this.centerOn(300, 300);
                this.updateDebugInfo();
            }
        });

        // Zoom with mouse wheel
        this.app.view.addEventListener('wheel', e => {
            e.preventDefault();
            
            // Get mouse position in model coordinates before zoom
            const mousePos = this.inverseTransform(e.clientX, e.clientY);
            
            // Determine zoom factor
            const zoomFactor = e.deltaY > 0 ? 1.1 : 0.9;
            
            // Calculate new viewport dimensions
            const newWidth = this.viewport.width * zoomFactor;
            const newHeight = this.viewport.height * zoomFactor;
            
            // Calculate new viewport position to zoom toward mouse position
            const ratioX = (mousePos.x - this.viewport.x) / this.viewport.width;
            const ratioY = (mousePos.y - this.viewport.y) / this.viewport.height;
            
            const newX = mousePos.x - ratioX * newWidth;
            const newY = mousePos.y - ratioY * newHeight;
            
            // Update viewport
            this.viewport = {
                x: newX,
                y: newY,
                width: newWidth,
                height: newHeight
            };
            
            this.drawGrid();
            this.updateDebugInfo();
        });

        // Keyboard zoom
        document.addEventListener('keydown', e => {
            const zoomFactor = e.key === '=' ? 0.9 : e.key === '-' ? 1.1 : null;
            
            if (zoomFactor) {
                // Zoom toward center of viewport
                const centerX = this.viewport.x + this.viewport.width / 2;
                const centerY = this.viewport.y + this.viewport.height / 2;
                
                const newWidth = this.viewport.width * zoomFactor;
                const newHeight = this.viewport.height * zoomFactor;
                
                this.viewport = {
                    x: centerX - newWidth / 2,
                    y: centerY - newHeight / 2,
                    width: newWidth,
                    height: newHeight
                };
                
                this.drawGrid();
                this.updateDebugInfo();
            }
            
            // Toggle grid with 'g' key
            if (e.key === 'g') {
                this.showGrid = !this.showGrid;
                this.drawGrid();
                if (!this.showGrid) {
                    this.gridContainer.removeChildren();
                }
                this.updateDebugInfo();
            }
        });
    }
    
    // Center the viewport on specific coordinates
    centerOn(x, y) {
        const newX = x - this.viewport.width / 2;
        const newY = y - this.viewport.height / 2;
        
        this.viewport = {
            x: newX,
            y: newY,
            width: this.viewport.width,
            height: this.viewport.height
        };
        
        this.drawGrid();
        Logger.log(`Centered viewport on (${x}, ${y})`);
    }
    
    // Add a custom shape to the canvas
    // addShape(shape) {
    //     this.contentContainer.addChild(shape);
    // }
    
    // Clear all content (not the grid)
    // clearContent() {
    //     this.contentContainer.removeChildren();
    // }
    
    // Reset view to initial viewport
    resetView(viewport = { x: 0, y: 0, width: 1000, height: 1000 }) {
        this.viewport = viewport;
        this.drawGrid();
        Logger.log("View reset to initial state");
    }
}