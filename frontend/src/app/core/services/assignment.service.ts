import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { MentorAseAssignment } from '../models/user.model';

@Injectable({
  providedIn: 'root'
})
export class AssignmentService {
  private readonly apiUrl = 'http://localhost:8001/api/v1/assignments';

  constructor(private http: HttpClient) {}

  getAssignments(): Observable<MentorAseAssignment[]> {
    return this.http.get<MentorAseAssignment[]>(this.apiUrl);
  }

  assignAseToMentor(mentorId: number, aseId: number): Observable<MentorAseAssignment> {
    return this.http.post<MentorAseAssignment>(this.apiUrl, {
      mentor_id: mentorId,
      ase_id: aseId
    });
  }

  deleteAssignment(id: number): Observable<{ message: string; id: number }> {
    return this.http.delete<{ message: string; id: number }>(`${this.apiUrl}/${id}`);
  }
}
