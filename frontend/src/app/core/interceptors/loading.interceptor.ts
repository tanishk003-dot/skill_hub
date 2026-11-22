import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { finalize } from 'rxjs';
import { LoadingService } from '../services/loading.service';

export const loadingInterceptor: HttpInterceptorFn = (req, next) => {
  const loadingService = inject(LoadingService);

  // Exclude silent background polling, debounce heartbeats, or autosaves from triggering full-screen bar
  const isSilent = req.headers.has('X-Silent') || req.url.includes('/exam/autosave') || req.url.includes('/notifications/unread-count');
  
  if (!isSilent) {
    loadingService.show();
  }

  return next(req).pipe(
    finalize(() => {
      if (!isSilent) {
        loadingService.hide();
      }
    })
  );
};
