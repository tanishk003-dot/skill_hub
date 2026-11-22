import { Component, OnInit, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatChipsModule } from '@angular/material/chips';
import { CohortService } from '../../../core/services/cohort.service';
import { AnalyticsService } from '../../../core/services/analytics.service';
import { AuthService } from '../../../core/services/auth.service';
import { CohortItem, ASESearchItem } from '../../../core/models/cohort.model';

@Component({
  selector: 'app-cohort-list',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatChipsModule
  ],
  template: `
    <div class="cohorts-page">
      <div class="page-header">
        <div>
          <h1>Cohorts & Batches Management</h1>
          <p>Organize, track, and assign evaluations across engineering trainee cohorts</p>
        </div>
        <button mat-flat-button class="btn-primary" (click)="openCreateModal()">
          <mat-icon>add</mat-icon> Create New Cohort
        </button>
      </div>

      <!-- Cohorts Grid -->
      @if (isLoading()) {
        <div class="loading-state">
          <mat-spinner diameter="36"></mat-spinner>
          <span>Loading batches & cohorts...</span>
        </div>
      } @else if (cohorts().length === 0) {
        <div class="empty-card card-shadow">
          <mat-icon>groups</mat-icon>
          <h3>No Cohorts Available</h3>
          <p>Get started by creating your first cohort to organize ASEs and track aggregate performance.</p>
          <button mat-flat-button class="btn-primary" (click)="openCreateModal()">Create Cohort</button>
        </div>
      } @else {
        <div class="cohorts-grid">
          @for (c of cohorts(); track c.id) {
            <div class="cohort-card card-shadow">
              <div class="card-top">
                <div class="cohort-title-wrap">
                  <span class="badge badge-cohort">Batch</span>
                  <h3>{{ c.name }}</h3>
                </div>
                <div class="actions-wrap">
                  <button mat-icon-button (click)="exportCsv(c)" title="Export Cohort Results (CSV)">
                    <mat-icon class="icon-download">download</mat-icon>
                  </button>
                  <button mat-icon-button color="warn" (click)="deleteCohort(c)" title="Delete Cohort">
                    <mat-icon>delete_outline</mat-icon>
                  </button>
                </div>
              </div>

              <p class="cohort-desc">{{ c.description || 'No batch description provided.' }}</p>

              <div class="cohort-meta">
                <span><mat-icon>event</mat-icon> Started: {{ c.start_date | date:'mediumDate' }}</span>
                <span><mat-icon>people</mat-icon> {{ c.member_count }} {{ c.member_count === 1 ? 'ASE' : 'ASEs' }}</span>
              </div>

              <div class="card-bottom">
                <button mat-stroked-button color="primary" (click)="openManageMembersModal(c)">
                  <mat-icon>group_add</mat-icon> Manage Members ({{ c.member_count }})
                </button>
              </div>
            </div>
          }
        </div>
      }

      <!-- Create Cohort Modal -->
      @if (showCreateModal()) {
        <div class="modal-backdrop" (click)="closeCreateModal()">
          <div class="modal-card card-shadow" (click)="$event.stopPropagation()">
            <div class="modal-header">
              <h3>Create New Cohort</h3>
              <button mat-icon-button (click)="closeCreateModal()"><mat-icon>close</mat-icon></button>
            </div>
            <div class="modal-body">
              <mat-form-field appearance="outline" class="w-100">
                <mat-label>Cohort / Batch Name</mat-label>
                <input matInput [(ngModel)]="newCohortName" placeholder="e.g. Alpha Engineering Cohort 2026" />
              </mat-form-field>

              <mat-form-field appearance="outline" class="w-100">
                <mat-label>Start Date</mat-label>
                <input matInput type="date" [(ngModel)]="newCohortStartDate" />
              </mat-form-field>

              <mat-form-field appearance="outline" class="w-100">
                <mat-label>Description (Optional)</mat-label>
                <textarea matInput [(ngModel)]="newCohortDesc" rows="3" placeholder="Describe the cohort's focus or curriculum"></textarea>
              </mat-form-field>
            </div>
            <div class="modal-actions">
              <button mat-button (click)="closeCreateModal()">Cancel</button>
              <button mat-flat-button class="btn-primary" [disabled]="!newCohortName.trim() || !newCohortStartDate" (click)="submitCreateCohort()">
                Create Cohort
              </button>
            </div>
          </div>
        </div>
      }

      <!-- Manage Members Modal -->
      @if (selectedCohort()) {
        <div class="modal-backdrop" (click)="closeManageModal()">
          <div class="modal-card card-shadow modal-wide" (click)="$event.stopPropagation()">
            <div class="modal-header">
              <div>
                <h3>Manage Cohort Members: {{ selectedCohort()?.name }}</h3>
                <p class="sub-text">An ASE belongs to one cohort at a time. Add available candidates below.</p>
              </div>
              <button mat-icon-button (click)="closeManageModal()"><mat-icon>close</mat-icon></button>
            </div>

            <div class="modal-body">
              <!-- Add Member Section -->
              <div class="add-member-bar">
                <mat-form-field appearance="outline" class="flex-1">
                  <mat-label>Search & Select ASE to Add</mat-label>
                  <mat-select [(ngModel)]="selectedAseToAdd">
                    @for (ase of availableAses(); track ase.id) {
                      <mat-option [value]="ase.id">
                        {{ ase.name }} ({{ ase.email }}) @if (ase.cohort_name) { [Currently: {{ ase.cohort_name }}] }
                      </mat-option>
                    }
                  </mat-select>
                </mat-form-field>
                <button mat-flat-button class="btn-primary" [disabled]="!selectedAseToAdd" (click)="addSelectedAse()">
                  <mat-icon>person_add</mat-icon> Add to Cohort
                </button>
              </div>

              <!-- Current Members Table -->
              <div class="members-list">
                <h4>Enrolled Associate Engineers ({{ cohortMembers().length }})</h4>
                @if (cohortMembers().length === 0) {
                  <p class="none-text">No ASEs enrolled in this cohort yet.</p>
                } @else {
                  <div class="member-items">
                    @for (m of cohortMembers(); track m.id) {
                      <div class="member-item">
                        <div class="mem-info">
                          <div class="avatar">{{ m.ase_name[0] }}</div>
                          <div>
                            <span class="m-name">{{ m.ase_name }}</span>
                            <span class="m-email">{{ m.ase_email }}</span>
                          </div>
                        </div>
                        <button mat-button color="warn" (click)="removeMember(m.ase_id)">
                          <mat-icon>remove_circle_outline</mat-icon> Remove
                        </button>
                      </div>
                    }
                  </div>
                }
              </div>
            </div>

            <div class="modal-actions">
              <button mat-flat-button class="btn-primary" (click)="closeManageModal()">Done</button>
            </div>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .cohorts-page {
      max-width: 1200px;
      margin: 0 auto;
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

      h1 { margin: 0; font-size: 1.6rem; color: var(--csm-primary); font-weight: 700; }
      p { margin: 4px 0 0; color: #64748B; font-size: 0.95rem; }
    }

    .btn-primary {
      background-color: var(--csm-primary) !important;
      color: #ffffff !important;
      font-weight: 600;
    }

    .loading-state, .empty-card {
      background: #ffffff;
      padding: 48px;
      border-radius: 12px;
      text-align: center;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;
      mat-icon { font-size: 48px; width: 48px; height: 48px; color: #94A3B8; }
      h3 { margin: 0; color: var(--csm-primary); }
      p { margin: 0; color: #64748B; max-width: 450px; }
    }

    .cohorts-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
      gap: 20px;
    }

    .cohort-card {
      background: #ffffff;
      padding: 24px;
      border-radius: 12px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 16px;
      border-top: 4px solid var(--csm-primary);

      .card-top {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;

        .cohort-title-wrap {
          h3 { margin: 6px 0 0; font-size: 1.2rem; color: #0f172a; font-weight: 700; }
        }

        .actions-wrap {
          display: flex;
          gap: 4px;
          .icon-download { color: var(--csm-primary); }
        }
      }

      .badge-cohort {
        background-color: #eff6ff;
        color: #1d4ed8;
        font-size: 0.72rem;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 4px;
      }

      .cohort-desc {
        color: #64748B;
        font-size: 0.9rem;
        line-height: 1.4;
        margin: 0;
        min-height: 40px;
      }

      .cohort-meta {
        display: flex;
        gap: 16px;
        font-size: 0.85rem;
        color: #475569;
        span {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          mat-icon { font-size: 18px; width: 18px; height: 18px; color: var(--csm-accent); }
        }
      }

      .card-bottom {
        padding-top: 12px;
        border-top: 1px solid #f1f5f9;
        button { width: 100%; font-weight: 600; }
      }
    }

    .modal-backdrop {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(15, 23, 42, 0.6);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      backdrop-filter: blur(3px);
    }

    .modal-card {
      background: #ffffff;
      border-radius: 14px;
      width: 90%;
      max-width: 500px;
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 18px;

      &.modal-wide {
        max-width: 650px;
      }

      .modal-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        h3 { margin: 0; font-size: 1.25rem; color: var(--csm-primary); font-weight: 700; }
        .sub-text { margin: 4px 0 0; font-size: 0.85rem; color: #64748B; }
      }

      .modal-actions {
        display: flex;
        justify-content: flex-end;
        gap: 12px;
        margin-top: 12px;
      }
    }

    .w-100 { width: 100%; }
    .flex-1 { flex: 1; }

    .add-member-bar {
      display: flex;
      gap: 12px;
      align-items: center;
      margin-bottom: 16px;
    }

    .members-list {
      h4 { margin: 0 0 12px; font-size: 0.95rem; color: #334155; }
      .member-items {
        max-height: 250px;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .member-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 12px;
        border-radius: 8px;
        background: #f8fafc;
        border: 1px solid #e2e8f0;

        .mem-info {
          display: flex;
          align-items: center;
          gap: 10px;

          .avatar {
            width: 32px; height: 32px;
            background: var(--csm-primary); color: #ffffff;
            border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-weight: 700; font-size: 0.85rem;
          }

          .m-name { font-weight: 600; font-size: 0.9rem; color: #0f172a; display: block; }
          .m-email { font-size: 0.78rem; color: #64748B; display: block; }
        }
      }
    }
  `]
})
export class CohortListComponent implements OnInit {
  cohorts = signal<CohortItem[]>([]);
  isLoading = signal(true);

