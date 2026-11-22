export interface CalendarEventItem {
  id: string;
  title: string;
  event_type: 'CLASS' | 'ASSESSMENT' | 'TRAINING';
  start_time: string; // UTC ISO string
  end_time?: string;
  status?: string;
  meeting_link?: string;
  action_url?: string;
  details?: string;
}

export interface CalendarEventsResponse {
  events: CalendarEventItem[];
}
