import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { tap, catchError } from 'rxjs/operators';
import { Observable, throwError } from 'rxjs';
import { environment } from '../../environments/environment';

export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string;
  avatar_url?: string;
  grade_level?: string;
  preferred_language: string;
  xp_points: number;
  level: number;
  streak_days: number;
  total_questions_solved: number;
  total_study_minutes: number;
  is_active: boolean;
  is_premium: boolean;
  role: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly API = `${environment.apiUrl}/auth`;

  // Reactive state using Angular signals
  currentUser = signal<User | null>(this.loadUserFromStorage());
  isLoading = signal(false);

  constructor(private http: HttpClient, private router: Router) {}

  register(payload: {
    email: string;
    username: string;
    full_name: string;
    password: string;
    grade_level?: string;
  }): Observable<TokenResponse> {
    this.isLoading.set(true);
    return this.http.post<TokenResponse>(`${this.API}/register`, payload).pipe(
      tap((res) => this.storeTokens(res)),
      catchError((err) => {
        this.isLoading.set(false);
        return throwError(() => err);
      })
    );
  }

  login(username: string, password: string): Observable<TokenResponse> {
    this.isLoading.set(true);
    return this.http.post<TokenResponse>(`${this.API}/login`, { username, password }).pipe(
      tap((res) => this.storeTokens(res)),
      catchError((err) => {
        this.isLoading.set(false);
        return throwError(() => err);
      })
    );
  }

  logout(): void {
    this.http.post(`${this.API}/logout`, {}).subscribe({ error: () => {} });
    this.clearTokens();
    this.router.navigate(['/auth']);
  }

  refreshToken(): Observable<TokenResponse> {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) return throwError(() => new Error('No refresh token'));

    return this.http
      .post<TokenResponse>(`${this.API}/refresh`, { refresh_token: refreshToken })
      .pipe(tap((res) => this.storeTokens(res)));
  }

  getMe(): Observable<User> {
    return this.http.get<User>(`${this.API}/me`).pipe(
      tap((user) => {
        this.currentUser.set(user);
        localStorage.setItem('user', JSON.stringify(user));
      })
    );
  }

  isAuthenticated(): boolean {
    const token = this.getAccessToken();
    if (!token) return false;

    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.exp * 1000 > Date.now();
    } catch {
      return false;
    }
  }

  getAccessToken(): string | null {
    return localStorage.getItem('access_token');
  }

  private storeTokens(res: TokenResponse): void {
    localStorage.setItem('access_token', res.access_token);
    localStorage.setItem('refresh_token', res.refresh_token);
    localStorage.setItem('user', JSON.stringify(res.user));
    this.currentUser.set(res.user);
    this.isLoading.set(false);
  }

  private clearTokens(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    this.currentUser.set(null);
  }

  private loadUserFromStorage(): User | null {
    try {
      const raw = localStorage.getItem('user');
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }
}
