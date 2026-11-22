export interface CoarseBuddee {
  pairing_id: number;
  buddee_id: number;
  coarse_name: string;
  cohort_name: string;
  coarse_status: 'On track' | 'Needs support';
  paired_at: string;
  status: string;
}

export interface CoarseBuddy {
  pairing_id: number;
  buddy_id: number;
  coarse_name: string;
  cohort_name: string;
  paired_at: string;
  status: string;
}

export interface BuddyViewResponse {
  is_volunteer: boolean;
  what_is_shared_notice: string;
  max_buddees_cap: number;
  my_buddees: CoarseBuddee[];
  my_buddy: CoarseBuddy | null;
}

export interface ForumPostItem {
  id: number;
  cohort_id: number;
  title: string;
  body: string;
  tags?: string;
  is_anonymous: boolean;
  author_name: string;
  status: string;
  is_resolved: boolean;
  view_count: number;
  answers_count: number;
  created_at: string;
}

export interface ForumAuthorInfo {
  author_id: number | null;
  author_name: string;
  is_anonymous_to_peers: boolean;
}

export interface ForumAnswerItem {
  id: number;
  body: string;
  author: ForumAuthorInfo;
  is_accepted: boolean;
  is_mentor_verified: boolean;
  is_ai_generated: boolean;
  ai_model?: string;
  is_hidden: boolean;
  upvote_count: number;
  user_has_upvoted: boolean;
  created_at: string;
}

export interface ForumThreadDetail {
  id: number;
  cohort_id: number;
  title: string;
  body: string;
  tags?: string;
  author: ForumAuthorInfo;
  status: string;
  held_reason?: string;
  is_resolved: boolean;
  accepted_answer_id?: number;
  view_count: number;
  created_at: string;
  answers: ForumAnswerItem[];
}

export interface ForumReportItem {
  id: number;
  target_type: 'POST' | 'ANSWER';
  post_id?: number;
  answer_id?: number;
  reason: string;
  notes?: string;
  status: string;
  created_at: string;
  reporter_abuse_stats?: {
    total_submitted: number;
    dismissed_count: number;
  };
}