  // Create Modal
  showCreateModal = signal(false);
  newCohortName = '';
  newCohortStartDate = '';
  newCohortDesc = '';

  // Manage Modal
  selectedCohort = signal<CohortItem | null>(null);
  cohortMembers = signal<any[]>([]);
  availableAses = signal<ASESearchItem[]>([]);
  selectedAseToAdd: number | null = null;

  private cohortService = inject(CohortService);
  private analyticsService = inject(AnalyticsService);
  private authService = inject(AuthService);
  private snackBar = inject(MatSnackBar);

  ngOnInit(): void {
    this.loadCohorts();
  }

  loadCohorts(): void {
    this.isLoading.set(true);
    this.cohortService.listCohorts().subscribe({
      next: (res) => {
        this.cohorts.set(res);
        this.isLoading.set(false);
      },
      error: () => {
        this.isLoading.set(false);
        this.snackBar.open('Failed to load cohorts', 'Close', { duration: 3000 });
      }
    });
  }

  openCreateModal(): void {
    this.newCohortName = '';
    this.newCohortStartDate = new Date().toISOString().split('T')[0];
    this.newCohortDesc = '';
    this.showCreateModal.set(true);
  }

  closeCreateModal(): void {
    this.showCreateModal.set(false);
  }

  submitCreateCohort(): void {
    if (!this.newCohortName.trim() || !this.newCohortStartDate) return;

    this.cohortService.createCohort({
      name: this.newCohortName.trim(),
      start_date: this.newCohortStartDate,
      description: this.newCohortDesc.trim() || undefined
    }).subscribe({
      next: (created) => {
        this.snackBar.open(`Cohort '${created.name}' created!`, 'OK', { duration: 3000 });
        this.closeCreateModal();
        this.loadCohorts();
      },
      error: (err) => {
        this.snackBar.open(err.error?.detail || 'Failed to create cohort', 'Close', { duration: 4000 });
      }
    });
  }

