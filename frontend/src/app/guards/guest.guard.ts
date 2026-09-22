import { type CanActivateFn } from '@angular/router';

// Authentication temporarily disabled — allow visiting guest routes freely
export const guestGuard: CanActivateFn = (_route, _state) => {
  return true;
};
