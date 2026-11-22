import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject, timer, switchMap, catchError, of, Subscription } from 'rxjs';
import { NotificationListResponse, NotificationItem } from '../models/notification.model';

@Injectable({
  providedIn: 'root'
})
export class NotificationService {
  private readonly apiUrl = 'http://localhost:8001/api/v1/notifications';

  private notificationsSubject = new BehaviorSubject<NotificationListResponse>({ unread_count: 0, items: [] });
  public notifications$ = this.notificationsSubject.asObservable();
  private pollingSub?: Subscription;

  constructor(private http: HttpClient) {
    this.startPolling();
  }

  public startPolling(): void {
    this.stopPolling();
    // Poll every 45 seconds (within 30-60s requirement)
    this.pollingSub = timer(0, 45000).pipe(
      switchMap(() => {
        const token = localStorage.getItem('skillhub_jwt_token') || localStorage.getItem('token');
        if (!token) return of({ unread_count: 0, items: [] });
        return this.getNotifications().pipe(
          catchError(() => of({ unread_count: 0, items: [] }))
        );
      })
    ).subscribe({
      next: (res) => this.notificationsSubject.next(res),
      error: (err) => console.error('Notification polling error (silenced)', err)
    });
  }

  public stopPolling(): void {
    if (this.pollingSub) {
      this.pollingSub.unsubscribe();
      this.pollingSub = undefined;
    }
    this.notificationsSubject.next({ unread_count: 0, items: [] });
  }

  public clearState(): void {
    this.stopPolling();
  }

  getNotifications(): Observable<NotificationListResponse> {
    return this.http.get<NotificationListResponse>(this.apiUrl);
  }

  markAsRead(notificationId: number): Observable<NotificationItem> {
    return this.http.put<NotificationItem>(`${this.apiUrl}/${notificationId}/read`, {});
  }

  markAllAsRead(): Observable<any> {
    return this.http.put(`${this.apiUrl}/read-all`, {});
  }

  refresh(): void {
    this.getNotifications().subscribe({
      next: (res) => this.notificationsSubject.next(res),
      error: (err) => console.error('Failed to refresh notifications', err)
    });
  }

  getPreferences(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/preferences`);
  }

  updatePreferences(payload: any): Observable<any> {
    return this.http.put<any>(`${this.apiUrl}/preferences`, payload);
  }
}
