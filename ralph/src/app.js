/**
 * Online Collaboration Whiteboard - Main Application
 * US-014: WebRTC Real-time Collaboration
 */

import { CollaborationManager } from './collaboration.js';

// Available tool types
const ToolTypes = {
  SELECT: 'select',
  RECTANGLE: 'rectangle',
  ELLIPSE: 'ellipse',
  DIAMOND: 'diamond',
  LINE: 'line',
  ARROW: 'arrow',
  PENCIL: 'pencil',
  TEXT: 'text',
  ERASER: 'eraser',
  UNDO: 'undo',
  REDO: 'redo'
};

// Element types
const ElementTypes = {
  RECTANGLE: 'rectangle',
  ELLIPSE: 'ellipse',
  DIAMOND: 'diamond',
  LINE: 'line',
  ARROW: 'arrow',
  PENCIL: 'pencil',
  TEXT: 'text'
};

// Default styles (will be customizable via color panel in US-011)
const DefaultStyles = {
  strokeColor: '#000000',
  fillColor: 'transparent',
  lineWidth: 2
};

class Whiteboard {
  constructor() {
    this.canvas = document.getElementById('whiteboard-canvas');
    this.ctx = this.canvas.getContext('2d');
    this.container = document.getElementById('canvas-container');

    // Canvas transform state
    this.scale = 1;
    this.offsetX = 0;
    this.offsetY = 0;

    // Pan state
    this.isPanning = false;
    this.lastX = 0;
    this.lastY = 0;

    // Zoom limits
    this.minScale = 0.1;
    this.maxScale = 5;

    // Tool state
    this.currentTool = ToolTypes.SELECT;
    this.elements = [];

    // Drawing state - for active shape being drawn
    this.isDrawing = false;
    this.currentShape = null;
    this.startPoint = null;

    // Text editing state
    this.isEditingText = false;
    this.textInput = null;
    this.currentTextElement = null;

    // Eraser state
    this.isErasing = false;
    this.eraserSize = 20; // Size of eraser in world coordinates

    // Selection state
    this.selectedElements = []; // Array of selected elements
    this.isDragging = false; // Dragging selected elements
    this.isResizing = false; // Resizing a selected element
    this.activeHandle = null; // Which resize handle is active
    this.dragStartX = 0;
    this.dragStartY = 0;
    this.elementStartPositions = new Map(); // Store original positions when dragging
    this.isMarqueeSelecting = false; // Marquee (box) selection
    this.marqueeStart = null;
    this.marqueeCurrent = null;

    // Current styles
    this.styles = { ...DefaultStyles };
    this.styles.fontSize = 16; // Default font size in pixels

    // Undo/Redo history
    this.undoStack = [];
    this.redoStack = [];
    this.maxHistorySize = 50; // Maximum number of history steps

    // LocalStorage key for persistence
    this.storageKey = 'online-whiteboard-data';

    // Collaboration state
    this.collaboration = null;
    this.collaborationEnabled = false;
    this.remoteCursors = new Map(); // peerId -> cursorElement
    this.availableColors = [
      '#ef4444', '#f97316', '#eab308', '#22c55e', '#06b6d4',
      '#3b82f6', '#8b5cf6', '#ec4899', '#f43f5e'
    ];

    // Try to load saved data from localStorage
    this.loadFromStorage();

    // Save initial state (if nothing loaded)
    this.saveState();

    // Initialize
    this.resizeCanvas();
    this.setupEventListeners();
    this.setupToolbar();
    this.setupTextInput();
    this.setupStylePanel();
    this.setupCollaboration();
    this.render();
  }

  resizeCanvas() {
    this.canvas.width = this.container.clientWidth;
    this.canvas.height = this.container.clientHeight;
    this.render();
  }

  setupEventListeners() {
    // Window resize
    window.addEventListener('resize', () => this.resizeCanvas());

    // Mouse events for panning (when no tool is selected or dragging on empty space)
    this.canvas.addEventListener('mousedown', (e) => this.handleMouseDown(e));
    this.canvas.addEventListener('mousemove', (e) => this.handleMouseMove(e));
    this.canvas.addEventListener('mouseup', () => this.handleMouseUp());
    this.canvas.addEventListener('mouseleave', () => this.handleMouseUp());

    // Wheel for zoom
    this.canvas.addEventListener('wheel', (e) => this.handleWheel(e));

    // Keyboard events for selection operations
    document.addEventListener('keydown', (e) => this.handleKeyDown(e));

    // Copy/paste events
    document.addEventListener('copy', (e) => this.handleCopy(e));
    document.addEventListener('paste', (e) => this.handlePaste(e));
  }

