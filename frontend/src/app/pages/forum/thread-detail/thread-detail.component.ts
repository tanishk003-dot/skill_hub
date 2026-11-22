import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { Phase12Service } from '../../../core/services/phase12.service';
import { AuthService } from '../../../core/services/auth.service';
import { ForumThreadDetail } from '../../../core/models/phase12.model';

@Component({
  selector: 'app-thread-detail',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatFormFieldModule,
    MatInputModule,
    MatCheckboxModule,
    MatSnackBarModule
  ],
  template: `
    <div class="thread-container" *ngIf="thread">
      <div class="back-link">
        <a routerLink="/forum">
          <mat-icon>arrow_back</mat-icon> Back to Cohort Doubts
        </a>
      </div>

      <!-- Question Card -->
      <div class="question-card">
        <div class="q-header">
          <h1>{{ thread.title }}</h1>
          <div class="q-meta">
            <span class="author-badge" [class.anon]="thread.author.is_anonymous_to_peers">
              <mat-icon>{{ thread.author.is_anonymous_to_peers ? 'visibility_off' : 'person' }}</mat-icon>
              {{ thread.author.author_name }}
              <span class="anon-mentor-pill" *ngIf="thread.author.is_anonymous_to_peers && isPrivileged">
                (Anonymous to peers)
              </span>
            </span>
            <span class="date">{{ thread.created_at | date:'medium' }}</span>
            <span class="views">{{ thread.view_count }} views</span>
            <span class="resolved-pill" *ngIf="thread.is_resolved">
              <mat-icon>check_circle</mat-icon> Resolved
            </span>
          </div>
        </div>

        <div class="q-body">
          <p>{{ thread.body }}</p>
        </div>

        <div class="q-footer">
          <div class="tags">
            <span class="tag-chip" *ngFor="let t of getTagList(thread.tags)">{{ t }}</span>
          </div>

          <div class="q-actions">
            <button mat-button color="accent" (click)="requestAIDraft()">
              <mat-icon>auto_awesome</mat-icon> Generate AI Draft
            </button>
            <button mat-button color="warn" (click)="reportPost()">
              <mat-icon>flag</mat-icon> Report
            </button>
          </div>
        </div>
      </div>

      <!-- Answers Section -->
      <div class="answers-header">
        <h2>{{ thread.answers.length }} Answers</h2>
      </div>

      <div class="answers-list">
        <div class="answer-card" *ngFor="let a of thread.answers" [class.accepted-card]="a.is_accepted">
          <div class="vote-column">
            <button mat-icon-button (click)="toggleVote(a.id)">
              <mat-icon [class.upvoted]="a.user_has_upvoted">thumb_up</mat-icon>
            </button>
            <span class="vote-count">{{ a.upvote_count }}</span>
          </div>

          <div class="ans-content">
            <div class="ans-header">
              <div class="author-meta">
                <strong>{{ a.author.author_name }}</strong>
                <span class="anon-mentor-pill" *ngIf="a.author.is_anonymous_to_peers && isPrivileged">
                  (Anonymous to peers)
                </span>
                <span class="time">{{ a.created_at | date:'short' }}</span>
              </div>

              <div class="badges">
                <span class="verified-badge" *ngIf="a.is_mentor_verified">
                  <mat-icon>verified</mat-icon> Verified by Mentor
                </span>
                <span class="accepted-badge" *ngIf="a.is_accepted">
                  <mat-icon>check</mat-icon> Accepted Answer
                </span>
              </div>
            </div>

            <div class="ans-body">
              <p>{{ a.body }}</p>
            </div>

            <div class="ans-actions">
              <!-- Question Author can accept -->
              <button mat-stroked-button color="primary" *ngIf="!a.is_accepted && isPostAuthor" (click)="acceptAnswer(a.id)">
                <mat-icon>check_circle_outline</mat-icon> Accept Answer
              </button>

              <!-- Mentor can verify -->
              <button mat-stroked-button color="accent" *ngIf="!a.is_mentor_verified && isPrivileged" (click)="verifyAnswer(a.id)">
                <mat-icon>verified</mat-icon> Mark Verified
              </button>

              <button mat-button color="warn" (click)="reportAnswer(a.id)">
                <mat-icon>flag</mat-icon> Report
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Submit Answer Card -->
      <div class="reply-card">
        <h3>Post Your Answer</h3>
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Your solution or insight...</mat-label>
          <textarea matInput [(ngModel)]="newAnswerBody" rows="4" placeholder="Explain the technical concept or provide clear code steps."></textarea>
        </mat-form-field>

        <div class="reply-actions">
          <mat-checkbox [(ngModel)]="isAnswerAnonymous" color="primary">
            Answer anonymously to peers
          </mat-checkbox>
          <button mat-flat-button color="primary" [disabled]="!newAnswerBody" (click)="submitAnswer()">
            Submit Answer
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .thread-container {
      max-width: 900px;
      margin: 24px auto;
      padding: 0 16px;
    }
    .back-link {
      margin-bottom: 16px;
    }
    .back-link a {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      color: #2563EB;
      text-decoration: none;
      font-weight: 500;
      font-size: 14px;
    }
    .question-card {
      background: white;
      border: 1px solid #E2E8F0;
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 24px;
    }
    h1 {
      margin: 0 0 12px 0;
      font-size: 22px;
      color: #0F172A;
    }
    .q-meta {
      display: flex;
      align-items: center;
      gap: 16px;
      font-size: 13px;
      color: #64748B;
      padding-bottom: 16px;
      border-bottom: 1px solid #F1F5F9;
    }
    .author-badge {
      display: flex;
      align-items: center;
      gap: 4px;
      font-weight: 600;
      color: var(--csm-primary);
    }
    .author-badge.anon {
      color: #9333EA;
    }
    .anon-mentor-pill {
      background: #F3E8FF;
      color: #7E22CE;
      font-size: 11px;
      padding: 2px 6px;
      border-radius: 4px;
      margin-left: 4px;
    }
    .resolved-pill {
      display: flex;
      align-items: center;
      gap: 4px;
      color: #10B981;
      font-weight: 600;
    }
    .q-body {
      padding: 20px 0;
      font-size: 15px;
      color: #334155;
      line-height: 1.6;
    }
    .q-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-top: 16px;
      border-top: 1px solid #F1F5F9;
    }
    .tag-chip {
      background: #EFF6FF;
      color: #2563EB;
      padding: 3px 10px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 500;
      margin-right: 6px;
    }
    .answers-header {
      margin-bottom: 16px;
    }
    .answers-header h2 {
      font-size: 18px;
      color: #1E293B;
      margin: 0;
    }
    .answer-card {
      display: flex;
      gap: 16px;
      background: white;
      border: 1px solid #E2E8F0;
      border-radius: 10px;
      padding: 20px;
      margin-bottom: 16px;
    }
    .answer-card.accepted-card {
      border: 2px solid #10B981;
      background: #F0FDF4;
    }
    .vote-column {
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    .upvoted {
      color: #2563EB;
    }
    .vote-count {
      font-weight: 600;
      color: #334155;
    }
    .ans-content {
      flex: 1;
    }
    .ans-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }
    .author-meta strong {
      font-size: 14px;
      color: #0F172A;
      margin-right: 8px;
    }
    .author-meta .time {
      font-size: 12px;
      color: #94A3B8;
    }
    .verified-badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      background: #FEF3C7;
      color: #92400E;
      font-size: 12px;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 6px;
      margin-left: 8px;
    }
    .verified-badge mat-icon {
      font-size: 14px;
      width: 14px;
      height: 14px;
    }
    .accepted-badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      background: #DCFCE7;
      color: #166534;
      font-size: 12px;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 6px;
    }
    .ans-body {
      font-size: 14px;
      color: #334155;
      line-height: 1.6;
      margin-bottom: 16px;
    }
    .ans-actions {
      display: flex;
      gap: 8px;
    }
    .reply-card {
      background: white;
      border: 1px solid #E2E8F0;
      border-radius: 12px;
      padding: 24px;
      margin-top: 24px;
    }
    .reply-card h3 {
      margin: 0 0 16px 0;
      font-size: 16px;
      color: #1E293B;
    }
    .full-width {
      width: 100%;
    }
    .reply-actions {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  `]
})
export class ThreadDetailComponent implements OnInit {
  thread: ForumThreadDetail | null = null;
  newAnswerBody = '';
  isAnswerAnonymous = false;

