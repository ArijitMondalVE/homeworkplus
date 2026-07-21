import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule, DecimalPipe } from '@angular/common';
import { AuthService } from '../../services/auth.service';
import { AiService } from '../../services/ai.service';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, DecimalPipe],
  templateUrl: './profile.component.html',
  styleUrls: ['./profile.component.css']
})
export class ProfileComponent implements OnInit {
  auth = inject(AuthService);
  private aiService = inject(AiService);

  badges = [
    { name: 'First Steps', icon: '🎯', xp: 50, earned: true, rare: false },
    { name: 'Quick Learner', icon: '⚡', xp: 100, earned: true, rare: false },
    { name: 'Problem Solver', icon: '🧮', xp: 200, earned: false, rare: false },
    { name: 'Math Wizard', icon: '🔮', xp: 250, earned: false, rare: true },
    { name: 'On Fire', icon: '🔥', xp: 150, earned: false, rare: false },
    { name: 'Scholar', icon: '📚', xp: 200, earned: false, rare: false },
    { name: 'Voice Champ', icon: '🎙️', xp: 100, earned: false, rare: false },
    { name: 'Centurion', icon: '💯', xp: 500, earned: false, rare: true },
  ];

  activityDays = this.generateActivityDays();

  ngOnInit(): void {
    // Update badges based on actual user stats
    const user = this.auth.currentUser();
    if (user) {
      if (user.total_questions_solved >= 1) this.badges[0].earned = true;
      if (user.total_questions_solved >= 10) this.badges[1].earned = true;
      if (user.total_questions_solved >= 50) this.badges[2].earned = true;
      if (user.streak_days >= 7) this.badges[4].earned = true;
    }
  }

  nextLevelXp(): number {
    const level = this.auth.currentUser()?.level ?? 1;
    return level * level * 100;
  }

  xpProgressPct(): number {
    const user = this.auth.currentUser();
    if (!user) return 0;
    const currentLevelXp = ((user.level - 1) ** 2) * 100;
    const nextLevelXp = (user.level ** 2) * 100;
    const range = nextLevelXp - currentLevelXp;
    const progress = user.xp_points - currentLevelXp;
    return Math.min(100, Math.round((progress / range) * 100));
  }

  getBarColor(count: number): string {
    if (count === 0) return 'rgba(255,255,255,0.06)';
    if (count < 3) return 'rgba(59, 130, 246, 0.5)';
    if (count < 6) return 'rgba(124, 58, 237, 0.6)';
    return 'rgba(124, 58, 237, 0.9)';
  }

  private generateActivityDays(): Array<{ label: string; count: number; height: number }> {
    const days = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];
    return days.map((label) => {
      const count = Math.floor(Math.random() * 8);
      return { label, count, height: Math.max(4, count * 12.5) };
    });
  }
}
