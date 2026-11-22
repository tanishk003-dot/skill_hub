import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { AssessmentService } from '../../core/services/assessment.service';
import { AssessmentItem } from '../../core/models/assessment.model';
import { AdminAssignAssessmentDialogComponent } from '../admin/assessments/assign-assessment-dialog.component';

@Component({
  selector: 'app-mentor-assessments',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatDialogModule,
    MatSnackBarModule,
    MatProgressSpinnerModule
  ],
  template: `
    <div class="mentor-assessments-page">
      <div class="page-header">
        <div>
          <h1>Assessments Directory</h1>
          <p>Assign technical and psychometric evaluations to your Associate Engineers (ASEs)</p>
        </div>
      </div>

      <!-- Table -->
      <div class="table-container card-shadow">
        @if (isLoading()) {
          <div class="loading-state">
            <mat-spinner diameter="36"></mat-spinner>
            <span>Loading assessment catalog...</span>
          </div>
        } @else if (assessments().length === 0) {
          <div class="empty-state">
            <mat-icon>quiz</mat-icon>
            <h3>No assessments available</h3>
            <p>Platform administrators have not published any assessments yet.</p>
          </div>
        } @else {
          <table mat-table [dataSource]="assessments()" class="assessments-table">
            <ng-container matColumnDef="title">
              <th mat-header-cell *matHeaderCellDef>Assessment Title</th>
              <td mat-cell *matCellDef="let a">
                <div class="title-cell">
                  <span class="title">{{ a.title }}</span>
                  <div class="meta-row">
                    <span class="badge badge-type">{{ a.type }}</span>
                    <span>{{ a.total_duration_minutes }} mins</span>
                    <span>Passing: {{ a.passing_percentage }}%</span>
                  </div>
                </div>
              </td>
            </ng-container>

            <ng-container matColumnDef="structure">
              <th mat-header-cell *matHeaderCellDef>Structure</th>
              <td mat-cell *matCellDef="let a">
                <span class="structure-badge">
                  {{ a.total_sections }} sections • {{ a.total_questions }} Qs • {{ a.total_marks }} marks
                </span>
              </td>
            </ng-container>

            <ng-container matColumnDef="actions">
              <th mat-header-cell *matHeaderCellDef class="text-right">Action</th>
              <td mat-cell *matCellDef="let a" class="text-right">
                <button
                  mat-flat-button
                  class="btn-primary"
                  (click)="openAssignDialog(a)"
                >
                  <mat-icon>assignment_ind</mat-icon> Assign to Mentees
                </button>
              </td>
            </ng-container>

            <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
            <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
          </table>
        }
      </div>
    </div>
  `,
  styles: [`
    .mentor-assessments-page { display: flex; flex-direction: column; gap: 24px; }
    .page-header {
      h1 { margin: 0; font-size: 1.6rem; font-weight: 700; color: #0f172a; }
      p { margin: 4px 0 0; color: var(--text-muted); font-size: 0.9rem; }
    }
    .table-container { background: #ffffff; border-radius: 12px; overflow-x: auto; }
    .assessments-table { width: 100%;
      th { font-weight: 600; color: var(--text-secondary); font-size: 0.8rem; text-transform: uppercase; padding: 16px; }
      td { padding: 14px 16px; }
      .text-right { text-align: right; }
    }
    .title-cell {
      display: flex; flex-direction: column; gap: 4px;
      .title { font-weight: 600; font-size: 0.95rem; color: #0f172a; }
      .meta-row { display: flex; align-items: center; gap: 10px; font-size: 0.78rem; color: var(--text-muted);
        .badge-type { background: #eff6ff; color: var(--csm-primary); font-size: 0.72rem; padding: 2px 6px; border-radius: 4px; }
      }
    }
    .structure-badge { font-size: 0.82rem; color: #334155; font-weight: 500; }
    .loading-state, .empty-state {
      display: flex; flex-direction: column; align-items: center; padding: 64px 20px; color: var(--text-muted);
      mat-icon { font-size: 48px; width: 48px; height: 48px; opacity: 0.5; margin-bottom: 8px; }
      h3 { margin: 0; color: #0f172a; }
      p { margin: 4px 0 0; }
    }
  `]
})
export class MentorAssessmentsComponent implements OnInit {
  assessments = signal<AssessmentItem[]>([]);
  isLoading = signal(true);
  displayedColumns = ['title', 'structure', 'actions'];

  private assessmentService = inject(AssessmentService);
  private dialog = inject(MatDialog);

  ngOnInit(): void {
    this.loadAssessments();
  }

  loadAssessments(): void {
    this.isLoading.set(true);
    this.assessmentService.getAssessments().subscribe({
      next: (res) => {
        this.assessments.set(res);
        this.isLoading.set(false);
      },
      error: () => this.isLoading.set(false)
    });
  }

  openAssignDialog(assessment: AssessmentItem): void {
    this.dialog.open(AdminAssignAssessmentDialogComponent, {
      data: { assessment }
    });
  }
}
