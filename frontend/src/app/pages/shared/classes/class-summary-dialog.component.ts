import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSliderModule } from '@angular/material/slider';
import { MatChipsModule } from '@angular/material/chips';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatTabsModule } from '@angular/material/tabs';

import { AISummaryService } from '../../../core/services/ai-summary.service';
import { AuthService } from '../../../core/services/auth.service';
import {
  ClassTranscript,
  ClassSummary,
  AssessmentPlan,
  AIGeneratedAssessment,
  AIGeneratedQuestion,
  ClassEffectivenessReport
} from '../../../core/models/ai-summary.model';
import { LiveClassItem } from '../../../core/models/live-class.model';

@Component({
  selector: 'app-class-summary-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatSliderModule,
    MatChipsModule,
    MatCheckboxModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatTabsModule
  ],
  template: `
    <div class="summary-modal-backdrop">
      <div class="summary-modal-container">
        <!-- Header -->
        <div class="modal-topbar">
          <div class="topbar-title">
            <span class="ai-badge"><mat-icon>auto_awesome</mat-icon> AI Intelligence Studio</span>
            <span class="demo-tag" *ngIf="isDemoMode">Demo AI mode</span>
            <h2>{{ liveClass.title }}</h2>
          </div>
          <button mat-icon-button (click)="closeDialog()"><mat-icon>close</mat-icon></button>
        </div>

        <!-- Navigation Tabs for Mentor / Admin -->
        <div class="tabs-header" *ngIf="isMentorOrAdmin">
          <button class="tab-btn" [class.active]="activeTab === 'transcript'" (click)="activeTab = 'transcript'">
            <mat-icon>upload_file</mat-icon> 1. Lecture Input & Transcripts
          </button>
          <button class="tab-btn" [class.active]="activeTab === 'summary'" (click)="activeTab = 'summary'">
            <mat-icon>menu_book</mat-icon> 2. Class Summary & Recap
          </button>
          <button class="tab-btn" [class.active]="activeTab === 'assessment'" (click)="activeTab = 'assessment'">
            <mat-icon>quiz</mat-icon> 3. Assessment Generator
          </button>
          <button class="tab-btn" [class.active]="activeTab === 'effectiveness'" (click)="activeTab = 'effectiveness'">
            <mat-icon>insights</mat-icon> 4. Class Effectiveness
          </button>
        </div>

        <!-- Dialog Body -->
        <div class="modal-body">
          <div *ngIf="loading" class="center-spinner">
            <mat-spinner diameter="44"></mat-spinner>
            <p>{{ statusMessage || 'Processing with educational AI engine...' }}</p>
          </div>

          <!-- Alert / Toast -->
          <div *ngIf="feedbackMsg" class="feedback-banner" [class.success]="isSuccess" [class.error]="!isSuccess">
            <mat-icon>{{ isSuccess ? 'check_circle' : 'error' }}</mat-icon>
            <span>{{ feedbackMsg }}</span>
          </div>

          <!-- TAB 1: TRANSCRIPTS & NOTES (Mentor / Admin) -->
          <div *ngIf="!loading && activeTab === 'transcript' && isMentorOrAdmin" class="tab-pane">
            <div class="privacy-notice">
              <mat-icon class="privacy-icon">security</mat-icon>
              <div>
                <strong>Student Privacy & Content Governance Notice</strong>
                <p>
                  Transcripts may contain participant questions and verbal interactions. Raw text is automatically purged after 30 days
                  and is accessible exclusively to the class mentor and authorized admins. Never disclose PII.
                </p>
              </div>
            </div>

            <div class="consent-box">
              <mat-checkbox [(ngModel)]="privacyConsent">
                I explicitly consent to processing this transcript strictly for educational summarization and quiz generation.
              </mat-checkbox>
            </div>

            <div class="input-methods-grid">
              <!-- Method A: File Upload -->
              <div class="input-card">
                <h3><mat-icon>upload</mat-icon> Upload Class Transcript</h3>
                <p class="hint">Accepts safe plain text (.txt), WebVTT subtitles (.vtt), or Microsoft Word (.docx) up to 5 MB.</p>
                <input type="file" #fileInput (change)="onFileSelected($event)" accept=".txt,.vtt,.docx" class="file-input">
                <div class="selected-file-info" *ngIf="selectedFile">
                  <mat-icon>description</mat-icon>
                  <span>{{ selectedFile.name }} ({{ (selectedFile.size / 1024).toFixed(1) }} KB)</span>
                </div>
                <button mat-raised-button color="primary" (click)="uploadFile()" [disabled]="!selectedFile || !privacyConsent">
                  <mat-icon>cloud_upload</mat-icon> Upload & Process Transcript
                </button>
              </div>

              <!-- Method B: Paste Notes -->
              <div class="input-card">
                <h3><mat-icon>edit_note</mat-icon> Paste Mentor Lecture Notes</h3>
                <mat-form-field appearance="outline" class="full-width">
                  <mat-label>Key Topics Covered</mat-label>
                  <input matInput [(ngModel)]="topicsCovered" placeholder="e.g. Distributed Caching, Redis Cluster, Eviction Policies">
                </mat-form-field>

                <mat-form-field appearance="outline" class="full-width">
                  <mat-label>Lecture Notes / Code Snippets</mat-label>
                  <textarea matInput rows="4" [(ngModel)]="notesContent" placeholder="Paste lecture transcript, whiteboard discussion points, or key architectural trade-offs..."></textarea>
                </mat-form-field>

                <button mat-raised-button color="accent" (click)="submitNotes()" [disabled]="!notesContent || !privacyConsent">
                  <mat-icon>save</mat-icon> Save Lecture Notes
                </button>
              </div>
            </div>

            <!-- Current Transcript Status -->
            <div class="transcript-status-card" *ngIf="currentTranscript">
              <div class="status-header">
                <h4><mat-icon>fact_check</mat-icon> Active Transcript Metadata</h4>
                <button mat-stroked-button color="warn" (click)="deleteRawText()" *ngIf="currentTranscript.raw_text_present">
                  <mat-icon>delete_forever</mat-icon> Purge Raw Text
                </button>
              </div>
              <div class="meta-chips">
                <span class="chip">Tokens: {{ currentTranscript.token_count }}</span>
                <span class="chip">Tokens Used: {{ currentTranscript.used_token_count }}</span>
                <span class="chip highlight">Coverage: {{ (currentTranscript.truncated_ratio * 100).toFixed(0) }}%</span>
                <span class="chip" [class.warn]="!currentTranscript.raw_text_present">
                  Raw Text: {{ currentTranscript.raw_text_present ? 'Active (Auto-purges 30d)' : 'Purged' }}
                </span>
              </div>
              <div class="actions-row">
                <button mat-raised-button color="primary" (click)="triggerGenerateSummary()">
                  <mat-icon>auto_awesome</mat-icon> Generate AI Class Summary
                </button>
              </div>
            </div>
          </div>

          <!-- TAB 2: CLASS SUMMARY & RECAP (All Roles) -->
          <div *ngIf="!loading && (activeTab === 'summary' || !isMentorOrAdmin)" class="tab-pane">
            <div *ngIf="!currentSummary" class="empty-tab">
              <mat-icon class="empty-icon">menu_book</mat-icon>
              <h3>No Class Summary Generated Yet</h3>
              <p *ngIf="isMentorOrAdmin">Upload a transcript or paste notes in Step 1 to generate an AI summary.</p>
              <p *ngIf="!isMentorOrAdmin">The mentor has not published a summary for this session yet.</p>
            </div>

            <div *ngIf="currentSummary" class="summary-container">
              <div class="summary-header-row">
                <div>
                  <span class="version-tag">Version {{ currentSummary.version }}</span>
                  <span class="publish-tag" [class.pub]="currentSummary.is_published">
                    {{ currentSummary.is_published ? 'Published to ASEs' : 'Draft (Mentor Only)' }}
                  </span>
                </div>
                <div class="mentor-actions" *ngIf="isMentorOrAdmin">
                  <button mat-stroked-button *ngIf="!isEditingSummary" (click)="isEditingSummary = true">
                    <mat-icon>edit</mat-icon> Edit Summary
                  </button>
                  <button mat-raised-button color="primary" *ngIf="isEditingSummary" (click)="saveSummaryEdits()">
                    <mat-icon>check</mat-icon> Save Changes
                  </button>
                  <button mat-raised-button color="accent" *ngIf="!currentSummary.is_published" (click)="publishSummary()">
                    <mat-icon>send</mat-icon> Publish to ASEs
                  </button>
                  <button mat-stroked-button color="warn" *ngIf="currentSummary.is_published" (click)="unpublishSummary()">
                    <mat-icon>visibility_off</mat-icon> Unpublish
                  </button>
                </div>
              </div>

              <!-- Key Topics -->
              <div class="summary-section">
                <h4><mat-icon>label</mat-icon> Key Topics Covered</h4>
                <div class="topics-chips">
                  <span class="topic-chip" *ngFor="let topic of currentSummary.key_topics">{{ topic }}</span>
                </div>
              </div>

              <!-- ASE Concise Recap -->
              <div class="summary-section">
                <h4><mat-icon>psychology</mat-icon> Executive Recap for Engineers</h4>
                <div *ngIf="!isEditingSummary" class="recap-box">
                  <p>{{ currentSummary.ase_recap }}</p>
                </div>
                <div *ngIf="isEditingSummary">
                  <mat-form-field appearance="outline" class="full-width">
                    <textarea matInput rows="4" [(ngModel)]="editRecap"></textarea>
                  </mat-form-field>
                </div>
              </div>

              <!-- Key Concepts -->
              <div class="summary-section">
                <h4><mat-icon>lightbulb</mat-icon> Core Concepts Explained</h4>
                <div class="concepts-grid">
                  <div class="concept-card" *ngFor="let c of currentSummary.key_concepts">
                    <strong>{{ c.concept }}</strong>
                    <p>{{ c.explanation }}</p>
                  </div>
                </div>
              </div>

              <!-- Practical Examples & Suggested Homework -->
              <div class="split-sections">
                <div class="half-section">
                  <h4><mat-icon>code</mat-icon> Practical Walkthroughs & Examples</h4>
                  <ul>
                    <li *ngFor="let ex of currentSummary.practical_examples">{{ ex }}</li>
                  </ul>
                </div>
                <div class="half-section">
                  <h4><mat-icon>assignment</mat-icon> Suggested Homework & Practice Labs</h4>
                  <ul>
                    <li *ngFor="let hw of currentSummary.suggested_homework">{{ hw }}</li>
                  </ul>
                </div>
              </div>

              <!-- Next Action for Mentor -->
              <div class="summary-footer-actions" *ngIf="isMentorOrAdmin">
                <button mat-raised-button color="primary" (click)="goToAssessmentStudio()">
                  <mat-icon>arrow_forward</mat-icon> Proceed to Assessment Plan Recommendation
                </button>
              </div>
            </div>
          </div>

          <!-- TAB 3: ASSESSMENT GENERATOR (Mentor / Admin) -->
          <div *ngIf="!loading && activeTab === 'assessment' && isMentorOrAdmin" class="tab-pane">
            <!-- Step A: Plan Configuration -->
            <div class="plan-config-card" *ngIf="!currentAssessment">
              <div class="step-badge">Step 1: AI Recommendation & Assessment Plan</div>
              <h3>Configure Evaluation Blueprint</h3>
              <p class="hint">Adjust question quotas and difficulty balancing. The AI engine recommends questions based on topic depth.</p>

              <div class="plan-controls-grid">
                <div class="control-col">
                  <label>Total Questions: <strong>{{ targetQuestionCount }}</strong> (Range 20 - 50)</label>
                  <mat-slider min="20" max="50" step="5" class="full-width" discrete>
                    <input matSliderThumb [(ngModel)]="targetQuestionCount">
                  </mat-slider>
                </div>

                <div class="control-col">
                  <label>Difficulty Balancing: Easy {{ easyPct }}% / Medium {{ mediumPct }}% / Hard {{ hardPct }}%</label>
                  <div class="sliders-row">
                    <mat-form-field appearance="outline" class="mini-input">
                      <mat-label>Easy %</mat-label>
                      <input matInput type="number" [(ngModel)]="easyPct">
                    </mat-form-field>
                    <mat-form-field appearance="outline" class="mini-input">
                      <mat-label>Medium %</mat-label>
                      <input matInput type="number" [(ngModel)]="mediumPct">
                    </mat-form-field>
                    <mat-form-field appearance="outline" class="mini-input">
                      <mat-label>Hard %</mat-label>
                      <input matInput type="number" [(ngModel)]="hardPct">
                    </mat-form-field>
                  </div>
                </div>
              </div>

              <div class="mode-selector">
                <label><strong>Generation Strategy:</strong></label>
                <div class="mode-options">
                  <div class="mode-pill" [class.selected]="generationMode === 'AUTO'" (click)="generationMode = 'AUTO'">
                    <mat-icon>auto_awesome</mat-icon>
                    <strong>Auto-create</strong>
                    <span>AI creates entire question set</span>
                  </div>
                  <div class="mode-pill" [class.selected]="generationMode === 'BANK'" (click)="generationMode = 'BANK'">
                    <mat-icon>account_balance</mat-icon>
                    <strong>Pick from My Bank</strong>
                    <span>Pulls matching bank questions</span>
                  </div>
                  <div class="mode-pill" [class.selected]="generationMode === 'MIXED'" (click)="generationMode = 'MIXED'">
                    <mat-icon>shuffle</mat-icon>
                    <strong>Mixed</strong>
                    <span>Reuses bank questions + AI remainder</span>
                  </div>
                </div>
              </div>

              <div class="plan-action-row">
                <button mat-raised-button color="primary" (click)="generateAssessmentQuestions()">
                  <mat-icon>play_arrow</mat-icon> Generate Questions Card Deck
                </button>
              </div>
            </div>

            <!-- Step B: Question Review Card Deck -->
            <div class="card-deck-container" *ngIf="currentAssessment">
              <div class="deck-topbar">
                <div>
                  <h3>{{ currentAssessment.title }}</h3>
                  <div class="deck-stats">
                    <span class="stat-tag">Total: {{ currentAssessment.questions.length }}</span>
                    <span class="stat-tag approved">Approved: {{ countApproved }}</span>
                    <span class="stat-tag pending">Pending: {{ countPending }}</span>
                    <span class="stat-tag immutable" *ngIf="currentAssessment.is_immutable">
                      <mat-icon>lock</mat-icon> Immutable (Assigned)
                    </span>
                  </div>
                </div>
                <div class="deck-actions" *ngIf="!currentAssessment.is_immutable">
                  <button mat-stroked-button color="primary" (click)="approveAll()" [disabled]="hasFlaggedOrPending">
                    <mat-icon>done_all</mat-icon> Approve All
                  </button>
                  <button mat-stroked-button (click)="exportApprovedToBank()">
                    <mat-icon>cloud_download</mat-icon> Export Approved to Bank
                  </button>
                  <button mat-raised-button color="accent" (click)="finalizeAndAssign()">
                    <mat-icon>publish</mat-icon> Finalize & Publish to Core
                  </button>
                </div>
              </div>

              <!-- Flagged Warning Notice -->
              <div class="deck-warning" *ngIf="hasFlaggedOrPending && !currentAssessment.is_immutable">
                <mat-icon>warning</mat-icon>
                <span>Some questions require manual mentor verification before 'Approve All' is permitted.</span>
              </div>

              <!-- Questions List -->
              <div class="questions-deck">
                <mat-card class="q-card" *ngFor="let q of currentAssessment.questions; let i = index" [class.flagged]="q.mentor_verify_required">
                  <mat-card-header>
                    <div class="q-header-badges">
                      <span class="q-num">Q{{ i + 1 }}</span>
                      <span class="source-tag">{{ q.source }}</span>
                      <span class="diff-tag" [ngClass]="q.difficulty.toLowerCase()">{{ q.difficulty }}</span>
                      <span class="status-tag" [ngClass]="q.review_status.toLowerCase()">{{ q.review_status }}</span>
                      <span class="verify-flag" *ngIf="q.mentor_verify_required">
                        <mat-icon>flag</mat-icon> Mentor Verify
                      </span>
                    </div>
                  </mat-card-header>

                  <mat-card-content class="q-body">
                    <p class="q-text"><strong>{{ q.question_text }}</strong></p>

                    <div class="options-list">
                      <div class="opt-item" *ngFor="let opt of q.options" [class.correct]="q.correct_answers.includes(opt)">
                        <mat-icon class="opt-icon">{{ q.correct_answers.includes(opt) ? 'check_circle' : 'radio_button_unchecked' }}</mat-icon>
                        <span>{{ opt }}</span>
                      </div>
                    </div>

                    <div class="q-explanation">
                      <mat-icon>info</mat-icon>
                      <em>{{ q.explanation }}</em>
                    </div>
                  </mat-card-content>

                  <mat-card-actions class="q-actions" *ngIf="!currentAssessment.is_immutable">
                    <button mat-button color="primary" (click)="approveQuestion(q)" [disabled]="q.review_status === 'APPROVED' && !q.mentor_verify_required">
                      <mat-icon>check</mat-icon> Approve
                    </button>
                    <button mat-button color="warn" (click)="rejectQuestion(q)" [disabled]="q.review_status === 'REJECTED'">
                      <mat-icon>close</mat-icon> Reject
                    </button>
                    <button mat-button (click)="regenerateQuestion(q)">
                      <mat-icon>refresh</mat-icon> Regenerate
                    </button>
                  </mat-card-actions>
                </mat-card>
              </div>
            </div>
          </div>

          <!-- TAB 4: CLASS EFFECTIVENESS (Mentor / Admin) -->
          <div *ngIf="!loading && activeTab === 'effectiveness' && isMentorOrAdmin" class="tab-pane">
            <div *ngIf="!effectivenessReport" class="center-spinner">
              <mat-spinner diameter="36"></mat-spinner>
              <p>Analyzing cohort performance and learning retention...</p>
            </div>

            <div *ngIf="effectivenessReport">
              <!-- Privacy Guard State (< 3 attempts) -->
              <div *ngIf="!effectivenessReport.has_enough_data" class="privacy-empty-card">
                <mat-icon class="privacy-lock-icon">lock</mat-icon>
                <h3>Privacy Shield Active (Insufficient Data)</h3>
                <p>{{ effectivenessReport.message }}</p>
                <div class="privacy-badge">
                  <span>Completed Attempts: {{ effectivenessReport.total_attempts }} / Minimum 3 Required</span>
                </div>
              </div>

              <!-- Full Effectiveness Analytics (>= 3 attempts) -->
              <div *ngIf="effectivenessReport.has_enough_data" class="analytics-report-container">
                <div class="report-topbar">
                  <h3>Cohort Effectiveness & Misconceptions Analysis</h3>
                  <span class="cohort-count-tag">{{ effectivenessReport.total_attempts }} Evaluated Engineers</span>
                </div>

                <!-- Topic Score Gauges -->
                <div class="topic-bars-grid">
                  <div class="topic-gauge-card" *ngFor="let item of topicScoresArray">
                    <div class="gauge-head">
                      <span>{{ item.topic }}</span>
                      <strong [class.fail]="item.score < 60" [class.warn]="item.score >= 60 && item.score < 70" [class.pass]="item.score >= 70">
                        {{ item.score }}%
                      </strong>
                    </div>
                    <div class="gauge-bar-track">
                      <div class="gauge-fill" [style.width.%]="item.score" [ngClass]="getScoreColorClass(item.score)"></div>
                    </div>
                  </div>
                </div>

                <!-- Missed Concepts -->
                <div class="missed-concepts-box" *ngIf="effectivenessReport.missed_concepts.length > 0">
                  <h4><mat-icon>warning_amber</mat-icon> Missed Concepts & Critical Knowledge Gaps</h4>
                  <div class="missed-list">
                    <div class="missed-item" *ngFor="let m of effectivenessReport.missed_concepts">
                      <strong>{{ m.concept }} ({{ m.score }}%)</strong>
                      <p>{{ m.reason }}</p>
                    </div>
                  </div>
                </div>

                <!-- Follow-up Mini Class Proposal -->
                <div class="proposal-card" *ngIf="effectivenessReport.follow_up_proposal">
                  <div class="proposal-header">
                    <div>
                      <span class="proposal-badge"><mat-icon>alarm</mat-icon> 15-Minute Intervention Proposal</span>
                      <h4>{{ effectivenessReport.follow_up_proposal.title }}</h4>
                    </div>
                    <button mat-raised-button color="accent" (click)="scheduleFollowUpMiniClass()">
                      <mat-icon>schedule</mat-icon> Schedule Follow-up Mini Class
                    </button>
                  </div>
                  <p class="target-aud">Target Audience: {{ effectivenessReport.follow_up_proposal.recommended_audience }}</p>
                  <ul class="agenda-list" *ngIf="effectivenessReport.follow_up_proposal.suggested_agenda">
                    <li *ngFor="let ag of effectivenessReport.follow_up_proposal.suggested_agenda">{{ ag }}</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .summary-modal-backdrop {
      position: fixed;
      top: 0; left: 0; width: 100vw; height: 100vh;
      background: rgba(15, 23, 42, 0.7);
      backdrop-filter: blur(4px);
      display: flex; justify-content: center; align-items: center;
      z-index: 1050;
    }
    .summary-modal-container {
      background: #ffffff;
      width: 92%; max-width: 1050px;
      max-height: 90vh;
      border-radius: 12px;
      display: flex; flex-direction: column;
      box-shadow: 0 20px 40px rgba(0,0,0,0.25);
      overflow: hidden;
    }
    .modal-topbar {
      display: flex; justify-content: space-between; align-items: center;
      padding: 18px 24px;
      background: var(--csm-primary);
      color: #ffffff;
    }
    .topbar-title {
      display: flex; flex-direction: column; gap: 4px;
    }
    .topbar-title h2 { margin: 0; font-size: 1.25rem; font-weight: 600; color: #ffffff; }
    .ai-badge {
      font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px;
      display: flex; align-items: center; gap: 4px; color: var(--csm-accent); font-weight: 700;
    }
    .ai-badge mat-icon { font-size: 16px; width: 16px; height: 16px; }
    .demo-tag {
      background: rgba(249, 115, 22, 0.2); border: 1px solid var(--csm-accent);
      color: var(--csm-accent); font-size: 0.7rem; padding: 2px 8px; border-radius: 12px;
      align-self: flex-start;
    }
    .tabs-header {
      display: flex; background: #F1F5F9; border-bottom: 1px solid #CBD5E1;
      padding: 0 16px; overflow-x: auto;
    }
    .tab-btn {
      display: flex; align-items: center; gap: 8px;
      padding: 12px 16px; border: none; background: transparent;
      font-weight: 600; font-size: 0.9rem; color: #64748B;
      cursor: pointer; border-bottom: 3px solid transparent;
      transition: all 0.2s;
    }
    .tab-btn.active {
      color: var(--csm-primary); border-bottom-color: var(--csm-primary); background: #ffffff;
    }
    .modal-body {
      padding: 24px; overflow-y: auto; flex: 1;
    }
    .center-spinner {
      display: flex; flex-direction: column; align-items: center;
      justify-content: center; padding: 48px 0; gap: 16px; color: #64748B;
    }
    .feedback-banner {
      display: flex; align-items: center; gap: 8px;
      padding: 12px 16px; border-radius: 6px; margin-bottom: 16px;
      font-weight: 500; font-size: 0.9rem;
    }
    .feedback-banner.success { background: #ECFDF5; color: #065F46; border-left: 4px solid #10B981; }
    .feedback-banner.error { background: #FEF2F2; color: #991B1B; border-left: 4px solid #EF4444; }

    /* Privacy Banner */
    .privacy-notice {
      display: flex; gap: 12px; background: #EFF6FF; border: 1px solid #BFDBFE;
      padding: 14px 18px; border-radius: 8px; margin-bottom: 16px;
    }
    .privacy-icon { color: var(--csm-primary); }
    .privacy-notice p { margin: 4px 0 0 0; font-size: 0.85rem; color: #334155; }
    .consent-box { margin-bottom: 20px; }

    /* Input Grid */
    .input-methods-grid {
      display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px;
    }
    .input-card {
      background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 20px;
      display: flex; flex-direction: column; gap: 12px;
    }
    .input-card h3 {
      display: flex; align-items: center; gap: 8px; margin: 0; font-size: 1rem; color: #1E293B;
    }
    .hint { font-size: 0.8rem; color: #64748B; margin: 0; }
    .file-input { margin: 8px 0; }
    .selected-file-info {
      display: flex; align-items: center; gap: 6px; font-size: 0.85rem; color: var(--csm-primary);
      background: #DBEAFE; padding: 6px 12px; border-radius: 4px;
    }

    .transcript-status-card {
      background: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 8px; padding: 18px;
    }
    .status-header {
      display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;
    }
    .status-header h4 { margin: 0; display: flex; align-items: center; gap: 6px; }
    .meta-chips { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
    .chip {
      background: #E2E8F0; padding: 4px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: 500;
    }
    .chip.highlight { background: #FEF3C7; color: #92400E; font-weight: 600; }
    .chip.warn { background: #FEE2E2; color: #991B1B; }

    /* Summary Tab */
    .summary-header-row {
      display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;
    }
    .version-tag {
      background: #E0E7FF; color: #3730A3; font-size: 0.75rem; font-weight: 700;
      padding: 4px 8px; border-radius: 4px; margin-right: 8px;
    }
    .publish-tag {
      background: #F1F5F9; color: #64748B; font-size: 0.75rem; font-weight: 600;
      padding: 4px 8px; border-radius: 4px;
    }
    .publish-tag.pub { background: #D1FAE5; color: #065F46; }
    .summary-section { margin-bottom: 20px; }
    .summary-section h4 {
      display: flex; align-items: center; gap: 6px; margin: 0 0 8px 0;
      color: var(--csm-primary); font-size: 0.95rem;
    }
    .topics-chips { display: flex; gap: 8px; flex-wrap: wrap; }
    .topic-chip {
      background: #EFF6FF; border: 1px solid #BFDBFE; color: var(--csm-primary);
      font-size: 0.85rem; padding: 4px 12px; border-radius: 16px; font-weight: 500;
    }
    .recap-box {
      background: #F8FAFC; border-left: 4px solid var(--csm-primary); padding: 14px 18px;
      border-radius: 0 8px 8px 0; font-size: 0.95rem; line-height: 1.5; color: #334155;
    }
    .concepts-grid {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px;
    }
    .concept-card {
      background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px;
    }
    .concept-card strong { color: #0F172A; display: block; margin-bottom: 4px; }
    .concept-card p { margin: 0; font-size: 0.85rem; color: #475569; }
    .split-sections { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 16px; }
    .half-section ul { padding-left: 20px; margin: 0; font-size: 0.9rem; color: #334155; }
    .half-section li { margin-bottom: 6px; }

    /* Assessment Plan */
    .plan-config-card {
      background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 24px;
    }
    .step-badge {
      font-size: 0.75rem; text-transform: uppercase; color: var(--csm-primary); font-weight: 700; margin-bottom: 6px;
    }
    .plan-controls-grid {
      display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin: 20px 0;
    }
    .sliders-row { display: flex; gap: 12px; margin-top: 8px; }
    .mini-input { width: 90px; }
    .mode-options {
      display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; margin-top: 8px;
    }
    .mode-pill {
      border: 2px solid #E2E8F0; border-radius: 8px; padding: 14px; cursor: pointer;
      display: flex; flex-direction: column; gap: 4px; transition: all 0.2s;
    }
    .mode-pill.selected {
      border-color: var(--csm-primary); background: #EFF6FF;
    }
    .mode-pill mat-icon { color: var(--csm-primary); }
    .mode-pill span { font-size: 0.75rem; color: #64748B; }

    /* Card Deck */
    .deck-topbar {
      display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;
    }
    .deck-topbar h3 { margin: 0; }
    .deck-stats { display: flex; gap: 8px; margin-top: 4px; }
    .stat-tag { font-size: 0.75rem; padding: 2px 8px; border-radius: 12px; background: #E2E8F0; font-weight: 600; }
    .stat-tag.approved { background: #D1FAE5; color: #065F46; }
    .stat-tag.pending { background: #FEF3C7; color: #92400E; }
    .stat-tag.immutable { background: #E0E7FF; color: #3730A3; }
    .deck-actions { display: flex; gap: 8px; }
    .deck-warning {
      display: flex; align-items: center; gap: 8px; background: #FEF3C7; color: #92400E;
      padding: 10px 14px; border-radius: 6px; margin-bottom: 16px; font-size: 0.85rem; font-weight: 500;
    }
    .questions-deck { display: flex; flex-direction: column; gap: 16px; }
    .q-card { border: 1px solid #E2E8F0; border-radius: 8px; }
    .q-card.flagged { border-color: #F59E0B; background: #FFFDF7; }
    .q-header-badges { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 8px; }
    .q-num { font-weight: 700; color: var(--csm-primary); }
    .source-tag { font-size: 0.7rem; background: #F1F5F9; padding: 2px 6px; border-radius: 4px; }
    .diff-tag { font-size: 0.7rem; font-weight: 600; padding: 2px 6px; border-radius: 4px; text-transform: uppercase; }
    .diff-tag.easy { background: #D1FAE5; color: #065F46; }
    .diff-tag.medium { background: #FEF3C7; color: #92400E; }
    .diff-tag.hard { background: #FEE2E2; color: #991B1B; }
    .status-tag { font-size: 0.7rem; padding: 2px 6px; border-radius: 4px; }
    .status-tag.approved { background: #D1FAE5; color: #065F46; }
    .status-tag.rejected { background: #FEE2E2; color: #991B1B; }
    .verify-flag {
      display: flex; align-items: center; gap: 4px; color: #D97706; font-size: 0.75rem; font-weight: 700;
    }
    .verify-flag mat-icon { font-size: 14px; width: 14px; height: 14px; }
    .options-list { display: flex; flex-direction: column; gap: 6px; margin: 12px 0; }
    .opt-item {
      display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 4px;
      background: #F8FAFC; border: 1px solid #E2E8F0; font-size: 0.9rem;
    }
    .opt-item.correct { background: #ECFDF5; border-color: #10B981; font-weight: 600; color: #065F46; }
    .opt-icon { font-size: 18px; width: 18px; height: 18px; }
    .q-explanation {
      display: flex; gap: 6px; font-size: 0.85rem; color: #64748B; background: #F1F5F9;
      padding: 8px 12px; border-radius: 4px;
    }

    /* Effectiveness Tab */
    .privacy-empty-card {
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      padding: 48px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; text-align: center;
    }
    .privacy-lock-icon { font-size: 48px; width: 48px; height: 48px; color: #94A3B8; margin-bottom: 12px; }
    .privacy-badge {
      background: #DBEAFE; color: var(--csm-primary); font-weight: 600; font-size: 0.85rem;
      padding: 6px 14px; border-radius: 16px; margin-top: 14px;
    }
    .report-topbar {
      display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;
    }
    .cohort-count-tag {
      background: #E2E8F0; font-weight: 600; font-size: 0.85rem; padding: 4px 12px; border-radius: 12px;
    }
    .topic-bars-grid {
      display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px;
    }
    .topic-gauge-card {
      background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px;
    }
    .gauge-head { display: flex; justify-content: space-between; font-size: 0.9rem; margin-bottom: 8px; }
    .gauge-head strong.fail { color: #EF4444; }
    .gauge-head strong.warn { color: #F59E0B; }
    .gauge-head strong.pass { color: #10B981; }
    .gauge-bar-track { height: 10px; background: #E2E8F0; border-radius: 5px; overflow: hidden; }
    .gauge-fill { height: 100%; border-radius: 5px; }
    .gauge-fill.fill-pass { background: #10B981; }
    .gauge-fill.fill-warn { background: #F59E0B; }
    .gauge-fill.fill-fail { background: #EF4444; }
    .missed-concepts-box {
      background: #FEF2F2; border: 1px solid #FECACA; border-radius: 8px; padding: 18px; margin-bottom: 24px;
    }
    .missed-concepts-box h4 {
      display: flex; align-items: center; gap: 6px; margin: 0 0 12px 0; color: #991B1B;
    }
    .missed-list { display: flex; flex-direction: column; gap: 10px; }
    .missed-item strong { color: #7F1D1D; font-size: 0.9rem; }
    .missed-item p { margin: 2px 0 0 0; font-size: 0.85rem; color: #991B1B; }
    .proposal-card {
      background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 8px; padding: 20px;
    }
    .proposal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .proposal-badge { font-size: 0.75rem; font-weight: 700; color: #B45309; text-transform: uppercase; }
    .proposal-header h4 { margin: 4px 0 0 0; color: #78350F; font-size: 1.1rem; }
    .target-aud { font-size: 0.85rem; color: #92400E; margin-bottom: 8px; }
    .agenda-list { margin: 0; padding-left: 20px; font-size: 0.85rem; color: #78350F; }

    .full-width { width: 100%; }
  `]
})
export class ClassSummaryDialogComponent implements OnInit {
  @Input() liveClass!: LiveClassItem;
  @Output() close = new EventEmitter<void>();
  @Output() scheduleMiniClass = new EventEmitter<{ title: string; duration: number }>();

