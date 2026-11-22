import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { MotivationalQuote, DailyQuoteResponse } from '../models/quote.model';

@Injectable({
  providedIn: 'root'
})
export class QuoteService {
  private readonly apiUrl = 'http://localhost:8001/api/v1/quotes';

  constructor(private http: HttpClient) {}

  getDailyQuote(): Observable<DailyQuoteResponse> {
    return this.http.get<DailyQuoteResponse>(`${this.apiUrl}/daily`);
  }

  acknowledgeSplash(): Observable<any> {
    return this.http.post(`${this.apiUrl}/ack-splash`, {});
  }

  // Admin CRUD
  listQuotesAdmin(role?: string, isActive?: boolean): Observable<MotivationalQuote[]> {
    let params = new HttpParams();
    if (role) params = params.set('role', role);
    if (isActive !== undefined && isActive !== null) params = params.set('is_active', String(isActive));
    return this.http.get<MotivationalQuote[]>(`${this.apiUrl}/admin`, { params });
  }

  createQuote(quote: Partial<MotivationalQuote>): Observable<MotivationalQuote> {
    return this.http.post<MotivationalQuote>(`${this.apiUrl}/admin`, quote);
  }

  updateQuote(id: number, quote: Partial<MotivationalQuote>): Observable<MotivationalQuote> {
    return this.http.put<MotivationalQuote>(`${this.apiUrl}/admin/${id}`, quote);
  }

  deleteQuote(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/admin/${id}`);
  }
}
