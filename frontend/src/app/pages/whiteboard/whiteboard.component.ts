import { Component, OnInit, OnDestroy, ElementRef, ViewChild, AfterViewInit } from '@angular/core';
import * as fabric from 'fabric';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../services/auth.service';
import { environment } from '../../../environments/environment';
import { ActivatedRoute, Router } from '@angular/router';
import { AiService, PhotoAnswerResponse } from '../../services/ai.service';

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
  userName = 'Anonymous';
  roomId = 'main';
  userId = '';
  adminId = '';
  allowedDrawers = new Set<string>();
  userCount = 1;

  get isAdmin(): boolean {
    return this.userId === this.adminId;
  }

  get isDrawer(): boolean {
    return this.isAdmin || this.allowedDrawers.has(this.userId);
  }
  
  isSidebarOpen = false;
  activeMenuId: string | null = null;
  remoteCursors: { [userId: string]: { x: number, y: number, name: string } } = {};
  
  connectedUsers: {id: string, name: string}[] = [];
  joinCode = '';
  isSolving = false;
  aiResponse: PhotoAnswerResponse | null = null;
  aiError: string | null = null;

  colors = ['#1e293b', '#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6', '#ec4899', '#06b6d4', '#ffffff'];

  private canvas: any = null;
  private history: string[] = [];
  private historyIndex = -1;
  ws: WebSocket | null = null;
  private isReceivingSync = false;

  constructor(
    private auth: AuthService,
    private route: ActivatedRoute,
    private router: Router,
    private aiService: AiService
  ) {}

  ngOnInit(): void {
    const user = this.auth.currentUser();
    if (user) {
      this.userName = user.full_name || 'Anonymous';
      this.userId = user.id || 'anonymous';
    } else {
      this.userId = 'anonymous';
    }

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
    setTimeout(() => {
      this.initCanvas();
    }, 0);
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
      
      this.canvas.on('object:added', (e: any) => {
        if (this.isReceivingSync || !e.target) return;
        if (!e.target.id) {
          e.target.id = Math.random().toString(36).substring(2, 9);
        }
        this.strokeCount++;
        this.saveHistory();
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ type: 'object_added', data: e.target.toJSON(['id']) }));
        }
      });

      this.canvas.on('object:modified', (e: any) => {
        if (this.isReceivingSync || !e.target) return;
        this.saveHistory();
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ type: 'object_modified', data: e.target.toJSON(['id']) }));
        }
      });

      let lastMoveTime = 0;
      this.canvas.on('mouse:move', (o: any) => {
        const now = Date.now();
        if (now - lastMoveTime > 30) { // Throttle to ~30 FPS max
          lastMoveTime = now;
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            const pointer = this.canvas.getScenePoint ? this.canvas.getScenePoint(o.e) : (o.scenePoint || { x: o.e.clientX, y: o.e.clientY });
            this.ws.send(JSON.stringify({ type: 'cursor_move', data: { x: pointer.x, y: pointer.y } }));
          }
        }
      });

      this.connectWebSocket();
    } catch (e) {
      console.warn('Fabric.js not loaded:', e);
    }
  }

  private connectWebSocket(): void {
    const encodedName = encodeURIComponent(this.userName);

    this.ws = new WebSocket(`${environment.wsUrl}/ws/whiteboard/${this.roomId}?user_id=${this.userId}&user_name=${encodedName}`);

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
        } else if (msg.type === 'object_added') {
          this.isReceivingSync = true;
          // @ts-ignore
          fabric.util.enlivenObjects([msg.data]).then((objects: any[]) => {
            const obj = objects[0];
            const existing = this.canvas.getObjects().find((o: any) => o.id === obj.id);
            if (!existing) {
              this.canvas.add(obj);
              this.canvas.renderAll();
            }
            this.isReceivingSync = false;
          }).catch((err: any) => {
            console.error('Error enlivening object:', err);
            this.isReceivingSync = false;
          });
        } else if (msg.type === 'object_modified') {
          this.isReceivingSync = true;
          const targetObj = this.canvas.getObjects().find((o: any) => o.id === msg.data.id);
          if (targetObj) {
            targetObj.set(msg.data);
            targetObj.setCoords();
            this.canvas.renderAll();
          }
          this.isReceivingSync = false;
        } else if (msg.type === 'cursor_move') {
          if (msg.sender !== this.userId && msg.data) {
            const senderInfo = this.connectedUsers.find(u => u.id === msg.sender);
            if (senderInfo) {
              this.remoteCursors[msg.sender] = { x: msg.data.x, y: msg.data.y, name: senderInfo.name };
            }
          }
        } else if (msg.type === 'room_info' || msg.type === 'user_joined' || msg.type === 'user_left') {
          if (msg.user_count !== undefined) {
            this.userCount = msg.user_count;
          }
          if (msg.users !== undefined) {
            this.connectedUsers = msg.users;
          }
          if (msg.admin_id !== undefined) {
            this.adminId = msg.admin_id;
          }
          if (msg.allowed_drawers !== undefined) {
            this.allowedDrawers = new Set(msg.allowed_drawers);
          }
          if (msg.type === 'user_left' && msg.user_id) {
            delete this.remoteCursors[msg.user_id];
          }
          this.applyPermissions();
          // If a new user joined, broadcast our full canvas state to sync them up
          if (msg.type === 'user_joined' && this.isAdmin) {
            this.broadcastCanvas();
          }
        } else if (msg.type === 'permissions_update') {
          if (msg.allowed_drawers !== undefined) {
            this.allowedDrawers = new Set(msg.allowed_drawers);
          }
          this.applyPermissions();
        } else if (msg.type === 'admin_promoted') {
          if (msg.admin_id !== undefined) {
            this.adminId = msg.admin_id;
          }
          if (msg.allowed_drawers !== undefined) {
            this.allowedDrawers = new Set(msg.allowed_drawers);
          }
          this.applyPermissions();
        } else if (msg.type === 'room_disbanded') {
          alert("The room admin has disbanded this room.");
          this.closeAndLeave();
        } else if (msg.type === 'kicked') {
          if (msg.target_id === this.userId) {
            alert("You have been kicked from the room by the Admin.");
            this.closeAndLeave();
          }
        }
      } catch (e) {
        console.error('WS message error:', e);
        this.isReceivingSync = false;
      }
    };
  }

  private applyPermissions(): void {
    if (!this.canvas) return;
    if (this.isDrawer) {
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
        obj.id = Math.random().toString(36).substring(2, 9);
        this.canvas.add(obj);
        this.canvas.setActiveObject(obj);
        this.canvas.renderAll();
        // Object added will be fired automatically, which handles saveHistory and ws send
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

  async shareRoom(): Promise<void> {
    const url = window.location.href;
    const title = 'Join my Whiteboard on HomeworkPlus';
    const text = `Join my collaborative whiteboard session! Room ID: ${this.roomId}`;

    if (navigator.share) {
      try {
        await navigator.share({
          title,
          text,
          url
        });
      } catch (err) {
        console.error('Error sharing:', err);
      }
    } else {
      navigator.clipboard.writeText(url).then(() => {
        alert('Share link copied to clipboard!');
      }).catch(err => {
        console.error('Could not copy text: ', err);
      });
    }
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

  leaveRoom(): void {
    if (this.isAdmin && this.connectedUsers.length > 1) {
      if (confirm('You are the Admin. Do you want to DISBAND the room (kick everyone)? \n\nClick OK to Disband, or Cancel to automatically pass Admin to someone else and leave.')) {
        this.ws?.send(JSON.stringify({ type: 'disband_room' }));
        this.closeAndLeave();
        return;
      } else {
        const nextUser = this.connectedUsers.find(u => u.id !== this.userId);
        if (nextUser) {
           this.promoteAdmin(nextUser.id);
        }
      }
    }
    this.closeAndLeave();
  }

  private closeAndLeave(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.router.navigate(['/dashboard']).catch(err => {
      console.error('Navigation error:', err);
    });
  }

  handleAvatarClick(targetUserId: string): void {
    if (!this.isAdmin || targetUserId === this.userId) return;
    
    if (confirm(`Do you want to make this user the Admin?\n\nClick OK to promote them to Admin. Click Cancel to toggle their Drawing permissions instead.`)) {
      this.promoteAdmin(targetUserId);
    } else {
      this.toggleAccess(targetUserId);
    }
  }

  toggleAccess(targetUserId: string): void {
    if (!this.isAdmin) return;
    this.ws?.send(JSON.stringify({ type: 'toggle_access', target_id: targetUserId }));
  }

  promoteAdmin(targetUserId: string): void {
    if (!this.isAdmin) return;
    this.ws?.send(JSON.stringify({ type: 'promote_admin', target_id: targetUserId }));
  }

  kickUser(targetUserId: string): void {
    if (!this.isAdmin) return;
    this.ws?.send(JSON.stringify({ type: 'kick_user', target_id: targetUserId }));
  }

  toggleMenu(userId: string): void {
    this.activeMenuId = this.activeMenuId === userId ? null : userId;
  }

  toggleSidebar(): void {
    this.isSidebarOpen = !this.isSidebarOpen;
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

  getRemoteCursors() {
    return Object.values(this.remoteCursors);
  }

  ngOnDestroy(): void {
    if (this.ws) {
      this.ws.close();
    }
    if (this.canvas) {
      this.canvas.dispose();
    }
  }

  async solveWithAI(): Promise<void> {
    if (!this.canvas) return;
    this.isSolving = true;
    this.aiResponse = null;
    this.aiError = null;

    try {
      // Get canvas image as base64 string
      const dataURL = this.canvas.toDataURL({ format: 'png', quality: 1 });
      
      // Convert base64 to Blob, then to File
      const res = await fetch(dataURL);
      const blob = await res.blob();
      const file = new File([blob], `whiteboard-${this.roomId}-${Date.now()}.png`, { type: 'image/png' });

      // Upload image
      this.aiService.uploadImage(file).subscribe({
        next: (uploadRes) => {
          // Get answer
          this.aiService.solveFromPhoto(uploadRes.image_id, { language: 'en' }).subscribe({
            next: (answerRes) => {
              this.aiResponse = answerRes;
              this.isSolving = false;
            },
            error: (err) => {
              console.error('AI Solve Error:', err);
              this.aiError = 'Failed to get an answer from AI. Please try again.';
              this.isSolving = false;
            }
          });
        },
        error: (err) => {
          console.error('Image upload error:', err);
          this.aiError = 'Failed to upload the whiteboard image.';
          this.isSolving = false;
        }
      });
    } catch (e) {
      console.error('Solve preparation error:', e);
      this.aiError = 'An error occurred while preparing the image.';
      this.isSolving = false;
    }
  }

  closeAiModal(): void {
    this.aiResponse = null;
    this.aiError = null;
  }

  // FormsModule needed for ngModel in toolbar
  [key: string]: any;
}
