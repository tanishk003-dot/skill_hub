import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatRadioModule } from '@angular/material/radio';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { LiveClassService } from '../../../core/services/live-class.service';
import { CohortService } from '../../../core/services/cohort.service';
import { LiveClassItem, AttendeeItem } from '../../../core/models/live-class.model';
import { CohortItem } from '../../../core/models/cohort.model';
import { AuthService } from '../../../core/services/auth.service';
import { ClassSummaryDialogComponent } from './class-summary-dialog.component';

@Component({
  selector: 'app-live-class-list',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatRadioModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    ClassSummaryDialogComponent
  ],
  template: `
    <div class="classes-page">
      <!-- Header -->
      <div class="page-header">
        <div>
          <h1>Live Technical Classes & Interactive Sessions</h1>
          <p class="subtitle">Real-time coaching, architecture walkthroughs, and mentor-led engineering sessions</p>
        </div>
        <button mat-raised-button color="primary" (click)="openScheduleModal()" *ngIf="authService.currentUser()?.role !== 'ASE'">
          <mat-icon>video_call</mat-icon> Schedule Live Class
        </button>
      </div>

      <!-- Loading State -->
      <div *ngIf="loading" class="loading-state">
        <mat-spinner diameter="40"></mat-spinner>
        <span>Loading live classes...</span>
      </div>

      <!-- Class Cards Grid -->
      <div *ngIf="!loading" class="classes-grid">
        <mat-card class="class-card" *ngFor="let c of classes">
          <mat-card-header>
            <div class="badges-row">
              <span class="provider-badge">{{ c.provider }}</span>
              <span class="audience-badge">Audience: {{ c.audience_type }}</span>
            </div>
            <mat-card-title class="class-title">{{ c.title }}</mat-card-title>
            <mat-card-subtitle>{{ c.start_time | date:'medium' }} ({{ c.duration_minutes }} mins)</mat-card-subtitle>
          </mat-card-header>

          <mat-card-content class="card-body">
            <p>{{ c.description || 'Interactive live session with technical mentor.' }}</p>

            <div class="stats-row" *ngIf="authService.currentUser()?.role !== 'ASE'">
              <span class="stat-chip"><mat-icon>group</mat-icon> {{ c.total_invited }} Invited</span>
              <span class="stat-chip success"><mat-icon>how_to_reg</mat-icon> {{ c.total_attended }} Attended</span>
            </div>

            <!-- Join Meeting Button -->
            <div class="join-row">
              <a [href]="c.meeting_link" target="_blank" rel="noopener noreferrer" mat-raised-button color="primary" class="join-btn">
                <mat-icon>videocam</mat-icon> Join Session
              </a>
              <button mat-stroked-button color="primary" *ngIf="authService.currentUser()?.role === 'ASE'" (click)="selectedClassForSummary = c">
                <mat-icon>menu_book</mat-icon> Class Summary
              </button>
            </div>
          </mat-card-content>

          <mat-card-actions class="card-footer" *ngIf="authService.currentUser()?.role !== 'ASE'">
            <button mat-stroked-button color="accent" (click)="selectedClassForSummary = c">
              <mat-icon>auto_awesome</mat-icon> AI Summary & Studio
            </button>
            <button mat-stroked-button color="primary" (click)="openAttendanceModal(c)">
              <mat-icon>checklist</mat-icon> Attendance
            </button>
            <button mat-icon-button color="warn" (click)="deleteClass(c)" matTooltip="Delete Class">
              <mat-icon>delete_outline</mat-icon>
            </button>
          </mat-card-actions>
        </mat-card>

        <div *ngIf="classes.length === 0" class="empty-card full-span">
          <mat-icon class="empty-icon">videocam_off</mat-icon>
          <h3>No Live Classes Scheduled</h3>
          <p>Scheduled live sessions with mentors will appear here.</p>
        </div>
      </div>

      <!-- Schedule Modal -->
      <div class="modal-backdrop" *ngIf="showScheduleModal">
        <div class="modal-content">
          <div class="modal-header">
            <h2>Schedule Live Coaching Session</h2>
            <button mat-icon-button (click)="showScheduleModal = false"><mat-icon>close</mat-icon></button>
          </div>
          <div class="modal-body">
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Session Title</mat-label>
              <input matInput [(ngModel)]="newClass.title" placeholder="e.g. System Architecture & gRPC Deep-Dive">
            </mat-form-field>

            <div class="form-row">
              <mat-form-field appearance="outline" class="half-width">
                <mat-label>Date & Time (Local)</mat-label>
                <input matInput type="datetime-local" [(ngModel)]="tempStartTime">
              </mat-form-field>

              <mat-form-field appearance="outline" class="half-width">
                <mat-label>Duration (Minutes)</mat-label>
                <input matInput type="number" [(ngModel)]="newClass.duration_minutes" min="15" step="15">
              </mat-form-field>
            </div>

            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Target Audience</mat-label>
              <mat-select [(ngModel)]="newClass.audience_type">
                <mat-option value="COHORT">Entire Cohort</mat-option>
                <mat-option value="ALL">All Active ASEs</mat-option>
              </mat-select>
            </mat-form-field>

            <mat-form-field appearance="outline" class="full-width" *ngIf="newClass.audience_type === 'COHORT'">
              <mat-label>Select Cohort</mat-label>
              <mat-select [(ngModel)]="newClass.cohort_id">
                <mat-option *ngFor="let co of cohorts" [value]="co.id">{{ co.name }}</mat-option>
              </mat-select>
            </mat-form-field>

            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Meeting Link (Microsoft Teams / Zoom / Google Meet)</mat-label>
              <input matInput [(ngModel)]="newClass.meeting_link" placeholder="https://teams.microsoft.com/l/meetup-join/...">
              <mat-hint>Must be a secure https:// link from authorized meeting domains</mat-hint>
            </mat-form-field>

            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Agenda / Description</mat-label>
              <textarea matInput rows="3" [(ngModel)]="newClass.description" placeholder="Topics to cover..."></textarea>
            </mat-form-field>
          </div>
          <div class="modal-footer">
            <button mat-button (click)="showScheduleModal = false">Cancel</button>
            <button mat-raised-button color="primary" (click)="saveClass()" [disabled]="!newClass.title || !newClass.meeting_link || !tempStartTime">
              Confirm & Notify Attendees
            </button>
          </div>
        </div>
      </div>

      <!-- Attendance Modal -->
      <div class="modal-backdrop" *ngIf="showAttendanceModal && selectedClass">
        <div class="modal-content">
          <div class="modal-header">
            <h2>Mark Attendance: {{ selectedClass.title }}</h2>
            <button mat-icon-button (click)="showAttendanceModal = false"><mat-icon>close</mat-icon></button>
          </div>
          <div class="modal-body">
            <div class="attendance-top-bar">
              <p class="text-muted">Total Invited Engineers: <strong>{{ attendeeList.length }}</strong></p>
              <button mat-stroked-button color="accent" (click)="fetchTeamsAttendance()" [disabled]="teamsPreviewLoading">
                <mat-icon>cloud_download</mat-icon> {{ teamsPreviewLoading ? 'Fetching Teams Report...' : 'Import Teams Attendance' }}
              </button>
            </div>

            <!-- Teams Attendance Preview Section -->
            <div class="teams-preview-box" *ngIf="teamsPreviewData">
              <div class="preview-header">
                <h4><mat-icon>groups</mat-icon> Teams Attendance Report Preview</h4>
                <span class="preview-counts">Matched: {{ teamsPreviewData.matched_count }} / Total in report: {{ teamsPreviewData.total_attendees_in_report }}</span>
              </div>
              <p class="preview-notice"><mat-icon>info</mat-icon> {{ teamsPreviewData.notice }}</p>

              <div class="preview-table">
                <div class="preview-row" *ngFor="let rec of teamsPreviewData.records">
                  <div class="preview-info">
                    <strong>{{ rec.display_name }} ({{ rec.email }})</strong>
                    <span class="duration-tag">Duration: {{ rec.duration_seconds }}s</span>
                  </div>
                  <div class="preview-match">
                    <span class="badge" [class.badge-success]="rec.match_status === 'EXACT_MATCH'" [class.badge-warn]="rec.match_status === 'UNMATCHED'">
                      {{ rec.match_status }}
                    </span>
                    <span class="suggested-status">Suggested: {{ rec.suggested_status }}</span>
                  </div>
                </div>
              </div>

              <div class="preview-actions">
                <button mat-flat-button color="primary" (click)="applyTeamsImport()">
                  <mat-icon>check_circle</mat-icon> Confirm & Apply Suggested Attendance
                </button>
                <button mat-button (click)="teamsPreviewData = null">Dismiss</button>
              </div>
            </div>

            <div class="attendees-table">
              <div class="attendee-row" *ngFor="let a of attendeeList">
                <div class="attendee-info">
                  <strong>{{ a.ase_name }}</strong>
                  <span>{{ a.ase_email }}</span>
                </div>
                <div class="attendance-radios">
                  <button mat-stroked-button 
                          [class.btn-present]="a.status === 'ATTENDED'" 
                          (click)="a.status = 'ATTENDED'">
                    <mat-icon>check</mat-icon> Present
                  </button>
                  <button mat-stroked-button 
                          [class.btn-absent]="a.status === 'ABSENT'" 
                          (click)="a.status = 'ABSENT'">
                    <mat-icon>close</mat-icon> Absent
                  </button>
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button mat-button (click)="showAttendanceModal = false">Cancel</button>
            <button mat-raised-button color="primary" (click)="saveAttendance()">
              Save Attendance
            </button>
          </div>
        </div>
      </div>

      <!-- Phase 8: AI Class Summary & Assessment Studio Dialog -->
      <app-class-summary-dialog
        *ngIf="selectedClassForSummary"
        [liveClass]="selectedClassForSummary"
        (close)="selectedClassForSummary = null"
        (scheduleMiniClass)="handleScheduleMiniClass($event)">
      </app-class-summary-dialog>

    </div>
  `,
  styles: [`
    .classes-page {
      display: flex;
      flex-direction: column;
      gap: 24px;
      padding-bottom: 40px;
    }

    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
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

    .classes-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
      gap: 20px;
    }

    .class-card {
      border-radius: 12px;
      border: 1px solid #E2E8F0;
      background: #ffffff;
      padding: 16px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    .badges-row {
      display: flex;
      gap: 8px;
      margin-bottom: 8px;
    }

    .provider-badge {
      font-size: 0.72rem;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 6px;
      background: #EFF6FF;
      color: var(--csm-primary);
      text-transform: uppercase;
    }

    .audience-badge {
      font-size: 0.72rem;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 6px;
      background: #F1F5F9;
      color: #475569;
    }

    .class-title {
      font-size: 1.2rem;
      font-weight: 700;
      color: #0F172A;
    }

    .card-body {
      margin: 12px 0;
      font-size: 0.9rem;
      color: #475569;
    }

    .stats-row {
      display: flex;
      gap: 12px;
      margin: 12px 0;
    }

    .stat-chip {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 0.8rem;
      color: #64748B;
    }

    .stat-chip.success {
      color: #059669;
      font-weight: 600;
    }

    .stat-chip mat-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
    }

    .join-row {
      margin-top: 16px;
    }

    .join-btn {
      width: 100%;
    }

    .card-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-top: 1px solid #F1F5F9;
      padding-top: 12px;
    }

    .empty-card {
      text-align: center;
      padding: 60px 20px;
      background: #ffffff;
      border-radius: 16px;
      border: 1px solid #E2E8F0;
    }

    .full-span {
      grid-column: 1 / -1;
    }

    .empty-icon {
      font-size: 56px;
      width: 56px;
      height: 56px;
      color: #94A3B8;
    }

    /* Modal Backdrop */
    .modal-backdrop {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(15, 23, 42, 0.6);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      backdrop-filter: blur(4px);
    }

    .modal-content {
      background: #ffffff;
      border-radius: 16px;
      width: 90%;
      max-width: 540px;
      max-height: 90vh;
      display: flex;
      flex-direction: column;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
    }

    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 20px;
      border-bottom: 1px solid #E2E8F0;
    }

    .modal-header h2 {
      margin: 0;
      font-size: 1.25rem;
      color: #0F172A;
    }

    .modal-body {
      padding: 20px;
      overflow-y: auto;
    }

    .modal-footer {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      padding: 16px 20px;
      border-top: 1px solid #E2E8F0;
    }

    .full-width { width: 100%; margin-bottom: 12px; }
    .form-row { display: flex; gap: 12px; }
    .half-width { flex: 1; }

    .attendance-top-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }

    .teams-preview-box {
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      border-radius: 8px;
      padding: 14px;
      margin-bottom: 16px;

      .preview-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        h4 { margin: 0; color: var(--csm-primary); display: flex; align-items: center; gap: 6px; font-size: 0.95rem; }
        .preview-counts { font-size: 0.8rem; font-weight: 600; color: #3b82f6; }
      }

      .preview-notice {
        font-size: 0.75rem;
        color: #64748b;
        margin: 6px 0 12px;
        display: flex;
        align-items: center;
        gap: 4px;
        mat-icon { font-size: 16px; width: 16px; height: 16px; }
      }

      .preview-table {
        display: flex;
        flex-direction: column;
        gap: 6px;
        max-height: 200px;
        overflow-y: auto;
        margin-bottom: 12px;
      }

      .preview-row {
        background: #ffffff;
        border: 1px solid #dbeafe;
        border-radius: 6px;
        padding: 8px 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;

        .preview-info {
          display: flex;
          flex-direction: column;
          strong { font-size: 0.82rem; color: #1e293b; }
          .duration-tag { font-size: 0.72rem; color: #64748b; }
        }

        .preview-match {
          display: flex;
          align-items: center;
          gap: 8px;

          .badge {
            font-size: 0.7rem;
            font-weight: 600;
            padding: 2px 6px;
            border-radius: 4px;
            &.badge-success { background: #dcfce7; color: #166534; }
            &.badge-warn { background: #fef3c7; color: #92400e; }
          }
          .suggested-status { font-size: 0.75rem; color: #475569; }
        }
      }

      .preview-actions {
        display: flex;
        gap: 8px;
        align-items: center;
      }
    }

    /* Attendance */
    .attendees-table {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-top: 12px;
    }

    .attendee-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 10px 14px;
      background: #F8FAFC;
      border-radius: 8px;
      border: 1px solid #E2E8F0;
    }

    .attendee-info {
      display: flex;
      flex-direction: column;
    }

    .attendee-info strong {
      font-size: 0.9rem;
      color: #0F172A;
    }

    .attendee-info span {
      font-size: 0.78rem;
      color: #64748B;
    }

    .attendance-radios {
      display: flex;
      gap: 8px;
    }

    .btn-present {
      background: #ECFDF5 !important;
      color: #065F46 !important;
      border-color: #A7F3D0 !important;
    }

    .btn-absent {
      background: #FEE2E2 !important;
      color: #991B1B !important;
      border-color: #FCA5A5 !important;
    }
  `]
})
export class LiveClassListComponent implements OnInit {
  classes: LiveClassItem[] = [];
  cohorts: CohortItem[] = [];
  loading = true;

