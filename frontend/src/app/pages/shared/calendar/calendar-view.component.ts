import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { CalendarService } from '../../../core/services/calendar.service';
import { CalendarEventItem } from '../../../core/models/calendar.model';

@Component({
  selector: 'app-calendar-view',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatProgressSpinnerModule
  ],
  template: `
    <div class="calendar-page">
      <!-- Header -->
      <div class="page-header">
        <div>
          <h1>Unified Academic & Evaluation Schedule</h1>
          <p class="subtitle">Consolidated agenda for live coaching sessions, assessment evaluation deadlines, and training milestones</p>
        </div>
      </div>

      <!-- Loading State -->
      <div *ngIf="loading" class="loading-state">
        <mat-spinner diameter="40"></mat-spinner>
        <span>Loading schedule timeline...</span>
      </div>

      <!-- Events List View -->
      <div *ngIf="!loading && events.length > 0" class="schedule-timeline">
        <div class="timeline-group">
          <mat-card class="event-card" *ngFor="let ev of events" [ngClass]="'border-' + ev.event_type.toLowerCase()">
            <div class="event-left">
              <div class="event-icon-circle" [ngClass]="'icon-' + ev.event_type.toLowerCase()">
                <mat-icon>{{ getEventIcon(ev.event_type) }}</mat-icon>
              </div>
              <div class="event-details">
                <div class="event-type-row">
                  <span class="type-pill" [ngClass]="'pill-' + ev.event_type.toLowerCase()">{{ ev.event_type }}</span>
                  <span class="event-time">{{ ev.start_time | date:'EEEE, MMM d, y - h:mm a' }}</span>
                </div>
                <h3 class="event-title">{{ ev.title }}</h3>
                <p class="event-meta" *ngIf="ev.details">{{ ev.details }}</p>
              </div>
            </div>

            <div class="event-actions">
              <!-- Join Meeting if live class -->
              <a *ngIf="ev.meeting_link" 
                 [href]="ev.meeting_link" 
                 target="_blank" 
                 rel="noopener noreferrer" 
                 mat-raised-button 
                 color="primary">
                <mat-icon>videocam</mat-icon> Join Class
              </a>

              <!-- Action button for Assessment/Training -->
              <a *ngIf="!ev.meeting_link && ev.action_url" 
                 [routerLink]="ev.action_url" 
                 mat-stroked-button 
                 color="primary">
                <mat-icon>arrow_forward</mat-icon> View
              </a>
            </div>
          </mat-card>
        </div>
      </div>

      <!-- Empty State -->
      <div *ngIf="!loading && events.length === 0" class="empty-state-card">
        <mat-icon class="empty-icon">event_busy</mat-icon>
        <h2>No Scheduled Events Found</h2>
        <p>You have no pending live classes, assessments, or training programs scheduled at this time.</p>
      </div>
    </div>
  `,
  styles: [`
    .calendar-page {
      display: flex;
      flex-direction: column;
      gap: 24px;
      padding-bottom: 40px;
    }

    .page-header h1 {
      margin: 0;
      color: #0F172A;
      font-size: 1.7rem;
      font-weight: 700;
    }

    .subtitle {
      margin: 4px 0 0 0;
      color: #64748B;
      font-size: 0.95rem;
    }

    .loading-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;
      padding: 60px 0;
      color: #64748B;
    }

    .schedule-timeline {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .timeline-group {
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .event-card {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 18px 24px;
      border-radius: 12px;
      background: #ffffff;
      border: 1px solid #E2E8F0;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
      flex-wrap: wrap;
      gap: 16px;
      transition: transform 0.15s ease;
    }

    .event-card:hover {
      transform: translateY(-1px);
    }

    .border-class { border-left: 5px solid var(--csm-primary) !important; }
    .border-assessment { border-left: 5px solid var(--csm-accent) !important; }
    .border-training { border-left: 5px solid #059669 !important; }

    .event-left {
      display: flex;
      align-items: center;
      gap: 18px;
    }

    .event-icon-circle {
      width: 46px;
      height: 46px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .icon-class { background: #EFF6FF; color: var(--csm-primary); }
    .icon-assessment { background: #FFF7ED; color: var(--csm-accent); }
    .icon-training { background: #ECFDF5; color: #059669; }

    .event-type-row {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 4px;
    }

    .type-pill {
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      padding: 2px 8px;
      border-radius: 6px;
    }

    .pill-class { background: #EFF6FF; color: var(--csm-primary); }
    .pill-assessment { background: #FFF7ED; color: #EA580C; }
    .pill-training { background: #ECFDF5; color: #059669; }

    .event-time {
      font-size: 0.82rem;
      font-weight: 600;
      color: #64748B;
    }

    .event-title {
      margin: 0;
      font-size: 1.1rem;
      color: #0F172A;
      font-weight: 700;
    }

    .event-meta {
      margin: 2px 0 0 0;
      font-size: 0.8rem;
      color: #64748B;
    }

    .empty-state-card {
      text-align: center;
      padding: 60px 20px;
      background: #ffffff;
      border-radius: 16px;
      border: 1px solid #E2E8F0;
    }

    .empty-icon {
      font-size: 56px;
      width: 56px;
      height: 56px;
      color: #94A3B8;
    }
  `]
})
export class CalendarViewComponent implements OnInit {
  events: CalendarEventItem[] = [];
  loading = true;

  constructor(private calendarService: CalendarService) {}

  ngOnInit(): void {
    this.calendarService.getEvents().subscribe({
      next: (res) => {
        this.events = res.events;
        this.loading = false;
      },
      error: (err) => {
        console.error('Failed to load events', err);
        this.loading = false;
      }
    });
  }

  getEventIcon(type: string): string {
    switch (type) {
      case 'CLASS': return 'videocam';
      case 'ASSESSMENT': return 'quiz';
      case 'TRAINING': return 'school';
      default: return 'event';
    }
  }
}
