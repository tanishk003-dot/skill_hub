import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  CodingRunRequest,
  CodingRunResponse,
  CodingSubmitRequest,
  CodingSubmitResponse,
  CodingSubmissionOut,
  PlagiarismFlag,
  CodeReviewResponse,
  OnboardingProgress
} from '../models/coding.model';

@Injectable({
  providedIn: 'root'
})
export class CodingService {
  private readonly apiUrl = 'http://localhost:8001/api/v1';

  constructor(private http: HttpClient) {}

  runCode(payload: CodingRunRequest): Observable<CodingRunResponse> {
    return this.http.post<CodingRunResponse>(`${this.apiUrl}/coding/run`, payload);
  }

  submitCode(payload: CodingSubmitRequest): Observable<CodingSubmitResponse> {
    return this.http.post<CodingSubmitResponse>(`${this.apiUrl}/coding/submit`, payload);
  }

  getSubmissionReview(submissionId: number): Observable<CodeReviewResponse> {
    return this.http.post<CodeReviewResponse>(`${this.apiUrl}/coding/review/${submissionId}`, {});
  }

  getAttemptSubmissions(attemptId: number): Observable<CodingSubmissionOut[]> {
    return this.http.get<CodingSubmissionOut[]>(`${this.apiUrl}/coding/attempt/${attemptId}/submissions`);
  }

  getSubmission(submissionId: number): Observable<CodingSubmissionOut> {
    return this.http.get<CodingSubmissionOut>(`${this.apiUrl}/coding/submission/${submissionId}`);
  }

  getPlagiarismFlags(): Observable<PlagiarismFlag[]> {
    return this.http.get<PlagiarismFlag[]>(`${this.apiUrl}/coding/plagiarism`);
  }

  getOnboardingProgress(aseId: number): Observable<OnboardingProgress> {
    return this.http.get<OnboardingProgress>(`${this.apiUrl}/analytics/ase/${aseId}/onboarding-progress`);
  }
}