  openManageMembersModal(c: CohortItem): void {
    this.selectedCohort.set(c);
    this.selectedAseToAdd = null;
    this.cohortService.getCohort(c.id).subscribe({
      next: (full) => {
        this.cohortMembers.set(full.members || []);
      }
    });

    // Load available ASEs for adding
    this.cohortService.searchASEs({ page_size: 100 }).subscribe({
      next: (res) => {
        this.availableAses.set(res.items);
      }
    });
  }

  closeManageModal(): void {
    this.selectedCohort.set(null);
    this.loadCohorts();
  }

  addSelectedAse(): void {
    const c = this.selectedCohort();
    if (!c || !this.selectedAseToAdd) return;

    this.cohortService.addMembers(c.id, [this.selectedAseToAdd]).subscribe({
      next: (updated) => {
        this.cohortMembers.set(updated.members || []);
        this.selectedAseToAdd = null;
        this.snackBar.open('Member added successfully', 'OK', { duration: 2500 });
      },
      error: (err) => {
        this.snackBar.open(err.error?.detail || 'Failed to add member', 'Close', { duration: 3000 });
      }
    });
  }

  removeMember(aseId: number): void {
    const c = this.selectedCohort();
    if (!c) return;

    this.cohortService.removeMember(c.id, aseId).subscribe({
      next: () => {
        this.cohortMembers.set(this.cohortMembers().filter(m => m.ase_id !== aseId));
        this.snackBar.open('Member removed from cohort', 'OK', { duration: 2500 });
      },
      error: (err) => {
        this.snackBar.open(err.error?.detail || 'Failed to remove member', 'Close', { duration: 3000 });
      }
    });
  }

  deleteCohort(c: CohortItem): void {
    if (confirm(`Delete cohort '${c.name}'? This will unassign its members and assignments without deleting users or test results.`)) {
      this.cohortService.deleteCohort(c.id).subscribe({
        next: () => {
          this.snackBar.open(`Cohort '${c.name}' deleted`, 'OK', { duration: 3000 });
          this.loadCohorts();
        },
        error: (err) => {
          this.snackBar.open(err.error?.detail || 'Failed to delete cohort', 'Close', { duration: 3000 });
        }
      });
    }
  }

  exportCsv(c: CohortItem): void {
    this.analyticsService.downloadCohortCsv(c.id).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `cohort_${c.id}_${c.name.replace(/\\s+/g, '_')}_results.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
      },
      error: (err) => {
        this.snackBar.open(err.error?.detail || 'Failed to export CSV', 'Close', { duration: 3000 });
      }
    });
  }
}
