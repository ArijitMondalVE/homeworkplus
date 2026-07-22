import { Routes } from '@angular/router';
import { authGuard } from './guards/auth.guard';
import { guestGuard } from './guards/guest.guard';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/landing/landing.component').then((m) => m.LandingComponent),
    canActivate: [guestGuard],
  },
  {
    path: 'auth',
    loadComponent: () =>
      import('./pages/auth/auth.component').then((m) => m.AuthComponent),
    canActivate: [guestGuard],
  },
  {
    path: 'dashboard',
    loadComponent: () =>
      import('./pages/dashboard/dashboard.component').then((m) => m.DashboardComponent),
    canActivate: [authGuard],
  },
  {
    path: 'solve',
    loadComponent: () =>
      import('./pages/solve/solve.component').then((m) => m.SolveComponent),
    canActivate: [authGuard],
  },
  {
    path: 'voice',
    loadComponent: () =>
      import('./pages/voice/voice.component').then((m) => m.VoiceComponent),
    canActivate: [authGuard],
  },
  {
    path: 'whiteboard',
    redirectTo: '/whiteboard/main',
    pathMatch: 'full',
  },
  {
    path: 'whiteboard/:roomId',
    loadComponent: () =>
      import('./pages/whiteboard/whiteboard.component').then((m) => m.WhiteboardComponent),
    canActivate: [authGuard],
  },
  {
    path: 'map',
    loadComponent: () =>
      import('./pages/learning-map/learning-map.component').then((m) => m.LearningMapComponent),
    canActivate: [authGuard],
  },
  {
    path: 'profile',
    loadComponent: () =>
      import('./pages/profile/profile.component').then((m) => m.ProfileComponent),
    canActivate: [authGuard],
  },
  {
    path: 'subjects',
    loadComponent: () =>
      import('./pages/subjects/subjects.component').then((m) => m.SubjectsComponent),
    canActivate: [authGuard],
  },
  {
    path: '**',
    redirectTo: '/dashboard',
  },
];
