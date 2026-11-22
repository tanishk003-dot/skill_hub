import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { Phase12Service } from '../../../core/services/phase12.service';
import { BuddyViewResponse, CoarseBuddee, CoarseBuddy } from '../../../core/models/phase12.model';

@Component({
  selector: 'app-buddy-hub',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatSlideToggleModule,
    MatFormFieldModule,
    MatInputModule,
    MatSnackBarModule
  ],
  template: `
    <div class="buddy-container">
      <div class="header-section">
        <div class="title-row">
          <mat-icon class="hub-icon">people</mat-icon>
          <div>
            <h1>Peer Buddy Hub</h1>
            <p class="subtitle">Collaborative peer guidance, 1-on-1 check-ins, and shared onboarding milestones.</p>
          </div>
        </div>

        <div class="volunteer-card">
          <div class="vol-content">
            <strong>Volunteer as a Peer Buddy</strong>
            <p>Support newer engineers, conduct weekly check-ins, and earn XP towards the "Peer Guide" badge.</p>
          </div>
          <mat-slide-toggle
            [checked]="buddyData?.is_volunteer"
            (change)="onToggleVolunteer($event.checked)"
            color="primary">
            {{ buddyData?.is_volunteer ? 'Active Volunteer' : 'Opted Out' }}
          </mat-slide-toggle>
        </div>
      </div>

      <!-- What is Shared Privacy Notice -->
      <div class="notice-card">
        <mat-icon class="shield-icon">security</mat-icon>
        <div class="notice-text">
          <strong>Privacy Commitment: What is Shared</strong>
          <p>{{ buddyData?.what_is_shared_notice }}</p>
        </div>
      </div>

      <!-- MY ASSIGNED BUDDY (If I am a buddee) -->
      <div class="section-card" *ngIf="buddyData?.my_buddy">
        <h2>My Peer Buddy</h2>
        <div class="buddy-box">
          <div class="avatar-circle">{{ buddyData?.my_buddy?.coarse_name?.charAt(0) }}</div>
          <div class="buddy-info">
            <span class="buddy-name">{{ buddyData?.my_buddy?.coarse_name }}</span>
            <span class="cohort-badge">{{ buddyData?.my_buddy?.cohort_name }}</span>
            <span class="status-tag">Status: {{ buddyData?.my_buddy?.status }}</span>
          </div>

          <div class="actions">
            <button mat-stroked-button color="warn" (click)="openChangeRequest(buddyData!.my_buddy!.pairing_id)">
              <mat-icon>swap_horiz</mat-icon> Request Change
            </button>
          </div>
        </div>

        <!-- Rating Section -->
        <div class="rating-box">
          <h3>Rate Your Buddy Experience</h3>
          <div class="stars">
            <button mat-icon-button *ngFor="let s of [1,2,3,4,5]" (click)="selectedRating = s">
              <mat-icon [class.active-star]="s <= selectedRating">star</mat-icon>
            </button>
            <span class="star-label">{{ selectedRating }}/5 Stars</span>
          </div>
          <mat-form-field appearance="outline" class="feedback-input">
            <mat-label>Feedback (optional)</mat-label>
            <input matInput [(ngModel)]="ratingFeedback" placeholder="What was helpful about your peer check-in?">
          </mat-form-field>
          <button mat-flat-button color="primary" [disabled]="selectedRating === 0" (click)="submitRating(buddyData!.my_buddy!.pairing_id)">
            Submit Rating
          </button>
        </div>
      </div>

      <!-- MY ASSIGNED BUDDEES (If I am a buddy) -->
      <div class="section-card" *ngIf="buddyData?.my_buddees?.length">
        <h2>My Assigned Buddees ({{ buddyData?.my_buddees?.length }} / {{ buddyData?.max_buddees_cap }})</h2>
        <div class="buddees-grid">
          <div class="buddee-card" *ngFor="let b of buddyData?.my_buddees">
            <div class="b-header">
              <div class="avatar-small">{{ b.coarse_name.charAt(0) }}</div>
              <div>
                <strong>{{ b.coarse_name }}</strong>
                <span class="c-name">{{ b.cohort_name }}</span>
              </div>
            </div>

            <div class="coarse-indicator" [class.on-track]="b.coarse_status === 'On track'" [class.needs-support]="b.coarse_status === 'Needs support'">
              <mat-icon>{{ b.coarse_status === 'On track' ? 'check_circle' : 'help_outline' }}</mat-icon>
              <span>{{ b.coarse_status }}</span>
            </div>

            <div class="milestone-box">
              <button mat-stroked-button color="primary" (click)="addMilestone(b.pairing_id)">
                <mat-icon>add_task</mat-icon> Add Learning Check-in
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .buddy-container {
      max-width: 1000px;
      margin: 24px auto;
      padding: 0 16px;
    }
    .header-section {
      background: white;
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 20px;
      border: 1px solid #E2E8F0;
    }
    .title-row {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 16px;
    }
    .hub-icon {
      font-size: 40px;
      width: 40px;
      height: 40px;
      color: var(--csm-primary);
    }
    h1 {
      margin: 0;
      font-size: 24px;
      color: #0F172A;
    }
    .subtitle {
      margin: 4px 0 0 0;
      color: #64748B;
    }
    .volunteer-card {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #F8FAFC;
      border: 1px solid #E2E8F0;
      padding: 16px 20px;
      border-radius: 8px;
    }
    .notice-card {
      display: flex;
      gap: 16px;
      align-items: flex-start;
      background: #EFF6FF;
      border: 1px solid #BFDBFE;
      border-radius: 10px;
      padding: 16px;
      margin-bottom: 24px;
    }
    .shield-icon {
      color: #2563EB;
      font-size: 28px;
      width: 28px;
      height: 28px;
    }
    .notice-text strong {
      color: #1E40AF;
      display: block;
      margin-bottom: 4px;
    }
    .notice-text p {
      margin: 0;
      font-size: 13px;
      color: var(--csm-primary);
      line-height: 1.5;
    }
    .section-card {
      background: white;
      border: 1px solid #E2E8F0;
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 24px;
    }
    h2 {
      margin-top: 0;
      font-size: 18px;
      color: #1E293B;
      margin-bottom: 16px;
    }
    .buddy-box {
      display: flex;
      align-items: center;
      gap: 16px;
      background: #F8FAFC;
      border: 1px solid #E2E8F0;
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 20px;
    }
    .avatar-circle {
      width: 52px;
      height: 52px;
      border-radius: 50%;
      background: var(--csm-primary);
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 22px;
      font-weight: bold;
    }
    .buddy-info {
      flex: 1;
    }
    .buddy-name {
      display: block;
      font-size: 16px;
      font-weight: 600;
      color: #0F172A;
    }
    .cohort-badge {
      display: inline-block;
      font-size: 12px;
      background: #E2E8F0;
      padding: 2px 8px;
      border-radius: 4px;
      margin-top: 4px;
      margin-right: 8px;
    }
    .status-tag {
      font-size: 12px;
      color: #64748B;
    }
    .rating-box {
      background: #F8FAFC;
      border-radius: 8px;
      padding: 16px;
      border: 1px solid #E2E8F0;
    }
    .rating-box h3 {
      margin: 0 0 12px 0;
      font-size: 14px;
      color: #334155;
    }
    .stars {
      display: flex;
      align-items: center;
      gap: 4px;
      margin-bottom: 12px;
    }
    .active-star {
      color: #F59E0B;
    }
    .star-label {
      font-size: 13px;
      color: #475569;
      margin-left: 8px;
    }
    .feedback-input {
      width: 100%;
      margin-bottom: 8px;
    }
    .buddees-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 16px;
    }
    .buddee-card {
      border: 1px solid #E2E8F0;
      border-radius: 8px;
      padding: 16px;
      background: #F8FAFC;
    }
    .b-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
    }
    .avatar-small {
      width: 38px;
      height: 38px;
      border-radius: 50%;
      background: #2563EB;
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
    }
    .c-name {
      display: block;
      font-size: 12px;
      color: #64748B;
    }
    .coarse-indicator {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 500;
      margin-bottom: 16px;
    }
    .coarse-indicator.on-track {
      background: #DCFCE7;
      color: #166534;
    }
    .coarse-indicator.needs-support {
      background: #FEF3C7;
      color: #92400E;
    }
    .milestone-box button {
      width: 100%;
    }
  `]
})
export class BuddyHubComponent implements OnInit {
  buddyData: BuddyViewResponse | null = null;
  selectedRating = 0;
  ratingFeedback = '';

