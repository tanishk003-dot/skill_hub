import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSliderModule } from '@angular/material/slider';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterModule } from '@angular/router';
import { TrainingService } from '../../core/services/training.service';
import { TrainingAssignmentItem } from '../../core/models/training.model';

@Component({
  selector: 'app-my-learning',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressBarModule,
    MatSliderModule,
    MatChipsModule,
    MatProgressSpinnerModule
  ],
  template: `
    <div class="learning-page">
      <!-- Header -->
      <div class="page-header">
        <div>
          <h1>My Learning & Training Programs</h1>
          <p class="subtitle">Curated upskilling modules, technical workshops, and self-paced certifications</p>
        </div>
        <div>
          <a mat-raised-button color="primary" routerLink="/ase/schedule">
            <mat-icon>menu_book</mat-icon> Live Classes & Published Recaps
          </a>
        </div>
      </div>

      <!-- Loading State -->
      <div *ngIf="loading" class="loading-state">
        <mat-spinner diameter="40"></mat-spinner>
        <span>Loading your learning pathways...</span>
      </div>

      <!-- Empty State -->
      <div *ngIf="!loading && assignments.length === 0" class="empty-state-card">
        <mat-icon class="empty-icon">school</mat-icon>
        <h2>No Training Assigned Yet</h2>
        <p>Your mentor has not assigned any training modules to your plan yet.</p>
      </div>

      <!-- Trainings Grid -->
      <div *ngIf="!loading && assignments.length > 0" class="trainings-grid">
        <mat-card class="training-card" *ngFor="let item of assignments" [class.card-overdue]="item.is_overdue">
          <mat-card-header>
            <div class="header-badges">
              <span class="type-pill" [ngClass]="'pill-' + item.training_type.toLowerCase().replace(' ', '-')">
                {{ item.training_type }}
              </span>
              <span class="skill-pill">{{ item.skill_category }}</span>
              <span *ngIf="item.is_overdue" class="overdue-pill">
                <mat-icon>warning</mat-icon> OVERDUE
              </span>
            </div>
            <mat-card-title class="card-title">{{ item.training_title }}</mat-card-title>
            <mat-card-subtitle *ngIf="item.training_description">{{ item.training_description }}</mat-card-subtitle>
          </mat-card-header>

          <mat-card-content class="card-body">
            <!-- Meta Row -->
            <div class="meta-row">
              <span class="meta-item"><mat-icon>timer</mat-icon> {{ item.duration_hours }} hrs</span>
              <span class="meta-item" [class.text-danger]="item.is_overdue">
                <mat-icon>event</mat-icon> Due: {{ item.due_date | date:'mediumDate' }}
              </span>
              <span class="meta-item status-chip" [ngClass]="'status-' + item.status.toLowerCase()">
                {{ item.status.replace('_', ' ') }}
              </span>
            </div>

            <!-- Progress Bar -->
            <div class="progress-section">
              <div class="progress-info">
                <span>Completion</span>
                <strong>{{ item.progress_percent | number:'1.0-0' }}%</strong>
              </div>
              <mat-progress-bar mode="determinate" [value]="item.progress_percent" class="custom-progress"></mat-progress-bar>
            </div>

            <!-- Interactive Progress Slider -->
            <div class="progress-slider-row" *ngIf="item.status !== 'COMPLETED'">
              <label>Update Progress:</label>
              <mat-slider min="0" max="100" step="10" discrete class="slider-control">
                <input matSliderThumb [(ngModel)]="item.progress_percent" (change)="saveProgress(item)">
              </mat-slider>
              <button mat-stroked-button color="primary" (click)="markComplete(item)">
                <mat-icon>check_circle</mat-icon> Complete
              </button>
            </div>

            <!-- Resources List (Safe Links with rel="noopener noreferrer") -->
            <div class="resources-section" *ngIf="item.resources.length > 0">
              <h4>Learning Resources</h4>
              <div class="resource-links">
                <a *ngFor="let res of item.resources" 
                   [href]="res.url || ('http://localhost:8001/api/v1/trainings/resources/' + res.file_path)"
                   target="_blank"
                   rel="noopener noreferrer"
                   class="resource-chip">
                  <mat-icon>{{ res.type === 'file' ? 'attach_file' : 'open_in_new' }}</mat-icon>
                  <span>{{ res.name }}</span>
                </a>
              </div>
            </div>
          </mat-card-content>
        </mat-card>
      </div>
    </div>
  `,
  styles: [`
    .learning-page {
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

    .trainings-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
      gap: 20px;
    }

    .training-card {
      border-radius: 12px;
      border: 1px solid #E2E8F0;
      background: #ffffff;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .card-overdue {
      border-left: 5px solid #DC2626 !important;
    }

    .header-badges {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 8px;
    }

    .type-pill {
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      padding: 3px 8px;
      border-radius: 6px;
      background: #EFF6FF;
      color: var(--csm-primary);
    }

    .skill-pill {
      font-size: 0.72rem;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 6px;
      background: #F1F5F9;
      color: #475569;
    }

    .overdue-pill {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 0.72rem;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 6px;
      background: #FEE2E2;
      color: #991B1B;
    }

    .overdue-pill mat-icon {
      font-size: 14px;
      width: 14px;
      height: 14px;
    }

    .card-title {
      font-size: 1.15rem;
      font-weight: 700;
      color: #0F172A;
      margin-top: 4px;
    }

    .meta-row {
      display: flex;
      gap: 16px;
      align-items: center;
      flex-wrap: wrap;
      font-size: 0.85rem;
      color: #64748B;
      margin: 12px 0;
    }

    .meta-item {
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }

    .meta-item mat-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
    }

    .status-chip {
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
    }

    .status-not_started { background: #F1F5F9; color: #475569; }
    .status-in_progress { background: #FEF3C7; color: #B45309; }
    .status-completed { background: #ECFDF5; color: #065F46; }

    .progress-section {
      margin: 12px 0;
    }

    .progress-info {
      display: flex;
      justify-content: space-between;
      font-size: 0.82rem;
      margin-bottom: 4px;
      color: #475569;
    }

    .custom-progress {
      height: 8px;
      border-radius: 4px;
    }

    .progress-slider-row {
      display: flex;
      align-items: center;
      gap: 12px;
      background: #F8FAFC;
      padding: 10px 14px;
      border-radius: 8px;
      margin: 12px 0;
      font-size: 0.85rem;
    }

    .slider-control {
      flex: 1;
    }

    .resources-section {
      border-top: 1px solid #F1F5F9;
      padding-top: 12px;
      margin-top: 12px;
    }

    .resources-section h4 {
      margin: 0 0 8px 0;
      font-size: 0.85rem;
      color: #475569;
      text-transform: uppercase;
      font-weight: 600;
    }

    .resource-links {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .resource-chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #EFF6FF;
      color: var(--csm-primary);
      text-decoration: none;
      padding: 5px 12px;
      border-radius: 16px;
      font-size: 0.82rem;
      font-weight: 600;
      border: 1px solid #BFDBFE;
      transition: background 0.15s ease;
    }

    .resource-chip:hover {
      background: #DBEAFE;
    }

    .resource-chip mat-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
    }

    .text-danger { color: #DC2626; font-weight: 600; }
  `]
})
export class MyLearningComponent implements OnInit {
  assignments: TrainingAssignmentItem[] = [];
  loading = true;

  constructor(private trainingService: TrainingService) {}

  ngOnInit(): void {
    this.loadAssignments();
  }

  loadAssignments(): void {
    this.loading = true;
    this.trainingService.getMyLearning().subscribe({
      next: (list) => {
        this.assignments = list;
        this.loading = false;
      },
      error: (err) => {
        console.error('Failed to load trainings', err);
        this.loading = false;
      }
    });
  }

  saveProgress(item: TrainingAssignmentItem): void {
    this.trainingService.updateProgress(item.id, item.progress_percent).subscribe({
      next: (res) => {
        item.status = res.status;
        item.progress_percent = res.progress_percent;
      },
      error: (err) => console.error('Failed to save progress', err)
    });
  }

  markComplete(item: TrainingAssignmentItem): void {
    item.progress_percent = 100.0;
    this.trainingService.updateProgress(item.id, 100.0, 'COMPLETED').subscribe({
      next: (res) => {
        item.status = 'COMPLETED';
        item.progress_percent = 100.0;
      },
      error: (err) => console.error('Failed to mark complete', err)
    });
  }
}
