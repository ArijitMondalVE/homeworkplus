import { Component, OnInit, OnDestroy, ElementRef, ViewChild, AfterViewInit } from '@angular/core';
import * as fabric from 'fabric';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../services/auth.service';
import { environment } from '../../../environments/environment';
import { ActivatedRoute, Router } from '@angular/router';

@Component({
  selector: 'app-whiteboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './whiteboard.component.html',
  styleUrls: ['./whiteboard.component.css']
})
export class WhiteboardComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('whiteboardCanvas') canvasRef!: ElementRef<HTMLCanvasElement>;

  activeTool = 'pen';
  activeColor = '#1e293b';
  strokeWidth = 3;
  strokeCount = 0;
  userName = 'Y';
  roomId = 'main';
  joinCode = '';

  colors = ['#1e293b', '#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6', '#ec4899', '#06b6d4', '#ffffff'];

  private canvas: any = null;
  private history: string[] = [];
  private historyIndex = -1;
  private ws: WebSocket | null = null;
  private isReceivingSync = false;

  constructor(private auth: AuthService, private route: ActivatedRoute, private router: Router) {}

  ngOnInit(): void {
    const user = this.auth.currentUser();
    this.userName = user?.username || 'Guest';

    this.route.paramMap.subscribe(params => {
      const newRoomId = params.get('roomId') || 'main';
      const isRoomChange = this.roomId !== newRoomId && this.roomId !== 'main';
      this.roomId = newRoomId;
      
      if (this.canvas) {
        if (this.ws) {
          this.ws.close();
        }
        this.canvas.clear();
        this.canvas.backgroundColor = '#ffffff';
        this.canvas.renderAll();
        this.history = [];
        this.historyIndex = -1;
        this.strokeCount = 0;
        this.connectWebSocket();
      }
    });
  }

  ngAfterViewInit(): void {
    this.initCanvas();
  }

  async initCanvas(): Promise<void> {
    try {
      const canvasEl = this.canvasRef.nativeElement;

      // Size canvas to container
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

      this.setTool('pen');
      this.canvas.on('path:created', () => {
        this.strokeCount++;
        this.saveHistory();
        this.broadcastCanvas();
      });

      this.canvas.on('object:modified', () => {
        this.saveHistory();
        this.broadcastCanvas();
      });

      this.connectWebSocket();
    } catch (e) {
      console.warn('Fabric.js not loaded:', e);
    }
  }

  private connectWebSocket(): void {
    const user = this.auth.currentUser();
    const userId = user?.id || 'anonymous';

    this.ws = new WebSocket(`${environment.wsUrl}/ws/whiteboard/${this.roomId}?user_id=${userId}`);

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
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
        }
      } catch (e) {
        console.error('WS message error:', e);
      }
    };
  }

  private broadcastCanvas(): void {
    if (!this.canvas || !this.ws || this.ws.readyState !== WebSocket.OPEN || this.isReceivingSync) return;
    const json = JSON.stringify(this.canvas.toJSON());
    this.ws.send(JSON.stringify({ type: 'canvas_update', data: json }));
  }

  setTool(tool: string): void {
    this.activeTool = tool;
    if (!this.canvas) return;

    if (tool === 'pen' || tool === 'highlighter') {
      this.canvas.isDrawingMode = true;
      if (!this.canvas.freeDrawingBrush) {
        this.canvas.freeDrawingBrush = new fabric.PencilBrush(this.canvas);
      }
      this.canvas.freeDrawingBrush.color = this.activeColor;
      this.canvas.freeDrawingBrush.width = tool === 'highlighter' ? 12 : this.strokeWidth;
      if (tool === 'highlighter') {
        this.canvas.freeDrawingBrush.color = this.activeColor + '80'; // 50% opacity
      }
    } else if (tool === 'eraser') {
      this.canvas.isDrawingMode = true;
      if (!this.canvas.freeDrawingBrush) {
        this.canvas.freeDrawingBrush = new fabric.PencilBrush(this.canvas);
      }
      this.canvas.freeDrawingBrush.color = '#ffffff';
      this.canvas.freeDrawingBrush.width = 20;
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

  async addShape(shape: string): Promise<void> {
    if (!this.canvas) return;
    this.canvas.isDrawingMode = false;
    this.activeTool = 'select';

    try {
      let obj: any;

      const opts = { stroke: this.activeColor, strokeWidth: this.strokeWidth, fill: 'transparent', left: 100, top: 100 };

      if (shape === 'rect') {
        obj = new fabric.Rect({ ...opts, width: 150, height: 100 });
      } else if (shape === 'circle') {
        obj = new fabric.Circle({ ...opts, radius: 60 });
      } else if (shape === 'line') {
        obj = new fabric.Line([50, 50, 200, 200], opts);
      } else if (shape === 'arrow') {
        obj = new fabric.Line([50, 100, 200, 100], { ...opts, strokeWidth: 3 });
      }

      if (obj) {
        this.canvas.add(obj);
        this.canvas.setActiveObject(obj);
        this.canvas.renderAll();
        this.saveHistory();
        this.broadcastCanvas();
      }
    } catch (e) {
      console.warn('Fabric shape error:', e);
    }
  }

  undo(): void {
    if (!this.canvas || this.historyIndex <= 0) return;
    this.historyIndex--;
    this.loadHistoryAndBroadcast(this.history[this.historyIndex]);
  }

  redo(): void {
    if (!this.canvas || this.historyIndex >= this.history.length - 1) return;
    this.historyIndex++;
    this.loadHistoryAndBroadcast(this.history[this.historyIndex]);
  }

  private loadHistoryAndBroadcast(json: string): void {
    this.isReceivingSync = true;
    this.canvas.loadFromJSON(json).then(() => {
      this.canvas.renderAll();
      this.isReceivingSync = false;
      this.broadcastCanvas();
    }).catch((err: any) => {
      console.error('Error loading history:', err);
      this.isReceivingSync = false;
    });
  }

  clearCanvas(): void {
    if (!this.canvas) return;
    this.canvas.clear();
    this.canvas.backgroundColor = '#ffffff';
    this.canvas.renderAll();
    this.strokeCount = 0;
    this.saveHistory();
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'clear' }));
    }
  }

  saveCanvas(): void {
    if (!this.canvas) return;
    const dataURL = this.canvas.toDataURL({ format: 'png', quality: 1 });
    const link = document.createElement('a');
    link.download = `whiteboard-${this.roomId}-${Date.now()}.png`;
    link.href = dataURL;
    link.click();
  }

  copyShareLink(): void {
    const url = window.location.href;
    navigator.clipboard.writeText(url).then(() => {
      alert('Share link copied to clipboard!');
    }).catch(err => {
      console.error('Could not copy text: ', err);
    });
  }

  joinRoom(): void {
    const code = this.joinCode.trim();
    if (code) {
      this.router.navigate(['/whiteboard', code]).catch(err => {
        console.error('Navigation error:', err);
      });
      this.joinCode = '';
    }
  }

  generateNewRoom(): void {
    const randomCode = Math.random().toString(36).substring(2, 8);
    this.router.navigate(['/whiteboard', randomCode]).catch(err => {
      console.error('Navigation error:', err);
    });
  }

  private saveHistory(): void {
    if (!this.canvas) return;
    const json = JSON.stringify(this.canvas.toJSON());
    this.history = this.history.slice(0, this.historyIndex + 1);
    this.history.push(json);
    this.historyIndex = this.history.length - 1;
  }

  private loadHistory(json: string): void {
    this.canvas.loadFromJSON(json, () => this.canvas.renderAll());
  }

  ngOnDestroy(): void {
    if (this.ws) {
      this.ws.close();
    }
    if (this.canvas) {
      this.canvas.dispose();
    }
  }

  // FormsModule needed for ngModel in toolbar
  [key: string]: any;
}
