import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { QuestionBankItem, AssessmentType, QuestionDifficulty } from '../models/assessment.model';

@Injectable({
  providedIn: 'root'
})
export class QuestionService {
  private readonly apiUrl = 'http://localhost:8001/api/v1/questions';

  constructor(private http: HttpClient) {}

  getQuestions(filters?: { type?: AssessmentType; difficulty?: QuestionDifficulty; skill?: string; search?: string }): Observable<QuestionBankItem[]> {
    let params = new HttpParams();
    if (filters?.type) params = params.set('type', filters.type);
    if (filters?.difficulty) params = params.set('difficulty', filters.difficulty);
    if (filters?.skill) params = params.set('skill', filters.skill);
    if (filters?.search) params = params.set('search', filters.search);

    return this.http.get<QuestionBankItem[]>(this.apiUrl, { params });
  }

  getQuestionById(id: number): Observable<QuestionBankItem> {
    return this.http.get<QuestionBankItem>(`${this.apiUrl}/${id}`);
  }

  createQuestion(payload: Partial<QuestionBankItem>): Observable<QuestionBankItem> {
    return this.http.post<QuestionBankItem>(this.apiUrl, payload);
  }

  deleteQuestion(id: number): Observable<{ message: string; id: number }> {
    return this.http.delete<{ message: string; id: number }>(`${this.apiUrl}/${id}`);
  }
}
