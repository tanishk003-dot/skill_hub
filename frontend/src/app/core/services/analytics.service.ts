import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ASEDashboardData, MentorDashboardData, AdminDashboardData } from '../models/analytics.model';

@Injectable({
  providedIn: 'root'
})
export class AnalyticsService {
  private readonly analyticsUrl = 'http://localhost:8001/api/v1/analytics';
  private readonly reportsUrl = 'http://localhost:8001/api/v1/reports';

  constructor(private http: HttpClient) {}

  getAseDashboard(): Observable<ASEDashboardData> {
    return this.http.get<ASEDashboardData>(`${this.analyticsUrl}/ase/dashboard`);
  }

  getMentorDashboard(cohortId?: number): Observable<MentorDashboardData> {
    let params = new HttpParams();
    if (cohortId) {
      params = params.set('cohort_id', cohortId);
    }
    return this.http.get<MentorDashboardData>(`${this.analyticsUrl}/mentor/dashboard`, { params });
  }

  getAdminDashboard(): Observable<AdminDashboardData> {
    return this.http.get<AdminDashboardData>(`${this.analyticsUrl}/admin/dashboard`);
  }

  downloadAsePdf(attemptId: number): Observable<Blob> {
    return this.http.get(`${this.reportsUrl}/ase/${attemptId}/pdf`, {
      responseType: 'blob'
    });
  }

  downloadCohortCsv(cohortId: number): Observable<Blob> {
    return this.http.get(`${this.reportsUrl}/cohort/${cohortId}/csv`, {
      responseType: 'blob'
    });
  }
}
