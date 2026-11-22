export interface AttendeeItem {
  ase_id: number;
  ase_name: string;
  ase_email: string;
  status: 'INVITED' | 'ATTENDED' | 'ABSENT';
  marked_at?: string;
  marked_by_name?: string;
}

export interface LiveClassItem {
  id: number;
  title: string;
  description?: string;
  start_time: string; // UTC ISO string
  duration_minutes: number;
  audience_type: 'ALL' | 'COHORT' | 'SELECTED';
  cohort_id?: number;
  cohort_name?: string;
  meeting_link: string;
  provider: 'MANUAL' | 'TEAMS_GRAPH';
  created_by?: number;
  creator_name?: string;
  total_invited: number;
  total_attended: number;
  attendees: AttendeeItem[];
  created_at: string;
}

export interface LiveClassCreatePayload {
  title: string;
  description?: string;
  start_time: string;
  duration_minutes: number;
  audience_type: 'ALL' | 'COHORT' | 'SELECTED';
  cohort_id?: number;
  ase_ids?: number[];
  meeting_link: string;
  provider: 'MANUAL' | 'TEAMS_GRAPH';
}

export interface AttendanceBatchPayload {
  attendances: { ase_id: number; status: 'INVITED' | 'ATTENDED' | 'ABSENT' }[];
}
