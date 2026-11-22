import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  ChatMessage, ChatSession, StarterPrompts, AdminLLMUsageSummary
} from '../models/chat.model';

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  private readonly baseUrl = 'http://localhost:8001/api/v1/chat';
  private readonly adminUrl = 'http://localhost:8001/api/v1/admin/llm';

  constructor(private http: HttpClient) {}

  getStarterPrompts(): Observable<StarterPrompts> {
    return this.http.get<StarterPrompts>(`${this.baseUrl}/starter-prompts`);
  }

  getHistory(): Observable<ChatSession> {
    return this.http.get<ChatSession>(`${this.baseUrl}/history`);
  }

  clearHistory(): Observable<any> {
    return this.http.delete(`${this.baseUrl}/history`);
  }

  sendMessage(content: string): Observable<ChatMessage> {
    return this.http.post<ChatMessage>(`${this.baseUrl}/message`, { content });
  }

  submitFeedback(messageId: number, feedback: 'UP' | 'DOWN', comment?: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/feedback/${messageId}`, { feedback, comment });
  }

  getAdminLLMUsage(): Observable<AdminLLMUsageSummary> {
    return this.http.get<AdminLLMUsageSummary>(`${this.adminUrl}/usage`);
  }
}
