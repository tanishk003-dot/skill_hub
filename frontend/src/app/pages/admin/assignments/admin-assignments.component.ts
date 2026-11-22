import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatCardModule } from '@angular/material/card';
import { AssignmentService } from '../../../core/services/assignment.service';
import { UserService } from '../../../core/services/user.service';
import { MentorAseAssignment, User } from '../../../core/models/user.model';

@Component({
  selector: 'app-admin-assignments',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatSelectModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    MatCardModule
  ],
  template: `
    <div class="assignments-page">
      <div class="page-header">
        <div>
          <h1>Mentor - ASE Mapping</h1>
          <p>Pair Associate Engineers (ASE) with Mentors for structured guidance</p>
        </div>
      </div>

      <!-- Quick Assignment Card -->
      <div class="assignment-builder-card card-shadow">
        <div class="builder-header">
          <mat-icon>add_link</mat-icon>
          <h3>Create or Update Assignment</h3>
        </div>
        <p class="builder-desc">Select an active Mentor and an ASE. Each ASE can have exactly one primary Mentor.</p>

        <div class="builder-form">
          <mat-form-field appearance="outline" class="select-field">
            <mat-label>Select Mentor</mat-label>
            <mat-select [(ngModel)]="selectedMentorId">
              @for (m of mentors(); track m.id) {
                <mat-option [value]="m.id">
                  {{ m.name }} ({{ m.email }})
                </mat-option>
              }
            </mat-select>
            <mat-icon matPrefix>psychology</mat-icon>
          </mat-form-field>

          <mat-icon class="arrow-separator">arrow_forward</mat-icon>

          <mat-form-field appearance="outline" class="select-field">
            <mat-label>Select ASE (Associate Engineer)</mat-label>
            <mat-select [(ngModel)]="selectedAseId">
              @for (a of ases(); track a.id) {
                <mat-option [value]="a.id">
                  {{ a.name }} @if (a.assigned_mentor_name) { [Current: {{ a.assigned_mentor_name }}] }
                </mat-option>
              }
            </mat-select>
            <mat-icon matPrefix>engineering</mat-icon>
          </mat-form-field>

          <button
            mat-flat-button
            class="btn-accent assign-btn"
            [disabled]="!selectedMentorId || !selectedAseId || isAssigning()"
            (click)="onAssign()"
          >
            Assign Now
          </button>
        </div>
      </div>

      <!-- Current Assignments Table -->
      <div class="table-container card-shadow">
        <div class="table-header">
          <h3>Active Assignments ({{ assignments().length }})</h3>
        </div>

        @if (isLoading()) {
          <div class="loading-state">
            <mat-spinner diameter="36"></mat-spinner>
            <span>Loading assignments...</span>
          </div>
        } @else if (assignments().length === 0) {
          <div class="empty-state">
            <mat-icon>link_off</mat-icon>
            <h3>No assignments yet</h3>
            <p>Use the form above to assign an ASE to a Mentor.</p>
          </div>
        } @else {
          <table mat-table [dataSource]="assignments()" class="assignments-table">
            <ng-container matColumnDef="mentor">
              <th mat-header-cell *matHeaderCellDef>Assigned Mentor</th>
              <td mat-cell *matCellDef="let a">
                <div class="user-block mentor">
                  <mat-icon>psychology</mat-icon>
                  <div>
                    <span class="name">{{ a.mentor_name }}</span>
                    <span class="email">{{ a.mentor_email }}</span>
                  </div>
                </div>
              </td>
            </ng-container>

            <ng-container matColumnDef="arrow">
              <th mat-header-cell *matHeaderCellDef class="text-center"></th>
              <td mat-cell *matCellDef="let a" class="text-center">
                <mat-icon class="link-icon">arrow_forward</mat-icon>
              </td>
            </ng-container>

            <ng-container matColumnDef="ase">
              <th mat-header-cell *matHeaderCellDef>Associate Engineer (ASE)</th>
              <td mat-cell *matCellDef="let a">
                <div class="user-block ase">
                  <mat-icon>engineering</mat-icon>
                  <div>
                    <span class="name">{{ a.ase_name }}</span>
                    <span class="email">{{ a.ase_email }}</span>
                  </div>
                </div>
              </td>
            </ng-container>

            <ng-container matColumnDef="assigned_at">
              <th mat-header-cell *matHeaderCellDef>Assigned Date</th>
              <td mat-cell *matCellDef="let a">
                {{ a.assigned_at | date:'mediumDate' }}
              </td>
            </ng-container>

            <ng-container matColumnDef="actions">
              <th mat-header-cell *matHeaderCellDef class="text-right">Action</th>
              <td mat-cell *matCellDef="let a" class="text-right">
                <button
                  mat-stroked-button
                  color="warn"
                  (click)="unassign(a)"
                  class="unassign-btn"
                >
                  <mat-icon>link_off</mat-icon> Unassign
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
    .assignments-page {
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

    .assignment-builder-card {
      padding: 24px;
      background: #ffffff;
      border-radius: 12px;

      .builder-header {
        display: flex;
        align-items: center;
        gap: 8px;
        color: var(--csm-primary);

        mat-icon {
          font-size: 24px;
        }

        h3 {
          margin: 0;
          font-size: 1.15rem;
          font-weight: 600;
          color: #0f172a;
        }
      }

      .builder-desc {
        margin: 6px 0 20px;
        font-size: 0.85rem;
        color: var(--text-muted);
      }

      .builder-form {
        display: flex;
        align-items: center;
        gap: 16px;
        flex-wrap: wrap;

        .select-field {
          flex: 1;
          min-width: 260px;
        }

        .arrow-separator {
          color: var(--text-muted);
          font-size: 22px;
        }

        .assign-btn {
          height: 54px;
          padding: 0 24px;
          margin-bottom: 22px;
        }
      }
    }

    .table-container {
      background: #ffffff;
      border-radius: 12px;
      overflow-x: auto;

      .table-header {
        padding: 20px 24px 12px;
        h3 {
          margin: 0;
          font-size: 1.1rem;
          font-weight: 600;
          color: #0f172a;
        }
      }
    }

    .assignments-table {
      width: 100%;

      th {
        font-weight: 600;
        color: var(--text-secondary);
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding: 16px;
      }

      td {
        padding: 12px 16px;
      }

      .text-center { text-align: center; }
      .text-right { text-align: right; }

      .link-icon {
        color: #94a3b8;
        font-size: 20px;
      }
    }

    .user-block {
      display: flex;
      align-items: center;
      gap: 10px;

      mat-icon {
        font-size: 24px;
        width: 24px;
        height: 24px;
      }

      &.mentor mat-icon { color: #2563eb; }
      &.ase mat-icon { color: #ea580c; }

      div {
        display: flex;
        flex-direction: column;

        .name {
          font-weight: 600;
          font-size: 0.9rem;
          color: #0f172a;
        }

        .email {
          font-size: 0.78rem;
          color: var(--text-muted);
        }
      }
    }

    .unassign-btn {
      font-size: 0.8rem;
      border-radius: 6px;
    }

    .loading-state, .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 48px 20px;
      color: var(--text-muted);

      mat-icon {
        font-size: 44px;
        width: 44px;
        height: 44px;
        margin-bottom: 8px;
        opacity: 0.5;
      }

      h3 {
        margin: 0;
        font-size: 1.05rem;
        color: #0f172a;
      }

      p {
        margin: 4px 0 0;
        font-size: 0.85rem;
      }
    }
  `]
})
export class AdminAssignmentsComponent implements OnInit {
  assignments = signal<MentorAseAssignment[]>([]);
  mentors = signal<User[]>([]);
  ases = signal<User[]>([]);
  isLoading = signal(true);
  isAssigning = signal(false);

