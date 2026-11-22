import { Component, Inject, OnInit, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatRadioModule } from '@angular/material/radio';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { AssessmentService } from '../../../core/services/assessment.service';
import { UserService } from '../../../core/services/user.service';
import { CohortService } from '../../../core/services/cohort.service';
import { AssessmentItem } from '../../../core/models/assessment.model';
import { User } from '../../../core/models/user.model';
import { CohortItem } from '../../../core/models/cohort.model';

export interface AssignDialogData {
  assessment: AssessmentItem;
}

@Component({
  selector: 'app-assign-assessment-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatRadioModule,
    MatCheckboxModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    MatSnackBarModule
  ],
  template: `
    <div class="assign-dialog">
      <h2 mat-dialog-title>
        <mat-icon>assignment_ind</mat-icon> Assign Assessment: {{ data.assessment.title }}
      </h2>

      <mat-dialog-content>
        <div class="dialog-body">
          <!-- Target Selection -->
          <div class="target-select">
            <span class="sec-label">Assign To:</span>
            <div class="radio-row">
              <label class="radio-opt">
                <input type="radio" name="target" value="ALL" [(ngModel)]="target" />
                <span>All Active Associate Engineers (ASEs)</span>
              </label>
              <label class="radio-opt">
                <input type="radio" name="target" value="COHORT" [(ngModel)]="target" />
                <span>An Entire Cohort / Batch</span>
              </label>
              <label class="radio-opt">
                <input type="radio" name="target" value="SELECTED" [(ngModel)]="target" />
                <span>Selected Associate Engineers</span>
              </label>
            </div>
          </div>

          <!-- Cohort Select (if COHORT) -->
          @if (target === 'COHORT') {
            <mat-form-field appearance="outline" class="w-100">
              <mat-label>Select Cohort / Batch</mat-label>
              <mat-select [(ngModel)]="selectedCohortId">
                @for (c of cohorts(); track c.id) {
                  <mat-option [value]="c.id">{{ c.name }} ({{ c.member_count }} ASEs)</mat-option>
                }
              </mat-select>
            </mat-form-field>
          }

          <!-- ASE Search & Select (if SELECTED) -->
          @if (target === 'SELECTED') {
            <div class="ase-picker card-shadow">
              <div class="search-wrap">
                <mat-icon>search</mat-icon>
                <input
                  type="text"
                  [(ngModel)]="searchAseQuery"
                  placeholder="Filter ASEs by name or email..."
                />
              </div>

              <div class="ase-list">
                @for (ase of filteredAses(); track ase.id) {
                  <label class="ase-item" [class.checked]="selectedAseIds.includes(ase.id)">
                    <input
                      type="checkbox"
                      [checked]="selectedAseIds.includes(ase.id)"
                      (change)="toggleAse(ase.id, $event)"
                    />
                    <div class="ase-info">
                      <span class="name">{{ ase.name }}</span>
                      <span class="email">{{ ase.email }}</span>
                    </div>
                  </label>
                }
              </div>
              <div class="selection-footer">
                <span>{{ selectedAseIds.length }} ASEs selected</span>
              </div>
            </div>
          }

          <!-- Date-Time Range -->
          <div class="date-row">
            <mat-form-field appearance="outline" class="flex-1">
              <mat-label>Start Date & Time (Local)</mat-label>
              <input matInput type="datetime-local" [(ngModel)]="startDateTimeStr" />
            </mat-form-field>

            <mat-form-field appearance="outline" class="flex-1">
              <mat-label>End Date & Time (Deadline)</mat-label>
              <input matInput type="datetime-local" [(ngModel)]="endDateTimeStr" />
            </mat-form-field>
          </div>
        </div>
      </mat-dialog-content>

      <mat-dialog-actions align="end">
        <button mat-button mat-dialog-close>Cancel</button>
        <button
          mat-flat-button
          class="btn-primary"
          [disabled]="isAssigning() || (target === 'SELECTED' && selectedAseIds.length === 0) || (target === 'COHORT' && !selectedCohortId)"
          (click)="onAssign()"
        >
          Confirm Assignment
        </button>
      </mat-dialog-actions>
    </div>
  `,
  styles: [`
    .assign-dialog { min-width: 540px; padding: 12px; }
    h2 { display: flex; align-items: center; gap: 8px; color: var(--csm-primary); font-weight: 700; margin: 0; }
    .dialog-body { display: flex; flex-direction: column; gap: 16px; padding-top: 16px; }
    .sec-label { font-size: 0.85rem; font-weight: 700; color: #0f172a; text-transform: uppercase; }

    .radio-row { display: flex; flex-direction: column; gap: 8px; margin-top: 6px;
      .radio-opt { display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 0.9rem; }
    }

    .ase-picker {
      border: 1px solid var(--border-light);
      border-radius: 8px;
      padding: 12px;

      .search-wrap {
        display: flex;
        align-items: center;
        gap: 8px;
        background: #f1f5f9;
        padding: 6px 12px;
        border-radius: 6px;
        margin-bottom: 10px;
        mat-icon { font-size: 18px; color: var(--text-muted); }
        input { border: none; background: transparent; outline: none; width: 100%; font-size: 0.85rem; }
      }

      .ase-list {
        max-height: 180px;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        gap: 6px;

        .ase-item {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 6px 10px;
          border-radius: 6px;
          cursor: pointer;
          &:hover { background: #f8fafc; }
          &.checked { background: #eff6ff; }

          .ase-info {
            display: flex;
            flex-direction: column;
            .name { font-size: 0.88rem; font-weight: 600; }
            .email { font-size: 0.78rem; color: var(--text-muted); }
          }
        }
      }

      .selection-footer {
        padding-top: 8px;
        border-top: 1px solid var(--border-light);
        font-size: 0.75rem;
        color: var(--text-muted);
        text-align: right;
      }
    }

    .date-row { display: flex; gap: 12px; }
    .flex-1 { flex: 1; margin-bottom: -1.25em; }
  `]
})
export class AdminAssignAssessmentDialogComponent implements OnInit {
  target: 'ALL' | 'SELECTED' | 'COHORT' = 'ALL';
  selectedAseIds: number[] = [];
  selectedCohortId: number | null = null;
  ases = signal<User[]>([]);
  cohorts = signal<CohortItem[]>([]);
  searchAseQuery = '';
  startDateTimeStr = '';
  endDateTimeStr = '';
  isAssigning = signal(false);

