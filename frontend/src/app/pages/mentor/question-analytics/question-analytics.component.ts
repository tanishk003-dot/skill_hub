import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { Phase11Service } from '../../../core/services/phase11.service';
import { QuestionItemAnalytics } from '../../../core/models/phase11.model';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-question-analytics',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="min-h-screen bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100 p-6">
      <div class="max-w-7xl mx-auto space-y-6">

        <!-- Header -->
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
          <div>
            <div class="flex items-center space-x-3">
              <span class="p-2.5 rounded-xl bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300">
                <svg width="24" height="24" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
                </svg>
              </span>
              <h1 class="text-2xl font-bold">Question Analytics & Item Analysis</h1>
            </div>
            <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Statistical difficulty (p-value), discrimination index (top 27% vs bottom 27%), distractor analysis, and quality flags.
            </p>
          </div>

          <div class="flex items-center space-x-3">
            <button (click)="loadAnalytics()" [disabled]="isLoading"
              class="px-4 py-2 bg-slate-200 hover:bg-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 rounded-lg text-sm font-medium transition flex items-center space-x-1.5">
              <svg width="16" height="16" class="w-4 h-4" [ngClass]="{'animate-spin': isLoading}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
              </svg>
              <span>Refresh Analytics</span>
            </button>
          </div>
        </div>

        <!-- Formula & Methodology Disclosure Card -->
        <div class="bg-indigo-50/70 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-800/60 rounded-2xl p-5 space-y-3">
          <h3 class="text-sm font-bold text-indigo-950 dark:text-indigo-200 flex items-center space-x-2">
            <svg width="16" height="16" class="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            <span>Item Analysis Formulas & Quality Thresholds</span>
          </h3>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-indigo-900/80 dark:text-indigo-300/80">
            <div class="p-3 bg-white/70 dark:bg-slate-900/50 rounded-xl border border-indigo-100 dark:border-indigo-900">
              <span class="font-bold text-indigo-950 dark:text-indigo-200 block mb-1">Difficulty Index (p)</span>
              <code>p = Correct Attempts / Total Attempts</code>
              <p class="mt-1 text-[11px] text-slate-500 dark:text-slate-400">Flagged when N ≥ 10: Too Easy (p > 0.95), Too Hard (p < 0.10).</p>
            </div>
            <div class="p-3 bg-white/70 dark:bg-slate-900/50 rounded-xl border border-indigo-100 dark:border-indigo-900">
              <span class="font-bold text-indigo-950 dark:text-indigo-200 block mb-1">Discrimination Index (D)</span>
              <code>D = (U_correct - L_correct) / (0.27 * N)</code>
              <p class="mt-1 text-[11px] text-slate-500 dark:text-slate-400">Comparing top 27% (U) and bottom 27% (L). Confirmed at N ≥ 30; Indicative when 10 ≤ N < 30.</p>
            </div>
            <div class="p-3 bg-white/70 dark:bg-slate-900/50 rounded-xl border border-indigo-100 dark:border-indigo-900">
              <span class="font-bold text-indigo-950 dark:text-indigo-200 block mb-1">Versioning & Review</span>
              <p>Edits create an immutable new version. Flagged AI questions feature one-click "Send back to review" to ensure question quality.</p>
            </div>
          </div>
        </div>

        <!-- Filter bar -->
        <div class="flex flex-wrap items-center justify-between gap-3 bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700">
          <div class="flex items-center space-x-3 text-sm">
            <span class="font-semibold text-slate-600 dark:text-slate-300">Filter:</span>
            <button (click)="filterStatus = 'ALL'" [ngClass]="filterStatus === 'ALL' ? 'bg-indigo-600 text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300'" class="px-3 py-1 rounded-lg transition text-xs font-medium">All Questions ({{ analytics.length }})</button>
            <button (click)="filterStatus = 'NEEDS_REVIEW'" [ngClass]="filterStatus === 'NEEDS_REVIEW' ? 'bg-red-600 text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300'" class="px-3 py-1 rounded-lg transition text-xs font-medium">Needs Review ({{ getReviewCount() }})</button>
            <button (click)="filterStatus = 'STABLE'" [ngClass]="filterStatus === 'STABLE' ? 'bg-emerald-600 text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300'" class="px-3 py-1 rounded-lg transition text-xs font-medium">Optimal Items</button>
          </div>
          <span class="text-xs text-slate-400">Cached server-side; updated when attempts are submitted</span>
        </div>

        <!-- Items Table -->
        <div class="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full text-left text-sm">
              <thead class="bg-slate-50 dark:bg-slate-900/60 text-slate-500 dark:text-slate-400 font-semibold text-xs uppercase tracking-wider border-b border-slate-200 dark:border-slate-700">
                <tr>
                  <th class="py-3.5 px-4">Q ID & Ver</th>
                  <th class="py-3.5 px-4">Sample Size (N)</th>
                  <th class="py-3.5 px-4">Difficulty (p)</th>
                  <th class="py-3.5 px-4">Discrimination (D)</th>
                  <th class="py-3.5 px-4">Most Chosen Wrong</th>
                  <th class="py-3.5 px-4">Avg Time</th>
                  <th class="py-3.5 px-4">Status & Quality Flags</th>
                  <th class="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 dark:divide-slate-800">
                <tr *ngFor="let item of filteredAnalytics" class="hover:bg-slate-50/70 dark:hover:bg-slate-800/50 transition">
                  <!-- ID & Version -->
                  <td class="py-3 px-4 font-mono">
                    <span class="font-bold text-slate-900 dark:text-slate-100">#{{ item.question_id }}</span>
                    <span class="ml-1.5 px-1.5 py-0.5 text-[10px] rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 font-sans">v{{ item.question_version }}</span>
                  </td>

                  <!-- Sample Size N -->
                  <td class="py-3 px-4">
                    <span class="font-semibold">{{ item.attempts_count }}</span>
                    <span class="text-xs text-slate-400 block" *ngIf="item.attempts_count < 10">N &lt; 10 (Wait)</span>
                    <span class="text-xs text-amber-500 block" *ngIf="item.attempts_count >= 10 && item.attempts_count < 30">Indicative (10 ≤ N &lt; 30)</span>
                    <span class="text-xs text-emerald-500 block" *ngIf="item.attempts_count >= 30">Sufficient (N ≥ 30)</span>
                  </td>

                  <!-- Difficulty Index -->
                  <td class="py-3 px-4">
                    <div class="flex items-center space-x-2">
                      <span class="font-mono font-bold">{{ (item.difficulty_index * 100).toFixed(1) }}%</span>
                      <span *ngIf="item.is_too_easy" class="px-1.5 py-0.5 text-[10px] bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300 rounded font-semibold">Too Easy</span>
                      <span *ngIf="item.is_too_hard" class="px-1.5 py-0.5 text-[10px] bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300 rounded font-semibold">Too Hard</span>
                    </div>
                  </td>

                  <!-- Discrimination Index -->
                  <td class="py-3 px-4">
                    <div class="flex items-center space-x-2">
                      <span class="font-mono font-bold" [ngClass]="item.discrimination_index < 0.20 && item.attempts_count >= 30 ? 'text-red-500' : ''">
                        {{ item.discrimination_index.toFixed(2) }}
                      </span>
                      <span *ngIf="item.is_indicative_discrimination" class="text-[10px] px-1.5 py-0.5 bg-slate-100 dark:bg-slate-700 text-slate-500 rounded">Indicative</span>
                      <span *ngIf="item.is_poor_discrimination" class="px-1.5 py-0.5 text-[10px] bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300 rounded font-semibold">Poor D</span>
                    </div>
                  </td>

                  <!-- Distractor -->
                  <td class="py-3 px-4 font-mono text-xs">
                    {{ item.most_chosen_wrong_option || 'None' }}
                  </td>

                  <!-- Avg Time -->
                  <td class="py-3 px-4 text-xs font-mono">
                    {{ item.avg_time_seconds.toFixed(0) }}s
                  </td>

                  <!-- Status & Quality Flags -->
                  <td class="py-3 px-4">
                    <div *ngIf="item.needs_review" class="text-xs text-red-600 dark:text-red-400 font-medium">
                      <span>⚠️ {{ item.review_reason || 'Quality review needed' }}</span>
                    </div>
                    <div *ngIf="!item.needs_review && item.attempts_count >= 10" class="text-xs text-emerald-600 dark:text-emerald-400 font-medium">
                      <span>✓ Optimal discrimination</span>
                    </div>
                    <div *ngIf="item.attempts_count < 10" class="text-xs text-slate-400">
                      <span>Collecting responses...</span>
                    </div>
                  </td>

                  <!-- Actions -->
                  <td class="py-3 px-4 text-right">
                    <div class="flex items-center justify-end space-x-2">
                      <button *ngIf="item.needs_review" (click)="openReviewModal(item)"
                        class="px-2.5 py-1 bg-red-50 hover:bg-red-100 text-red-700 dark:bg-red-950/50 dark:hover:bg-red-900/60 dark:text-red-300 rounded text-xs font-medium border border-red-200 dark:border-red-800 transition">
                        Send to Review
                      </button>
                      <button (click)="recompute(item.question_id)" title="Force Recalculate"
                        class="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition">
                        <svg width="16" height="16" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                      </button>
                    </div>
                  </td>
                </tr>

                <tr *ngIf="filteredAnalytics.length === 0">
                  <td colspan="8" class="text-center py-8 text-slate-400">
                    No questions match the selected filter.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Review Modal -->
        <div *ngIf="selectedItemForReview" class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div class="bg-white dark:bg-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-xl border border-slate-200 dark:border-slate-700">
            <h3 class="text-lg font-bold">Send Question #{{ selectedItemForReview.question_id }} Back to Review</h3>
            <p class="text-xs text-slate-500">Provide an editorial reason or revision guidance for this question.</p>
            <textarea [(ngModel)]="reviewReason" rows="3" class="w-full text-sm p-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="e.g. Ambiguous distractor opt2 chosen by 40% of test takers; rephrase option."></textarea>
            <div class="flex items-center justify-end space-x-2 pt-2">
              <button (click)="selectedItemForReview = null" class="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg">Cancel</button>
              <button (click)="submitReview()" [disabled]="!reviewReason.trim()" class="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg">Confirm Send Back</button>
            </div>
          </div>
        </div>

      </div>
    </div>
  `
})
export class QuestionAnalyticsComponent implements OnInit {
  analytics: QuestionItemAnalytics[] = [];
  filterStatus: 'ALL' | 'NEEDS_REVIEW' | 'STABLE' = 'ALL';
  isLoading = false;
  selectedItemForReview: QuestionItemAnalytics | null = null;
  reviewReason = '';

  constructor(
    private phase11Service: Phase11Service,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.loadAnalytics();
  }

  loadAnalytics(): void {
    this.isLoading = true;
    this.phase11Service.getQuestionAnalytics().subscribe({
      next: (data) => {
        this.analytics = data;
        this.isLoading = false;
      },
      error: () => {
        this.isLoading = false;
      }
    });
  }

  get filteredAnalytics(): QuestionItemAnalytics[] {
    if (this.filterStatus === 'NEEDS_REVIEW') {
      return this.analytics.filter(a => a.needs_review);
    }
    if (this.filterStatus === 'STABLE') {
      return this.analytics.filter(a => !a.needs_review && a.attempts_count >= 10);
    }
    return this.analytics;
  }

  getReviewCount(): number {
    return this.analytics.filter(a => a.needs_review).length;
  }

  openReviewModal(item: QuestionItemAnalytics): void {
    this.selectedItemForReview = item;
    this.reviewReason = item.review_reason || '';
  }

  submitReview(): void {
    if (!this.selectedItemForReview || !this.reviewReason.trim()) return;
    this.phase11Service.flagQuestionForReview(this.selectedItemForReview.question_id, this.reviewReason).subscribe({
      next: (updated) => {
        const idx = this.analytics.findIndex(a => a.id === updated.id);
        if (idx >= 0) this.analytics[idx] = updated;
        this.selectedItemForReview = null;
        this.reviewReason = '';
      }
    });
  }

  recompute(questionId: number): void {
    this.phase11Service.recalculateQuestionAnalytics(questionId).subscribe({
      next: (updated) => {
        const idx = this.analytics.findIndex(a => a.id === updated.id);
        if (idx >= 0) this.analytics[idx] = updated;
      }
    });
  }
}