  constructor(
    private route: ActivatedRoute,
    private phase12Service: Phase12Service,
    private authService: AuthService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit() {
    this.route.params.subscribe(params => {
      const postId = +params['id'];
      if (postId) {
        this.loadThread(postId);
      }
    });
  }

  loadThread(postId: number) {
    this.phase12Service.getThreadDetail(postId).subscribe({
      next: (data) => this.thread = data,
      error: (err) => this.snackBar.open(err.error?.detail || 'Failed to load doubt thread', 'Close', { duration: 3000 })
    });
  }

  get isPrivileged(): boolean {
    const role = this.authService.currentUser()?.role;
    return role === 'MENTOR' || role === 'ADMIN';
  }

  get isPostAuthor(): boolean {
    return this.thread?.author.author_id === this.authService.currentUser()?.user_id;
  }

  getTagList(tags?: string): string[] {
    if (!tags) return [];
    return tags.split(',').map(t => t.trim()).filter(t => !!t);
  }

  toggleVote(answerId: number) {
    this.phase12Service.toggleVote(answerId).subscribe({
      next: (res) => {
        const ans = this.thread?.answers.find(a => a.id === answerId);
        if (ans) {
          ans.upvote_count = res.upvotes;
          ans.user_has_upvoted = (res.action === 'UPVOTED');
        }
      },
      error: (err) => this.snackBar.open(err.error?.detail || 'Vote failed', 'Close', { duration: 3000 })
    });
  }

  acceptAnswer(answerId: number) {
    if (!this.thread) return;
    this.phase12Service.acceptAnswer(this.thread.id, answerId).subscribe({
      next: () => {
        this.snackBar.open('Answer accepted as solution!', 'Close', { duration: 3000 });
        this.loadThread(this.thread!.id);
      },
      error: (err) => this.snackBar.open(err.error?.detail || 'Failed to accept answer', 'Close', { duration: 3000 })
    });
  }

  verifyAnswer(answerId: number) {
    this.phase12Service.verifyAnswer(answerId).subscribe({
      next: () => {
        this.snackBar.open('Answer marked Verified by Mentor!', 'Close', { duration: 3000 });
        this.loadThread(this.thread!.id);
      },
      error: (err) => this.snackBar.open(err.error?.detail || 'Failed to verify answer', 'Close', { duration: 3000 })
    });
  }

  requestAIDraft() {
    if (!this.thread) return;
    this.phase12Service.requestAIDraft(this.thread.id).subscribe({
      next: (res) => {
        this.snackBar.open('AI draft answer generated!', 'Close', { duration: 4000 });
        this.loadThread(this.thread!.id);
      },
      error: (err) => this.snackBar.open(err.error?.detail || 'Could not generate AI draft', 'Close', { duration: 4000 })
    });
  }

  submitAnswer() {
    if (!this.thread || !this.newAnswerBody.trim()) return;
    this.phase12Service.postAnswer(this.thread.id, {
      body: this.newAnswerBody.trim(),
      is_anonymous: this.isAnswerAnonymous
    }).subscribe({
      next: () => {
        this.snackBar.open('Answer posted successfully!', 'Close', { duration: 3000 });
        this.newAnswerBody = '';
        this.loadThread(this.thread!.id);
      },
      error: (err) => {
        const msg = err.status === 422 ? err.error?.detail?.message : err.error?.detail;
        this.snackBar.open(msg || 'Failed to post answer', 'Close', { duration: 4000 });
      }
    });
  }

  reportPost() {
    const reason = prompt('Specify reason (OFF_TOPIC, EXAM_LEAK, HARASSMENT, SPAM):');
    if (reason && this.thread) {
      this.phase12Service.reportContent({
        post_id: this.thread.id,
        reason: reason.trim().toUpperCase()
      }).subscribe({
        next: (res) => this.snackBar.open(res.message, 'Close', { duration: 3000 }),
        error: (err) => this.snackBar.open(err.error?.detail || 'Report failed', 'Close', { duration: 3000 })
      });
    }
  }

  reportAnswer(answerId: number) {
    const reason = prompt('Specify reason (OFF_TOPIC, EXAM_LEAK, HARASSMENT, SPAM):');
    if (reason) {
      this.phase12Service.reportContent({
        answer_id: answerId,
        reason: reason.trim().toUpperCase()
      }).subscribe({
        next: (res) => this.snackBar.open(res.message, 'Close', { duration: 3000 }),
        error: (err) => this.snackBar.open(err.error?.detail || 'Report failed', 'Close', { duration: 3000 })
      });
    }
  }
}