  activeTab: 'transcript' | 'summary' | 'assessment' | 'effectiveness' = 'summary';
  loading = false;
  statusMessage = '';
  feedbackMsg = '';
  isSuccess = true;

  // Transcripts
  privacyConsent = false;
  selectedFile: File | null = null;
  topicsCovered = '';
  notesContent = '';
  currentTranscript: ClassTranscript | null = null;

  // Summary
  currentSummary: ClassSummary | null = null;
  isEditingSummary = false;
  editRecap = '';

  // Assessment
  targetQuestionCount = 20;
  easyPct = 35;
  mediumPct = 45;
  hardPct = 20;
  generationMode = 'AUTO';
  currentAssessment: AIGeneratedAssessment | null = null;

  // Effectiveness
  effectivenessReport: ClassEffectivenessReport | null = null;

  isDemoMode = true;

  constructor(
    private aiSummaryService: AISummaryService,
    public authService: AuthService
  ) {}

  get isMentorOrAdmin(): boolean {
    const role = this.authService.currentUser()?.role;
    return role === 'MENTOR' || role === 'ADMIN';
  }

  get countApproved(): number {
    return this.currentAssessment?.questions.filter(q => q.review_status === 'APPROVED').length || 0;
  }

  get countPending(): number {
    return this.currentAssessment?.questions.filter(q => q.review_status === 'PENDING').length || 0;
  }

