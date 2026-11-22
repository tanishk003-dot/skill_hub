import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  CohortItem, CohortCreatePayload, CohortUpdatePayload, ASESearchResponse
} from '../models/cohort.model';

@Injectable({
  providedIn: 'root'
})
export class CohortService {
  private readonly apiUrl = 'http://localhost:8001/api/v1/cohorts';

  constructor(private http: HttpClient) {}

  listCohorts(): Observable<CohortItem[]> {
    return this.http.get<CohortItem[]>(this.apiUrl);
  }

  createCohort(payload: CohortCreatePayload): Observable<CohortItem> {
    return this.http.post<CohortItem>(this.apiUrl, payload);
  }

  getCohort(id: number): Observable<CohortItem> {
    return this.http.get<CohortItem>(`${this.apiUrl}/${id}`);
  }

  updateCohort(id: number, payload: CohortUpdatePayload): Observable<CohortItem> {
    return this.http.put<CohortItem>(`${this.apiUrl}/${id}`, payload);
  }

  deleteCohort(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }

  addMembers(cohortId: number, aseIds: number[]): Observable<CohortItem> {
    return this.http.post<CohortItem>(`${this.apiUrl}/${cohortId}/members`, {
      ase_ids: aseIds
    });
  }

  removeMember(cohortId: number, aseId: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${cohortId}/members/${aseId}`);
  }

  searchASEs(params: {
    query?: string;
    cohort_id?: number;
    mentor_id?: number;
    score_min?: number;
    score_max?: number;
    pass_status?: string;
    page?: number;
    page_size?: number;
  }): Observable<ASESearchResponse> {
    let httpParams = new HttpParams();
    if (params.query) httpParams = httpParams.set('query', params.query);
    if (params.cohort_id) httpParams = httpParams.set('cohort_id', params.cohort_id);
    if (params.mentor_id) httpParams = httpParams.set('mentor_id', params.mentor_id);
    if (params.score_min !== undefined && params.score_min !== null) httpParams = httpParams.set('score_min', params.score_min);
    if (params.score_max !== undefined && params.score_max !== null) httpParams = httpParams.set('score_max', params.score_max);
    if (params.pass_status) httpParams = httpParams.set('pass_status', params.pass_status);
    if (params.page) httpParams = httpParams.set('page', params.page);
    if (params.page_size) httpParams = httpParams.set('page_size', params.page_size);

    return this.http.get<ASESearchResponse>(`${this.apiUrl}/search/ases`, { params: httpParams });
  }
}