  selectedMentorId: number | null = null;
  selectedAseId: number | null = null;

  displayedColumns = ['mentor', 'arrow', 'ase', 'assigned_at', 'actions'];

  constructor(
    private assignmentService: AssignmentService,
    private userService: UserService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.isLoading.set(true);
    this.assignmentService.getAssignments().subscribe({
      next: (res) => {
        this.assignments.set(res);
        this.isLoading.set(false);
      },
      error: () => this.isLoading.set(false)
    });

    // Load active mentors and ases for dropdowns
    this.userService.getUsers('MENTOR', false).subscribe(m => this.mentors.set(m));
    this.userService.getUsers('ASE', false).subscribe(a => this.ases.set(a));
  }

  onAssign(): void {
    if (!this.selectedMentorId || !this.selectedAseId) return;

    this.isAssigning.set(true);
    this.assignmentService.assignAseToMentor(this.selectedMentorId, this.selectedAseId).subscribe({
      next: (assignment) => {
        this.isAssigning.set(false);
        this.snackBar.open(`Assigned '${assignment.ase_name}' to '${assignment.mentor_name}'`, 'Close', {
          duration: 3500,
          panelClass: ['snack-success']
        });
        this.selectedAseId = null;
        this.loadData();
      },
      error: (err) => {
        this.isAssigning.set(false);
        const detail = err.error?.detail || 'Assignment failed';
        this.snackBar.open(detail, 'Close', { duration: 4000, panelClass: ['snack-error'] });
      }
    });
  }

  unassign(assignment: MentorAseAssignment): void {
    if (confirm(`Unassign '${assignment.ase_name}' from mentor '${assignment.mentor_name}'?`)) {
      this.assignmentService.deleteAssignment(assignment.id).subscribe({
        next: () => {
          this.snackBar.open('Mapping unassigned successfully', 'Close', {
            duration: 3500,
            panelClass: ['snack-success']
          });
          this.loadData();
        },
        error: (err) => {
          const detail = err.error?.detail || 'Failed to unassign';
          this.snackBar.open(detail, 'Close', { duration: 4000, panelClass: ['snack-error'] });
        }
      });
    }
  }
}