  get hasFlaggedOrPending(): boolean {
    if (!this.currentAssessment) return false;
    return this.currentAssessment.questions.some(q => q.review_status === 'PENDING' || q.mentor_verify_required);
  }

  get topicScoresArray(): { topic: string; score: number }[] {
    if (!this.effectivenessReport?.topic_scores) return [];
    return Object.entries(this.effectivenessReport.topic_scores).map(([topic, score]) => ({
      topic,
      score: Number(score)
    }));
  }

  ngOnInit() {
    if (this.isMentorOrAdmin) {
      this.activeTab = 'transcript';
    } else {
      this.activeTab = 'summary';
    }
    this.loadSummaryAndEffectiveness();
  }

  closeDialog() {
    this.close.emit();
  }

  setFeedback(msg: string, success: boolean) {
    this.feedbackMsg = msg;
    this.isSuccess = success;
    setTimeout(() => { this.feedbackMsg = ''; }, 6000);
  }

  onFileSelected(event: any) {
    const file = event.target.files?.[0];
    if (file) {
      this.selectedFile = file;
    }
  }

  uploadFile() {
    if (!this.selectedFile || !this.privacyConsent) return;
    this.loading = true;
    this.statusMessage = 'Uploading and validating transcript securely...';

    const formData = new FormData();
    formData.append('file', this.selectedFile);
    formData.append('live_class_id', this.liveClass.id.toString());
    formData.append('privacy_consent_acknowledged', 'true');
    if (this.topicsCovered) {
      formData.append('topics_covered', this.topicsCovered);
    }

    this.aiSummaryService.uploadTranscript(formData).subscribe({
      next: (t) => {
        this.loading = false;
        this.currentTranscript = t;
        this.setFeedback('Transcript uploaded successfully with privacy governance check.', true);
      },
      error: (err) => {
        this.loading = false;
        this.setFeedback(err.error?.detail || 'Failed to upload transcript.', false);
      }
    });
  }