  private userService = inject(UserService);
  private cohortService = inject(CohortService);
  private assessmentService = inject(AssessmentService);
  private snackBar = inject(MatSnackBar);

  filteredAses = computed(() => {
    const q = this.searchAseQuery.trim().toLowerCase();
    return this.ases().filter(a => !q || a.name.toLowerCase().includes(q) || a.email.toLowerCase().includes(q));
  });

  constructor(
    public dialogRef: MatDialogRef<AdminAssignAssessmentDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: AssignDialogData
  ) {
    // Default start = now, end = 7 days from now
    const now = new Date();
    const future = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);
    this.startDateTimeStr = this.formatDateForInput(now);
    this.endDateTimeStr = this.formatDateForInput(future);
  }

  ngOnInit(): void {
    this.userService.getUsers('ASE', false).subscribe(res => this.ases.set(res));
    this.cohortService.listCohorts().subscribe(res => this.cohorts.set(res));
  }

  private formatDateForInput(d: Date): string {
    const pad = (n: number) => n.toString().padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  toggleAse(id: number, event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    if (checked) {
      if (!this.selectedAseIds.includes(id)) this.selectedAseIds.push(id);
    } else {
      this.selectedAseIds = this.selectedAseIds.filter(i => i !== id);
    }
  }

  onAssign(): void {
    const startDate = new Date(this.startDateTimeStr).toISOString();
    const endDate = new Date(this.endDateTimeStr).toISOString();

    if (new Date(endDate) <= new Date(startDate)) {
      this.snackBar.open('End date must be after start date', 'OK', { duration: 3000, panelClass: ['snack-error'] });
      return;
    }

    this.isAssigning.set(true);
    this.assessmentService.assignAssessment({
      assessment_id: this.data.assessment.id,
      target: this.target,
      ase_ids: this.target === 'SELECTED' ? this.selectedAseIds : undefined,
      cohort_id: this.target === 'COHORT' && this.selectedCohortId ? this.selectedCohortId : undefined,
      start_date: startDate,
      end_date: endDate
    }).subscribe({
      next: (assignments) => {
        this.isAssigning.set(false);
        this.snackBar.open(`Assigned to ${assignments.length} ASE(s) successfully!`, 'Close', { duration: 3500, panelClass: ['snack-success'] });
        this.dialogRef.close(true);
      },
      error: (err) => {
        this.isAssigning.set(false);
        const detail = err.error?.detail || 'Assignment failed';
        this.snackBar.open(detail, 'Close', { duration: 4000, panelClass: ['snack-error'] });
      }
    });
  }
}
