import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  TrainingItem, TrainingCreatePayload, TrainingAssignPayload,
  TrainingAssignmentItem, SuggestedAseItem
} from '../models/training.model';

@Injectable({
  providedIn: 'root'
})
export class TrainingService {
  private readonly apiUrl = 'http://localhost:8001/api/v1/trainings';

  constructor(private http: HttpClient) {}

  listTrainings(): Observable<TrainingItem[]> {
    return this.http.get<TrainingItem[]>(this.apiUrl);
  }

  createTraining(payload: TrainingCreatePayload): Observable<TrainingItem> {
    return this.http.post<TrainingItem>(this.apiUrl, payload);
  }

  getTraining(id: number): Observable<TrainingItem> {
    return this.http.get<TrainingItem>(`${this.apiUrl}/${id}`);
  }

  deleteTraining(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }

  assignTraining(id: number, payload: TrainingAssignPayload): Observable<any> {
    return this.http.post(`${this.apiUrl}/${id}/assign`, payload);
  }

  suggestASEs(skillCategory: string): Observable<SuggestedAseItem[]> {
    return this.http.get<SuggestedAseItem[]>(`${this.apiUrl}/suggest-ases/${encodeURIComponent(skillCategory)}`);
  }

  getMyLearning(): Observable<TrainingAssignmentItem[]> {
    return this.http.get<TrainingAssignmentItem[]>(`${this.apiUrl}/my-learning`);
  }

  updateProgress(assignmentId: number, progressPercent: number, status?: string): Observable<any> {
    return this.http.put(`${this.apiUrl}/assignments/${assignmentId}/progress`, {
      progress_percent: progressPercent,
      status: status
    });
  }

  uploadResource(file: File): Observable<{ name: string; file_path: string; url: string; type: string }> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<{ name: string; file_path: string; url: string; type: string }>(`${this.apiUrl}/upload-resource`, formData);
  }
}
