import { Injectable, OnDestroy } from '@angular/core';
import * as fabric from 'fabric';
import { WhiteboardSyncService } from './whiteboard-sync.service';
import { Subscription } from 'rxjs';

export interface CanvasOperation {
  action: 'add' | 'remove' | 'clear';
  objectJSON?: any;
}

@Injectable({
  providedIn: 'root'
})
export class WhiteboardCanvasService implements OnDestroy {
  public canvas: any = null;
  public activeTool = 'pen';
  public activeColor = '#1e293b';
  public strokeWidth = 3;
  public strokeCount = 0;
  
  private history: CanvasOperation[] = [];
  private historyIndex = -1;
  private isUndoingRedoing = false;
  private isReceivingSync = false;
  
  private isDrawing = false;
  private currentDrawId = '';
  private remotePaths: { [id: string]: { pathObj: any, pathData: any[] } } = {};
  private sub: Subscription | null = null;

  constructor(private sync: WhiteboardSyncService) {}

  initCanvas(canvasEl: HTMLCanvasElement): void {
    const wrapper = canvasEl.parentElement!;
    this.canvas = new fabric.Canvas(canvasEl, {
      width: wrapper.clientWidth,
      height: wrapper.clientHeight,
      backgroundColor: '#ffffff',
      isDrawingMode: true,
    });

    if (!this.canvas.freeDrawingBrush) {
      this.canvas.freeDrawingBrush = new fabric.PencilBrush(this.canvas);
    }
    
    this.setupFabricEvents();
    this.setupSyncSubscription();
    this.setTool('pen');
  }

  private pushOperation(op: CanvasOperation) {
    if (this.isUndoingRedoing || this.isReceivingSync) return;
    this.history.splice(this.historyIndex + 1);
    this.history.push(op);
    if (this.history.length > 50) {
      this.history.shift();
    }
    this.historyIndex = this.history.length - 1;
  }

  private setupFabricEvents(): void {
    this.canvas.on('object:added', (e: any) => {
      if (this.isReceivingSync || !e.target || (e.target.id && e.target.id.startsWith('temp_'))) return;
      if (!e.target.id) {
        e.target.id = Math.random().toString(36).substring(2, 9);
      }
      this.strokeCount++;
      
      const objJSON = e.target.toJSON(['id']);
      objJSON.id = e.target.id; // Force ID

      this.pushOperation({ action: 'add', objectJSON: objJSON });
      
      const payload: any = { type: 'object_added', data: objJSON };
      if (!this.isDrawing && this.currentDrawId) {
        payload.replaces = this.currentDrawId;
      }
      this.sync.sendMessage(payload);
    });

    this.canvas.on('object:modified', (e: any) => {
      if (this.isReceivingSync || !e.target || (e.target.id && e.target.id.startsWith('temp_'))) return;
      const objJSON = e.target.toJSON(['id']);
      objJSON.id = e.target.id;
      this.sync.sendMessage({ type: 'object_modified', data: objJSON });
    });

    this.canvas.on('mouse:down', (o: any) => {
      // Handle Text Tool
      if (this.activeTool === 'text') {
        const p = this.canvas.getScenePoint ? this.canvas.getScenePoint(o.e) : (o.scenePoint || { x: o.e.clientX, y: o.e.clientY });
        const text = new fabric.IText('Text', {
          left: p.x, top: p.y, fill: this.activeColor, fontSize: 24
        });
        // @ts-ignore
        text.id = Math.random().toString(36).substring(2, 9);
        this.canvas.add(text);
        this.canvas.setActiveObject(text);
        this.canvas.renderAll();
        this.setTool('select');
        return;
      }

      // Handle Eraser Tool (click to delete)
      if (this.activeTool === 'eraser') {
        if (o.target) {
          const id = o.target.id;
          const objJSON = o.target.toJSON(['id']);
          objJSON.id = id;
          this.pushOperation({ action: 'remove', objectJSON: objJSON });
          this.canvas.remove(o.target);
          this.sync.sendMessage({ type: 'object_removed', data: { id } });
        }
        return;
      }

      if (!this.canvas.isDrawingMode) return;
      this.isDrawing = true;
      this.currentDrawId = Math.random().toString(36).substring(2, 9);
      const p = this.canvas.getScenePoint ? this.canvas.getScenePoint(o.e) : (o.scenePoint || { x: o.e.clientX, y: o.e.clientY });
      const color = this.canvas.freeDrawingBrush.color;
      const width = this.canvas.freeDrawingBrush.width;
      this.sync.sendMessage({
        type: 'draw_start',
        data: { id: this.currentDrawId, x: p.x, y: p.y, color, width }
      });
    });

    let lastMoveTime = 0;
    this.canvas.on('mouse:move', (o: any) => {
      const now = Date.now();
      if (now - lastMoveTime > 16) {
        lastMoveTime = now;
        const pointer = this.canvas.getScenePoint ? this.canvas.getScenePoint(o.e) : (o.scenePoint || { x: o.e.clientX, y: o.e.clientY });
        this.sync.sendMessage({ type: 'cursor_move', data: { x: pointer.x, y: pointer.y } });
        
        if (this.isDrawing && this.canvas.isDrawingMode) {
          this.sync.sendMessage({
            type: 'draw_move',
            data: { id: this.currentDrawId, x: pointer.x, y: pointer.y }
          });
        }
      }
    });

    this.canvas.on('mouse:up', () => {
      if (!this.isDrawing) return;
      this.isDrawing = false;
      this.sync.sendMessage({
        type: 'draw_end',
        data: { id: this.currentDrawId }
      });
    });
  }

