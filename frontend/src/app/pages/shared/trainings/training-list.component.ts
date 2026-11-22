import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TrainingService } from '../../../core/services/training.service';
import { CohortService } from '../../../core/services/cohort.service';
import { TrainingItem, SuggestedAseItem, ResourceItem } from '../../../core/models/training.model';
import { CohortItem } from '../../../core/models/cohort.model';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-training-list',
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
    MatChipsModule,
    MatProgressSpinnerModule,
    MatTooltipModule
  ],
  template: `
    <div class="trainings-admin-page">
      <!-- Header -->
      <div class="page-header">
        <div>
          <h1>Training & Upskilling Programs</h1>
          <p class="subtitle">Curate courses, workshops, and assign skill remediation modules to cohorts or individual engineers</p>
        </div>
        <button mat-raised-button color="primary" (click)="openCreateModal()">
          <mat-icon>add</mat-icon> Create Training
        </button>
      </div>

      <!-- Loading State -->
      <div *ngIf="loading" class="loading-state">
        <mat-spinner diameter="40"></mat-spinner>
        <span>Loading training programs...</span>
      </div>

      <!-- Training Cards Grid -->
      <div *ngIf="!loading" class="trainings-grid">
        <mat-card class="training-card" *ngFor="let t of trainings">
          <mat-card-header>
            <div class="card-badges">
              <span class="type-badge">{{ t.type }}</span>
              <span class="skill-badge">{{ t.skill_category }}</span>
            </div>
            <mat-card-title class="card-title">{{ t.title }}</mat-card-title>
            <mat-card-subtitle>{{ t.duration_hours }} hours estimated</mat-card-subtitle>
          </mat-card-header>

          <mat-card-content class="card-desc">
            <p>{{ t.description || 'No description provided.' }}</p>
            <div class="resources-chips" *ngIf="t.resources && t.resources.length > 0">
              <span class="res-chip" *ngFor="let r of t.resources">
                <mat-icon>{{ r.type === 'file' ? 'attach_file' : 'link' }}</mat-icon> {{ r.name }}
              </span>
            </div>
          </mat-card-content>

          <mat-card-actions class="card-actions">
            <button mat-flat-button color="accent" (click)="openAssignModal(t)">
              <mat-icon>person_add</mat-icon> Assign Training
            </button>
            <button mat-icon-button color="warn" (click)="deleteTraining(t)" matTooltip="Delete Training">
              <mat-icon>delete_outline</mat-icon>
            </button>
          </mat-card-actions>
        </mat-card>

        <div *ngIf="trainings.length === 0" class="empty-state full-span">
          <mat-icon class="empty-icon">school</mat-icon>
          <h3>No Training Programs Found</h3>
          <p>Create your first training course to start upskilling your engineers.</p>
        </div>
      </div>

      <!-- Create Training Modal -->
      <div class="modal-backdrop" *ngIf="showCreateModal">
        <div class="modal-content">
          <div class="modal-header">
            <h2>Create New Training Program</h2>
            <button mat-icon-button (click)="showCreateModal = false"><mat-icon>close</mat-icon></button>
          </div>
          <div class="modal-body">
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Training Title</mat-label>
              <input matInput [(ngModel)]="newTraining.title" placeholder="e.g. Advanced Distributed Systems">
            </mat-form-field>

            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Skill Category</mat-label>
              <input matInput [(ngModel)]="newTraining.skill_category" placeholder="e.g. System Architecture Logic">
            </mat-form-field>

            <div class="form-row">
              <mat-form-field appearance="outline" class="half-width">
                <mat-label>Type</mat-label>
                <mat-select [(ngModel)]="newTraining.type">
                  <mat-option value="Self-paced">Self-paced</mat-option>
                  <mat-option value="Workshop">Workshop</mat-option>
                  <mat-option value="Live class">Live class</mat-option>
                </mat-select>
              </mat-form-field>

              <mat-form-field appearance="outline" class="half-width">
                <mat-label>Duration (Hours)</mat-label>
                <input matInput type="number" [(ngModel)]="newTraining.duration_hours" min="0.5" step="0.5">
              </mat-form-field>
            </div>

            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Description</mat-label>
              <textarea matInput rows="3" [(ngModel)]="newTraining.description" placeholder="Summary of learning outcomes..."></textarea>
            </mat-form-field>

            <!-- Resources list -->
            <div class="resources-form">
              <h4>External Links or Resources</h4>
              <div class="add-resource-row">
                <mat-form-field appearance="outline" style="flex: 1;">
                  <mat-label>Resource Name</mat-label>
                  <input matInput [(ngModel)]="tempResourceName" placeholder="e.g. Documentation Guide">
                </mat-form-field>
                <mat-form-field appearance="outline" style="flex: 2;">
                  <mat-label>URL Link</mat-label>
                  <input matInput [(ngModel)]="tempResourceUrl" placeholder="https://...">
                </mat-form-field>
                <button mat-stroked-button color="primary" (click)="addResourceLink()">Add</button>
              </div>

              <div class="added-resources-list" *ngIf="newTraining.resources.length > 0">
                <div class="res-item" *ngFor="let r of newTraining.resources; let idx = index">
                  <span>{{ r.name }} ({{ r.url }})</span>
                  <button mat-icon-button color="warn" (click)="removeResource(idx)"><mat-icon>delete</mat-icon></button>
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button mat-button (click)="showCreateModal = false">Cancel</button>
            <button mat-raised-button color="primary" (click)="saveNewTraining()" [disabled]="!newTraining.title || !newTraining.skill_category">Save Training</button>
          </div>
        </div>
      </div>

      <!-- Assign Training Modal with Suggest ASEs Button -->
      <div class="modal-backdrop" *ngIf="showAssignModal && selectedTraining">
        <div class="modal-content">
          <div class="modal-header">
            <h2>Assign: {{ selectedTraining.title }}</h2>
            <button mat-icon-button (click)="showAssignModal = false"><mat-icon>close</mat-icon></button>
          </div>
          <div class="modal-body">
            <p class="text-muted">Target Skill: <strong>{{ selectedTraining.skill_category }}</strong></p>

            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Target Audience</mat-label>
              <mat-select [(ngModel)]="assignTarget">
                <mat-option value="ALL">All Active ASEs</mat-option>
                <mat-option value="COHORT">Entire Cohort</mat-option>
                <mat-option value="SELECTED">Selected Associate Engineers</mat-option>
              </mat-select>
            </mat-form-field>

            <mat-form-field appearance="outline" class="full-width" *ngIf="assignTarget === 'COHORT'">
              <mat-label>Select Cohort</mat-label>
              <mat-select [(ngModel)]="selectedCohortId">
                <mat-option *ngFor="let c of cohorts" [value]="c.id">{{ c.name }}</mat-option>
              </mat-select>
            </mat-form-field>

            <div class="suggest-box" *ngIf="assignTarget === 'SELECTED'">
              <div class="suggest-header">
                <div>
                  <strong>AI & Diagnostic Recommendations</strong>
                  <p>Auto-detect engineers who scored below 70% in assessments for {{ selectedTraining.skill_category }}</p>
                </div>
                <button mat-flat-button color="accent" (click)="suggestASEs()">
                  <mat-icon>psychology</mat-icon> Suggest ASEs
                </button>
              </div>

              <!-- Suggested Chips -->
              <div class="suggestions-list" *ngIf="suggestedAseList.length > 0">
                <div class="suggest-pill" *ngFor="let s of suggestedAseList" (click)="toggleAseSelection(s.ase_id)" [class.selected]="selectedAseIds.includes(s.ase_id)">
                  <mat-icon>{{ selectedAseIds.includes(s.ase_id) ? 'check_circle' : 'add_circle_outline' }}</mat-icon>
                  <span>{{ s.ase_name }} ({{ s.score_percentage | number:'1.0-0' }}%)</span>
                </div>
              </div>
            </div>

            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Completion Due Date</mat-label>
              <input matInput type="date" [(ngModel)]="dueDate">
            </mat-form-field>
          </div>
          <div class="modal-footer">
            <button mat-button (click)="showAssignModal = false">Cancel</button>
            <button mat-raised-button color="primary" (click)="submitAssignment()" [disabled]="assigning">
              {{ assigning ? 'Dispatching...' : 'Confirm Assignment' }}
            </button>
          </div>
        </div>
      </div>

    </div>
  `,
  styles: [`
    .trainings-admin-page {
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

    .trainings-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
      gap: 20px;
    }

    .training-card {
      border-radius: 12px;
      border: 1px solid #E2E8F0;
      background: #ffffff;
      padding: 16px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    .card-badges {
      display: flex;
      gap: 8px;
      margin-bottom: 8px;
    }

    .type-badge {
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      padding: 3px 8px;
      border-radius: 6px;
      background: #EFF6FF;
      color: var(--csm-primary);
    }

    .skill-badge {
      font-size: 0.72rem;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 6px;
      background: #F1F5F9;
      color: #475569;
    }

    .card-title {
      font-size: 1.15rem;
      font-weight: 700;
      color: #0F172A;
    }

    .card-desc {
      margin: 12px 0;
      color: #475569;
      font-size: 0.9rem;
      line-height: 1.4;
    }

    .resources-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 10px;
    }

    .res-chip {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      background: #F8FAFC;
      border: 1px solid #E2E8F0;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 0.75rem;
      color: #64748B;
    }

    .res-chip mat-icon {
      font-size: 14px;
      width: 14px;
      height: 14px;
    }

    .card-actions {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-top: 12px;
      border-top: 1px solid #F1F5F9;
    }

    .empty-state {
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
      max-width: 560px;
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

    .resources-form {
      background: #F8FAFC;
      padding: 12px;
      border-radius: 8px;
      margin-top: 12px;
    }

    .resources-form h4 {
      margin: 0 0 8px 0;
      font-size: 0.85rem;
      color: #475569;
    }

    .add-resource-row {
      display: flex;
      gap: 8px;
      align-items: center;
    }

    .added-resources-list {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-top: 8px;
    }

    .res-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #ffffff;
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 0.82rem;
      border: 1px solid #E2E8F0;
    }

    /* Suggest Box */
    .suggest-box {
      background: #FFFBEB;
      border: 1px solid #FCD34D;
      border-radius: 10px;
      padding: 14px;
      margin-bottom: 16px;
    }

    .suggest-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
      gap: 8px;
    }

    .suggest-header strong {
      color: #92400E;
      font-size: 0.95rem;
    }

    .suggest-header p {
      margin: 2px 0 0 0;
      font-size: 0.78rem;
      color: #78350F;
    }

    .suggestions-list {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .suggest-pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #ffffff;
      border: 1px solid #FCD34D;
      padding: 4px 10px;
      border-radius: 16px;
      font-size: 0.8rem;
      cursor: pointer;
      color: #78350F;
      transition: all 0.15s ease;
    }

    .suggest-pill.selected {
      background: #F59E0B;
      color: #ffffff;
      border-color: #D97706;
    }

    .suggest-pill mat-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
    }
  `]
})
export class TrainingListComponent implements OnInit {
  trainings: TrainingItem[] = [];
  cohorts: CohortItem[] = [];
  loading = true;
  assigning = false;