  setupToolbar() {
    const toolbar = document.getElementById('toolbar');
    if (!toolbar) return;

    // Add click handlers to all tool buttons
    toolbar.querySelectorAll('.tool-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const tool = btn.dataset.tool;
        this.selectTool(tool);
      });
    });

    // Select initial tool and highlight it
    this.updateToolbarHighlight();
  }

  selectTool(toolName) {
    // Undo/Redo/Clear/Export are actions, not persistent tools
    if (toolName === 'undo') {
      this.undo();
      return;
    }
    if (toolName === 'redo') {
      this.redo();
      return;
    }
    if (toolName === 'clear') {
      this.clearCanvas();
      return;
    }
    if (toolName === 'export') {
      this.exportToPNG();
      return;
    }

    this.currentTool = toolName;
    this.updateToolbarHighlight();
    this.updateCursor();
  }

  updateToolbarHighlight() {
    // Remove active class from all buttons
    document.querySelectorAll('.tool-btn').forEach(btn => {
      btn.classList.remove('active');
    });

    // Add active class to current tool button
    const currentBtn = document.querySelector(`.tool-btn[data-tool="${this.currentTool}"]`);
    if (currentBtn) {
      currentBtn.classList.add('active');
    }

    // Update enabled/disabled state for undo/redo buttons
    const undoBtn = document.querySelector('.tool-btn[data-tool="undo"]');
    const redoBtn = document.querySelector('.tool-btn[data-tool="redo"]');
    if (undoBtn) {
      undoBtn.disabled = !this.canUndo();
    }
    if (redoBtn) {
      redoBtn.disabled = !this.canRedo();
    }
  }

  updateCursor() {
    switch (this.currentTool) {
      case 'select':
        this.canvas.style.cursor = 'default';
        break;
      case 'rectangle':
      case 'ellipse':
      case 'diamond':
      case 'line':
      case 'arrow':
      case 'pencil':
      case 'text':
        this.canvas.style.cursor = 'crosshair';
        break;
      case 'eraser':
        this.canvas.style.cursor = 'cell';
        break;
      default:
        this.canvas.style.cursor = 'default';
    }
  }

  handleMouseDown(e) {
    if (e.button !== 0) return; // Only handle left mouse button

    const { x: worldX, y: worldY } = this.screenToWorld(e.clientX, e.clientY);

    // Handle based on current tool
    if (this.currentTool === ToolTypes.SELECT) {
      // Check if clicking on a resize handle
      if (this.selectedElements.length === 1) {
        const handle = this.getHandleAtPoint(worldX, worldY);
        if (handle) {
          this.isResizing = true;
          this.activeHandle = handle;
          this.dragStartX = worldX;
          this.dragStartY = worldY;
          this.elementStartPositions = new Map();
          this.selectedElements.forEach(el => this.elementStartPositions.set(el, { ...this.getElementBounds(el) }));
          return;
        }
      }

      // Check if clicking on a selected element
      const clickedElement = this.getElementAtPoint(worldX, worldY);
      if (clickedElement) {
        if (!this.isSelected(clickedElement)) {
          // If not already selected, select it
          if (!e.shiftKey) {
            // Clear selection if not holding shift
            this.clearSelection();
          }
          this.selectElement(clickedElement);
        }
        // Start dragging the selected elements
        this.isDragging = true;
        this.dragStartX = worldX;
        this.dragStartY = worldY;
        this.elementStartPositions = new Map();
        this.selectedElements.forEach(el => this.elementStartPositions.set(el, { ...this.getElementBounds(el) }));
        return;
      }

      // If clicked empty area, start marquee selection
      if (!e.shiftKey) {
        this.clearSelection();
      }
      this.isMarqueeSelecting = true;
      this.marqueeStart = { x: worldX, y: worldY };
      this.marqueeCurrent = { x: worldX, y: worldY };
    } else if (this.currentTool === ToolTypes.RECTANGLE) {
      // Start drawing rectangle
      this.isDrawing = true;
      this.startPoint = { x: worldX, y: worldY };
      this.currentShape = {
        type: ElementTypes.RECTANGLE,
        x: worldX,
        y: worldY,
        width: 0,
        height: 0,
        strokeColor: this.styles.strokeColor,
        fillColor: this.styles.fillColor,
        lineWidth: this.styles.lineWidth
      };
    } else if (this.currentTool === ToolTypes.ELLIPSE) {
      // Start drawing ellipse
      this.isDrawing = true;
      this.startPoint = { x: worldX, y: worldY };
      this.currentShape = {
        type: ElementTypes.ELLIPSE,
        x: worldX,
        y: worldY,
        width: 0,
        height: 0,
        strokeColor: this.styles.strokeColor,
        fillColor: this.styles.fillColor,
        lineWidth: this.styles.lineWidth
      };
    } else if (this.currentTool === ToolTypes.DIAMOND) {
      // Start drawing diamond
      this.isDrawing = true;
      this.startPoint = { x: worldX, y: worldY };
      this.currentShape = {
        type: ElementTypes.DIAMOND,
        x: worldX,
        y: worldY,
        width: 0,
        height: 0,
        strokeColor: this.styles.strokeColor,
        fillColor: this.styles.fillColor,
        lineWidth: this.styles.lineWidth
      };
    } else if (this.currentTool === ToolTypes.LINE || this.currentTool === ToolTypes.ARROW) {
      // Start drawing line or arrow
      this.isDrawing = true;
      this.startPoint = { x: worldX, y: worldY };
      this.currentShape = {
        type: this.currentTool === ToolTypes.LINE ? ElementTypes.LINE : ElementTypes.ARROW,
        x1: worldX,
        y1: worldY,
        x2: worldX,
        y2: worldY,
        strokeColor: this.styles.strokeColor,
        lineWidth: this.styles.lineWidth
      };
    } else if (this.currentTool === ToolTypes.PENCIL) {
      // Start drawing pencil stroke
      this.isDrawing = true;
      this.currentShape = {
        type: ElementTypes.PENCIL,
        points: [{ x: worldX, y: worldY }],
        strokeColor: this.styles.strokeColor,
        lineWidth: this.styles.lineWidth
      };
    } else if (this.currentTool === ToolTypes.TEXT) {
      // Start text editing
      this.startTextEditing(worldX, worldY);
    } else if (this.currentTool === ToolTypes.ERASER) {
      // Start erasing
      this.isErasing = true;
      // Check if we hit an element immediately on mousedown
      this.eraseAtPoint(worldX, worldY);
      this.currentShape = { x: worldX, y: worldY };
    }
  }

  handleMouseMove(e) {
    if (this.isPanning) {
      const deltaX = e.clientX - this.lastX;
      const deltaY = e.clientY - this.lastY;

      this.offsetX += deltaX;
      this.offsetY += deltaY;

      this.lastX = e.clientX;
      this.lastY = e.clientY;

      this.render();
      return;
    }

    // Handle resizing
    if (this.isResizing && this.selectedElements.length === 1) {
      const { x: worldX, y: worldY } = this.screenToWorld(e.clientX, e.clientY);
      const deltaX = worldX - this.dragStartX;
      const deltaY = worldY - this.dragStartY;

      const element = this.selectedElements[0];
      const bounds = this.elementStartPositions.get(element);

      this.resizeElement(element, this.activeHandle, bounds, deltaX, deltaY, e.shiftKey);
      this.render();
      return;
    }

    // Handle dragging selected elements
    if (this.isDragging) {
      const { x: worldX, y: worldY } = this.screenToWorld(e.clientX, e.clientY);
      const deltaX = worldX - this.dragStartX;
      const deltaY = worldY - this.dragStartY;

      this.selectedElements.forEach(element => {
        const startBounds = this.elementStartPositions.get(element);
        this.moveElementBy(element, deltaX, deltaY);
      });

      this.render();
      return;
    }

    // Handle marquee selection
    if (this.isMarqueeSelecting) {
      const { x: worldX, y: worldY } = this.screenToWorld(e.clientX, e.clientY);
      this.marqueeCurrent = { x: worldX, y: worldY };
      this.render();
      return;
    }

    if (this.isErasing) {
      const { x: worldX, y: worldY } = this.screenToWorld(e.clientX, e.clientY);
      this.currentShape = { x: worldX, y: worldY };
      this.eraseAtPoint(worldX, worldY);
      this.render();
      return;
    }

    if (this.isDrawing && this.currentShape) {
      const { x: worldX, y: worldY } = this.screenToWorld(e.clientX, e.clientY);

      if (this.currentShape.type === ElementTypes.PENCIL) {
        // Pencil: add point to path
        this.currentShape.points.push({ x: worldX, y: worldY });
      } else {
        // Calculate bounds from start point for other shapes
        let minX = Math.min(this.startPoint.x, worldX);
        let maxX = Math.max(this.startPoint.x, worldX);
        let minY = Math.min(this.startPoint.y, worldY);
        let maxY = Math.max(this.startPoint.y, worldY);

        // Hold Shift to force uniform (perfect circle/square/symmetric diamond)
        if (e.shiftKey && (this.currentShape.type === ElementTypes.ELLIPSE || this.currentShape.type === ElementTypes.RECTANGLE || this.currentShape.type === ElementTypes.DIAMOND)) {
          const width = maxX - minX;
          const height = maxY - minY;
          const size = Math.max(width, height);

          // Maintain aspect ratio starting from original corner
          if (worldX < this.startPoint.x) minX = this.startPoint.x - size;
          else maxX = this.startPoint.x + size;

          if (worldY < this.startPoint.y) minY = this.startPoint.y - size;
          else maxY = this.startPoint.y + size;
        }

        if (this.currentShape.type === ElementTypes.LINE || this.currentShape.type === ElementTypes.ARROW) {
          // Line/arrow: update end point
          let endX = worldX;
          let endY = worldY;

          // Hold Shift to constrain to 45-degree angles
          if (e.shiftKey) {
            const dx = Math.abs(endX - this.startPoint.x);
            const dy = Math.abs(endY - this.startPoint.y);

            if (dx > dy) {
              // Mostly horizontal
              endY = this.startPoint.y;
            } else if (dy > dx) {
              // Mostly vertical
              endX = this.startPoint.x;
            } else {
              // 45 degrees - keep equal distances
              const signX = endX >= this.startPoint.x ? 1 : -1;
              const signY = endY >= this.startPoint.y ? 1 : -1;
              const distance = Math.max(dx, dy);
              endX = this.startPoint.x + signX * distance;
              endY = this.startPoint.y + signY * distance;
            }
          }

          this.currentShape.x2 = endX;
          this.currentShape.y2 = endY;
        } else {
          // Regular shape handling for rectangles/ellipses
          this.currentShape.x = minX;
          this.currentShape.y = minY;
          this.currentShape.width = maxX - minX;
          this.currentShape.height = maxY - minY;
        }
      }

      this.render();
    }
  }

  handleMouseUp() {
    if (this.isPanning) {
      this.isPanning = false;
      this.updateCursor();
      return;
    }

    // Finish resizing
    if (this.isResizing) {
      this.isResizing = false;
      this.activeHandle = null;
      // Broadcast resize changes to remote collaborators
      if (this.selectedElements.length === 1) {
        const element = this.selectedElements[0];
        this.broadcastLocalAction({
          type: 'resize-element',
          oldElement: this.elementStartPositions.get(element),
          newElement: element
        });
      }
      this.elementStartPositions.clear();
      this.saveState();
      this.render();
      return;
    }

    // Finish dragging
    if (this.isDragging) {
      this.isDragging = false;
      // Broadcast move changes to remote collaborators
      this.selectedElements.forEach(element => {
        const oldElement = this.elementStartPositions.get(element);
        this.broadcastLocalAction({
          type: 'move-element',
          oldElement: oldElement,
          newElement: element
        });
      });
      this.elementStartPositions.clear();
      // Only save if we actually moved something
      if (this.selectedElements.length > 0) {
        this.saveState();
      }
      this.render();
      return;
    }

    // Finish marquee selection
    if (this.isMarqueeSelecting) {
      this.finishMarqueeSelection();
      this.isMarqueeSelecting = false;
      this.marqueeStart = null;
      this.marqueeCurrent = null;
      this.render();
      return;
    }

    if (this.isErasing) {
      this.isErasing = false;
      this.currentShape = null;
      // Switch back to select after erasing like other tools
      this.selectTool(ToolTypes.SELECT);
      this.render();
      return;
    }

    if (this.isDrawing && this.currentShape) {
      // Only add if it has enough content
      let shouldAdd = false;

      if (this.currentShape.type === ElementTypes.PENCIL) {
        // Pencil needs at least 2 points to be visible
        shouldAdd = this.currentShape.points.length >= 2;
      } else {
        // Other shapes need reasonable size
        shouldAdd = (this.currentShape.width > 1 || this.currentShape.height > 1);
      }

      if (shouldAdd) {
        this.elements.push({ ...this.currentShape });
        this.saveState();
        // Broadcast to remote collaborators
        this.broadcastLocalAction({
          type: 'add-element',
          element: this.currentShape
        });
      }

      // Clear drawing state and switch back to select
      this.isDrawing = false;
      this.currentShape = null;
      this.startPoint = null;
      this.selectTool(ToolTypes.SELECT);
      this.render();
    }
  }

  handleWheel(e) {
    e.preventDefault();

    // Get mouse position
    const mouseX = e.clientX;
    const mouseY = e.clientY;

    // Calculate zoom factor
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    let newScale = this.scale * delta;

    // Clamp to zoom limits
    newScale = Math.max(this.minScale, Math.min(this.maxScale, newScale));

    // Adjust offset to zoom towards mouse position
    const scaleFactor = newScale / this.scale;
    this.offsetX = mouseX - (mouseX - this.offsetX) * scaleFactor;
    this.offsetY = mouseY - (mouseY - this.offsetY) * scaleFactor;

    this.scale = newScale;

    this.render();
  }

  screenToWorld(x, y) {
    return {
      x: (x - this.offsetX) / this.scale,
      y: (y - this.offsetY) / this.scale
    };
  }

  worldToScreen(x, y) {
    return {
      x: x * this.scale + this.offsetX,
      y: y * this.scale + this.offsetY
    };
  }

  setupTextInput() {
    // Create hidden text input for editing
    this.textInput = document.createElement('textarea');
    this.textInput.style.position = 'absolute';
    this.textInput.style.border = 'none';
    this.textInput.style.outline = 'none';
    this.textInput.style.resize = 'none';
    this.textInput.style.background = 'transparent';
    this.textInput.style.color = 'transparent';
    this.textInput.style.caretColor = '#000000';
    this.textInput.style.fontFamily = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    this.textInput.style.zIndex = '10';
    this.textInput.style.display = 'none';
    this.textInput.placeholder = 'Type text...';
    this.container.appendChild(this.textInput);

    // Event handlers for text input
    this.textInput.addEventListener('blur', () => this.finishTextEditing());
    this.textInput.addEventListener('keydown', (e) => {
      // Enter key (with Ctrl/Cmd for newline) finishes editing
      if (e.key === 'Enter' && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        this.finishTextEditing();
      }
      // Escape cancels
      if (e.key === 'Escape') {
        this.cancelTextEditing();
      }
    });
  }

  setupStylePanel() {
    // Get DOM elements
    const strokeColorInput = document.getElementById('stroke-color');
    const fillColorInput = document.getElementById('fill-color');
    const fillTransparentBtn = document.getElementById('fill-transparent');
    const lineWidthInput = document.getElementById('line-width');
    const lineWidthValue = document.getElementById('line-width-value');
    const fontSizeInput = document.getElementById('font-size');
    const fontSizeValue = document.getElementById('font-size-value');

    // Set initial values
    strokeColorInput.value = this.styles.strokeColor === 'transparent' ? '#000000' : this.styles.strokeColor;
    if (this.styles.fillColor !== 'transparent') {
      fillColorInput.value = this.styles.fillColor;
    } else {
      fillColorInput.value = '#ffffff';
      fillTransparentBtn.classList.add('active');
    }

    lineWidthInput.value = this.styles.lineWidth;
    lineWidthValue.textContent = `${this.styles.lineWidth}px`;
    fontSizeInput.value = this.styles.fontSize;
    fontSizeValue.textContent = `${this.styles.fontSize}px`;

    // Stroke color change
    strokeColorInput.addEventListener('input', (e) => {
      this.styles.strokeColor = e.target.value;
    });

    // Fill color change
    fillColorInput.addEventListener('input', (e) => {
      this.styles.fillColor = e.target.value;
      fillTransparentBtn.classList.remove('active');
    });

    // Transparent fill button
    fillTransparentBtn.addEventListener('click', () => {
      this.styles.fillColor = 'transparent';
      fillTransparentBtn.classList.add('active');
    });

    // Line width change
    lineWidthInput.addEventListener('input', (e) => {
      this.styles.lineWidth = parseInt(e.target.value, 10);
      lineWidthValue.textContent = `${this.styles.lineWidth}px`;
    });

    // Font size change
    fontSizeInput.addEventListener('input', (e) => {
      this.styles.fontSize = parseInt(e.target.value, 10);
      fontSizeValue.textContent = `${this.styles.fontSize}px`;
    });
  }

  startTextEditing(worldX, worldY) {
    const { x: screenX, y: screenY } = this.worldToScreen(worldX, worldY);

    // Calculate font size in screen coordinates
    const screenFontSize = this.styles.fontSize * this.scale;

    // Position and show input
    this.textInput.style.left = `${screenX}px`;
    this.textInput.style.top = `${screenY}px`;
    this.textInput.style.minWidth = '100px';
    this.textInput.style.minHeight = `${screenFontSize}px`;
    this.textInput.style.fontSize = `${screenFontSize}px`;
    this.textInput.style.color = this.styles.strokeColor;
    this.textInput.style.display = 'block';
    this.textInput.value = '';

    // Store the text element being created
    this.currentTextElement = {
      type: ElementTypes.TEXT,
      x: worldX,
      y: worldY,
      text: '',
      fontSize: this.styles.fontSize,
      color: this.styles.strokeColor
    };

    this.isEditingText = true;
    this.textInput.focus();
  }

  finishTextEditing() {
    if (!this.isEditingText || !this.currentTextElement) return;

    const text = this.textInput.value.trim();
    if (text.length > 0) {
      this.currentTextElement.text = text;
      this.elements.push({ ...this.currentTextElement });
      this.saveState();
      // Broadcast to remote collaborators
      this.broadcastLocalAction({
        type: 'add-element',
        element: this.currentTextElement
      });
      this.render();
    }

    this.cancelTextEditing();
    this.selectTool(ToolTypes.SELECT);
  }

  cancelTextEditing() {
    this.textInput.style.display = 'none';
    this.isEditingText = false;
    this.currentTextElement = null;
  }

  eraseAtPoint(worldX, worldY) {
    // Check elements from top to bottom (last drawn is top)
    for (let i = this.elements.length - 1; i >= 0; i--) {
      const element = this.elements[i];
      if (this.hitTest(element, worldX, worldY)) {
        this.elements.splice(i, 1);
        this.saveState();
        this.render();
        break; // Only delete one element on click - for drag we delete multiple as mouse moves
      }
    }
  }

  hitTest(element, x, y) {
    // Check if point (x,y) in world coordinates hits the element
    switch (element.type) {
      case ElementTypes.RECTANGLE:
        // Check if point is inside or exactly on the rectangle
        return x >= element.x && x <= element.x + element.width &&
               y >= element.y && y <= element.y + element.height;

      case ElementTypes.ELLIPSE: {
        // Ellipse hit test - check if point is inside ellipse
        const cx = element.x + element.width / 2;
        const cy = element.y + element.height / 2;
        const rx = element.width / 2;
        const ry = element.height / 2;
        if (rx === 0 || ry === 0) return false;
        const dx = (x - cx) / rx;
        const dy = (y - cy) / ry;
        return dx * dx + dy * dy <= 1;
      }

      case ElementTypes.DIAMOND: {
        // Diamond hit test (rotated square/rectangle)
        const cx = element.x + element.width / 2;
        const cy = element.y + element.height / 2;
        const halfW = element.width / 2;
        const halfH = element.height / 2;
        const dx = Math.abs(x - cx) / halfW;
        const dy = Math.abs(y - cy) / halfH;
        return dx + dy <= 1;
      }

      case ElementTypes.LINE:
      case ElementTypes.ARROW: {
        // Line hit test - check distance from point to line
        return this.pointToLineDistance(x, y, element.x1, element.y1, element.x2, element.y2) <= (element.lineWidth / 2 + this.eraserSize / 2);
      }

      case ElementTypes.PENCIL: {
        // For pencil strokes, check distance to any of the line segments
        if (!element.points || element.points.length < 2) return false;
        for (let i = 1; i < element.points.length; i++) {
          const p1 = element.points[i-1];
          const p2 = element.points[i];
          const dist = this.pointToLineDistance(x, y, p1.x, p1.y, p2.x, p2.y);
          if (dist <= (element.lineWidth / 2 + this.eraserSize / 2)) {
            return true;
          }
        }
        return false;
      }

      case ElementTypes.TEXT: {
        // Rough approximation: check if point is in bounding box
        this.ctx.font = `${element.fontSize}px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`;
        const metrics = this.ctx.measureText(element.text);
        const width = metrics.width;
        const height = element.fontSize;
        return x >= element.x && x <= element.x + width &&
               y >= element.y && y <= element.y + height;
      }

      default:
        return false;
    }
  }

  pointToLineDistance(px, py, x1, y1, x2, y2) {
    // Calculate distance from point (px,py) to line segment (x1,y1)-(x2,y2)
    const A = px - x1;
    const B = py - y1;
    const C = x2 - x1;
    const D = y2 - y1;

    const dot = A * C + B * D;
    const lenSq = C * C + D * D;

    if (lenSq === 0) return Math.sqrt(A * A + B * B);

    // Parameter of projection of point onto line
    let param = dot / lenSq;

    let xx, yy;
    if (param < 0) {
      xx = x1;
      yy = y1;
    } else if (param > 1) {
      xx = x2;
      yy = y2;
    } else {
      xx = x1 + param * C;
      yy = y1 + param * D;
    }

    const dx = px - xx;
    const dy = py - yy;
    return Math.sqrt(dx * dx + dy * dy);
  }

  render() {
    // Clear canvas
    this.ctx.save();
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    // Apply transform
    this.ctx.translate(this.offsetX, this.offsetY);
    this.ctx.scale(this.scale, this.scale);

    // Draw all completed elements
    this.elements.forEach(element => {
      this.drawElement(element);
    });

    // Draw current shape being drawn (preview)
    if (this.isDrawing && this.currentShape) {
      this.drawElement(this.currentShape);
    }

    // Draw eraser preview (visual feedback)
    if (this.isErasing && this.currentShape) {
      this.ctx.beginPath();
      this.ctx.arc(this.currentShape.x, this.currentShape.y, this.eraserSize / 2, 0, 2 * Math.PI);
      this.ctx.fillStyle = 'rgba(255, 0, 0, 0.2)';
      this.ctx.fill();
      this.ctx.strokeStyle = 'rgba(255, 0, 0, 0.5)';
      this.ctx.lineWidth = 1;
      this.ctx.stroke();
    }

    // Draw selection handles and marquee
    this.drawSelection();

    this.ctx.restore();
  }

  drawElement(element, targetCtx = null) {
    const ctx = targetCtx || this.ctx;

    switch (element.type) {
      case ElementTypes.RECTANGLE:
        ctx.beginPath();
        ctx.rect(element.x, element.y, element.width, element.height);
        ctx.strokeStyle = element.strokeColor;
        ctx.fillStyle = element.fillColor;
        ctx.lineWidth = element.lineWidth;
        ctx.fill();
        ctx.stroke();
        break;
      case ElementTypes.ELLIPSE:
        ctx.beginPath();
        const centerX = element.x + element.width / 2;
        const centerY = element.y + element.height / 2;
        ctx.ellipse(
          centerX,
          centerY,
          element.width / 2,
          element.height / 2,
          0,
          0,
          2 * Math.PI
        );
        ctx.strokeStyle = element.strokeColor;
        ctx.fillStyle = element.fillColor;
        ctx.lineWidth = element.lineWidth;
        ctx.fill();
        ctx.stroke();
        break;
      case ElementTypes.LINE:
        ctx.beginPath();
        ctx.moveTo(element.x1, element.y1);
        ctx.lineTo(element.x2, element.y2);
        ctx.strokeStyle = element.strokeColor;
        ctx.lineWidth = element.lineWidth;
        ctx.lineCap = 'round';
        ctx.stroke();
        break;
      case ElementTypes.ARROW:
        // Draw the main line
        ctx.beginPath();
        ctx.moveTo(element.x1, element.y1);
        ctx.lineTo(element.x2, element.y2);
        ctx.strokeStyle = element.strokeColor;
        ctx.lineWidth = element.lineWidth;
        ctx.lineCap = 'round';
        ctx.stroke();

        // Draw arrowhead
        this.drawArrowhead(element.x1, element.y1, element.x2, element.y2, element.lineWidth, element.strokeColor);
        break;
      case ElementTypes.PENCIL:
        // Draw freehand pencil stroke
        if (element.points.length < 2) break;

        ctx.beginPath();
        ctx.moveTo(element.points[0].x, element.points[0].y);

        // Simple smoothing: use lineTo for each point with round line caps
        for (let i = 1; i < element.points.length; i++) {
          ctx.lineTo(element.points[i].x, element.points[i].y);
        }

        ctx.strokeStyle = element.strokeColor;
        ctx.lineWidth = element.lineWidth;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.stroke();
        break;
      case ElementTypes.TEXT:
        // Draw text element
        ctx.font = `${element.fontSize}px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`;
        ctx.fillStyle = element.color;
        ctx.textBaseline = 'top';
        ctx.fillText(element.text, element.x, element.y);
        break;
      case ElementTypes.DIAMOND:
        // Draw diamond shape
        ctx.beginPath();
        const cx = element.x + element.width / 2;
        const cy = element.y + element.height / 2;
        // Four points: top, right, bottom, left
        ctx.moveTo(cx, element.y);
        ctx.lineTo(element.x + element.width, cy);
        ctx.lineTo(cx, element.y + element.height);
        ctx.lineTo(element.x, cy);
        ctx.closePath();
        ctx.strokeStyle = element.strokeColor;
        ctx.fillStyle = element.fillColor;
        ctx.lineWidth = element.lineWidth;
        ctx.fill();
        ctx.stroke();
        break;
      default:
        break;
    }
  }

  drawArrowhead(x1, y1, x2, y2, lineWidth, strokeColor) {
    const { ctx } = this;
    // Calculate arrowhead size proportional to line width
    const headSize = Math.max(8, lineWidth * 3);

    // Calculate angle of the line
    const angle = Math.atan2(y2 - y1, x2 - x1);

    ctx.beginPath();
    // Draw the two sides of the arrowhead
    ctx.moveTo(x2, y2);
    ctx.lineTo(
      x2 - headSize * Math.cos(angle - Math.PI / 6),
      y2 - headSize * Math.sin(angle - Math.PI / 6)
    );
    ctx.moveTo(x2, y2);
    ctx.lineTo(
      x2 - headSize * Math.cos(angle + Math.PI / 6),
      y2 - headSize * Math.sin(angle + Math.PI / 6)
    );
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = lineWidth;
    ctx.lineCap = 'round';
    ctx.stroke();
  }

  // === Selection methods ===

  getElementAtPoint(x, y) {
    // Find top-most element at given point
    for (let i = this.elements.length - 1; i >= 0; i--) {
      const element = this.elements[i];
      if (this.hitTest(element, x, y)) {
        return element;
      }
    }
    return null;
  }

  isSelected(element) {
    return this.selectedElements.includes(element);
  }

  selectElement(element) {
    if (!this.isSelected(element)) {
      this.selectedElements.push(element);
    }
  }

  clearSelection() {
    this.selectedElements = [];
  }

  getElementBounds(element) {
    // Calculate bounding box of any element
    switch (element.type) {
      case ElementTypes.RECTANGLE:
      case ElementTypes.ELLIPSE:
      case ElementTypes.DIAMOND:
        return {
          x: element.x,
          y: element.y,
          width: element.width,
          height: element.height
        };
      case ElementTypes.LINE:
      case ElementTypes.ARROW:
        const minX = Math.min(element.x1, element.x2);
        const maxX = Math.max(element.x1, element.x2);
        const minY = Math.min(element.y1, element.y2);
        const maxY = Math.max(element.y1, element.y2);
        const padding = element.lineWidth / 2 + 4;
        return {
          x: minX - padding,
          y: minY - padding,
          width: (maxX - minX) + padding * 2,
          height: (maxY - minY) + padding * 2
        };
      case ElementTypes.PENCIL:
        if (!element.points || element.points.length === 0) {
          return { x: 0, y: 0, width: 0, height: 0 };
        }
        const xs = element.points.map(p => p.x);
        const ys = element.points.map(p => p.y);
        const minPx = Math.min(...xs);
        const maxPx = Math.max(...xs);
        const minPy = Math.min(...ys);
        const maxPy = Math.max(...ys);
        const pad = element.lineWidth / 2 + 4;
        return {
          x: minPx - pad,
          y: minPy - pad,
          width: (maxPx - minPx) + pad * 2,
          height: (maxPy - minPy) + pad * 2
        };
      case ElementTypes.TEXT: {
        this.ctx.font = `${element.fontSize}px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`;
        const metrics = this.ctx.measureText(element.text);
        return {
          x: element.x,
          y: element.y,
          width: metrics.width,
          height: element.fontSize
        };
      }
      default:
        return { x: 0, y: 0, width: 0, height: 0 };
    }
  }

  getHandleAtPoint(worldX, worldY) {
    // Check if click is on a resize handle
    if (this.selectedElements.length !== 1) return null;

    const bounds = this.getElementBounds(this.selectedElements[0]);
    const handleSize = this.getHandleSizeInWorld();

    // All eight handles
    const handles = this.getHandles(bounds);

    for (const [name, handleX, handleY] of handles) {
      const dx = worldX - handleX;
      const dy = worldY - handleY;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist <= handleSize / 2) {
        return name;
      }
    }

    return null;
  }

  getHandleSizeInWorld() {
    // Handle size is 8 pixels screen, convert to world coordinates
    return 8 / this.scale;
  }

  getHandles(bounds) {
    const handleSize = this.getHandleSizeInWorld();
    const halfSize = handleSize / 2;

    return [
      ['top-left', bounds.x - halfSize, bounds.y - halfSize],
      ['top-middle', bounds.x + bounds.width / 2 - halfSize, bounds.y - halfSize],
      ['top-right', bounds.x + bounds.width - halfSize, bounds.y - halfSize],
      ['middle-left', bounds.x - halfSize, bounds.y + bounds.height / 2 - halfSize],
      ['middle-right', bounds.x + bounds.width - halfSize, bounds.y + bounds.height / 2 - halfSize],
      ['bottom-left', bounds.x - halfSize, bounds.y + bounds.height - halfSize],
      ['bottom-middle', bounds.x + bounds.width / 2 - halfSize, bounds.y + bounds.height - halfSize],
      ['bottom-right', bounds.x + bounds.width - halfSize, bounds.y + bounds.height - halfSize]
    ];
  }

  moveElementBy(element, deltaX, deltaY) {
    // Move element by delta
    switch (element.type) {
      case ElementTypes.RECTANGLE:
      case ElementTypes.ELLIPSE:
      case ElementTypes.DIAMOND:
        element.x += deltaX;
        element.y += deltaY;
        break;
      case ElementTypes.LINE:
      case ElementTypes.ARROW:
        element.x1 += deltaX;
        element.y1 += deltaY;
        element.x2 += deltaX;
        element.y2 += deltaY;
        break;
      case ElementTypes.PENCIL:
        if (element.points) {
          element.points.forEach(p => {
            p.x += deltaX;
            p.y += deltaY;
          });
        }
        break;
      case ElementTypes.TEXT:
        element.x += deltaX;
        element.y += deltaY;
        break;
    }
  }

  resizeElement(element, handle, originalBounds, deltaX, deltaY, shiftKey) {
    const { x: ox, y: oy, width: ow, height: oh } = originalBounds;
    let newX = ox;
    let newY = oy;
    let newWidth = ow + deltaX;
    let newHeight = oh + deltaY;

    // Adjust based on which handle is being dragged
    if (handle.includes('left')) {
      newX = ox + deltaX;
      newWidth = ow - deltaX;
    }
    if (handle.includes('top')) {
      newY = oy + deltaY;
      newHeight = oh - deltaY;
    }
    if (handle.includes('right')) {
      newWidth = ow + deltaX;
    }
    if (handle.includes('bottom')) {
      newHeight = oh + deltaY;
    }

    // Hold shift to maintain aspect ratio
    if (shiftKey && handle.includes('corner')) {
      const aspectRatio = ow / oh;
      if (newWidth / aspectRatio > newHeight) {
        newWidth = newHeight * aspectRatio;
        if (handle.includes('left')) {
          newX = ox + (ow - newWidth);
        }
      } else {
        newHeight = newWidth / aspectRatio;
        if (handle.includes('top')) {
          newY = oy + (oh - newHeight);
        }
      }
    }

    // Don't allow negative sizes
    if (newWidth < 1) newWidth = 1;
    if (newHeight < 1) newHeight = 1;

    // Apply resized bounds back to element
    switch (element.type) {
      case ElementTypes.RECTANGLE:
      case ElementTypes.ELLIPSE:
      case ElementTypes.DIAMOND:
        element.x = newX;
        element.y = newY;
        element.width = newWidth;
        element.height = newHeight;
        break;
      case ElementTypes.LINE:
      case ElementTypes.ARROW:
        // Line bounds are padded, adjust accordingly
        const padding = element.lineWidth / 2 + 4;
        if (handle.includes('left') || handle.includes('top')) {
          element.x1 = newX + padding;
          element.y1 = newY + padding;
        } else {
          element.x2 = newX + newWidth - padding;
          element.y2 = newY + newHeight - padding;
        }
        break;
    }
  }

  finishMarqueeSelection() {
    if (!this.marqueeStart || !this.marqueeCurrent) return;

    const minX = Math.min(this.marqueeStart.x, this.marqueeCurrent.x);
    const maxX = Math.max(this.marqueeStart.x, this.marqueeCurrent.x);
    const minY = Math.min(this.marqueeStart.y, this.marqueeCurrent.y);
    const maxY = Math.max(this.marqueeStart.y, this.marqueeCurrent.y);

    // Find all elements that intersect with the marquee box
    this.elements.forEach(element => {
      const bounds = this.getElementBounds(element);
      if (this.boundsIntersect(
        minX, minY, maxX - minX, maxY - minY,
        bounds.x, bounds.y, bounds.width, bounds.height
      )) {
        if (!this.isSelected(element)) {
          this.selectElement(element);
        }
      }
    });
  }

  boundsIntersect(ax, ay, aw, ah, bx, by, bw, bh) {
    // Check if two rectangles intersect
    return !(ax + aw < bx || bx + bw < ax || ay + ah < by || by + bh < ay);
  }

  deleteSelectedElements() {
    // Remove all selected elements from elements array
    let deleted = false;
    for (let i = this.selectedElements.length - 1; i >= 0; i--) {
      const element = this.selectedElements[i];
      const index = this.elements.indexOf(element);
      if (index !== -1) {
        this.elements.splice(index, 1);
        // Broadcast deletion to remote collaborators
        this.broadcastLocalAction({
          type: 'delete-element',
          element: element
        });
        deleted = true;
      }
    }
    if (deleted) {
      this.saveState();
    }
    this.clearSelection();
    this.render();
  }

  handleKeyDown(e) {
    // Handle Undo/Redo keyboard shortcuts globally
    if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
      if (e.shiftKey) {
        // Ctrl+Shift+Z for redo
        this.redo();
      } else {
        // Ctrl+Z for undo
        this.undo();
      }
      e.preventDefault();
      return;
    }

    if ((e.ctrlKey || e.metaKey) && e.key === 'y') {
      // Ctrl+Y for redo (alternative)
      this.redo();
      e.preventDefault();
      return;
    }

    // Only handle delete when we have selected elements and tool is select
    if (this.currentTool !== ToolTypes.SELECT || this.selectedElements.length === 0) {
      return;
    }

    if (e.key === 'Delete' || e.key === 'Backspace') {
      this.deleteSelectedElements();
      // Prevent backspace from navigating back
      if (e.key === 'Backspace') {
        e.preventDefault();
      }
    }
  }

  handleCopy(e) {
    // Only copy when we have selected elements and tool is select
    if (this.currentTool !== ToolTypes.SELECT || this.selectedElements.length === 0) {
      return;
    }

    // Create a deep copy of selected elements
    const toCopy = JSON.stringify(this.selectedElements.map(el => ({ ...el })));
    e.clipboardData.setData('application/json', toCopy);
    e.preventDefault();
  }

  handlePaste(e) {
    // Only paste when tool is select
    if (this.currentTool !== ToolTypes.SELECT) {
      return;
    }

    try {
      const data = e.clipboardData.getData('application/json');
      if (!data) return;

      const elementsToPaste = JSON.parse(data);
      // Offset pasted elements slightly for visibility
      const offset = 10 / this.scale;

      elementsToPaste.forEach(el => {
        // Deep copy with offset
        const copy = this.deepCopyElement(el);
        // Move copy down-right
        this.offsetElement(copy, offset, offset);
        this.elements.push(copy);
        // Broadcast to remote collaborators
        this.broadcastLocalAction({
          type: 'add-element',
          element: copy
        });
        // Select the pasted elements
        if (!this.selectedElements.includes(copy)) {
          this.selectedElements.push(copy);
        }
      });

      this.saveState();
      this.render();
      e.preventDefault();
    } catch (err) {
      console.error('Failed to paste:', err);
    }
  }

  deepCopyElement(element) {
    const copy = JSON.parse(JSON.stringify(element));
    return copy;
  }

  offsetElement(element, deltaX, deltaY) {
    this.moveElementBy(element, deltaX, deltaY);
  }

  drawSelection() {
    if (this.selectedElements.length === 0) return;

    const { ctx } = this;
    ctx.save();

    // Draw a semi-transparent blue overlay for multiple selections
    if (this.selectedElements.length > 1) {
      this.selectedElements.forEach(element => {
        const bounds = this.getElementBounds(element);
        ctx.beginPath();
        ctx.rect(bounds.x - 2, bounds.y - 2, bounds.width + 4, bounds.height + 4);
        ctx.fillStyle = 'rgba(37, 99, 235, 0.1)';
        ctx.fill();
        ctx.strokeStyle = '#2563eb';
        ctx.lineWidth = 1 / this.scale;
        ctx.stroke();
      });
    }

    // Draw resize handles for single selection
    if (this.selectedElements.length === 1) {
      const element = this.selectedElements[0];
      const bounds = this.getElementBounds(element);
      const handleSize = this.getHandleSizeInWorld();

      // Draw selection bounding box
      ctx.beginPath();
      ctx.rect(bounds.x, bounds.y, bounds.width, bounds.height);
      ctx.strokeStyle = '#2563eb';
      ctx.lineWidth = 1 / this.scale;
      ctx.setLineDash([4 / this.scale, 4 / this.scale]);
      ctx.stroke();
      ctx.setLineDash([]);

      // Draw handles
      const handles = this.getHandles(bounds);
      ctx.fillStyle = '#ffffff';
      ctx.strokeStyle = '#2563eb';
      ctx.lineWidth = 1 / this.scale;

      handles.forEach(([name, x, y]) => {
        const hs = handleSize;
        ctx.beginPath();
        ctx.rect(x, y, hs, hs);
        ctx.fill();
        ctx.stroke();
      });
    }

    // Draw active marquee selection
    if (this.isMarqueeSelecting && this.marqueeStart && this.marqueeCurrent) {
      const minX = Math.min(this.marqueeStart.x, this.marqueeCurrent.x);
      const maxX = Math.max(this.marqueeStart.x, this.marqueeCurrent.x);
      const minY = Math.min(this.marqueeStart.y, this.marqueeCurrent.y);
      const maxY = Math.max(this.marqueeStart.y, this.marqueeCurrent.y);

      ctx.beginPath();
      ctx.rect(minX, minY, maxX - minX, maxY - minY);
      ctx.fillStyle = 'rgba(37, 99, 235, 0.1)';
      ctx.fill();
      ctx.strokeStyle = '#2563eb';
      ctx.lineWidth = 1 / this.scale;
      ctx.setLineDash([4 / this.scale, 4 / this.scale]);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    ctx.restore();
  }

  // === Undo/Redo History ===

  saveState() {
    // Save a deep copy of current elements state to undo stack
    const state = JSON.parse(JSON.stringify(this.elements));
    this.undoStack.push(state);

    // Clear redo stack when new state is saved (can't redo after new action)
    this.redoStack = [];

    // Trim history if exceeds max size
    if (this.undoStack.length > this.maxHistorySize) {
      this.undoStack.shift();
    }

    // Auto-save to localStorage
    this.saveToStorage();

    // Update button enabled/disabled state
    this.updateToolbarHighlight();
  }

  // === LocalStorage Persistence ===

  saveToStorage() {
    try {
      const data = {
        elements: this.elements,
        offsetX: this.offsetX,
        offsetY: this.offsetY,
        scale: this.scale,
        styles: this.styles,
        timestamp: Date.now()
      };
      localStorage.setItem(this.storageKey, JSON.stringify(data));
    } catch (e) {
      console.warn('Failed to save to localStorage:', e);
    }
  }

  loadFromStorage() {
    try {
      const saved = localStorage.getItem(this.storageKey);
      if (!saved) {
        return false;
      }

      const data = JSON.parse(saved);
      if (data && Array.isArray(data.elements)) {
        this.elements = JSON.parse(JSON.stringify(data.elements));
        if (typeof data.offsetX === 'number') this.offsetX = data.offsetX;
        if (typeof data.offsetY === 'number') this.offsetY = data.offsetY;
        if (typeof data.scale === 'number') this.scale = data.scale;
        if (data.styles) this.styles = { ...data.styles };
        return true;
      }
    } catch (e) {
      console.warn('Failed to load from localStorage:', e);
    }
    return false;
  }

  clearCanvas() {
    if (this.elements.length === 0) {
      return;
    }

    if (!confirm('确定要清空画布吗？此操作无法撤销。')) {
      return;
    }

    // Clear all elements
    this.elements = [];
    this.clearSelection();

    // Broadcast to remote collaborators
    this.broadcastLocalAction({
      type: 'clear-all'
    });

    // Save to history and storage
    this.saveState();
    this.render();
  }

  exportToPNG() {
    // Calculate bounding box of all elements to know how big the export should be
    if (this.elements.length === 0) {
      alert('画布是空的，没有内容可以导出。');
      return;
    }

    // Find min/max bounds across all elements
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;

    this.elements.forEach(element => {
      const bounds = this.getElementBounds(element);
      // Add padding around the content
      minX = Math.min(minX, bounds.x - 20);
      minY = Math.min(minY, bounds.y - 20);
      maxX = Math.max(maxX, bounds.x + bounds.width + 20);
      maxY = Math.max(maxY, bounds.y + bounds.height + 20);
    });

    const exportWidth = maxX - minX;
    const exportHeight = maxY - minY;

    // Create a new canvas for export
    const exportCanvas = document.createElement('canvas');
    exportCanvas.width = exportWidth * 2; // 2x for higher resolution
    exportCanvas.height = exportHeight * 2;
    const exportCtx = exportCanvas.getContext('2d');

    // Scale for higher resolution
    exportCtx.scale(2, 2);

    // Fill transparent background (keep transparency)
    // Background grid is optional - we don't draw it by default but user can see it in app
    // Transparent background allows pasting into other tools easily

    // Translate to the correct position so our elements fit
    exportCtx.translate(-minX, -minY);

    // Draw all elements onto the export canvas
    this.elements.forEach(element => {
      this.drawElement(element, exportCtx);
    });

    // Convert to blob and trigger download
    exportCanvas.toBlob((blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.download = `whiteboard-export-${new Date().toISOString().slice(0, 10)}.png`;
      a.href = url;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 'image/png');
  }

  canUndo() {
    // We need at least two states to undo: current and previous
    // Because initial empty state is always on the stack
    return this.undoStack.length > 1;
  }

  canRedo() {
    return this.redoStack.length > 0;
  }

  undo() {
    if (!this.canUndo()) {
      return false;
    }

    // Save current state to redo stack before popping
    const currentState = this.undoStack.pop();
    this.redoStack.push(currentState);

    // Restore previous state
    const previousState = this.undoStack[this.undoStack.length - 1];
    this.elements = JSON.parse(JSON.stringify(previousState));

    // Save to localStorage
    this.saveToStorage();

    // Clear selection after undo
    this.clearSelection();
    this.updateToolbarHighlight();
    this.render();
    return true;
  }

  redo() {
    if (!this.canRedo()) {
      return false;
    }

    // Get state from redo stack and push to undo stack
    const nextState = this.redoStack.pop();
    this.undoStack.push(JSON.parse(JSON.stringify(nextState)));

    // Restore the state
    this.elements = JSON.parse(JSON.stringify(nextState));

    // Save to localStorage
    this.saveToStorage();

    // Clear selection after redo
    this.clearSelection();
    this.updateToolbarHighlight();
    this.render();
    return true;
  }

  // === Collaboration (WebRTC) ===

  setupCollaboration() {
    // Generate default username
    const defaultUsername = 'User_' + Math.random().toString(36).substr(2, 5);
    document.getElementById('username').value = defaultUsername;

    // Setup UI event listeners
    document.getElementById('create-room').addEventListener('click', () => this.createRoom());
    document.getElementById('join-room').addEventListener('click', () => this.joinRoom());
    document.getElementById('leave-room').addEventListener('click', () => this.leaveRoom());
    document.getElementById('copy-room').addEventListener('click', () => this.copyRoomCode());

    // Track mouse movement for cursor broadcasting
    this.canvas.addEventListener('mousemove', (e) => this.handleMouseMoveCollaboration(e));
  }

  createRoom() {
    const roomId = this.collaboration ? this.collaboration.generateRoomId() : 'ABC123';
    this.connectToRoom(roomId, true);
  }

  joinRoom() {
    const roomInput = document.getElementById('room-id');
    const roomId = roomInput.value.trim().toUpperCase();
    if (!roomId) {
      alert('请输入房间码');
      return;
    }
    this.connectToRoom(roomId, false);
  }

  async connectToRoom(roomId, isInitiator) {
    try {
      this.collaboration = new CollaborationManager({
        onRemoteAction: (peerId, action) => this.handleRemoteAction(peerId, action),
        onRemoteElements: (peerId, elements) => this.handleRemoteFullElements(peerId, elements),
        onRemoteCursor: (peerId, position, username) => this.updateRemoteCursor(peerId, position, username),
        onPeerConnect: (peerId) => this.handlePeerConnect(peerId),
        onPeerDisconnect: (peerId) => this.handlePeerDisconnect(peerId),
        onConnectionChange: (connected) => this.updateConnectionStatus(connected),
        onPeerConnected: (peerId, callback) => callback(this.elements)
      });

      await this.collaboration.connect(roomId, isInitiator);

      // Update UI
      document.getElementById('room-controls').style.display = 'none';
      document.getElementById('room-info').style.display = 'block';
      document.getElementById('current-room-code').textContent = roomId;

      this.collaborationEnabled = true;
      this.updatePeerCount();
    } catch (e) {
      console.error('Failed to connect to room:', e);
      alert('连接房间失败: ' + e.message);
    }
  }

  leaveRoom() {
    if (this.collaboration) {
      this.collaboration.disconnect();
      this.collaborationEnabled = false;
      this.collaboration = null;

      // Clean up remote cursors
      this.remoteCursors.forEach(cursor => {
        cursor.element.remove();
      });
      this.remoteCursors.clear();

      // Update UI
      document.getElementById('room-controls').style.display = 'block';
      document.getElementById('room-info').style.display = 'none';
      document.getElementById('connection-status').className = 'status-indicator disconnected';

      if (this.undoStack.length === 0) {
        this.saveState();
      }
    }
  }

  copyRoomCode() {
    const roomCode = document.getElementById('current-room-code').textContent;
    navigator.clipboard.writeText(roomCode).then(() => {
      alert('房间码已复制到剪贴板');
    }).catch(() => {
      alert('复制失败，请手动复制: ' + roomCode);
    });
  }

  updateConnectionStatus(connected) {
    const statusEl = document.getElementById('connection-status');
    if (connected) {
      statusEl.className = 'status-indicator connected';
    } else {
      statusEl.className = 'status-indicator disconnected';
    }
  }

  updatePeerCount() {
    if (!this.collaboration) {
      document.getElementById('peer-count').textContent = '';
      return;
    }
    const count = this.collaboration.getConnectedPeerCount();
    if (count > 0) {
      document.getElementById('peer-count').textContent = `(${count + 1} 在线)`;
    } else {
      document.getElementById('peer-count').textContent = '(等待连接...)';
    }
  }

  handlePeerConnect(peerId) {
    this.updatePeerCount();
  }

  handlePeerDisconnect(peerId) {
    // Remove remote cursor
    if (this.remoteCursors.has(peerId)) {
      this.remoteCursors.get(peerId).element.remove();
      this.remoteCursors.delete(peerId);
    }
    this.updatePeerCount();
  }

  getRandomColorForPeer(peerId) {
    // Simple hash based on peerId to get consistent color
    let hash = 0;
    for (let i = 0; i < peerId.length; i++) {
      hash = peerId.charCodeAt(i) + ((hash << 5) - hash);
    }
    const index = Math.abs(hash) % this.availableColors.length;
    return this.availableColors[index];
  }

  updateRemoteCursor(peerId, position, username) {
    // Convert world position to screen position
    const screenX = position.x * this.scale + this.offsetX;
    const screenY = position.y * this.scale + this.offsetY;

    if (!this.remoteCursors.has(peerId)) {
      // Create new cursor element
      const color = this.getRandomColorForPeer(peerId);
      const cursorEl = document.createElement('div');
      cursorEl.className = 'remote-cursor';
      cursorEl.innerHTML = `<div class="remote-cursor-dot" style="background: ${color};"></div><div class="remote-cursor-label" style="background: ${color};">${username}</div>`;
      this.container.appendChild(cursorEl);
      this.remoteCursors.set(peerId, {
        element: cursorEl,
        color: color,
        username: username
      });
    }

    const cursorInfo = this.remoteCursors.get(peerId);
    cursorInfo.element.style.transform = `translate(${screenX - 6}px, ${screenY - 6}px)`;
  }

  handleMouseMoveCollaboration(e) {
    if (!this.collaborationEnabled || !this.collaboration) return;

    const rect = this.canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Convert to world coordinates
    const worldPos = this.screenToWorld(x, y);
    const username = document.getElementById('username').value || 'Anonymous';

    this.collaboration.broadcastCursor(worldPos, username);
  }

  handleRemoteFullElements(peerId, remoteElements) {
    // Replace our elements with the full remote state when joining
    this.elements = JSON.parse(JSON.stringify(remoteElements));
    this.saveState();
    this.render();
  }

  handleRemoteAction(peerId, action) {
    // Apply remote action to local canvas
    switch (action.type) {
      case 'add-element':
        // Add the new element
        this.elements.push(action.element);
        this.saveState();
        this.render();
        break;
      case 'delete-element':
        // Find and remove the element (by matching properties, since we don't have ids yet)
        // For MVP, we do a best effort match based on type and position
        const index = this.findElementIndexByApproximateMatch(action.element);
        if (index !== -1) {
          this.elements.splice(index, 1);
          this.saveState();
          this.render();
        }
        break;
      case 'move-element':
        // Update element position
        const moveIndex = this.findElementIndexByApproximateMatch(action.oldElement);
        if (moveIndex !== -1) {
          this.elements[moveIndex] = JSON.parse(JSON.stringify(action.newElement));
          this.saveState();
          this.render();
        }
        break;
      case 'resize-element':
        // Update element bounds after resize
        const resizeIndex = this.findElementIndexByApproximateMatch(action.oldElement);
        if (resizeIndex !== -1) {
          this.elements[resizeIndex] = JSON.parse(JSON.stringify(action.newElement));
          this.saveState();
          this.render();
        }
        break;
      case 'clear-all':
        // Clear all elements
        this.elements = [];
        this.saveState();
        this.render();
        break;
    }
  }

  findElementIndexByApproximateMatch(searchElement) {
    // Find element by matching type and approximate position
    // In future we should add unique IDs to elements for proper collaboration
    for (let i = this.elements.length - 1; i >= 0; i--) {
      const el = this.elements[i];
      if (el.type !== searchElement.type) continue;

      // Check approximate position match
      let match = true;
      if (typeof el.x === 'number' && typeof searchElement.x === 'number') {
        if (Math.abs(el.x - searchElement.x) > 5) match = false;
      }
      if (typeof el.y === 'number' && typeof searchElement.y === 'number') {
        if (Math.abs(el.y - searchElement.y) > 5) match = false;
      }
      if (match) return i;
    }
    return -1;
  }

  broadcastLocalAction(action) {
    // Broadcast action to all connected peers if collaboration is enabled
    if (!this.collaborationEnabled || !this.collaboration) return;
    this.collaboration.broadcastAction(action);
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.whiteboard = new Whiteboard();
});
