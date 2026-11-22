import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  QuestionItemAnalytics,
  OneOnOneMeeting,
  OneOnOneGoal,
  OneOnOneActionItem,
  OneOnOneComment,
  ReportingApiToken,
  ReportingTokenCreatedResponse,
  StaffingProject,
  StaffingProjectMatchesResponse
} from '../models/phase11.model';

@Injectable({
  providedIn: 'root'
})
export class Phase11Service {
  private apiUrl = 'http://localhost:8001/api/v1';

  constructor(private http: HttpClient) {}

  // ================= QUESTION ITEM ANALYSIS =================
  getQuestionAnalytics(): Observable<QuestionItemAnalytics[]> {
    return this.http.get<QuestionItemAnalytics[]>(`${this.apiUrl}/analytics/questions`);
  }

  getQuestionItemAnalysis(questionId: number): Observable<QuestionItemAnalytics> {
    return this.http.get<QuestionItemAnalytics>(`${this.apiUrl}/analytics/questions/${questionId}`);
  }

  flagQuestionForReview(questionId: number, reason: string): Observable<QuestionItemAnalytics> {
    return this.http.post<QuestionItemAnalytics>(`${this.apiUrl}/analytics/questions/${questionId}/review`, { reason });
  }

  recalculateQuestionAnalytics(questionId: number): Observable<QuestionItemAnalytics> {
    return this.http.post<QuestionItemAnalytics>(`${this.apiUrl}/analytics/questions/${questionId}/recalculate`, {});
  }

  // ================= 1-ON-1 MEETINGS & GOALS =================
  getMeetings(menteeId?: number): Observable<OneOnOneMeeting[]> {
    let params = new HttpParams();
    if (menteeId) params = params.set('mentee_id', menteeId.toString());
    return this.http.get<OneOnOneMeeting[]>(`${this.apiUrl}/one-on-one/meetings`, { params });
  }

  getMeeting(meetingId: number): Observable<OneOnOneMeeting> {
    return this.http.get<OneOnOneMeeting>(`${this.apiUrl}/one-on-one/meetings/${meetingId}`);
  }

  createMeeting(payload: {
    mentee_id: number;
    title: string;
    meeting_date: string;
    shared_notes?: string;
    private_notes?: string;
  }): Observable<OneOnOneMeeting> {
    return this.http.post<OneOnOneMeeting>(`${this.apiUrl}/one-on-one/meetings`, payload);
  }

  updateMeeting(meetingId: number, payload: {
    title?: string;
    meeting_date?: string;
    status?: string;
    shared_notes?: string;
    private_notes?: string;
  }): Observable<OneOnOneMeeting> {
    return this.http.put<OneOnOneMeeting>(`${this.apiUrl}/one-on-one/meetings/${meetingId}`, payload);
  }

  summarizeMeeting(meetingId: number, target: 'shared' | 'private'): Observable<{ meeting_id: number; target: string; summary: string }> {
    return this.http.post<{ meeting_id: number; target: string; summary: string }>(
      `${this.apiUrl}/one-on-one/meetings/${meetingId}/summarize`,
      { target }
    );
  }

  getGoals(menteeId?: number): Observable<OneOnOneGoal[]> {
    let params = new HttpParams();
    if (menteeId) params = params.set('mentee_id', menteeId.toString());
    return this.http.get<OneOnOneGoal[]>(`${this.apiUrl}/one-on-one/goals`, { params });
  }

  createGoal(payload: {
    mentee_id: number;
    title: string;
    target_date: string;
    description?: string;
    meeting_id?: number;
  }): Observable<OneOnOneGoal> {
    return this.http.post<OneOnOneGoal>(`${this.apiUrl}/one-on-one/goals`, payload);
  }

  updateGoalStatus(goalId: number, status: string): Observable<OneOnOneGoal> {
    return this.http.patch<OneOnOneGoal>(`${this.apiUrl}/one-on-one/goals/${goalId}/status?status=${status}`, {});
  }

  getActionItems(menteeId?: number, meetingId?: number, goalId?: number): Observable<OneOnOneActionItem[]> {
    let params = new HttpParams();
    if (menteeId) params = params.set('mentee_id', menteeId.toString());
    if (meetingId) params = params.set('meeting_id', meetingId.toString());
    if (goalId) params = params.set('goal_id', goalId.toString());
    return this.http.get<OneOnOneActionItem[]>(`${this.apiUrl}/one-on-one/actions`, { params });
  }

  createActionItem(payload: {
    mentee_id: number;
    task: string;
    assigned_to: 'ASE' | 'MENTOR';
    meeting_id?: number;
    goal_id?: number;
  }): Observable<OneOnOneActionItem> {
    return this.http.post<OneOnOneActionItem>(`${this.apiUrl}/one-on-one/actions`, payload);
  }

  toggleActionItem(actionId: number, isCompleted: boolean): Observable<OneOnOneActionItem> {
    return this.http.patch<OneOnOneActionItem>(
      `${this.apiUrl}/one-on-one/actions/${actionId}/toggle?is_completed=${isCompleted}`,
      {}
    );
  }

  addComment(payload: {
    comment_text: string;
    meeting_id?: number;
    goal_id?: number;
    action_item_id?: number;
  }): Observable<OneOnOneComment> {
    return this.http.post<OneOnOneComment>(`${this.apiUrl}/one-on-one/comments`, payload);
  }

  // ================= EXPORTS =================
  downloadExport(entity: string, format: 'xlsx' | 'csv' = 'xlsx', includePii: boolean = false): Observable<Blob> {
    let params = new HttpParams()
      .set('format', format)
      .set('include_pii', includePii.toString());

    return this.http.get(`${this.apiUrl}/export/${entity}`, {
      params,
      responseType: 'blob'
    });
  }

  // ================= REPORTING TOKENS =================
  getReportingTokens(): Observable<ReportingApiToken[]> {
    return this.http.get<ReportingApiToken[]>(`${this.apiUrl}/reporting/tokens`);
  }

  createReportingToken(payload: {
    name: string;
    scopes: string[];
    include_pii: boolean;
    expires_in_days: number;
    allowed_ips?: string[];
  }): Observable<ReportingTokenCreatedResponse> {
    return this.http.post<ReportingTokenCreatedResponse>(`${this.apiUrl}/reporting/tokens`, payload);
  }

  revokeReportingToken(tokenId: number): Observable<{ message: string; token_id: number; is_revoked: boolean }> {
    return this.http.delete<{ message: string; token_id: number; is_revoked: boolean }>(
      `${this.apiUrl}/reporting/tokens/${tokenId}`
    );
  }

  // ================= SKILL-TO-PROJECT MATCHING =================
  getStaffingProjects(): Observable<StaffingProject[]> {
    return this.http.get<StaffingProject[]>(`${this.apiUrl}/staffing/projects`);
  }

  getStaffingProject(projectId: number): Observable<StaffingProject> {
    return this.http.get<StaffingProject>(`${this.apiUrl}/staffing/projects/${projectId}`);
  }

  createStaffingProject(payload: {
    name: string;
    description?: string;
    headcount: number;
    start_date: string;
    ready_now_threshold_pct: number;
    skills: Array<{ skill_name: string; min_level_pct: number; weight: number }>;
  }): Observable<StaffingProject> {
    return this.http.post<StaffingProject>(`${this.apiUrl}/staffing/projects`, payload);
  }

  getProjectMatches(projectId: number): Observable<StaffingProjectMatchesResponse> {
    return this.http.get<StaffingProjectMatchesResponse>(`${this.apiUrl}/staffing/projects/${projectId}/matches`);
  }
}
