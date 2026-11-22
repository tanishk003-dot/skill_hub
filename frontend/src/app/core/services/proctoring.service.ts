import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  WebcamConsentResponse,
  CameraHandshakeResponse,
  CameraHeartbeatResponse,
  CameraEventRequest,
  CameraEventResponse,
  CameraOverrideRequest,
  CameraOverrideResponse,
  CameraProctoringLogResponse,
  AccommodationRequestItem,
  AccommodationCreatePayload,
  AccommodationDecisionPayload,
  ActiveAccommodationResponse
} from '../models/proctoring.model';

@Injectable({
  providedIn: 'root'
})
export class ProctoringService {
  private readonly baseUrl = 'http://localhost:8001/api/v1/proctoring';
  private readonly assessmentsUrl = 'http://localhost:8001/api/v1/assessments';

  constructor(private http: HttpClient) {}

  submitConsent(assignmentId: number, consented: boolean): Observable<WebcamConsentResponse> {
    return this.http.post<WebcamConsentResponse>(`${this.baseUrl}/consent/${assignmentId}`, { consented });
  }

  requestHandshake(assignmentId: number): Observable<CameraHandshakeResponse> {
    return this.http.post<CameraHandshakeResponse>(`${this.baseUrl}/handshake/${assignmentId}`, {});
  }

  sendHeartbeat(attemptId: number, status: string, details?: string): Observable<CameraHeartbeatResponse> {
    return this.http.post<CameraHeartbeatResponse>(`${this.baseUrl}/camera-heartbeat`, {
      attempt_id: attemptId,
      status,
      details
    });
  }

  reportCameraEvent(payload: CameraEventRequest): Observable<CameraEventResponse> {
    return this.http.post<CameraEventResponse>(`${this.baseUrl}/camera-event`, payload);
  }

  grantOverride(payload: CameraOverrideRequest): Observable<CameraOverrideResponse> {
    return this.http.post<CameraOverrideResponse>(`${this.baseUrl}/camera-override`, payload);
  }

  getProctoringLog(attemptId: number): Observable<CameraProctoringLogResponse> {
    return this.http.get<CameraProctoringLogResponse>(`${this.baseUrl}/events/${attemptId}`);
  }

  requestAccommodation(payload: AccommodationCreatePayload): Observable<{ success: boolean; request_id: number; status: string; created_at: string }> {
    return this.http.post<{ success: boolean; request_id: number; status: string; created_at: string }>(
      `${this.baseUrl}/accommodations/request`,
      payload
    );
  }

  listAccommodations(aseId?: number): Observable<AccommodationRequestItem[]> {
    let params = new HttpParams();
    if (aseId) params = params.set('ase_id', aseId.toString());
    return this.http.get<AccommodationRequestItem[]>(`${this.baseUrl}/accommodations/list`, { params });
  }

  reviewAccommodation(requestId: number, approved: boolean, notes?: string): Observable<any> {
    return this.http.put<any>(`${this.baseUrl}/accommodations/${requestId}/decision`, {
      approved,
      admin_notes: notes
    });
  }

  checkActiveAccommodation(aseId: number, type?: string): Observable<ActiveAccommodationResponse> {
    let params = new HttpParams();
    if (type) params = params.set('accommodation_type', type);
    return this.http.get<ActiveAccommodationResponse>(`${this.baseUrl}/accommodations/active/${aseId}`, { params });
  }

  updateAssessmentWebcamConfig(assessmentId: number, config: {
    webcam_mode?: string;
    webcam_policy?: string;
    camera_no_face_seconds?: number;
    camera_multiple_faces_seconds?: number;
    camera_head_turn_seconds?: number;
    camera_grace_period_seconds?: number;
  }): Observable<any> {
    return this.http.patch<any>(`${this.assessmentsUrl}/${assessmentId}/webcam-config`, config);
  }
}