  showScheduleModal = false;
  showAttendanceModal = false;
  selectedClass: LiveClassItem | null = null;
  selectedClassForSummary: LiveClassItem | null = null;
  attendeeList: AttendeeItem[] = [];
  teamsPreviewLoading = false;
  teamsPreviewData: any = null;

  tempStartTime = '';
  newClass = {
    title: '',
    description: '',
    duration_minutes: 60,
    audience_type: 'COHORT' as 'ALL' | 'COHORT' | 'SELECTED',
    cohort_id: undefined as number | undefined,
    meeting_link: '',
    provider: 'MANUAL' as 'MANUAL' | 'TEAMS_GRAPH'
  };

  constructor(
    private liveClassService: LiveClassService,
    private cohortService: CohortService,
    public authService: AuthService
  ) {}

  ngOnInit(): void {
    this.loadClasses();
    this.loadCohorts();
  }

  loadClasses(): void {
    this.loading = true;
    this.liveClassService.listLiveClasses().subscribe({
      next: (list) => {
        this.classes = list;
        this.loading = false;
      },
      error: (err) => {
        console.error('Failed to load live classes', err);
        this.loading = false;
      }
    });
  }

  loadCohorts(): void {
    this.cohortService.listCohorts().subscribe({
      next: (list) => {
        this.cohorts = list;
        if (list.length > 0) {
          this.newClass.cohort_id = list[0].id;
        }
      },
      error: (err) => console.error('Failed to load cohorts', err)
    });
  }