  submitNotes() {
    if (!this.notesContent || !this.privacyConsent) return;
    this.loading = true;
    this.statusMessage = 'Storing lecture notes safely...';

    this.aiSummaryService.submitNotesTranscript({
      live_class_id: this.liveClass.id,
      notes: this.notesContent,
      topics_covered: this.topicsCovered,
      privacy_consent_acknowledged: true
    }).subscribe({
      next: (t) => {
        this.loading = false;
        this.currentTranscript = t;
        this.setFeedback('Lecture notes stored successfully.', true);
      },
      error: (err) => {
        this.loading = false;
        this.setFeedback(err.error?.detail || 'Failed to store notes.', false);
      }
    });
  }

  deleteRawText() {
    if (!this.currentTranscript) return;
    this.aiSummaryService.deleteRawTranscript(this.currentTranscript.id).subscribe({
      next: () => {
        if (this.currentTranscript) {
          this.currentTranscript.raw_text_present = false;
        }
        this.setFeedback('Raw transcript text purged immediately. Summaries preserved.', true);
      },
      error: (err) => {
        this.setFeedback(err.error?.detail || 'Failed to delete raw transcript.', false);
      }
    });
  }

  triggerGenerateSummary() {
    if (!this.currentTranscript) return;
    this.loading = true;
    this.statusMessage = 'Analyzing transcript and synthesizing class summary...';

    this.aiSummaryService.generateSummary(this.currentTranscript.id).subscribe({
      next: (sum) => {
        this.loading = false;
        this.currentSummary = sum;
        this.editRecap = sum.ase_recap;
        this.activeTab = 'summary';
        this.setFeedback('AI Class Summary synthesized successfully!', true);
      },
      error: (err) => {
        this.loading = false;
        this.setFeedback(err.error?.detail || 'Failed to generate summary.', false);
      }
    });
  }

