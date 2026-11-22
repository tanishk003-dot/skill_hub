import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { AssessmentService } from '../../../core/services/assessment.service';
import { AssessmentItem } from '../../../core/models/assessment.model';
import { AdminAssignAssessmentDialogComponent } from './assign-assessment-dialog.component';

@Component({
  selector: 'app-admin-assessments',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatDialogModule,
    MatSnackBarModule,
    MatProgressSpinnerModule
  ],
  template: `
    <div class="assessments-admin-page">
      <div class="page-header">
        <div>
          <h1>Assessments Management</h1>
          <p>Design multi-section technical evaluations, configure question banks, and assign to ASEs</p>
        </div>
        <div class="header-btns">
          <a mat-stroked-button routerLink="/admin/assessments/question-bank">
            <mat-icon>quiz</mat-icon> Question Bank
          </a>
          <a mat-flat-button class="btn-primary" routerLink="/admin/assessments/create">
            <mat-icon>add</mat-icon> Create Assessment
          </a>
        </div>
      </div>

      <!-- Assessments Table -->
      <div class="table-container card-shadow">
        @if (isLoading()) {
          <div class="loading-state">
            <mat-spinner diameter="36"></mat-spinner>
            <span>Loading assessments...</span>
          </div>
        } @else if (assessments().length === 0) {
          <div class="empty-state">
            <mat-icon>assignment</mat-icon>
            <h3>No assessments created yet</h3>
            <p>Click "Create Assessment" above to build your first evaluation.</p>
          </div>
        } @else {
          <table mat-table [dataSource]="assessments()" class="assessments-table">
            <ng-container matColumnDef="id">
              <th mat-header-cell *matHeaderCellDef>#</th>
              <td mat-cell *matCellDef="let a">{{ a.id }}</td>
            </ng-container>

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

            <ng-container matColumnDef="created_at">
              <th mat-header-cell *matHeaderCellDef>Created</th>
              <td mat-cell *matCellDef="let a">
                {{ a.created_at | date:'mediumDate' }}
              </td>
            </ng-container>

            <ng-container matColumnDef="actions">
              <th mat-header-cell *matHeaderCellDef class="text-right">Actions</th>
              <td mat-cell *matCellDef="let a" class="text-right">
                <button
                  mat-flat-button
                  class="btn-accent btn-sm"
                  (click)="openAssignDialog(a)"
                >
                  <mat-icon>assignment_ind</mat-icon> Assign
                </button>
                <button mat-icon-button color="warn" (click)="deleteAssessment(a)">
                  <mat-icon>delete_outline</mat-icon>
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
    .assessments-admin-page { display: flex; flex-direction: column; gap: 24px; }
    .page-header { display: flex; justify-content: space-between; align-items: center;
      h1 { margin: 0; font-size: 1.6rem; font-weight: 700; color: #0f172a; }
      p { margin: 4px 0 0; color: var(--text-muted); font-size: 0.9rem; }
      .header-btns { display: flex; gap: 12px; }
    }

    .table-container { background: #ffffff; border-radius: 12px; overflow-x: auto; }
    .assessments-table { width: 100%;
      th { font-weight: 600; color: var(--text-secondary); font-size: 0.8rem; text-transform: uppercase; padding: 16px; }
      td { padding: 14px 16px; }
      .text-right { text-align: right; }
    }

    .title-cell {
      display: flex;
      flex-direction: column;
      gap: 4px;

      .title { font-weight: 600; font-size: 0.95rem; color: #0f172a; }
      .meta-row {
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 0.78rem;
        color: var(--text-muted);

        .badge-type { background: #eff6ff; color: var(--csm-primary); font-size: 0.72rem; padding: 2px 6px; border-radius: 4px; }
      }
    }

    .structure-badge {
      font-size: 0.82rem;
      color: #334155;
      font-weight: 500;
    }

    .btn-sm {
      height: 34px;
      font-size: 0.8rem;
      padding: 0 12px;
      margin-right: 6px;
    }

    .loading-state, .empty-state {
      display: flex; flex-direction: column; align-items: center; padding: 64px 20px; color: var(--text-muted);
      mat-icon { font-size: 48px; width: 48px; height: 48px; opacity: 0.5; margin-bottom: 8px; }
      h3 { margin: 0; color: #0f172a; }
      p { margin: 4px 0 0; }
    }
  `]
})
export class AdminAssessmentsComponent implements OnInit {
  assessments = signal<AssessmentItem[]>([]);
  isLoading = signal(true);
  displayedColumns = ['id', 'title', 'structure', 'created_at', 'actions'];

  private assessmentService = inject(AssessmentService);
  private dialog = inject(MatDialog);
  private snackBar = inject(MatSnackBar);

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
    const dialogRef = this.dialog.open(AdminAssignAssessmentDialogComponent, {
      data: { assessment }
    });
    dialogRef.afterClosed().subscribe((res) => {
      if (res) {
        this.loadAssessments();
      }
    });
  }

  deleteAssessment(a: AssessmentItem): void {
    if (confirm(`Delete assessment '${a.title}'? All sections and mappings will be removed.`)) {
      this.assessmentService.deleteAssessment(a.id).subscribe({
        next: () => {
          this.snackBar.open('Assessment deleted', 'Close', { duration: 3000, panelClass: ['snack-success'] });
          this.loadAssessments();
        },
        error: (err) => {
          const detail = err.error?.detail || 'Failed to delete assessment';
          this.snackBar.open(detail, 'Close', { duration: 4000, panelClass: ['snack-error'] });
        }
      });
    }
  }
}
