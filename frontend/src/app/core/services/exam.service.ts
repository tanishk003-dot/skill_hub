import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ExamStartData, ExamResultData } from '../models/assessment.model';

@Injectable({
  providedIn: 'root'
})
export class ExamService {
  private readonly apiUrl = 'http://localhost:8001/api/v1/exam';

  constructor(private http: HttpClient) {}

  startOrResumeExam(assignmentId: number, handshakeToken?: string): Observable<ExamStartData> {
    const headers: { [key: string]: string } = {};
    if (handshakeToken) {
      headers['X-Camera-Handshake'] = handshakeToken;
    }
    return this.http.post<ExamStartData>(`${this.apiUrl}/start/${assignmentId}`, {}, { headers });
  }

  autosave(attemptId: number, questionId: number, selectedOptions: string[]): Observable<{ status: string; question_id: number }> {
    return this.http.post<{ status: string; question_id: number }>(`${this.apiUrl}/autosave`, {
      attempt_id: attemptId,
      question_id: questionId,
      selected_options: selectedOptions
    });
  }

  submitExam(attemptId: number): Observable<ExamResultData> {
    return this.http.post<ExamResultData>(`${this.apiUrl}/submit`, {
      attempt_id: attemptId
    });
  }

  getExamResult(attemptId: number): Observable<ExamResultData> {
    return this.http.get<ExamResultData>(`${this.apiUrl}/result/${attemptId}`);
  }

  recordViolation(attemptId: number, type: string, details?: any): Observable<{
    violation_count: number;
    auto_submitted: boolean;
    status: string;
    debounced: boolean;
    message?: string;
  }> {
    return this.http.post<{
      violation_count: number;
      auto_submitted: boolean;
      status: string;
      debounced: boolean;
      message?: string;
    }>(`${this.apiUrl}/violation/${attemptId}`, {
      type,
      details
    });
  }
}