  loadSummaryAndEffectiveness() {
    this.aiSummaryService.getSummaryByClass(this.liveClass.id).subscribe({
      next: (sum) => {
        this.currentSummary = sum;
        if (sum) {
          this.editRecap = sum.ase_recap;
        }
      },
      error: () => {}
    });

    if (this.isMentorOrAdmin) {
      this.aiSummaryService.getClassEffectiveness(this.liveClass.id).subscribe({
        next: (eff) => {
          this.effectivenessReport = eff;
        },
        error: () => {}
      });
    }
  }

  saveSummaryEdits() {
    if (!this.currentSummary) return;
    this.aiSummaryService.updateSummary(this.currentSummary.id, {
      ase_recap: this.editRecap
    }).subscribe({
      next: (updated) => {
        this.currentSummary = updated;
        this.isEditingSummary = false;
        this.setFeedback(`Summary updated to Version ${updated.version}.`, true);
      },
      error: (err) => {
        this.setFeedback(err.error?.detail || 'Failed to update summary.', false);
      }
    });
  }

  publishSummary() {
    if (!this.currentSummary) return;
    this.aiSummaryService.publishSummary(this.currentSummary.id).subscribe({
      next: (pub) => {
        this.currentSummary = pub;
        this.setFeedback('Summary published to ASE learners and notified!', true);
      },
      error: (err) => {
        this.setFeedback(err.error?.detail || 'Failed to publish summary.', false);
      }
    });
  }

