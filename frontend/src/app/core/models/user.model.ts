export type UserRole = 'ADMIN' | 'MENTOR' | 'ASE';

export interface User {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  must_change_password?: boolean;
  assigned_mentor_id?: number | null;
  assigned_mentor_name?: string | null;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  name: string;
  email: string;
  role: UserRole;
  must_change_password?: boolean;
}

export interface MentorAseAssignment {
  id: number;
  mentor_id: number;
  mentor_name: string;
  mentor_email: string;
  ase_id: number;
  ase_name: string;
  ase_email: string;
  assigned_at: string;
}

export interface AdminDashboardData {
  total_mentors: number;
  total_ases: number;
  total_assignments: number;
  unassigned_ases: number;
  recent_users: Array<{
    id: number;
    name: string;
    email: string;
    role: UserRole;
    created_at: string;
  }>;
}

export interface MentorDashboardData {
  mentor_id: number;
  mentor_name: string;
  mentor_email: string;
  total_mentees: number;
  mentees: Array<{
    id: number;
    name: string;
    email: string;
    role: string;
    assigned_at: string;
  }>;
}

export interface AseDashboardData {
  ase_id: number;
  name: string;
  email: string;
  role: string;
  created_at: string;
  has_mentor: boolean;
  mentor?: {
    id: number;
    name: string;
    email: string;
    assigned_at: string;
  } | null;
}
