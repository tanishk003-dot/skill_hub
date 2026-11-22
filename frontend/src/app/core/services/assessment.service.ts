import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  AssessmentItem,
  AssessmentCreatePayload,
  AssessmentAssignmentItem,
  AssessmentType
} from '../models/assessment.model';

@Injectable({
  providedIn: 'root'
})
export class AssessmentService {
  private readonly apiUrl = 'http://localhost:8001/api/v1/assessments';
  private readonly assignApiUrl = 'http://localhost:8001/api/v1/assessment-assignments';

  constructor(private http: HttpClient) {}

  getAssessments(type?: AssessmentType): Observable<AssessmentItem[]> {
    let params = new HttpParams();
    if (type) params = params.set('type', type);
    return this.http.get<AssessmentItem[]>(this.apiUrl, { params });
  }

  getAssessmentById(id: number): Observable<AssessmentItem> {
    return this.http.get<AssessmentItem>(`${this.apiUrl}/${id}`);
  }

  createAssessment(payload: AssessmentCreatePayload): Observable<AssessmentItem> {
    return this.http.post<AssessmentItem>(this.apiUrl, payload);
  }

  deleteAssessment(id: number): Observable<{ message: string; id: number }> {
    return this.http.delete<{ message: string; id: number }>(`${this.apiUrl}/${id}`);
  }

  assignAssessment(payload: {
    assessment_id: number;
    target: 'ALL' | 'SELECTED' | 'COHORT';
    ase_ids?: number[];
    cohort_id?: number;
    start_date: string;
    end_date: string;
  }): Observable<AssessmentAssignmentItem[]> {
    return this.http.post<AssessmentAssignmentItem[]>(this.assignApiUrl, payload);
  }

  getMyAssessments(): Observable<AssessmentAssignmentItem[]> {
    return this.http.get<AssessmentAssignmentItem[]>(`${this.assignApiUrl}/my`);
  }

  getAseAssessments(aseId: number): Observable<AssessmentAssignmentItem[]> {
    return this.http.get<AssessmentAssignmentItem[]>(`${this.assignApiUrl}/ase/${aseId}`);
  }

  getAllAssignments(): Observable<AssessmentAssignmentItem[]> {
    return this.http.get<AssessmentAssignmentItem[]>(`${this.assignApiUrl}/all`);
  }
}
