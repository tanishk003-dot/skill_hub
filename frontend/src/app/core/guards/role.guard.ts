import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { UserRole } from '../models/user.model';

export const roleGuard = (allowedRoles: UserRole[]): CanActivateFn => {
  return () => {
    const authService = inject(AuthService);
    const router = inject(Router);

    const userRole = authService.userRole();
    if (userRole && allowedRoles.includes(userRole)) {
      return true;
    }

    // Redirect to user's appropriate home if logged in with wrong role
    if (userRole === 'ADMIN') {
      router.navigate(['/admin/dashboard']);
    } else if (userRole === 'MENTOR') {
      router.navigate(['/mentor/dashboard']);
    } else if (userRole === 'ASE') {
      router.navigate(['/ase/dashboard']);
    } else {
      router.navigate(['/login']);
    }
    return false;
  };
};
