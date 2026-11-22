export interface ChatMessage {
  id: number;
  session_id: number;
  sender_role: 'USER' | 'ASSISTANT';
  content: string;
  feedback?: 'UP' | 'DOWN' | null;
  feedback_comment?: string | null;
  created_at: string;
  is_demo_mode?: boolean;
}

export interface ChatSession {
  id: number;
  title: string;
  is_active: boolean;
  created_at: string;
  messages: ChatMessage[];
}

export interface StarterPrompts {
  role: string;
  prompts: string[];
  demo_mode: boolean;
  provider: string;
}

export interface AdminLLMUsageItem {
  id: number;
  user_id: number;
  user_name: string;
  role: string;
  provider: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  created_at: string;
}

export interface AdminLLMUsageSummary {
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  total_requests: number;
  demo_mode: boolean;
  provider: string;
  model: string;
  rate_limit_per_hour: number;
  recent_logs: AdminLLMUsageItem[];
}
