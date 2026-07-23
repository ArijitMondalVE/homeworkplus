import { Component, OnInit, OnDestroy, ElementRef, ViewChild, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { AiService, PhotoAnswerResponse } from '../../services/ai.service';
import { WhiteboardSyncService } from './services/whiteboard-sync.service';
import { WhiteboardCanvasService } from './services/whiteboard-canvas.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-whiteboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './whiteboard.component.html',
  styleUrls: ['./whiteboard.component.css']
})
export class WhiteboardComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('whiteboardCanvas') canvasRef!: ElementRef<HTMLCanvasElement>;

  userName = 'Anonymous';
  roomId = 'main';
  
  isSidebarOpen = false;
  activeMenuId: string | null = null;
  joinCode = '';
  
  isSolving = false;
  aiResponse: PhotoAnswerResponse | null = null;
  aiError: string | null = null;

  colors = ['#1e293b', '#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6', '#ec4899', '#06b6d4', '#ffffff'];

  // Template getters/setters mapped to services
  get isAdmin(): boolean { return this.sync.isAdmin; }
  get isDrawer(): boolean { return this.sync.isDrawer; }
  get connectedUsers() { return this.sync.connectedUsers; }
  get remoteCursors() { return this.sync.getRemoteCursors(); }
  get userCount() { return this.sync.userCount; }
  get userId() { return this.sync.currentUserId; }
  get ws() { return this.sync.ws; }
  get adminId() { return this.sync.adminId; }
  get allowedDrawers() { return this.sync.allowedDrawers; }
  
  get activeTool() { return this.canvasService.activeTool; }
  set activeTool(val: string) { this.canvasService.setTool(val); }
  
  get activeColor() { return this.canvasService.activeColor; }
  set activeColor(val: string) { this.canvasService.activeColor = val; this.canvasService.applyColor(); }
  
  get strokeWidth() { return this.canvasService.strokeWidth; }
  set strokeWidth(val: number) { this.canvasService.strokeWidth = val; this.canvasService.applyStrokeWidth(); }
  
  get strokeCount() { return this.canvasService.strokeCount; }

  private sub: Subscription | null = null;

  constructor(
    private auth: AuthService,
    private route: ActivatedRoute,
    private router: Router,
    private aiService: AiService,
    public sync: WhiteboardSyncService,
    public canvasService: WhiteboardCanvasService
  ) {}

  ngOnInit(): void {
    const user = this.auth.currentUser();
    this.userName = user?.full_name || 'Anonymous';

    this.route.paramMap.subscribe(params => {
      this.roomId = params.get('roomId') || 'main';
      if (this.canvasService.canvas) {
        this.canvasService.clearCanvas();
      }
      this.sync.connect(this.roomId, this.userName);
    });

    // Listen for room disbanding or kicks
    this.sub = this.sync.messages$.subscribe(msg => {
      if (msg.type === 'room_disbanded') {
        alert("The room admin has disbanded this room.");
        this.closeAndLeave();
      } else if (msg.type === 'kicked' && msg.target_id === this.userId) {
        alert("You have been kicked from the room by the Admin.");
        this.closeAndLeave();
      }
    });
  }

  ngAfterViewInit(): void {
    setTimeout(() => {
      this.canvasService.initCanvas(this.canvasRef.nativeElement);
    }, 0);
  }

  setTool(tool: string): void {
    this.canvasService.setTool(tool);
    this.canvasService.applyPermissions();
  }

  applyColor(): void {
    this.canvasService.applyColor();
  }

  applyStrokeWidth(): void {
    this.canvasService.applyStrokeWidth();
  }

  addShape(shape: string): void {
    this.canvasService.addShape(shape);
  }

  undo(): void {
    this.canvasService.undo();
  }

  redo(): void {
    this.canvasService.redo();
  }

  clearCanvas(): void {
    this.canvasService.clearCanvas();
  }

  saveCanvas(): void {
    this.canvasService.saveCanvas(this.roomId);
  }

  async shareRoom(): Promise<void> {
    const url = window.location.href;
    const title = 'Join my Whiteboard on HomeworkPlus';
    const text = `Join my collaborative whiteboard session! Room ID: ${this.roomId}`;

    if (navigator.share) {
      try {
        await navigator.share({ title, text, url });
      } catch (err) {
        console.error('Error sharing:', err);
      }
    } else {
      navigator.clipboard.writeText(url).then(() => {
        alert('Share link copied to clipboard!');
      }).catch(err => console.error('Could not copy text: ', err));
    }
  }

  joinRoom(): void {
    const code = this.joinCode.trim();
    if (code) {
      this.router.navigate(['/whiteboard', code]);
      this.joinCode = '';
    }
  }

  generateNewRoom(): void {
    const randomCode = Math.random().toString(36).substring(2, 8);
    this.router.navigate(['/whiteboard', randomCode]);
  }

  leaveRoom(): void {
    if (this.sync.isAdmin && this.sync.connectedUsers.length > 1) {
      if (confirm('You are the Admin. Do you want to DISBAND the room (kick everyone)? \n\nClick OK to Disband, or Cancel to automatically pass Admin to someone else and leave.')) {
        this.sync.sendMessage({ type: 'disband_room' });
        this.closeAndLeave();
        return;
      } else {
        const nextUser = this.sync.connectedUsers.find(u => u.id !== this.userId);
        if (nextUser) {
           this.promoteAdmin(nextUser.id);
        }
      }
    }
    this.closeAndLeave();
  }

  private closeAndLeave(): void {
    this.sync.disconnect();
    this.router.navigate(['/dashboard']);
  }

  handleAvatarClick(targetUserId: string): void {
    if (!this.sync.isAdmin || targetUserId === this.sync.currentUserId) return;
    
    if (confirm(`Do you want to make this user the Admin?\n\nClick OK to promote them to Admin. Click Cancel to toggle their Drawing permissions instead.`)) {
      this.promoteAdmin(targetUserId);
    } else {
      this.toggleAccess(targetUserId);
    }
  }

  toggleAccess(targetUserId: string): void {
    if (!this.sync.isAdmin) return;
    this.sync.sendMessage({ type: 'toggle_access', target_id: targetUserId });
  }

  promoteAdmin(targetUserId: string): void {
    if (!this.sync.isAdmin) return;
    this.sync.sendMessage({ type: 'promote_admin', target_id: targetUserId });
  }

  kickUser(targetUserId: string): void {
    if (!this.sync.isAdmin) return;
    this.sync.sendMessage({ type: 'kick_user', target_id: targetUserId });
  }

  toggleMenu(userId: string): void {
    this.activeMenuId = this.activeMenuId === userId ? null : userId;
  }

  toggleSidebar(): void {
    this.isSidebarOpen = !this.isSidebarOpen;
  }

  async solveWithAI(): Promise<void> {
    if (!this.canvasService.canvas) return;
    this.isSolving = true;
    this.aiResponse = null;
    this.aiError = null;

    try {
      const dataURL = this.canvasService.canvas.toDataURL({ format: 'png', quality: 1 });
      const res = await fetch(dataURL);
      const blob = await res.blob();
      const file = new File([blob], `whiteboard-${this.roomId}-${Date.now()}.png`, { type: 'image/png' });

      this.aiService.uploadImage(file).subscribe({
        next: (uploadRes) => {
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

  ngOnDestroy(): void {
    if (this.sub) this.sub.unsubscribe();
    this.sync.disconnect();
  }

}
