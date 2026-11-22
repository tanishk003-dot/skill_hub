import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { User, UserRole } from '../models/user.model';

@Injectable({
  providedIn: 'root'
})
export class UserService {
  private readonly apiUrl = 'http://localhost:8001/api/v1/users';

  constructor(private http: HttpClient) {}

  getUsers(role?: UserRole, includeInactive: boolean = false): Observable<User[]> {
    let params = new HttpParams().set('include_inactive', includeInactive.toString());
    if (role) {
      params = params.set('role', role);
    }
    return this.http.get<User[]>(this.apiUrl, { params });
  }

  getUserById(id: number): Observable<User> {
    return this.http.get<User>(`${this.apiUrl}/${id}`);
  }

  createUser(payload: { name: string; email: string; password: string; role: UserRole }): Observable<User> {
    return this.http.post<User>(this.apiUrl, payload);
  }

  updateUser(id: number, payload: Partial<{ name: string; email: string; password: string; role: UserRole; is_active: boolean }>): Observable<User> {
    return this.http.put<User>(`${this.apiUrl}/${id}`, payload);
  }

  deleteUser(id: number): Observable<{ message: string; id: number; is_active: boolean }> {
    return this.http.delete<{ message: string; id: number; is_active: boolean }>(`${this.apiUrl}/${id}`);
  }
}
