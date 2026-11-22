export interface CohortMemberItem {
  id: number;
  ase_id: number;
  ase_name: string;
  ase_email: string;
  mentor_id?: number;
  mentor_name?: string;
  added_at: string;
}

export interface CohortItem {
  id: number;
  name: string;
  description?: string;
  start_date: string;
  created_by?: number;
  creator_name?: string;
  created_at: string;
  member_count: number;
  members?: CohortMemberItem[];
}

export interface CohortCreatePayload {
  name: string;
  description?: string;
  start_date: string;
}

export interface CohortUpdatePayload {
  name?: string;
  description?: string;
  start_date?: string;
}

export interface ASESearchItem {
  id: number;
  name: string;
  email: string;
  cohort_id?: number;
  cohort_name?: string;
  mentor_id?: number;
  mentor_name?: string;
  total_assessments: number;
  latest_score?: number;
  latest_passed?: boolean;
  latest_status?: string;
  violation_count: number;
  suggested_focus?: string;
}

export interface ASESearchResponse {
  items: ASESearchItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
