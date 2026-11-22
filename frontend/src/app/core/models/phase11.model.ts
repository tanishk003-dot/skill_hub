export interface QuestionItemAnalytics {
  id: number;
  question_id: number;
  question_version: number;
  attempts_count: number;
  correct_count: number;
  difficulty_index: number;
  discrimination_index: number;
  is_indicative_discrimination: boolean;
  most_chosen_wrong_option?: string;
  avg_time_seconds: number;
  is_too_easy: boolean;
  is_too_hard: boolean;
  is_poor_discrimination: boolean;
  needs_review: boolean;
  review_reason?: string;
  option_distribution?: Record<string, number>;
  formula_metadata?: {
    sample_size: number;
    upper_group_size: number;
    upper_correct: number;
    lower_correct: number;
    discrimination_formula: string;
    difficulty_formula: string;
    sample_status: string;
  };
  calculated_at: string;
  updated_at: string;
}

export interface OneOnOneMeeting {
  id: number;
  mentor_id: number;
  mentee_id: number;
  title: string;
  meeting_date: string;
  status: 'SCHEDULED' | 'COMPLETED' | 'CANCELLED';
  shared_notes?: string;
  private_notes?: string; // Null for ASEs and Admins!
  ai_summary_shared?: string;
  ai_summary_private?: string;
  created_at: string;
  updated_at: string;
}

export interface OneOnOneGoal {
  id: number;
  mentor_id: number;
  mentee_id: number;
  meeting_id?: number;
  title: string;
  description?: string;
  target_date: string;
  status: 'NOT_STARTED' | 'IN_PROGRESS' | 'ACHIEVED' | 'ABANDONED';
  created_at: string;
  updated_at: string;
}

export interface OneOnOneActionItem {
  id: number;
  mentor_id: number;
  mentee_id: number;
  meeting_id?: number;
  goal_id?: number;
  task: string;
  assigned_to: 'ASE' | 'MENTOR';
  is_completed: boolean;
  completed_at?: string;
  created_at: string;
}

export interface OneOnOneComment {
  id: number;
  user_id: number;
  comment_text: string;
  created_at: string;
}

export interface ReportingApiToken {
  id: number;
  name: string;
  scopes: string[];
  include_pii: boolean;
  allowed_ips?: string[];
  expires_at: string;
  is_revoked: boolean;
  last_used_at?: string;
  created_at: string;
}

export interface ReportingTokenCreatedResponse {
  id: number;
  name: string;
  token: string;
  scopes: string[];
  include_pii: boolean;
  allowed_ips?: string[];
  expires_at: string;
  created_at: string;
}

export interface StaffingProjectSkill {
  id?: number;
  skill_name: string;
  min_level_pct: number;
  weight: number;
}

export interface StaffingProject {
  id: number;
  name: string;
  description?: string;
  headcount: number;
  start_date: string;
  ready_now_threshold_pct: number;
  status: string;
  skill_count?: number;
  skills?: StaffingProjectSkill[];
  disclaimer: string;
}

export interface SkillMatchBreakdown {
  skill_name: string;
  required_level_pct: number;
  candidate_level_pct: number;
  gap_pct: number;
  weight: number;
  recommended_training?: {
    training_id: number;
    title: string;
    duration_hours: number;
  };
}

export interface CandidateProjectMatch {
  candidate_id: number;
  pseudonymous_id: string;
  name?: string;
  email?: string;
  match_percentage: number;
  readiness_label: string;
  weeks_estimate: number;
  is_ready_now: boolean;
  skill_breakdowns: SkillMatchBreakdown[];
  recommended_trainings: Array<{ training_id: number; title: string; duration_hours: number }>;
  formula_breakdown: {
    weighted_numerator: number;
    weighted_denominator: number;
    formula: string;
    ready_now_threshold_pct: number;
  };
}

export interface StaffingProjectMatchesResponse {
  project_id: number;
  project_name: string;
  description?: string;
  headcount: number;
  start_date: string;
  ready_now_threshold_pct: number;
  status: string;
  disclaimer: string;
  total_evaluated: number;
  candidates: CandidateProjectMatch[];
}
