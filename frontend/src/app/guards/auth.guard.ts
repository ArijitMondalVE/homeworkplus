import { type CanActivateFn } from '@angular/router';

// Authentication temporarily disabled — allow direct access to all routes
export const authGuard: CanActivateFn = (_route, _state) => {
  return true;
};
