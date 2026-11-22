import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { CalendarEventsResponse } from '../models/calendar.model';

@Injectable({
  providedIn: 'root'
})
export class CalendarService {
  private readonly apiUrl = 'http://localhost:8001/api/v1/calendar/events';

  constructor(private http: HttpClient) {}

  getEvents(): Observable<CalendarEventsResponse> {
    return this.http.get<CalendarEventsResponse>(this.apiUrl);
  }
}