  openScheduleModal(): void {
    this.newClass = {
      title: '',
      description: '',
      duration_minutes: 60,
      audience_type: 'COHORT',
      cohort_id: this.cohorts.length > 0 ? this.cohorts[0].id : undefined,
      meeting_link: '',
      provider: 'MANUAL'
    };
    this.tempStartTime = '';
    this.showScheduleModal = true;
  }

  saveClass(): void {
    const startUtcIso = new Date(this.tempStartTime).toISOString();
    this.liveClassService.scheduleClass({
      title: this.newClass.title,
      description: this.newClass.description,
      start_time: startUtcIso,
      duration_minutes: this.newClass.duration_minutes,
      audience_type: this.newClass.audience_type,
      cohort_id: this.newClass.cohort_id,
      meeting_link: this.newClass.meeting_link,
      provider: this.newClass.provider
    }).subscribe({
      next: (created) => {
        this.classes.unshift(created);
        this.showScheduleModal = false;
      },
      error: (err) => {
        alert(err.error?.detail || 'Failed to schedule class');
      }
    });
  }

  deleteClass(c: LiveClassItem): void {
    if (confirm(`Cancel and delete live class '${c.title}'?`)) {
      this.liveClassService.deleteClass(c.id).subscribe({
        next: () => {
          this.classes = this.classes.filter(item => item.id !== c.id);
        },
        error: (err) => console.error('Failed to delete class', err)
      });
    }
  }

