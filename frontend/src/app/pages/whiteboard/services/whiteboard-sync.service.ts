import { Injectable, OnDestroy, NgZone } from '@angular/core';
import { Subject } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { AuthService } from '../../../services/auth.service';

export interface RemoteCursor {
  x: number;
  y: number;
  name: string;
}

export interface ConnectedUser {
  id: string;
  name: string;
}

@Injectable({
  providedIn: 'root'
})
export class WhiteboardSyncService implements OnDestroy {
  ws: WebSocket | null = null;
  
  // State
  roomId = 'main';
  adminId = '';
  allowedDrawers = new Set<string>();
  userCount = 1;
  connectedUsers: ConnectedUser[] = [];
  remoteCursors: { [userId: string]: RemoteCursor } = {};
  
  // Streams for canvas to subscribe to
  public messages$ = new Subject<any>();

  constructor(private auth: AuthService, private zone: NgZone) {}

  get currentUserId(): string {
    return this.auth.currentUser()?.id || 'anonymous';
  }

  get isAdmin(): boolean {
    return this.currentUserId === this.adminId;
  }

  get isDrawer(): boolean {
    return this.isAdmin || this.allowedDrawers.has(this.currentUserId);
  }

  connect(roomId: string, userName: string): void {
    this.disconnect();
    this.roomId = roomId;
    
    const encodedName = encodeURIComponent(userName);
    const token = this.auth.getAccessToken() || '';

    this.ws = new WebSocket(`${environment.wsUrl}/ws/whiteboard/${this.roomId}?token=${token}&user_name=${encodedName}`);

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        this.zone.run(() => {
          this.handleSystemMessage(msg);
          this.messages$.next(msg);
        });
      } catch (e) {
        console.error('WS parse error:', e);
      }
    };
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.remoteCursors = {};
    this.connectedUsers = [];
    this.allowedDrawers.clear();
    this.adminId = '';
  }

  sendMessage(payload: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
    }
  }

  private handleSystemMessage(msg: any): void {
    if (msg.type === 'room_info' || msg.type === 'user_joined' || msg.type === 'user_left') {
      if (msg.user_count !== undefined) this.userCount = msg.user_count;
      if (msg.users !== undefined) this.connectedUsers = msg.users;
      if (msg.admin_id !== undefined) this.adminId = msg.admin_id;
      if (msg.allowed_drawers !== undefined) this.allowedDrawers = new Set(msg.allowed_drawers);
      if (msg.type === 'user_left' && msg.user_id) {
        delete this.remoteCursors[msg.user_id];
      }
    } else if (msg.type === 'permissions_update' || msg.type === 'admin_promoted') {
      if (msg.admin_id !== undefined) this.adminId = msg.admin_id;
      if (msg.allowed_drawers !== undefined) this.allowedDrawers = new Set(msg.allowed_drawers);
    } else if (msg.type === 'cursor_move') {
      if (msg.sender !== this.currentUserId && msg.data) {
        const senderInfo = this.connectedUsers.find(u => u.id === msg.sender);
        if (senderInfo) {
          this.remoteCursors[msg.sender] = { x: msg.data.x, y: msg.data.y, name: senderInfo.name };
        }
      }
    }
  }

  getRemoteCursors() {
    return Object.values(this.remoteCursors);
  }

  ngOnDestroy(): void {
    this.disconnect();
    this.messages$.complete();
  }
}
