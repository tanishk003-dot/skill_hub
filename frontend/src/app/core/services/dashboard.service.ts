import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AdminDashboardData, MentorDashboardData, AseDashboardData } from '../models/user.model';

@Injectable({
  providedIn: 'root'
})
export class DashboardService {
  private readonly apiUrl = 'http://localhost:8001/api/v1/dashboard';

  constructor(private http: HttpClient) {}

  getAdminStats(): Observable<AdminDashboardData> {
    return this.http.get<AdminDashboardData>(`${this.apiUrl}/admin`);
  }

  getMentorStats(): Observable<MentorDashboardData> {
    return this.http.get<MentorDashboardData>(`${this.apiUrl}/mentor`);
  }

  getAseStats(): Observable<AseDashboardData> {
    return this.http.get<AseDashboardData>(`${this.apiUrl}/ase`);
  }
}