  unpublishSummary() {
    if (!this.currentSummary) return;
    this.aiSummaryService.unpublishSummary(this.currentSummary.id).subscribe({
      next: (unpub) => {
        this.currentSummary = unpub;
        this.setFeedback('Summary unpublished.', true);
      },
      error: (err) => {
        this.setFeedback(err.error?.detail || 'Failed to unpublish summary.', false);
      }
    });
  }

  goToAssessmentStudio() {
    this.activeTab = 'assessment';
    if (this.currentSummary) {
      this.aiSummaryService.recommendPlan(this.currentSummary.id).subscribe({
        next: (plan) => {
          this.targetQuestionCount = plan.recommended_total_questions;
          this.easyPct = plan.difficulty_split['EASY'] || 35;
          this.mediumPct = plan.difficulty_split['MEDIUM'] || 45;
          this.hardPct = plan.difficulty_split['HARD'] || 20;
        },
        error: () => {}
      });
    }
  }

  generateAssessmentQuestions() {
    this.loading = true;
    this.statusMessage = 'Synthesizing question card deck with anti-bias quality checks...';

    this.aiSummaryService.generateAssessment({
      live_class_id: this.liveClass.id,
      title: `${this.liveClass.title} - Mastery Evaluation`,
      generation_mode: this.generationMode,
      recommended_total_questions: this.targetQuestionCount,
      difficulty_split: {
        EASY: this.easyPct,
        MEDIUM: this.mediumPct,
        HARD: this.hardPct
      },
      skill_category: 'Software Engineering'
    }).subscribe({
      next: (ass) => {
        this.loading = false;
        this.currentAssessment = ass;
        this.setFeedback(`Generated ${ass.questions.length} questions in card deck for review.`, true);
      },
      error: (err) => {
        this.loading = false;
        this.setFeedback(err.error?.detail || 'Failed to generate assessment questions.', false);
      }
    });
  }

