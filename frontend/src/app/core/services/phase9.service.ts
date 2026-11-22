import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  ReadinessConfig,
  ReadinessResponse,
  JourneyMapResponse,
  LeaderboardEntry,
  RoadmapPlan,
  RiskSignal,
  CEOOverview,
  CertificateItem,
  PublicVerifyResult,
  MockInterviewSession
} from '../models/phase9.model';

@Injectable({
  providedIn: 'root'
})
export class Phase9Service {
  private apiUrl = 'http://localhost:8001/api/v1';

  constructor(private http: HttpClient) {}

  // 1. Project-Readiness & Skill DNA
  getReadiness(aseId?: number): Observable<ReadinessResponse> {
    let params = new HttpParams();
    if (aseId) params = params.set('ase_id', aseId.toString());
    return this.http.get<ReadinessResponse>(`${this.apiUrl}/readiness`, { params });
  }

  getReadinessConfig(): Observable<ReadinessConfig> {
    return this.http.get<ReadinessConfig>(`${this.apiUrl}/readiness/config`);
  }

  updateReadinessConfig(config: ReadinessConfig): Observable<any> {
    return this.http.put(`${this.apiUrl}/readiness/config`, config);
  }

  // 2. Journey Map & Gamification
  getJourneyMap(aseId?: number): Observable<JourneyMapResponse> {
    let params = new HttpParams();
    if (aseId) params = params.set('ase_id', aseId.toString());
    return this.http.get<JourneyMapResponse>(`${this.apiUrl}/gamification/journey`, { params });
  }

  completeMilestone(milestoneId: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/gamification/milestone/${milestoneId}/complete`, {});
  }

  getLeaderboard(): Observable<LeaderboardEntry[]> {
    return this.http.get<LeaderboardEntry[]>(`${this.apiUrl}/gamification/leaderboard`);
  }

  toggleLeaderboardOptIn(optIn: boolean): Observable<any> {
    return this.http.post(`${this.apiUrl}/gamification/opt-in`, { opt_in: optIn });
  }

  // 3. AI Learning Roadmap
  getRoadmap(aseId?: number): Observable<RoadmapPlan> {
    let params = new HttpParams();
    if (aseId) params = params.set('ase_id', aseId.toString());
    return this.http.get<RoadmapPlan>(`${this.apiUrl}/roadmap`, { params });
  }

  generateRoadmap(aseId?: number): Observable<RoadmapPlan> {
    let params = new HttpParams();
    if (aseId) params = params.set('ase_id', aseId.toString());
    return this.http.post<RoadmapPlan>(`${this.apiUrl}/roadmap/generate`, {}, { params });
  }

  toggleRoadmapTask(taskId: string, isDone: boolean): Observable<any> {
    return this.http.post(`${this.apiUrl}/roadmap/task/${taskId}/toggle`, { is_done: isDone });
  }

  // 4. Early Warning System
  getRiskSignals(): Observable<RiskSignal[]> {
    return this.http.get<RiskSignal[]>(`${this.apiUrl}/early-warning/signals`);
  }

  sendMentorNudge(aseId: number, message?: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/early-warning/nudge`, { ase_id: aseId, message });
  }

  // 5. Re-Assessment Growth
  scheduleReassessment(data: {
    ase_id: number;
    original_assignment_id: number;
    reassessment_day: number;
    scheduled_days_from_now?: number;
  }): Observable<any> {
    return this.http.post(`${this.apiUrl}/reassessment/schedule`, data);
  }

  getReassessmentGrowth(aseId?: number, cohortId?: number): Observable<any> {
    let params = new HttpParams();
    if (aseId) params = params.set('ase_id', aseId.toString());
    if (cohortId) params = params.set('cohort_id', cohortId.toString());
    return this.http.get<any>(`${this.apiUrl}/reassessment/growth`, { params });
  }

  // 6. CEO Command Center
  getCEOOverview(): Observable<CEOOverview> {
    return this.http.get<CEOOverview>(`${this.apiUrl}/ceo-center/overview`);
  }

  downloadExecutiveReport(): Observable<Blob> {
    return this.http.get(`${this.apiUrl}/ceo-center/export-pdf`, { responseType: 'blob' });
  }

  // 7. Verified Certificates
  getCertificates(): Observable<CertificateItem[]> {
    return this.http.get<CertificateItem[]>(`${this.apiUrl}/certificates`);
  }

  verifyCertificatePublic(certUuid: string): Observable<PublicVerifyResult> {
    return this.http.get<PublicVerifyResult>(`${this.apiUrl}/certificates/verify/${certUuid}`);
  }

  downloadCertificatePdf(certUuid: string): Observable<Blob> {
    return this.http.get(`${this.apiUrl}/certificates/${certUuid}/download`, { responseType: 'blob' });
  }

  // 8. AI Mock Interviewer
  startMockInterview(data: {
    interview_type?: string;
    difficulty?: string;
    topic?: string;
  }): Observable<MockInterviewSession> {
    return this.http.post<MockInterviewSession>(`${this.apiUrl}/mock-interview/start`, data);
  }

  answerMockInterview(sessionId: string, answer: string): Observable<MockInterviewSession> {
    return this.http.post<MockInterviewSession>(`${this.apiUrl}/mock-interview/${sessionId}/answer`, { answer });
  }

  endMockInterview(sessionId: string): Observable<MockInterviewSession> {
    return this.http.post<MockInterviewSession>(`${this.apiUrl}/mock-interview/${sessionId}/end`, {});
  }
}