  private setupSyncSubscription(): void {
    this.sub = this.sync.messages$.subscribe((msg: any) => {
      if (!this.canvas) return;
      
      if (msg.type === 'canvas_update' && msg.data) {
        this.isReceivingSync = true;
        this.canvas.loadFromJSON(msg.data).then(() => {
          this.canvas.renderAll();
          this.isReceivingSync = false;
        }).catch((err: any) => {
          console.error('Error loading JSON:', err);
          this.isReceivingSync = false;
        });
      } else if (msg.type === 'clear') {
        this.isReceivingSync = true;
        this.canvas.clear();
        this.canvas.backgroundColor = '#ffffff';
        this.canvas.renderAll();
        this.strokeCount = 0;
        this.isReceivingSync = false;
      } else if (msg.type === 'object_added') {
        // @ts-ignore
        fabric.util.enlivenObjects([msg.data]).then((objects: any[]) => {
          const obj = objects[0];
          const existing = this.canvas.getObjects().find((o: any) => o.id === obj.id);
          if (!existing) {
            this.isReceivingSync = true;
            if (msg.replaces && this.remotePaths[msg.replaces]) {
              this.canvas.remove(this.remotePaths[msg.replaces].pathObj);
              delete this.remotePaths[msg.replaces];
            }
            this.canvas.add(obj);
            this.isReceivingSync = false;
            this.canvas.renderAll();
          }
        });
      } else if (msg.type === 'object_removed') {
        const targetObj = this.canvas.getObjects().find((o: any) => o.id === msg.data.id);
        if (targetObj) {
          this.isReceivingSync = true;
          this.canvas.remove(targetObj);
          this.isReceivingSync = false;
          this.canvas.renderAll();
        }
      } else if (msg.type === 'object_modified') {
        const targetObj = this.canvas.getObjects().find((o: any) => o.id === msg.data.id);
        if (targetObj) {
          const { type, ...updateData } = msg.data;
          this.isReceivingSync = true;
          targetObj.set(updateData);
          targetObj.setCoords();
          this.isReceivingSync = false;
          this.canvas.renderAll();
        }
      } else if (msg.type === 'draw_start') {
        if (msg.sender === this.sync.currentUserId) return;
        const { id, x, y, color, width } = msg.data;
        const pathData: any[] = [['M', x, y]];
        const pathObj = new fabric.Path(pathData as any, {
          fill: 'transparent', stroke: color, strokeWidth: width,
          strokeLineCap: 'round', strokeLineJoin: 'round',
          selectable: false, evented: false, id: `temp_${id}`
        });
        this.remotePaths[id] = { pathObj, pathData };
        this.isReceivingSync = true;
        this.canvas.add(pathObj);
        this.isReceivingSync = false;
      } else if (msg.type === 'draw_move') {
        if (msg.sender === this.sync.currentUserId) return;
        const { id, x, y } = msg.data;
        if (this.remotePaths[id]) {
          const { pathObj, pathData } = this.remotePaths[id];
          pathData.push(['L', x, y]);
          this.isReceivingSync = true;
          pathObj.set({ path: pathData as any });
          this.isReceivingSync = false;
          this.canvas.requestRenderAll();
        }
      } else if (msg.type === 'draw_end') {
        if (msg.sender === this.sync.currentUserId) return;
        const { id } = msg.data;
        if (this.remotePaths[id]) {
          setTimeout(() => {
            if (this.remotePaths[id]) {
              this.isReceivingSync = true;
              this.canvas.remove(this.remotePaths[id].pathObj);
              this.isReceivingSync = false;
              delete this.remotePaths[id];
              this.canvas.requestRenderAll();
            }
          }, 3000);
        }
      }
    });
  }

