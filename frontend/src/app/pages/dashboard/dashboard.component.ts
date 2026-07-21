import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule, DecimalPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { AiService, DashboardStats } from '../../services/ai.service';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink, DecimalPipe],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent implements OnInit {
  auth = inject(AuthService);
  private aiService = inject(AiService);

  stats = signal<DashboardStats | null>(null);
  leaderboard = signal<any[]>([]);
  isLoading = signal(true);

  ngOnInit(): void {
    this.loadDashboard();
  }

  loadDashboard(): void {
    this.aiService.getDashboardStats().subscribe({
      next: (data) => {
        this.stats.set(data);
        this.isLoading.set(false);
      },
      error: () => this.isLoading.set(false),
    });

    this.aiService.getLeaderboard('weekly', 5).subscribe({
      next: (data) => this.leaderboard.set(data.entries ?? []),
      error: () => {},
    });
  }

  timeOfDay(): string {
    const h = new Date().getHours();
    if (h < 12) return 'morning';
    if (h < 17) return 'afternoon';
    return 'evening';
  }

  firstName(): string {
    const name = this.auth.currentUser()?.full_name ?? '';
    return name.split(' ')[0] ?? name;
  }

  xpProgressPct(): number {
    const user = this.stats()?.user;
    if (!user) return 0;
    const currentLevelXp = ((user.level - 1) ** 2) * 100;
    const nextLevelXp = (user.level ** 2) * 100;
    const range = nextLevelXp - currentLevelXp;
    const progress = user.xp_points - currentLevelXp;
    return Math.min(100, Math.round((progress / range) * 100));
  }

  getTypeColor(type: string): string {
    const map: Record<string, string> = {
      math: 'purple', physics: 'blue', chemistry: 'emerald',
      calculus: 'purple', biology: 'emerald', general: 'amber',
    };
    return map[type] ?? 'amber';
  }

  getTypeIcon(type: string): string {
    const map: Record<string, string> = {
      math: 'calculate', physics: 'bolt', chemistry: 'science',
      calculus: 'functions', biology: 'biotech', general: 'menu_book',
    };
    return map[type] ?? 'menu_book';
  }

  getRankIcon(rank: number): string {
    if (rank === 1) return 'looks_one';
    if (rank === 2) return 'looks_two';
    if (rank === 3) return 'looks_3';
    return '';
  }

  showConfirmModal = signal(false);

  confirmClear(): void {
    this.showConfirmModal.set(true);
  }

  cancelClear(): void {
    this.showConfirmModal.set(false);
  }

  clearRecentActivity(): void {
    this.showConfirmModal.set(false);
    this.isLoading.set(true);
    this.aiService.clearRecentQuestions().subscribe({
      next: () => {
        this.loadDashboard();
      },
      error: (err) => {
        console.error('Failed to clear recent activity', err);
        this.isLoading.set(false);
      },
    });
  }
}
