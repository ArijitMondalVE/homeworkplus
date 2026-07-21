import { Component, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-auth',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './auth.component.html',
  styleUrls: ['./auth.component.css']
})
export class AuthComponent {
  private auth = inject(AuthService);
  private router = inject(Router);

  mode = signal<'login' | 'register'>('login');
  isLoading = signal(false);
  error = signal('');
  showPassword = signal(false);

  loginUsername = '';
  loginPassword = '';

  reg = {
    full_name: '',
    username: '',
    email: '',
    password: '',
    grade_level: '',
  };

  grades = [
    'Grade 6', 'Grade 7', 'Grade 8', 'Grade 9', 'Grade 10',
    'Grade 11', 'Grade 12', 'University Year 1', 'University Year 2',
    'University Year 3', 'University Year 4',
  ];

  onLogin(): void {
    if (!this.loginUsername || !this.loginPassword) return;
    this.isLoading.set(true);
    this.error.set('');

    this.auth.login(this.loginUsername, this.loginPassword).subscribe({
      next: () => this.router.navigate(['/dashboard']),
      error: (err) => {
        let msg = 'Login failed. Please try again.';
        if (err?.status === 0) msg = 'Could not connect to server. Is the backend running?';
        else if (err?.status === 404) msg = 'Endpoint not found (404).';
        else if (typeof err?.error?.detail === 'string') msg = err.error.detail;
        else if (Array.isArray(err?.error?.detail)) msg = err.error.detail.map((e: any) => e.msg).join(', ');
        
        this.error.set(msg);
        this.isLoading.set(false);
      },
    });
  }

  onRegister(): void {
    if (!this.reg.email || !this.reg.password || !this.reg.username) return;
    this.isLoading.set(true);
    this.error.set('');

    this.auth.register(this.reg).subscribe({
      next: () => this.router.navigate(['/dashboard']),
      error: (err) => {
        let msg = 'Registration failed. Please try again.';
        if (err?.status === 0) msg = 'Could not connect to server. Is the backend running?';
        else if (err?.status === 404) msg = 'Endpoint not found (404).';
        else if (typeof err?.error?.detail === 'string') msg = err.error.detail;
        else if (Array.isArray(err?.error?.detail)) msg = err.error.detail.map((e: any) => e.msg).join(', ');
        
        this.error.set(msg);
        this.isLoading.set(false);
      },
    });
  }
}