  openAttendanceModal(c: LiveClassItem): void {
    this.selectedClass = c;
    this.teamsPreviewData = null;
    this.liveClassService.getClassAttendance(c.id).subscribe({
      next: (attendees) => {
        this.attendeeList = attendees;
        this.showAttendanceModal = true;
      },
      error: (err) => console.error('Failed to load attendance', err)
    });
  }

  fetchTeamsAttendance(): void {
    if (!this.selectedClass) return;
    this.teamsPreviewLoading = true;
    this.liveClassService.previewTeamsAttendance(this.selectedClass.id).subscribe({
      next: (data) => {
        this.teamsPreviewLoading = false;
        this.teamsPreviewData = data;
      },
      error: (err) => {
        this.teamsPreviewLoading = false;
        alert(err.error?.detail || 'Failed to fetch Teams attendance report.');
      }
    });
  }

  applyTeamsImport(): void {
    if (!this.selectedClass || !this.teamsPreviewData) return;
    const mappings: { ase_id: number; status: string }[] = [];
    for (const rec of this.teamsPreviewData.records) {
      if (rec.matched_ase_id && (rec.suggested_status === 'ATTENDED' || rec.suggested_status === 'ABSENT')) {
        mappings.push({
          ase_id: rec.matched_ase_id,
          status: rec.suggested_status
        });
      }
    }

    if (mappings.length === 0) {
      alert('No matched attendees found to confirm.');
      return;
    }

    this.liveClassService.confirmTeamsAttendance(this.selectedClass.id, {
      import_id: this.teamsPreviewData.import_id,
      mappings: mappings
    }).subscribe({
      next: (res) => {
        alert(`Successfully imported Teams attendance! Updated ${res.updated_attendees_count} record(s).`);
        this.teamsPreviewData = null;
        this.openAttendanceModal(this.selectedClass!); // reload attendance
        this.loadClasses();
      },
      error: (err) => alert(err.error?.detail || 'Failed to confirm Teams attendance.')
    });
  }

  handleScheduleMiniClass(event: { title: string; duration: number }): void {
    this.newClass = {
      title: event.title,
      description: 'Follow-up interactive session targeting missed concepts and knowledge gaps identified by AI class analytics.',
      duration_minutes: event.duration || 15,
      audience_type: 'COHORT',
      cohort_id: this.cohorts.length > 0 ? this.cohorts[0].id : undefined,
      meeting_link: '',
      provider: 'MANUAL'
    };
    this.tempStartTime = '';
    this.showScheduleModal = true;
  }

  saveAttendance(): void {
    if (!this.selectedClass) return;
    this.liveClassService.markAttendance(this.selectedClass.id, {
      attendances: this.attendeeList.map(a => ({ ase_id: a.ase_id, status: a.status }))
    }).subscribe({
      next: () => {
        this.showAttendanceModal = false;
        this.loadClasses(); // Refresh counts
      },
      error: (err) => alert(err.error?.detail || 'Failed to save attendance')
    });
  }
}