  approveQuestion(q: AIGeneratedQuestion) {
    this.aiSummaryService.approveQuestion(q.id).subscribe({
      next: (updated) => {
        q.review_status = updated.review_status;
        q.mentor_verify_required = updated.mentor_verify_required;
      },
      error: (err) => {
        this.setFeedback(err.error?.detail || 'Failed to approve question.', false);
      }
    });
  }

  rejectQuestion(q: AIGeneratedQuestion) {
    this.aiSummaryService.rejectQuestion(q.id).subscribe({
      next: (updated) => {
        q.review_status = updated.review_status;
      },
      error: (err) => {
        this.setFeedback(err.error?.detail || 'Failed to reject question.', false);
      }
    });
  }

  regenerateQuestion(q: AIGeneratedQuestion) {
    this.aiSummaryService.regenerateQuestion(q.id).subscribe({
      next: (updated) => {
        q.question_text = updated.question_text;
        q.options = updated.options;
        q.correct_answers = updated.correct_answers;
        q.explanation = updated.explanation;
        q.review_status = updated.review_status;
        q.mentor_verify_required = updated.mentor_verify_required;
        this.setFeedback('Question regenerated with fresh concept variation.', true);
      },
      error: (err) => {
        this.setFeedback(err.error?.detail || 'Failed to regenerate question.', false);
      }
    });
  }

