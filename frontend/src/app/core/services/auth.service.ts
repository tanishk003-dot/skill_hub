import { Injectable, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';
import { LoginResponse, User, UserRole } from '../models/user.model';
import { NotificationService } from './notification.service';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly apiUrl = 'http://localhost:8001/api/v1';
  private readonly TOKEN_KEY = 'skillhub_jwt_token';
  private readonly USER_KEY = 'skillhub_user';

  // Signals for reactive state
  private currentUserSignal = signal<LoginResponse | null>(this.getStoredUser());

  readonly currentUser = computed(() => this.currentUserSignal());
  readonly isAuthenticated = computed(() => !!this.currentUserSignal() && !!this.getToken());
  readonly userRole = computed(() => this.currentUserSignal()?.role ?? null);

  constructor(
    private http: HttpClient,
    private router: Router,
    private notifService: NotificationService
  ) {}

  login(credentials: { email: string; password: string }): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${this.apiUrl}/auth/login`, credentials).pipe(
      tap((response) => {
        localStorage.setItem(this.TOKEN_KEY, response.access_token);
        localStorage.setItem(this.USER_KEY, JSON.stringify(response));
        this.currentUserSignal.set(response);
        this.notifService.startPolling();
      })
    );
  }

  logout(): void {
    // 1. Call backend logout if one exists (safe non-blocking call)
    try {
      this.http.post(`${this.apiUrl}/auth/logout`, {}).subscribe({
        next: () => {},
        error: () => {}
      });
    } catch {
      // safe fallback
    }

    // 2. Stop notification polling and clear state
    try {
      this.notifService.stopPolling();
    } catch {
      // safe fallback
    }

    // 3. Clear all tokens and session state
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    sessionStorage.clear();

    // 4. Reset cached user signal
    this.currentUserSignal.set(null);

    // 5. Navigate to login with replaceUrl: true so browser Back button cannot restore protected view
    this.router.navigate(['/login'], { replaceUrl: true });
  }

  getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  getMe(): Observable<User> {
    return this.http.get<User>(`${this.apiUrl}/auth/me`);
  }

  hasRole(expectedRole: UserRole): boolean {
    return this.userRole() === expectedRole;
  }

  getSsoConfig(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/auth/sso/config`);
  }

  initiateSso(redirectUri: string): Observable<{ authorization_url: string; state: string }> {
    return this.http.post<{ authorization_url: string; state: string }>(`${this.apiUrl}/auth/sso/authorize`, {
      redirect_uri: redirectUri
    });
  }

  handleSsoCallback(code: string, state: string, redirectUri: string): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${this.apiUrl}/auth/sso/callback`, {
      code,
      state,
      redirect_uri: redirectUri
    }).pipe(
      tap((response) => {
        localStorage.setItem(this.TOKEN_KEY, response.access_token);
        localStorage.setItem(this.USER_KEY, JSON.stringify(response));
        this.currentUserSignal.set(response);
      })
    );
  }

  changePassword(passwords: { current_password: string; new_password: string; confirm_password: string }): Observable<{ message: string; must_change_password: boolean }> {
    return this.http.post<{ message: string; must_change_password: boolean }>(`${this.apiUrl}/auth/change-password`, passwords);
  }

  updateCurrentUser(updates: Partial<LoginResponse>): void {
    const current = this.currentUserSignal();
    if (current) {
      const updated = { ...current, ...updates };
      localStorage.setItem(this.USER_KEY, JSON.stringify(updated));
      this.currentUserSignal.set(updated);
    }
  }

  private getStoredUser(): LoginResponse | null {
    const raw = localStorage.getItem(this.USER_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as LoginResponse;
    } catch {
      return null;
    }
  }
}
