import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  BuddyViewResponse,
  ForumPostItem,
  ForumThreadDetail,
  ForumReportItem
} from '../models/phase12.model';

@Injectable({
  providedIn: 'root'
})
export class Phase12Service {
  private apiUrl = 'http://localhost:8001/api/v1';

  constructor(private http: HttpClient) {}

  // ================= BUDDY SYSTEM =================

  getMyBuddyDetails(): Observable<BuddyViewResponse> {
    return this.http.get<BuddyViewResponse>(`${this.apiUrl}/buddy/my-pairings`);
  }

  toggleVolunteer(isVolunteer: boolean): Observable<{ is_buddy_volunteer: boolean; message: string }> {
    return this.http.post<{ is_buddy_volunteer: boolean; message: string }>(
      `${this.apiUrl}/buddy/volunteer`,
      { is_volunteer: isVolunteer }
    );
  }

  createPairing(buddyId: number, buddeeId: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/buddy/pairings`, {
      buddy_id: buddyId,
      buddee_id: buddeeId
    });
  }

  requestPairingChange(pairingId: number, reason: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/buddy/pairings/${pairingId}/change-request`, {
      reason
    });
  }

  rateBuddy(pairingId: number, rating: number, feedback?: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/buddy/pairings/${pairingId}/rate`, {
      rating,
      feedback
    });
  }

  createMilestone(pairingId: number, title: string, description?: string, xpAmount: number = 25): Observable<any> {
    return this.http.post(`${this.apiUrl}/buddy/pairings/${pairingId}/milestones`, {
      title,
      description,
      xp_amount: xpAmount
    });
  }

  verifyMilestone(milestoneId: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/buddy/milestones/${milestoneId}/verify`, {});
  }

  // ================= DOUBT FORUM =================

  getPosts(params?: {
    cohort_id?: number;
    tag?: string;
    unanswered_only?: boolean;
    page?: number;
    page_size?: number;
  }): Observable<{ total: number; page: number; page_size: number; items: ForumPostItem[] }> {
    let httpParams = new HttpParams();
    if (params?.cohort_id) httpParams = httpParams.set('cohort_id', params.cohort_id);
    if (params?.tag) httpParams = httpParams.set('tag', params.tag);
    if (params?.unanswered_only) httpParams = httpParams.set('unanswered_only', params.unanswered_only);
    if (params?.page) httpParams = httpParams.set('page', params.page);
    if (params?.page_size) httpParams = httpParams.set('page_size', params.page_size);

    return this.http.get<{ total: number; page: number; page_size: number; items: ForumPostItem[] }>(
      `${this.apiUrl}/forum/posts`,
      { params: httpParams }
    );
  }

  createPost(payload: {
    cohort_id: number;
    title: string;
    body: string;
    tags?: string;
    tagged_assessment_id?: number;
    is_anonymous?: boolean;
  }): Observable<any> {
    return this.http.post(`${this.apiUrl}/forum/posts`, payload);
  }

  getSimilarQuestions(query: string): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/forum/posts/similar`, {
      params: new HttpParams().set('query', query)
    });
  }

  getThreadDetail(postId: number): Observable<ForumThreadDetail> {
    return this.http.get<ForumThreadDetail>(`${this.apiUrl}/forum/posts/${postId}`);
  }

  postAnswer(postId: number, payload: { body: string; is_anonymous?: boolean }): Observable<any> {
    return this.http.post(`${this.apiUrl}/forum/posts/${postId}/answers`, payload);
  }

  toggleVote(answerId: number): Observable<{ action: string; upvotes: number }> {
    return this.http.post<{ action: string; upvotes: number }>(
      `${this.apiUrl}/forum/answers/${answerId}/vote`,
      {}
    );
  }

  acceptAnswer(postId: number, answerId: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/forum/posts/${postId}/accept/${answerId}`, {});
  }

  verifyAnswer(answerId: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/forum/answers/${answerId}/verify`, {});
  }

  requestAIDraft(postId: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/forum/posts/${postId}/ai-draft`, {});
  }

  reportContent(payload: {
    reason: string;
    notes?: string;
    post_id?: number;
    answer_id?: number;
  }): Observable<any> {
    return this.http.post(`${this.apiUrl}/forum/report`, payload);
  }

  getModerationReports(): Observable<{ reports: ForumReportItem[] }> {
    return this.http.get<{ reports: ForumReportItem[] }>(`${this.apiUrl}/forum/moderation/reports`);
  }

  moderateContent(payload: {
    target_type: 'POST' | 'ANSWER';
    target_id: number;
    action: string;
    reason: string;
  }): Observable<any> {
    return this.http.post(`${this.apiUrl}/forum/moderation/action`, payload);
  }
}
