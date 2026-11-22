import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class LoadingService {
  private activeRequestCount = 0;
  private debounceTimer: any = null;
  private readonly DEBOUNCE_MS = 150;

  private loadingSubject = new BehaviorSubject<boolean>(false);
  public isLoading$ = this.loadingSubject.asObservable();

  show(): void {
    this.activeRequestCount++;
    if (this.activeRequestCount === 1) {
      // 150ms debounce to prevent micro-flicker on quick cached or local requests
      this.debounceTimer = setTimeout(() => {
        this.loadingSubject.next(true);
      }, this.DEBOUNCE_MS);
    }
  }

  hide(): void {
    if (this.activeRequestCount > 0) {
      this.activeRequestCount--;
    }
    if (this.activeRequestCount === 0) {
      if (this.debounceTimer) {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = null;
      }
      this.loadingSubject.next(false);
    }
  }
}