  applyPermissions(): void {
    if (!this.canvas) return;
    if (this.sync.isDrawer) {
      if (['pen', 'highlighter', 'eraser'].includes(this.activeTool)) {
        this.canvas.isDrawingMode = true;
      }
      this.canvas.selection = true;
      this.canvas.forEachObject((obj: any) => {
        obj.selectable = true;
        obj.evented = true;
      });
    } else {
      this.canvas.isDrawingMode = false;
      this.canvas.selection = false;
      this.canvas.forEachObject((obj: any) => {
        obj.selectable = false;
        obj.evented = false;
      });
      this.canvas.discardActiveObject();
    }
    this.canvas.renderAll();
  }

  setTool(tool: string): void {
    this.activeTool = tool;
    if (!this.canvas) return;

    if (tool === 'pen' || tool === 'highlighter') {
      this.canvas.isDrawingMode = true;
      if (!this.canvas.freeDrawingBrush) this.canvas.freeDrawingBrush = new fabric.PencilBrush(this.canvas);
      
      let color = this.activeColor;
      if (tool === 'highlighter' && color.startsWith('#')) {
        const r = parseInt(color.slice(1, 3), 16);
        const g = parseInt(color.slice(3, 5), 16);
        const b = parseInt(color.slice(5, 7), 16);
        color = `rgba(${r}, ${g}, ${b}, 0.5)`;
      }
      
      this.canvas.freeDrawingBrush.color = color;
      this.canvas.freeDrawingBrush.width = tool === 'highlighter' ? 12 : this.strokeWidth;
    } else if (tool === 'eraser') {
      // Eraser is now click-to-delete
      this.canvas.isDrawingMode = false;
      this.canvas.selection = false;
    } else {
      this.canvas.isDrawingMode = false;
    }
  }

  applyColor(): void {
    if (!this.canvas) return;
    if (this.canvas.isDrawingMode) {
      if (!this.canvas.freeDrawingBrush) this.canvas.freeDrawingBrush = new fabric.PencilBrush(this.canvas);
      this.canvas.freeDrawingBrush.color = this.activeColor;
    }
    const active = this.canvas.getActiveObject();
    if (active) {
      active.set('stroke', this.activeColor);
      this.canvas.renderAll();
    }
  }

  applyStrokeWidth(): void {
    if (this.canvas?.isDrawingMode) {
      if (!this.canvas.freeDrawingBrush) this.canvas.freeDrawingBrush = new fabric.PencilBrush(this.canvas);
      this.canvas.freeDrawingBrush.width = this.strokeWidth;
    }
  }

