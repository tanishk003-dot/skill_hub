import { Component, OnInit, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { AssessmentService } from '../../core/services/assessment.service';
import { AssessmentAssignmentItem } from '../../core/models/assessment.model';

@Component({
  selector: 'app-mentor-mentee-results',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    FormsModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule
  ],
  template: `
    <div class="results-page">
      <div class="page-header">
        <div>
          <h1>Mentees Assessment Reports</h1>
          <p>Review comprehensive scorecards, skill radar profiles, and section breakdowns for your assigned ASEs</p>
        </div>
      </div>

      <!-- Search & Filters -->
      <div class="filter-card card-shadow">
        <div class="search-box">
          <mat-icon>search</mat-icon>
          <input
            type="text"
            [(ngModel)]="searchQuery"
            placeholder="Search by mentee name, email, or assessment title..."
          />
        </div>
      </div>

      <!-- Table of Results -->
      <div class="table-container card-shadow">
        @if (isLoading()) {
          <div class="loading-state">
            <mat-spinner diameter="36"></mat-spinner>
            <span>Loading assessment records...</span>
          </div>
        } @else if (filteredAssignments().length === 0) {
          <div class="empty-state">
            <mat-icon>assignment_turned_in</mat-icon>
            <h3>No assessment records found</h3>
            <p>Your mentees have not attempted any evaluations matching your criteria.</p>
          </div>
        } @else {
          <table mat-table [dataSource]="filteredAssignments()" class="results-table">
            <ng-container matColumnDef="mentee">
              <th mat-header-cell *matHeaderCellDef>Associate Engineer</th>
              <td mat-cell *matCellDef="let a">
                <div class="user-block">
                  <div class="avatar-sm">{{ a.ase_name[0] }}</div>
                  <div>
                    <span class="name">{{ a.ase_name }}</span>
                    <span class="email">{{ a.ase_email }}</span>
                  </div>
                </div>
              </td>
            </ng-container>

            <ng-container matColumnDef="assessment">
              <th mat-header-cell *matHeaderCellDef>Assessment</th>
              <td mat-cell *matCellDef="let a">
                <div class="assessment-info">
                  <span class="title">{{ a.assessment_title }}</span>
                  <span class="badge badge-type">{{ a.assessment_type }}</span>
                </div>
              </td>
            </ng-container>

            <ng-container matColumnDef="status">
              <th mat-header-cell *matHeaderCellDef>Status</th>
              <td mat-cell *matCellDef="let a">
                @if (a.attempt_status === 'SUBMITTED' || a.attempt_status === 'AUTO_SUBMITTED') {
                  <span class="badge" [ngClass]="a.passed ? 'badge-pass' : 'badge-fail'">
                    {{ a.passed ? 'PASSED' : 'FAILED' }} ({{ a.percentage }}%)
                  </span>
                } @else if (a.attempt_status === 'IN_PROGRESS') {
                  <span class="badge badge-progress">In Progress</span>
                } @else {
                  <span class="badge badge-unattempted">{{ a.status }}</span>
                }
              </td>
            </ng-container>

            <ng-container matColumnDef="score">
              <th mat-header-cell *matHeaderCellDef>Score</th>
              <td mat-cell *matCellDef="let a">
                @if (a.total_score !== null && a.total_score !== undefined) {
                  <strong>{{ a.total_score }} / {{ a.max_score }}</strong>
                } @else {
                  <span class="dash">—</span>
                }
              </td>
            </ng-container>

            <ng-container matColumnDef="actions">
              <th mat-header-cell *matHeaderCellDef class="text-right">Analytics</th>
              <td mat-cell *matCellDef="let a" class="text-right">
                @if (a.attempt_id && (a.attempt_status === 'SUBMITTED' || a.attempt_status === 'AUTO_SUBMITTED')) {
                  <a
                    mat-flat-button
                    class="btn-primary report-btn"
                    [routerLink]="['/mentor/results', a.attempt_id]"
                  >
                    <mat-icon>insights</mat-icon> View Analytics
                  </a>
                } @else {
                  <span class="dash">Awaiting Attempt</span>
                }
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
    .results-page { display: flex; flex-direction: column; gap: 24px; }
    .page-header {
      h1 { margin: 0; font-size: 1.6rem; font-weight: 700; color: #0f172a; }
      p { margin: 4px 0 0; color: var(--text-muted); font-size: 0.9rem; }
    }
    .filter-card {
      background: #ffffff;
      padding: 16px 20px;
      border-radius: 12px;

      .search-box {
        display: flex;
        align-items: center;
        gap: 10px;
        background-color: var(--bg-main);
        padding: 8px 16px;
        border-radius: 8px;
        border: 1px solid var(--border-light);

        mat-icon { color: var(--text-muted); font-size: 20px; }
        input { border: none; background: transparent; outline: none; width: 100%; font-size: 0.9rem; }
      }
    }

    .table-container { background: #ffffff; border-radius: 12px; overflow-x: auto; }
    .results-table { width: 100%;
      th { font-weight: 600; color: var(--text-secondary); font-size: 0.8rem; text-transform: uppercase; padding: 16px; }
      td { padding: 14px 16px; }
      .text-right { text-align: right; }
    }

    .user-block {
      display: flex;
      align-items: center;
      gap: 12px;

      .avatar-sm {
        width: 34px;
        height: 34px;
        border-radius: 50%;
        background-color: var(--csm-accent);
        color: #ffffff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 0.85rem;
      }

      .name { font-weight: 600; font-size: 0.92rem; color: #0f172a; display: block; }
      .email { font-size: 0.78rem; color: var(--text-muted); }
    }

    .assessment-info {
      display: flex;
      flex-direction: column;
      gap: 4px;

      .title { font-weight: 600; font-size: 0.92rem; color: #0f172a; }
      .badge-type { background: #eff6ff; color: var(--csm-primary); font-size: 0.72rem; padding: 2px 6px; border-radius: 4px; display: inline-block; width: fit-content; }
    }

    .badge-pass { background: #dcfce7; color: #15803d; font-weight: 700; }
    .badge-fail { background: #fee2e2; color: #b91c1c; font-weight: 700; }
    .badge-progress { background: #fef3c7; color: #b45309; }
    .badge-unattempted { background: #f1f5f9; color: #64748b; }

    .report-btn {
      height: 34px;
      font-size: 0.8rem;
      padding: 0 14px;
    }

    .dash { color: var(--text-muted); font-size: 0.85rem; }

    .loading-state, .empty-state {
      display: flex; flex-direction: column; align-items: center; padding: 64px 20px; color: var(--text-muted);
      mat-icon { font-size: 48px; width: 48px; height: 48px; opacity: 0.5; margin-bottom: 8px; }
      h3 { margin: 0; color: #0f172a; }
      p { margin: 4px 0 0; }
    }
  `]
})
export class MentorMenteeResultsComponent implements OnInit {
  assignments = signal<AssessmentAssignmentItem[]>([]);
  isLoading = signal(true);
  searchQuery = '';
  displayedColumns = ['mentee', 'assessment', 'status', 'score', 'actions'];

  private assessmentService = inject(AssessmentService);

  filteredAssignments = computed(() => {
    const q = this.searchQuery.trim().toLowerCase();
    return this.assignments().filter(a =>
      !q ||
      a.ase_name.toLowerCase().includes(q) ||
      a.ase_email.toLowerCase().includes(q) ||
      a.assessment_title.toLowerCase().includes(q)
    );
  });

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.isLoading.set(true);
    this.assessmentService.getAllAssignments().subscribe({
      next: (res) => {
        this.assignments.set(res);
        this.isLoading.set(false);
      },
      error: () => this.isLoading.set(false)
    });
  }
}