  constructor(
    private phase12Service: Phase12Service,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit() {
    this.loadBuddyDetails();
  }

  loadBuddyDetails() {
    this.phase12Service.getMyBuddyDetails().subscribe({
      next: (data) => this.buddyData = data,
      error: (err) => this.snackBar.open(err.error?.detail || 'Failed to load buddy pairings', 'Close', { duration: 3000 })
    });
  }

  onToggleVolunteer(checked: boolean) {
    this.phase12Service.toggleVolunteer(checked).subscribe({
      next: (res) => {
        this.snackBar.open(res.message, 'Close', { duration: 3000 });
        this.loadBuddyDetails();
      },
      error: (err) => {
        this.snackBar.open(err.error?.detail || 'Failed to update volunteer status', 'Close', { duration: 4000 });
        this.loadBuddyDetails();
      }
    });
  }

  submitRating(pairingId: number) {
    this.phase12Service.rateBuddy(pairingId, this.selectedRating, this.ratingFeedback).subscribe({
      next: () => {
        this.snackBar.open('Buddy rating submitted successfully!', 'Close', { duration: 3000 });
        this.selectedRating = 0;
        this.ratingFeedback = '';
      },
      error: (err) => this.snackBar.open(err.error?.detail || 'Error submitting rating', 'Close', { duration: 3000 })
    });
  }

  openChangeRequest(pairingId: number) {
    const reason = prompt('Please specify a reason for requesting a change of peer buddy:');
    if (reason && reason.trim().length >= 5) {
      this.phase12Service.requestPairingChange(pairingId, reason.trim()).subscribe({
        next: (res) => {
          this.snackBar.open(res.message, 'Close', { duration: 3000 });
          this.loadBuddyDetails();
        },
        error: (err) => this.snackBar.open(err.error?.detail || 'Failed to request change', 'Close', { duration: 3000 })
      });
    }
  }

  addMilestone(pairingId: number) {
    const title = prompt('Enter Milestone title (e.g., Code Review or Setup Sync):');
    if (title && title.trim().length >= 3) {
      this.phase12Service.createMilestone(pairingId, title.trim()).subscribe({
        next: () => this.snackBar.open('Milestone check-in added. Awaiting confirmation.', 'Close', { duration: 3000 }),
        error: (err) => this.snackBar.open(err.error?.detail || 'Failed to add milestone', 'Close', { duration: 3000 })
      });
    }
  }
}
