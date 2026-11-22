export interface MotivationalQuote {
  id: number;
  role: 'ADMIN' | 'MENTOR' | 'ASE';
  text: string;
  author: string;
  is_active: boolean;
  is_demo?: boolean;
  created_at?: string;
}

export interface DailyQuoteData {
  id: number;
  role: string;
  text: string;
  author: string;
  date: string;
  dismiss_timeout_ms: number;
}

export interface DailyQuoteResponse {
  should_show_splash: boolean;
  quote: DailyQuoteData;
}