  approveAll() {
    if (!this.currentAssessment) return;
    this.aiSummaryService.approveAllQuestions(this.currentAssessment.id).subscribe({
      next: (ass) => {
        this.currentAssessment = ass;
        this.setFeedback('All questions approved and validated successfully!', true);
      },
      error: (err) => {
        this.setFeedback(err.error?.detail || 'Cannot approve all: check pending or flagged questions.', false);
      }
    });
  }

  exportApprovedToBank() {
    if (!this.currentAssessment) return;
    const approvedIds = this.currentAssessment.questions
      .filter(q => q.review_status === 'APPROVED')
      .map(q => q.id);

    if (approvedIds.length === 0) {
      this.setFeedback('No approved questions to export. Please approve questions first.', false);
      return;
    }

    this.aiSummaryService.exportToBank(this.currentAssessment.id, approvedIds).subscribe({
      next: (res) => {
        this.setFeedback(res.message, true);
      },
      error: (err) => {
        this.setFeedback(err.error?.detail || 'Failed to export questions to bank.', false);
      }
    });
  }

  finalizeAndAssign() {
    if (!this.currentAssessment) return;
    this.aiSummaryService.finalizeAndAssign(this.currentAssessment.id).subscribe({
      next: (res) => {
        if (this.currentAssessment) {
          this.currentAssessment.is_immutable = true;
          this.currentAssessment.assessment_id = res.assessment_id;
        }
        this.setFeedback('Assessment finalized, assigned, and locked as immutable!', true);
      },
      error: (err) => {
        this.setFeedback(err.error?.detail || 'Failed to finalize assessment.', false);
      }
    });
  }

  scheduleFollowUpMiniClass() {
    if (!this.effectivenessReport?.follow_up_proposal) return;
    const prop = this.effectivenessReport.follow_up_proposal;
    this.scheduleMiniClass.emit({
      title: prop.title,
      duration: prop.duration_minutes || 15
    });
    this.closeDialog();
  }

  getScoreColorClass(score: number): string {
    if (score >= 70) return 'fill-pass';
    if (score >= 60) return 'fill-warn';
    return 'fill-fail';
  }
}