  showCreateModal = false;
  showAssignModal = false;
  selectedTraining: TrainingItem | null = null;

  newTraining = {
    title: '',
    description: '',
    skill_category: '',
    type: 'Self-paced',
    resources: [] as ResourceItem[],
    duration_hours: 1.0
  };

  tempResourceName = '';
  tempResourceUrl = '';

  assignTarget: 'ALL' | 'COHORT' | 'SELECTED' = 'SELECTED';
  selectedCohortId?: number;
  selectedAseIds: number[] = [];
  dueDate = new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10);
  suggestedAseList: SuggestedAseItem[] = [];

  constructor(
    private trainingService: TrainingService,
    private cohortService: CohortService,
    public authService: AuthService
  ) {}

  ngOnInit(): void {
    this.loadTrainings();
    this.loadCohorts();
  }

  loadTrainings(): void {
    this.loading = true;
    this.trainingService.listTrainings().subscribe({
      next: (list) => {
        this.trainings = list;
        this.loading = false;
      },
      error: (err) => {
        console.error('Failed to load trainings', err);
        this.loading = false;
      }
    });
  }

  loadCohorts(): void {
    this.cohortService.listCohorts().subscribe({
      next: (list) => this.cohorts = list,
      error: (err) => console.error('Failed to load cohorts', err)
    });
  }

  openCreateModal(): void {
    this.newTraining = {
      title: '',
      description: '',
      skill_category: '',
      type: 'Self-paced',
      resources: [],
      duration_hours: 1.0
    };
    this.showCreateModal = true;
  }

  addResourceLink(): void {
    if (this.tempResourceName && this.tempResourceUrl) {
      this.newTraining.resources.push({
        name: this.tempResourceName,
        url: this.tempResourceUrl,
        type: 'link'
      });
      this.tempResourceName = '';
      this.tempResourceUrl = '';
    }
  }

  removeResource(index: number): void {
    this.newTraining.resources.splice(index, 1);
  }

  saveNewTraining(): void {
    this.trainingService.createTraining(this.newTraining).subscribe({
      next: (created) => {
        this.trainings.unshift(created);
        this.showCreateModal = false;
      },
      error: (err) => console.error('Failed to create training', err)
    });
  }

  deleteTraining(t: TrainingItem): void {
    if (confirm(`Delete training '${t.title}'? This will not delete any ASE users or assessment results.`)) {
      this.trainingService.deleteTraining(t.id).subscribe({
        next: () => {
          this.trainings = this.trainings.filter(item => item.id !== t.id);
        },
        error: (err) => console.error('Failed to delete training', err)
      });
    }
  }

  openAssignModal(t: TrainingItem): void {
    this.selectedTraining = t;
    this.assignTarget = 'SELECTED';
    this.selectedAseIds = [];
    this.suggestedAseList = [];
    this.showAssignModal = true;
    this.suggestASEs(); // pre-load suggestions automatically!
  }

  suggestASEs(): void {
    if (!this.selectedTraining) return;
    this.trainingService.suggestASEs(this.selectedTraining.skill_category).subscribe({
      next: (list) => {
        this.suggestedAseList = list;
        // Pre-select suggested ASEs
        this.selectedAseIds = list.map(s => s.ase_id);
      },
      error: (err) => console.error('Failed to suggest ASEs', err)
    });
  }

  toggleAseSelection(aseId: number): void {
    const idx = this.selectedAseIds.indexOf(aseId);
    if (idx >= 0) {
      this.selectedAseIds.splice(idx, 1);
    } else {
      this.selectedAseIds.push(aseId);
    }
  }

  submitAssignment(): void {
    if (!this.selectedTraining) return;
    this.assigning = true;
    const dueIso = new Date(this.dueDate + 'T23:59:59Z').toISOString();

    this.trainingService.assignTraining(this.selectedTraining.id, {
      target: this.assignTarget,
      cohort_id: this.selectedCohortId,
      ase_ids: this.selectedAseIds,
      due_date: dueIso
    }).subscribe({
      next: (res) => {
        alert(res.message);
        this.assigning = false;
        this.showAssignModal = false;
      },
      error: (err) => {
        console.error('Assignment error', err);
        alert(err.error?.detail || 'Assignment failed');
        this.assigning = false;
      }
    });
  }
}
