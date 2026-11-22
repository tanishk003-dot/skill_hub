import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  LiveClassItem, LiveClassCreatePayload, AttendeeItem, AttendanceBatchPayload
} from '../models/live-class.model';

@Injectable({
  providedIn: 'root'
})
export class LiveClassService {
  private readonly apiUrl = 'http://localhost:8001/api/v1/classes';

  constructor(private http: HttpClient) {}

  listLiveClasses(cohortId?: number): Observable<LiveClassItem[]> {
    const url = cohortId ? `${this.apiUrl}?cohort_id=${cohortId}` : this.apiUrl;
    return this.http.get<LiveClassItem[]>(url);
  }

  scheduleClass(payload: LiveClassCreatePayload): Observable<LiveClassItem> {
    return this.http.post<LiveClassItem>(this.apiUrl, payload);
  }

  getClass(id: number): Observable<LiveClassItem> {
    return this.http.get<LiveClassItem>(`${this.apiUrl}/${id}`);
  }

  deleteClass(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }

  getClassAttendance(classId: number): Observable<AttendeeItem[]> {
    return this.http.get<AttendeeItem[]>(`${this.apiUrl}/${classId}/attendance`);
  }

  markAttendance(classId: number, payload: AttendanceBatchPayload): Observable<any> {
    return this.http.put(`${this.apiUrl}/${classId}/attendance`, payload);
  }

  previewTeamsAttendance(classId: number): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/${classId}/attendance/import-preview`);
  }

  confirmTeamsAttendance(classId: number, payload: { import_id: number; mappings: { ase_id: number; status: string }[] }): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/${classId}/attendance/import-confirm`, payload);
  }
}
