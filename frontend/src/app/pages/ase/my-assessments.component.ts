import { Component, OnInit, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatTabsModule } from '@angular/material/tabs';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { AssessmentService } from '../../core/services/assessment.service';
import { AssessmentAssignmentItem } from '../../core/models/assessment.model';

@Component({
  selector: 'app-ase-assessments',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatTabsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule
  ],
  template: `
    <div class="my-assessments-page">
      <div class="page-header">
        <div>
          <h1>My Assessments</h1>
          <p>Access your assigned evaluations, track progress, and review competency reports</p>
        </div>
      </div>

      @if (isLoading()) {
        <div class="loading-state">
          <mat-spinner diameter="36"></mat-spinner>
          <span>Loading your assessments...</span>
        </div>
      } @else {
        <mat-tab-group animationDuration="200ms" class="custom-tabs card-shadow">
          <!-- Active Tab -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon class="tab-icon">play_circle</mat-icon>
              <span>Active ({{ activeAssessments().length }})</span>
            </ng-template>

            <div class="tab-content">
              @if (activeAssessments().length === 0) {
                <div class="empty-state">
                  <mat-icon>assignment_turned_in</mat-icon>
                  <h3>No active assessments right now</h3>
                  <p>You have no evaluations waiting for your attempt.</p>
                </div>
              } @else {
                <div class="assessments-grid">
                  @for (a of activeAssessments(); track a.id) {
                    <div class="assessment-card card-shadow">
                      <div class="card-head">
                        <span class="badge badge-type">{{ a.assessment_type }}</span>
                        @if (a.webcam_mode === 'REQUIRED') {
                          <span class="badge badge-webcam" title="Webcam required for this assessment">
                            <mat-icon class="badge-icon">videocam</mat-icon> Webcam Required
                          </span>
                        }
                        <span class="badge badge-active">Available</span>
                      </div>

                      <h3 class="card-title">{{ a.assessment_title }}</h3>

                      <div class="meta-list">
                        <div class="meta-item">
                          <mat-icon>timer</mat-icon>
                          <span>Duration: {{ a.total_duration_minutes }} minutes</span>
                        </div>
                        <div class="meta-item">
                          <mat-icon>check_circle</mat-icon>
                          <span>Passing Requirement: {{ a.passing_percentage }}%</span>
                        </div>
                        <div class="meta-item">
                          <mat-icon>event</mat-icon>
                          <span>Deadline: {{ a.end_date | date:'medium' }}</span>
                        </div>
                      </div>

                      <div class="card-actions">
                        <a
                          mat-flat-button
                          class="btn-primary start-btn"
                          [routerLink]="['/ase/exam', a.id]"
                        >
                          <mat-icon>{{ a.attempt_status === 'IN_PROGRESS' ? 'replay' : 'play_arrow' }}</mat-icon>
                          {{ a.attempt_status === 'IN_PROGRESS' ? 'Resume Assessment' : 'Start Assessment' }}
                        </a>
                      </div>
                    </div>
                  }
                </div>
              }
            </div>
          </mat-tab>

          <!-- Upcoming Tab -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon class="tab-icon">schedule</mat-icon>
              <span>Upcoming ({{ upcomingAssessments().length }})</span>
            </ng-template>

            <div class="tab-content">
              @if (upcomingAssessments().length === 0) {
                <div class="empty-state">
                  <mat-icon>event_busy</mat-icon>
                  <h3>No upcoming assessments scheduled</h3>
                  <p>Check back later or contact your mentor.</p>
                </div>
              } @else {
                <div class="assessments-grid">
                  @for (a of upcomingAssessments(); track a.id) {
                    <div class="assessment-card card-shadow upcoming-card">
                      <div class="card-head">
                        <span class="badge badge-type">{{ a.assessment_type }}</span>
                        <span class="badge badge-upcoming">Upcoming</span>
                      </div>

                      <h3 class="card-title">{{ a.assessment_title }}</h3>

                      <div class="meta-list">
                        <div class="meta-item">
                          <mat-icon>timer</mat-icon>
                          <span>Duration: {{ a.total_duration_minutes }} minutes</span>
                        </div>
                        <div class="meta-item">
                          <mat-icon>event_available</mat-icon>
                          <span>Starts: {{ a.start_date | date:'medium' }}</span>
                        </div>
                        <div class="meta-item">
                          <mat-icon>event</mat-icon>
                          <span>Ends: {{ a.end_date | date:'medium' }}</span>
                        </div>
                      </div>

                      <div class="card-actions">
                        <button mat-stroked-button disabled>
                          <mat-icon>lock</mat-icon> Opens Soon
                        </button>
                      </div>
                    </div>
                  }
                </div>
              }
            </div>
          </mat-tab>

          <!-- Completed Tab -->
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon class="tab-icon">task_alt</mat-icon>
              <span>Completed ({{ completedAssessments().length }})</span>
            </ng-template>

            <div class="tab-content">
              @if (completedAssessments().length === 0) {
                <div class="empty-state">
                  <mat-icon>quiz</mat-icon>
                  <h3>No completed assessments yet</h3>
                  <p>Attempt active assessments to see your results and skill analytics here.</p>
                </div>
              } @else {
                <div class="assessments-grid">
                  @for (a of completedAssessments(); track a.id) {
                    <div class="assessment-card card-shadow completed-card">
                      <div class="card-head">
                        <span class="badge badge-type">{{ a.assessment_type }}</span>
                        <span class="badge" [ngClass]="a.passed ? 'badge-pass' : 'badge-fail'">
                          {{ a.passed ? 'PASSED' : 'FAILED' }}
                        </span>
                      </div>

                      <h3 class="card-title">{{ a.assessment_title }}</h3>

                      <div class="score-banner">
                        <div class="score-col">
                          <span class="score-val">{{ a.total_score }} / {{ a.max_score }}</span>
                          <span class="score-lbl">Score</span>
                        </div>
                        <div class="score-col">
                          <span class="score-val" [style.color]="a.passed ? '#15803d' : '#b91c1c'">
                            {{ a.percentage }}%
                          </span>
                          <span class="score-lbl">Percentage</span>
                        </div>
                      </div>

                      <div class="card-actions">
                        @if (a.attempt_id) {
                          <a
                            mat-flat-button
                            class="btn-primary view-res-btn"
                            [routerLink]="['/ase/result', a.attempt_id]"
                          >
                            <mat-icon>insights</mat-icon> View Skill Analytics
                          </a>
                        }
                      </div>
                    </div>
                  }
                </div>
              }
            </div>
          </mat-tab>
        </mat-tab-group>
      }
    </div>
  `,
  styles: [`
    .my-assessments-page {
      display: flex;
      flex-direction: column;
      gap: 24px;
    }

    .page-header {
      h1 {
        font-size: 1.6rem;
        font-weight: 700;
        margin: 0;
        color: #0f172a;
      }
      p {
        margin: 4px 0 0;
        color: var(--text-muted);
        font-size: 0.9rem;
      }
    }

    .custom-tabs {
      background: #ffffff;
      border-radius: 12px;
      overflow: hidden;

      .tab-icon {
        margin-right: 8px;
        font-size: 20px;
        width: 20px;
        height: 20px;
      }
    }

    .tab-content {
      padding: 24px;
    }

    .assessments-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 20px;
    }

    .assessment-card {
      background: #ffffff;
      border-radius: 12px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      border: 1px solid var(--border-light);

      .card-head {
        display: flex;
        justify-content: space-between;
        align-items: center;

        .badge-type {
          background: #eff6ff;
          color: var(--csm-primary);
          font-size: 0.75rem;
          padding: 3px 8px;
          border-radius: 4px;
        }

        .badge-active {
          background: #dcfce7;
          color: #166534;
        }

        .badge-webcam {
          background: #fee2e2;
          color: #dc2626;
          font-size: 0.72rem;
          padding: 2px 6px;
          border-radius: 4px;
          font-weight: 700;
          display: inline-flex;
          align-items: center;
          gap: 4px;

          .badge-icon {
            font-size: 13px;
            width: 13px;
            height: 13px;
          }
        }

        .badge-upcoming {
          background: #f1f5f9;
          color: #475569;
        }

        .badge-pass {
          background: #dcfce7;
          color: #15803d;
          font-weight: 700;
        }

        .badge-fail {
          background: #fee2e2;
          color: #b91c1c;
          font-weight: 700;
        }
      }

      .card-title {
        margin: 0;
        font-size: 1.1rem;
        font-weight: 700;
        color: #0f172a;
        line-height: 1.35;
      }

      .meta-list {
        display: flex;
        flex-direction: column;
        gap: 8px;

        .meta-item {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 0.82rem;
          color: var(--text-muted);

          mat-icon {
            font-size: 16px;
            width: 16px;
            height: 16px;
            color: #94a3b8;
          }
        }
      }

      .score-banner {
        display: flex;
        gap: 20px;
        padding: 12px 16px;
        background: #f8fafc;
        border-radius: 8px;

        .score-col {
          display: flex;
          flex-direction: column;

          .score-val {
            font-size: 1.25rem;
            font-weight: 700;
          }

          .score-lbl {
            font-size: 0.72rem;
            color: var(--text-muted);
            text-transform: uppercase;
          }
        }
      }

      .card-actions {
        margin-top: auto;
        padding-top: 8px;

        .start-btn, .view-res-btn {
          width: 100%;
          border-radius: 8px;
          height: 42px;
        }
      }
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 64px 20px;
      color: var(--text-muted);

      mat-icon {
        font-size: 48px;
        width: 48px;
        height: 48px;
        opacity: 0.5;
        margin-bottom: 12px;
      }

      h3 {
        margin: 0;
        font-size: 1.1rem;
        color: #0f172a;
      }

      p {
        margin: 4px 0 0;
        font-size: 0.85rem;
      }
    }

    .loading-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 80px 0;
      color: var(--text-muted);
      gap: 16px;
    }
  `]
})
export class AseAssessmentsComponent implements OnInit {
  assignments = signal<AssessmentAssignmentItem[]>([]);
  isLoading = signal(true);

  private assessmentService = inject(AssessmentService);

  activeAssessments = computed(() =>
    this.assignments().filter(a => a.status === 'ACTIVE')
  );

  upcomingAssessments = computed(() =>
    this.assignments().filter(a => a.status === 'UPCOMING')
  );

  completedAssessments = computed(() =>
    this.assignments().filter(a => a.status === 'COMPLETED' || a.attempt_status === 'SUBMITTED' || a.attempt_status === 'AUTO_SUBMITTED')
  );

  ngOnInit(): void {
    this.loadAssignments();
  }

  loadAssignments(): void {
    this.isLoading.set(true);
    this.assessmentService.getMyAssessments().subscribe({
      next: (res) => {
        this.assignments.set(res);
        this.isLoading.set(false);
      },
      error: () => this.isLoading.set(false)
    });
  }
}
