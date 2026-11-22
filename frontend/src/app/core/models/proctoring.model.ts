export type WebcamMode = 'OFF' | 'ADVISORY' | 'REQUIRED';
export type WebcamPolicy = 'WARNING_ONLY' | 'COUNTED_STRIKES';
export type CameraStatus = 'ACTIVE' | 'BLOCKED' | 'REVOKED' | 'NO_FACE' | 'MULTIPLE_FACES' | 'HEAD_TURNED' | 'EXEMPT' | 'OVERRIDDEN' | 'INACTIVE';

export interface WebcamConsentRequest {
  consented: boolean;
}

export interface WebcamConsentResponse {
  success: boolean;
  consented: boolean;
  consented_at: string;
}

export interface CameraHandshakeResponse {
  handshake_token: string;
  expires_at: string;
  is_exempt: boolean;
  is_overridden: boolean;
}

export interface CameraHeartbeatRequest {
  attempt_id: number;
  status: string;
  details?: string;
}

export interface CameraHeartbeatResponse {
  ok: boolean;
  server_time: string;
  remaining_seconds: number;
  camera_status: string;
  webcam_policy: string;
  grace_period_seconds: number;
}

export interface CameraEventRequest {
  attempt_id: number;
  event_type: string; // NO_FACE, MULTIPLE_FACES, HEAD_TURNED, CAMERA_BLOCKED, CAMERA_REVOKED
  duration_seconds: number;
  snapshot_base64?: string;
  is_warning: boolean;
}

export interface CameraEventResponse {
  event_recorded: boolean;
  event_type: string;
  policy: string;
  strike_triggered: boolean;
  current_violations: number;
  auto_submitted: boolean;
}

export interface CameraOverrideRequest {
  assignment_id: number;
  reason: string;
  attempt_id?: number;
}

export interface CameraOverrideResponse {
  success: boolean;
  message: string;
  override_token: string;
  granted_at: string;
}

export interface CameraProctoringLogResponse {
  attempt_id: number;
  ase_name?: string;
  camera_override_active: boolean;
  camera_exempt: boolean;
  last_camera_status: string;
  recent_heartbeats: {
    status: string;
    timestamp: string;
    details?: string;
  }[];
  snapshot_count: number;
  human_review_notice: string;
}

export interface AccommodationRequestItem {
  id: number;
  ase_id: number;
  ase_name?: string;
  requested_by: number;
  requested_by_name?: string;
  accommodation_type: 'EXTRA_TIME_PCT' | 'CAMERA_EXEMPTION' | 'REST_BREAKS' | 'ALTERNATIVE_PROCTORING' | 'OTHER';
  extra_time_percent: number;
  reason_category: string;
  medical_notes?: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  admin_notes?: string;
  reviewed_by?: number;
  reviewed_at?: string;
  created_at: string;
}

export interface AccommodationCreatePayload {
  ase_id: number;
  accommodation_type: string;
  extra_time_percent?: number;
  reason_category: string;
  medical_notes?: string;
}

export interface AccommodationDecisionPayload {
  approved: boolean;
  admin_notes?: string;
}

export interface ActiveAccommodationResponse {
  has_active: boolean;
  accommodation_type?: string;
  extra_time_percent?: number;
  neutral_notice?: string;
}