  addShape(shape: string): void {
    if (!this.canvas) return;
    this.canvas.isDrawingMode = false;
    this.setTool('select');

    let obj: any;
    const left = this.canvas.width ? this.canvas.width / 2 : 100;
    const top = this.canvas.height ? this.canvas.height / 2 : 100;
    const opts = { stroke: this.activeColor, strokeWidth: this.strokeWidth, fill: 'transparent', left, top, originX: 'center' as const, originY: 'center' as const };

    if (shape === 'rect') obj = new fabric.Rect({ ...opts, width: 150, height: 100 });
    else if (shape === 'circle') obj = new fabric.Circle({ ...opts, radius: 60 });
    else if (shape === 'line') obj = new fabric.Line([-75, 0, 75, 0], opts);
    else if (shape === 'arrow') {
      // Simple representation of an arrow using a path, or just a thick line for now
      obj = new fabric.Line([-75, 0, 75, 0], { ...opts, strokeWidth: 3 });
    }

    if (obj) {
      obj.id = Math.random().toString(36).substring(2, 9);
      this.canvas.add(obj);
      this.canvas.setActiveObject(obj);
      this.canvas.renderAll();
    }
  }

  undo(): void {
    if (!this.canvas || this.historyIndex < 0) return;
    this.isUndoingRedoing = true;
    const op = this.history[this.historyIndex];
    this.historyIndex--;

    if (op.action === 'add' && op.objectJSON) {
      const obj = this.canvas.getObjects().find((o: any) => o.id === op.objectJSON.id);
      if (obj) {
        this.isReceivingSync = true;
        this.canvas.remove(obj);
        this.isReceivingSync = false;
        this.sync.sendMessage({ type: 'object_removed', data: { id: op.objectJSON.id } });
        this.canvas.renderAll();
      }
    } else if (op.action === 'remove' && op.objectJSON) {
      // @ts-ignore
      fabric.util.enlivenObjects([op.objectJSON]).then((objects: any[]) => {
        this.isReceivingSync = true;
        this.canvas.add(objects[0]);
        this.isReceivingSync = false;
        this.sync.sendMessage({ type: 'object_added', data: op.objectJSON });
        this.canvas.renderAll();
      });
    }
    
    this.isUndoingRedoing = false;
  }

  redo(): void {
    if (!this.canvas || this.historyIndex >= this.history.length - 1) return;
    this.historyIndex++;
    this.isUndoingRedoing = true;
    const op = this.history[this.historyIndex];

    if (op.action === 'add' && op.objectJSON) {
      // @ts-ignore
      fabric.util.enlivenObjects([op.objectJSON]).then((objects: any[]) => {
        this.isReceivingSync = true;
        this.canvas.add(objects[0]);
        this.isReceivingSync = false;
        this.sync.sendMessage({ type: 'object_added', data: op.objectJSON });
        this.canvas.renderAll();
      });
    } else if (op.action === 'remove' && op.objectJSON) {
      const obj = this.canvas.getObjects().find((o: any) => o.id === op.objectJSON.id);
      if (obj) {
        this.isReceivingSync = true;
        this.canvas.remove(obj);
        this.isReceivingSync = false;
        this.sync.sendMessage({ type: 'object_removed', data: { id: op.objectJSON.id } });
        this.canvas.renderAll();
      }
    }

    this.isUndoingRedoing = false;
  }

  clearCanvas(): void {
    if (!this.canvas) return;
    this.canvas.clear();
    this.canvas.backgroundColor = '#ffffff';
    this.canvas.renderAll();
    this.strokeCount = 0;
    this.history = [];
    this.historyIndex = -1;
    this.sync.sendMessage({ type: 'clear' });
  }

  saveCanvas(roomId: string): void {
    if (!this.canvas) return;
    const dataURL = this.canvas.toDataURL({ format: 'png', quality: 1 });
    const link = document.createElement('a');
    link.download = `whiteboard-${roomId}-${Date.now()}.png`;
    link.href = dataURL;
    link.click();
  }

  ngOnDestroy(): void {
    if (this.sub) this.sub.unsubscribe();
    if (this.canvas) {
      this.canvas.dispose();
      this.canvas = null;
    }
    this.history = [];
    this.historyIndex = -1;
  }
}
