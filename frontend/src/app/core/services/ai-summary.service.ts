import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  ClassTranscript,
  ClassSummary,
  AssessmentPlan,
  AIGeneratedAssessment,
  AIGeneratedQuestion,
  ClassEffectivenessReport
} from '../models/ai-summary.model';

@Injectable({
  providedIn: 'root'
})
export class AISummaryService {
  private readonly baseUrl = 'http://localhost:8001/api/v1/class-summaries';

  constructor(private http: HttpClient) {}

  uploadTranscript(formData: FormData): Observable<ClassTranscript> {
    return this.http.post<ClassTranscript>(`${this.baseUrl}/transcripts/upload`, formData);
  }

  submitNotesTranscript(payload: {
    live_class_id?: number;
    training_id?: number;
    notes?: string;
    topics_covered?: string;
    privacy_consent_acknowledged: boolean;
  }): Observable<ClassTranscript> {
    return this.http.post<ClassTranscript>(`${this.baseUrl}/transcripts/notes`, payload);
  }

  deleteRawTranscript(transcriptId: number): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${this.baseUrl}/transcripts/${transcriptId}/raw`);
  }

  generateSummary(transcriptId: number): Observable<ClassSummary> {
    return this.http.post<ClassSummary>(`${this.baseUrl}/generate?transcript_id=${transcriptId}`, {});
  }

  getSummaryByClass(liveClassId: number): Observable<ClassSummary | null> {
    return this.http.get<ClassSummary | null>(`${this.baseUrl}/by-class/${liveClassId}`);
  }

  updateSummary(summaryId: number, payload: Partial<ClassSummary>): Observable<ClassSummary> {
    return this.http.put<ClassSummary>(`${this.baseUrl}/${summaryId}`, payload);
  }

  publishSummary(summaryId: number): Observable<ClassSummary> {
    return this.http.post<ClassSummary>(`${this.baseUrl}/${summaryId}/publish`, {});
  }

  unpublishSummary(summaryId: number): Observable<ClassSummary> {
    return this.http.post<ClassSummary>(`${this.baseUrl}/${summaryId}/unpublish`, {});
  }

  recommendPlan(summaryId: number): Observable<AssessmentPlan> {
    return this.http.post<AssessmentPlan>(`${this.baseUrl}/recommend-plan`, { summary_id: summaryId });
  }

  generateAssessment(payload: {
    live_class_id?: number;
    training_id?: number;
    title: string;
    generation_mode: string;
    recommended_total_questions: number;
    difficulty_split: { [key: string]: number };
    topic_split?: { [key: string]: number };
    skill_category?: string;
  }): Observable<AIGeneratedAssessment> {
    return this.http.post<AIGeneratedAssessment>(`${this.baseUrl}/assessments/generate`, payload);
  }

  getAssessment(assessmentId: number): Observable<AIGeneratedAssessment> {
    return this.http.get<AIGeneratedAssessment>(`${this.baseUrl}/assessments/${assessmentId}`);
  }

  updateQuestion(questionId: number, payload: Partial<AIGeneratedQuestion>): Observable<AIGeneratedQuestion> {
    return this.http.put<AIGeneratedQuestion>(`${this.baseUrl}/questions/${questionId}`, payload);
  }

  approveQuestion(questionId: number): Observable<AIGeneratedQuestion> {
    return this.http.post<AIGeneratedQuestion>(`${this.baseUrl}/questions/${questionId}/approve`, {});
  }

  rejectQuestion(questionId: number): Observable<AIGeneratedQuestion> {
    return this.http.post<AIGeneratedQuestion>(`${this.baseUrl}/questions/${questionId}/reject`, {});
  }

  regenerateQuestion(questionId: number): Observable<AIGeneratedQuestion> {
    return this.http.post<AIGeneratedQuestion>(`${this.baseUrl}/questions/${questionId}/regenerate`, {});
  }

  approveAllQuestions(assessmentId: number): Observable<AIGeneratedAssessment> {
    return this.http.post<AIGeneratedAssessment>(`${this.baseUrl}/assessments/${assessmentId}/approve-all`, {});
  }

  exportToBank(assessmentId: number, questionIds: number[]): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${this.baseUrl}/assessments/${assessmentId}/export-to-bank`, {
      question_ids: questionIds
    });
  }

  finalizeAndAssign(assessmentId: number): Observable<{ message: string; assessment_id: number; is_immutable: boolean }> {
    return this.http.post<{ message: string; assessment_id: number; is_immutable: boolean }>(
      `${this.baseUrl}/assessments/${assessmentId}/finalize-assign`,
      {}
    );
  }

  getClassEffectiveness(liveClassId: number): Observable<ClassEffectivenessReport> {
    return this.http.get<ClassEffectivenessReport>(`${this.baseUrl}/effectiveness/live-class/${liveClassId}`);
  }
}
