import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-nav',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, CommonModule],
  template: `
    <nav class="navbar">
      <div class="nav-container">
        <!-- Logo -->
        <a [routerLink]="auth.currentUser() ? '/dashboard' : '/'" class="nav-logo">
          <span class="logo-icon material-symbols-rounded">menu_book</span>
          <span class="logo-text">Homework<span class="logo-accent">Plus</span></span>
        </a>

        <!-- Nav Links -->
        @if (auth.currentUser()) {
          <div class="nav-links" [class.open]="mobileOpen">
            <a routerLink="/dashboard" routerLinkActive="active" class="nav-link">
              <span class="material-symbols-rounded">home</span> Dashboard
            </a>
            <a routerLink="/solve" routerLinkActive="active" class="nav-link">
              <span class="material-symbols-rounded">photo_camera</span> Solve
            </a>
            <a routerLink="/voice" routerLinkActive="active" class="nav-link">
              <span class="material-symbols-rounded">mic</span> Voice
            </a>
            <a routerLink="/whiteboard" routerLinkActive="active" class="nav-link">
              <span class="material-symbols-rounded">edit</span> Whiteboard
            </a>
            <a routerLink="/map" routerLinkActive="active" class="nav-link">
              <span class="material-symbols-rounded">explore</span> 3D Map
            </a>
            <a routerLink="/subjects" routerLinkActive="active" class="nav-link">
              <span class="material-symbols-rounded">import_contacts</span> Subjects
            </a>
          </div>
        }

        <!-- User Actions -->
        <div class="nav-actions">
          @if (auth.currentUser()) {
            <div class="user-xp">
              <span class="xp-badge"><span class="material-symbols-rounded" style="font-size: 14px">bolt</span> {{ auth.currentUser()?.xp_points | number }} XP</span>
              <span class="level-badge">Lv.{{ auth.currentUser()?.level }}</span>
            </div>
            <a routerLink="/profile" class="avatar-btn">
              @if (auth.currentUser()?.avatar_url) {
                <img [src]="auth.currentUser()?.avatar_url" alt="avatar" class="avatar-img" />
              } @else {
                <div class="avatar-placeholder">
                  {{ auth.currentUser()?.username?.[0]?.toUpperCase() }}
                </div>
              }
            </a>
            <button class="btn btn-ghost btn-sm" (click)="auth.logout()">Logout</button>
          } @else {
            <a routerLink="/auth" class="btn btn-primary btn-sm">Sign In</a>
          }

          <!-- Mobile Toggle -->
          <button class="mobile-toggle" (click)="mobileOpen = !mobileOpen">
            <span [class]="mobileOpen ? 'icon-close' : 'icon-menu'">{{ mobileOpen ? '✕' : '☰' }}</span>
          </button>
        </div>
      </div>
    </nav>
  `,
  styles: [`
    .navbar {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      z-index: 100;
      height: 70px;
      background: rgba(5, 10, 20, 0.85);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border-bottom: 1px solid rgba(148, 163, 184, 0.08);
    }

    .nav-container {
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 100%;
      max-width: 1440px;
      margin: 0 auto;
      padding: 0 1.5rem;
      gap: 1rem;
    }

    .nav-logo {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      text-decoration: none;
      font-size: 1.25rem;
      font-weight: 800;
      color: #f0f4ff;
      white-space: nowrap;
    }

    .logo-icon { font-size: 1.5rem; }
    .logo-accent { color: #a78bfa; }

    .nav-links {
      display: flex;
      align-items: center;
      gap: 0.25rem;
      flex: 1;
      justify-content: center;
    }

    .nav-link {
      display: flex;
      align-items: center;
      gap: 0.375rem;
      padding: 0.5rem 0.875rem;
      border-radius: 10px;
      font-size: 0.875rem;
      font-weight: 500;
      color: #94a3b8;
      text-decoration: none;
      transition: all 150ms ease;
      white-space: nowrap;
    }

    .nav-link:hover {
      color: #f0f4ff;
      background: rgba(255, 255, 255, 0.06);
    }

    .nav-link.active {
      color: #a78bfa;
      background: rgba(124, 58, 237, 0.15);
    }

    .nav-actions {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .user-xp {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .xp-badge {
      padding: 0.25rem 0.625rem;
      background: rgba(245, 158, 11, 0.15);
      color: #fcd34d;
      border: 1px solid rgba(245, 158, 11, 0.3);
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 700;
    }

    .level-badge {
      padding: 0.25rem 0.5rem;
      background: rgba(124, 58, 237, 0.2);
      color: #a78bfa;
      border: 1px solid rgba(124, 58, 237, 0.3);
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 700;
    }

    .avatar-btn { text-decoration: none; }

    .avatar-img {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      border: 2px solid rgba(124, 58, 237, 0.5);
      object-fit: cover;
    }

    .avatar-placeholder {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: linear-gradient(135deg, #7c3aed, #3b82f6);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.875rem;
      font-weight: 700;
      color: white;
    }

    .mobile-toggle {
      display: none;
      background: transparent;
      border: none;
      color: #94a3b8;
      font-size: 1.25rem;
      cursor: pointer;
      padding: 0.5rem;
    }

    @media (max-width: 900px) {
      .nav-links {
        position: fixed;
        top: 70px;
        left: 0;
        right: 0;
        background: rgba(5, 10, 20, 0.97);
        backdrop-filter: blur(20px);
        flex-direction: column;
        align-items: flex-start;
        padding: 1rem;
        gap: 0.25rem;
        border-bottom: 1px solid rgba(148, 163, 184, 0.1);
        transform: translateY(-110%);
        transition: transform 250ms ease;
      }
      .nav-links.open { transform: translateY(0); }
      .nav-link { width: 100%; padding: 0.75rem 1rem; }
      .mobile-toggle { display: flex; }
      .user-xp { display: none; }
    }
  `],
})
export class NavComponent {
  auth = inject(AuthService);
  mobileOpen = false;
}
