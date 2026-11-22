import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
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
import { ForumPostItem } from '../../../core/models/phase12.model';

@Component({
  selector: 'app-forum-list',
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
    <div class="forum-container">
      <div class="header-section">
        <div class="title-row">
          <mat-icon class="forum-icon">forum</mat-icon>
          <div>
            <h1>Cohort Doubt Forum</h1>
            <p class="subtitle">Ask questions, share solutions, and get verified answers from mentors and peers.</p>
          </div>
        </div>

        <button mat-flat-button color="primary" (click)="openAskModal = true">
          <mat-icon>add_comment</mat-icon> Ask a Doubt
        </button>
      </div>

      <!-- Filters & Search -->
      <div class="filter-bar">
        <mat-form-field appearance="outline" class="search-input">
          <mat-label>Search doubts or tags...</mat-label>
          <input matInput [(ngModel)]="searchTag" (keyup.enter)="loadPosts()" placeholder="e.g. Python, FastAPI, DFS">
          <button mat-icon-button matSuffix (click)="loadPosts()">
            <mat-icon>search</mat-icon>
          </button>
        </mat-form-field>

        <div class="filter-chips">
          <mat-chip-set>
            <mat-chip [highlighted]="!unansweredOnly" (click)="setFilter(false)">All Questions</mat-chip>
            <mat-chip [highlighted]="unansweredOnly" (click)="setFilter(true)">Unanswered Only</mat-chip>
          </mat-chip-set>
        </div>
      </div>

      <!-- Questions List -->
      <div class="posts-list" *ngIf="posts.length; else noPosts">
        <div class="post-card" *ngFor="let p of posts" (click)="viewThread(p.id)">
          <div class="post-stats">
            <span class="answers-badge" [class.has-answers]="p.answers_count > 0">
              {{ p.answers_count }} answers
            </span>
            <span class="views-count">{{ p.view_count }} views</span>
            <span class="resolved-tag" *ngIf="p.is_resolved">
              <mat-icon>check_circle</mat-icon> Resolved
            </span>
          </div>

          <div class="post-content">
            <h3 class="post-title">{{ p.title }}</h3>
            <p class="post-preview">{{ p.body }}</p>

            <div class="post-meta">
              <span class="tag-chip" *ngFor="let tag of getTagList(p.tags)">{{ tag }}</span>
              <span class="spacer"></span>
              <span class="author-label" [class.anon]="p.is_anonymous">
                <mat-icon class="meta-icon">{{ p.is_anonymous ? 'visibility_off' : 'person' }}</mat-icon>
                {{ p.author_name }}
              </span>
              <span class="time-label">{{ p.created_at | date:'shortDate' }}</span>
            </div>
          </div>
        </div>
      </div>

      <ng-template #noPosts>
        <div class="empty-state">
          <mat-icon class="empty-icon">chat_bubble_outline</mat-icon>
          <h3>No doubts found</h3>
          <p>Be the first to post a question for your cohort!</p>
        </div>
      </ng-template>

      <!-- Ask Question Modal -->
      <div class="modal-backdrop" *ngIf="openAskModal">
        <div class="modal-card">
          <h2>Ask a Technical Doubt</h2>
          <p class="modal-desc">Questions quoting live exam items will be held for review. PII & secrets are strictly filtered.</p>

          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Question Title</mat-label>
            <input matInput [(ngModel)]="newTitle" (ngModelChange)="checkSimilarQuestions($event)" placeholder="e.g. How to handle connection timeouts in Redis pool?">
          </mat-form-field>

          <!-- Similar Questions Preview -->
          <div class="similar-box" *ngIf="similarQuestions.length">
            <strong>Similar questions already asked:</strong>
            <ul>
              <li *ngFor="let sim of similarQuestions" (click)="viewThread(sim.id)">
                {{ sim.title }} ({{ sim.answers_count }} answers)
              </li>
            </ul>
          </div>

          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Detailed Description</mat-label>
            <textarea matInput [(ngModel)]="newBody" rows="5" placeholder="Explain what you are trying to achieve and what error or behavior occurs. Include code snippets where relevant."></textarea>
          </mat-form-field>

          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Tags (comma-separated)</mat-label>
            <input matInput [(ngModel)]="newTags" placeholder="Python, AsyncIO, Database">
          </mat-form-field>

          <div class="checkbox-row">
            <mat-checkbox [(ngModel)]="isAnonymous" color="primary">
              Post anonymously to peers
            </mat-checkbox>
            <span class="anon-note">(Mentors can still inspect author identity for moderation)</span>
          </div>

          <!-- PII Warning Banner -->
          <div class="pii-banner" *ngIf="piiWarning">
            <mat-icon>warning</mat-icon>
            <div>
              <strong>Content Flagged</strong>
              <p>{{ piiWarning }}</p>
            </div>
          </div>

          <div class="modal-actions">
            <button mat-button (click)="openAskModal = false">Cancel</button>
            <button mat-flat-button color="primary" [disabled]="!newTitle || !newBody" (click)="submitQuestion()">
              Submit Question
            </button>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .forum-container {
      max-width: 1000px;
      margin: 24px auto;
      padding: 0 16px;
    }
    .header-section {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: white;
      padding: 24px;
      border-radius: 12px;
      border: 1px solid #E2E8F0;
      margin-bottom: 20px;
    }
    .title-row {
      display: flex;
      align-items: center;
      gap: 16px;
    }
    .forum-icon {
      font-size: 40px;
      width: 40px;
      height: 40px;
      color: var(--csm-primary);
    }
    h1 {
      margin: 0;
      font-size: 22px;
      color: #0F172A;
    }
    .subtitle {
      margin: 4px 0 0 0;
      color: #64748B;
    }
    .filter-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      margin-bottom: 20px;
    }
    .search-input {
      flex: 1;
    }
    .post-card {
      display: flex;
      gap: 20px;
      background: white;
      border: 1px solid #E2E8F0;
      border-radius: 10px;
      padding: 20px;
      margin-bottom: 16px;
      cursor: pointer;
      transition: all 0.2s;
    }
    .post-card:hover {
      border-color: #3B82F6;
      box-shadow: 0 4px 12px rgba(59, 130, 246, 0.08);
    }
    .post-stats {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      min-width: 90px;
    }
    .answers-badge {
      font-size: 13px;
      font-weight: 600;
      padding: 4px 8px;
      border-radius: 6px;
      background: #F1F5F9;
      color: #475569;
    }
    .answers-badge.has-answers {
      background: #DCFCE7;
      color: #166534;
    }
    .views-count {
      font-size: 12px;
      color: #94A3B8;
    }
    .resolved-tag {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;
      color: #10B981;
      font-weight: 500;
    }
    .resolved-tag mat-icon {
      font-size: 14px;
      width: 14px;
      height: 14px;
    }
    .post-content {
      flex: 1;
    }
    .post-title {
      margin: 0 0 8px 0;
      font-size: 16px;
      color: var(--csm-primary);
      font-weight: 600;
    }
    .post-preview {
      margin: 0 0 12px 0;
      font-size: 14px;
      color: #475569;
      line-height: 1.4;
    }
    .post-meta {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
    }
    .tag-chip {
      background: #EFF6FF;
      color: #2563EB;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 500;
    }
    .spacer {
      flex: 1;
    }
    .author-label {
      display: flex;
      align-items: center;
      gap: 4px;
      color: #475569;
      font-weight: 500;
    }
    .author-label.anon {
      color: #9333EA;
    }
    .meta-icon {
      font-size: 14px;
      width: 14px;
      height: 14px;
    }
    .time-label {
      color: #94A3B8;
    }
    .empty-state {
      text-align: center;
      padding: 60px 20px;
      background: white;
      border-radius: 12px;
      border: 1px dashed #CBD5E1;
    }
    .empty-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      color: #94A3B8;
      margin-bottom: 12px;
    }
    /* Modal styles */
    .modal-backdrop {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(15, 23, 42, 0.6);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      padding: 16px;
    }
    .modal-card {
      background: white;
      border-radius: 12px;
      padding: 24px;
      max-width: 650px;
      width: 100%;
      max-height: 90vh;
      overflow-y: auto;
    }
    .modal-desc {
      font-size: 13px;
      color: #64748B;
      margin-bottom: 20px;
    }
    .full-width {
      width: 100%;
      margin-bottom: 12px;
    }
    .similar-box {
      background: #F8FAFC;
      border: 1px solid #E2E8F0;
      padding: 12px;
      border-radius: 8px;
      margin-bottom: 16px;
      font-size: 13px;
    }
    .similar-box ul {
      margin: 8px 0 0 16px;
      padding: 0;
    }
    .similar-box li {
      color: #2563EB;
      cursor: pointer;
      text-decoration: underline;
      margin-bottom: 4px;
    }
    .checkbox-row {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 16px;
    }
    .anon-note {
      font-size: 12px;
      color: #94A3B8;
    }
    .pii-banner {
      display: flex;
      gap: 12px;
      background: #FEF2F2;
      border: 1px solid #FECACA;
      border-radius: 8px;
      padding: 12px;
      color: #991B1B;
      font-size: 13px;
      margin-bottom: 16px;
    }
    .modal-actions {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      margin-top: 16px;
    }
  `]
})
export class ForumListComponent implements OnInit {
  posts: ForumPostItem[] = [];
  searchTag = '';
  unansweredOnly = false;
  openAskModal = false;

  newTitle = '';
  newBody = '';
  newTags = '';
  isAnonymous = false;
  piiWarning = '';
  similarQuestions: any[] = [];

  constructor(
    private phase12Service: Phase12Service,
    private authService: AuthService,
    private router: Router,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit() {
    this.loadPosts();
  }

  loadPosts() {
    this.phase12Service.getPosts({
      tag: this.searchTag.trim() || undefined,
      unanswered_only: this.unansweredOnly
    }).subscribe({
      next: (res) => this.posts = res.items,
      error: (err) => this.snackBar.open(err.error?.detail || 'Failed to load forum doubts', 'Close', { duration: 3000 })
    });
  }

  setFilter(unanswered: boolean) {
    this.unansweredOnly = unanswered;
    this.loadPosts();
  }

  getTagList(tags?: string): string[] {
    if (!tags) return [];
    return tags.split(',').map(t => t.trim()).filter(t => !!t);
  }

  checkSimilarQuestions(query: string) {
    if (query && query.trim().length >= 4) {
      this.phase12Service.getSimilarQuestions(query.trim()).subscribe({
        next: (items) => this.similarQuestions = items
      });
    } else {
      this.similarQuestions = [];
    }
  }

  submitQuestion() {
    this.piiWarning = '';
    const user = this.authService.currentUser();
    const userCohortId = 1; // Cohort fallback

    this.phase12Service.createPost({
      cohort_id: userCohortId,
      title: this.newTitle.trim(),
      body: this.newBody.trim(),
      tags: this.newTags.trim() || undefined,
      is_anonymous: this.isAnonymous
    }).subscribe({
      next: (res) => {
        this.snackBar.open(res.message, 'Close', { duration: 4000 });
        this.openAskModal = false;
        this.newTitle = '';
        this.newBody = '';
        this.newTags = '';
        this.loadPosts();
      },
      error: (err) => {
        if (err.status === 422) {
          this.piiWarning = err.error?.detail?.message || 'Sensitive contact info or prohibited language detected.';
        } else {
          this.snackBar.open(err.error?.detail || 'Failed to submit doubt', 'Close', { duration: 4000 });
        }
      }
    });
  }

  viewThread(postId: number) {
    this.router.navigate(['/forum/thread', postId]);
  }
}
