import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatTabsModule } from '@angular/material/tabs';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration, ChartData } from 'chart.js';
import { getCssToken } from '../../core/utils/theme-tokens.util';
import { AnalyticsService } from '../../core/services/analytics.service';
import { CodingService } from '../../core/services/coding.service';
import { Phase9Service } from '../../core/services/phase9.service';
import { PlagiarismFlag } from '../../core/models/coding.model';
import { RiskSignal } from '../../core/models/phase9.model';
import {
  MentorDashboardData, HeatmapRow, MentorRankingRow, NeedsAttentionItem
} from '../../core/models/analytics.model';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-mentor-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    MatCardModule,
    MatIconModule,
    MatTableModule,
    MatButtonModule,
    MatSelectModule,
    MatFormFieldModule,
    MatChipsModule,
    MatTooltipModule,
    MatTabsModule,
    MatProgressSpinnerModule,
    MatProgressBarModule,
    BaseChartDirective
  ],
  template: `
    <div class="mentor-analytics-page">
      <!-- Header Banner -->
      <div class="page-header">
        <div>
          <h1>Mentor Analytics & Performance Hub</h1>
          <p class="subtitle">Monitor cohort mastery, spot at-risk mentees, and track training engagement</p>
        </div>
        <div class="filter-actions" *ngIf="dashboardData">
          <mat-form-field appearance="outline" class="cohort-filter">
            <mat-label>Filter Cohort</mat-label>
            <mat-select [(ngModel)]="selectedCohortId" (selectionChange)="onCohortChange()">
              <mat-option [value]="undefined">All Assigned Cohorts</mat-option>
              <mat-option *ngFor="let c of dashboardData.cohort_options" [value]="c.id">{{ c.name }}</mat-option>
            </mat-select>
          </mat-form-field>
          <button mat-flat-button color="primary" class="export-btn" (click)="exportCohortCsv()" [disabled]="!selectedCohortId || exportingCsv">
            <mat-icon>download</mat-icon>
            {{ exportingCsv ? 'Exporting...' : 'Export Cohort CSV' }}
          </button>
        </div>
      </div>

      <!-- Loading State -->
      <div *ngIf="loading" class="loading-state">
        <mat-spinner diameter="44"></mat-spinner>
        <span>Synthesizing cohort learning data...</span>
      </div>

      <!-- Main Content -->
      <div *ngIf="!loading && dashboardData" class="dashboard-body">
        
        <!-- Summary Metric Cards -->
        <div class="metrics-grid">
          <mat-card class="stat-card">
            <div class="stat-icon blue">
              <mat-icon>people</mat-icon>
            </div>
            <div class="stat-text">
              <span class="label">Total Mentees</span>
              <span class="value">{{ dashboardData.ranking_table.length }}</span>
              <span class="hint">In active cohort filter</span>
            </div>
          </mat-card>

          <mat-card class="stat-card">
            <div class="stat-icon green">
              <mat-icon>trending_up</mat-icon>
            </div>
            <div class="stat-text">
              <span class="label">Cohort Average</span>
              <span class="value">{{ cohortAverage !== null ? (cohortAverage | number:'1.1-1') + '%' : 'N/A' }}</span>
              <span class="hint">Mean score across attempts</span>
            </div>
          </mat-card>

          <mat-card class="stat-card">
            <div class="stat-icon red">
              <mat-icon>notification_important</mat-icon>
            </div>
            <div class="stat-text">
              <span class="label">Needs Attention</span>
              <span class="value" [class.text-danger]="dashboardData.needs_attention.length > 0">{{ dashboardData.needs_attention.length }}</span>
              <span class="hint">Mentees requiring guidance</span>
            </div>
          </mat-card>

          <mat-card class="stat-card">
            <div class="stat-icon orange">
              <mat-icon>groups</mat-icon>
            </div>
            <div class="stat-text">
              <span class="label">Assigned Cohorts</span>
              <span class="value">{{ dashboardData.cohort_options.length }}</span>
              <span class="hint">Active batches</span>
            </div>
          </mat-card>

          <mat-card class="stat-card">
            <div class="stat-icon purple">
              <mat-icon>school</mat-icon>
            </div>
            <div class="stat-text">
              <span class="label">Training Completion</span>
              <span class="value">{{ dashboardData.training_metrics ? (dashboardData.training_metrics.completion_rate | number:'1.0-0') + '%' : '0%' }}</span>
              <span class="hint">{{ dashboardData.training_metrics?.completed || 0 }} of {{ dashboardData.training_metrics?.total_assigned || 0 }} completed</span>
            </div>
          </mat-card>

          <mat-card class="stat-card">
            <div class="stat-icon teal">
              <mat-icon>video_camera_front</mat-icon>
            </div>
            <div class="stat-text">
              <span class="label">Class Attendance</span>
              <span class="value">{{ dashboardData.attendance_metrics ? (dashboardData.attendance_metrics.attendance_rate | number:'1.0-0') + '%' : '0%' }}</span>
              <span class="hint">{{ dashboardData.attendance_metrics?.total_attended || 0 }} attended / {{ dashboardData.attendance_metrics?.total_invited || 0 }} invited</span>
            </div>
          </mat-card>
        </div>

        <!-- Phase 9 Early Warning Center -->
        <mat-card class="attention-card early-warning-card" *ngIf="riskSignals.length > 0">
          <div class="attention-header">
            <div class="title-with-badge">
              <mat-icon class="text-danger">shield</mat-icon>
              <h3>Early Warning System & Mentor Coaching Signals ({{ riskSignals.length }})</h3>
            </div>
            <span class="hint-text">🔒 Mentor-only diagnostic: AI-written risk explanations with supportive coaching nudges. Strictly hidden from ASEs.</span>
          </div>
          <div class="risk-signals-list">
            <div *ngFor="let s of riskSignals" class="risk-item" [class.risk-item-high]="s.risk_level === 'HIGH'">
              <div class="risk-item-header">
                <div class="risk-user-info">
                  <span class="risk-user-name">{{ s.ase_name }}</span>
                  <span class="risk-level-badge" [ngClass]="'badge-' + s.risk_level.toLowerCase()">
                    {{ s.risk_level }} RISK (Score: {{ s.risk_score }}/100)
                  </span>
                </div>
                <div class="risk-action-col">
                  <button
                    class="btn-nudge"
                    [disabled]="!s.can_nudge || isNudging[s.ase_id]"
                    (click)="sendSupportiveNudge(s)"
                    title="Send supportive, encouragement nudge (Rate limit: 1 per 48h)"
                  >
                    <mat-icon>send</mat-icon>
                    <span *ngIf="s.can_nudge && !isNudging[s.ase_id]">Send Supportive Nudge</span>
                    <span *ngIf="isNudging[s.ase_id]">Sending...</span>
                    <span *ngIf="!s.can_nudge">Nudged (Cooldown Active)</span>
                  </button>
                </div>
              </div>

              <!-- Flagged Reasons Chips -->
              <div class="risk-factors" *ngIf="s.flagged_reasons.length > 0">
                <span class="factor-tag" *ngFor="let r of s.flagged_reasons">⚠️ {{ r }}</span>
              </div>

              <!-- AI Coaching Recommendation -->
              <div class="ai-coach-quote" *ngIf="s.ai_explanation">
                <span class="coach-icon">💡</span>
                <div class="coach-text">
                  <strong>AI Coaching Diagnosis:</strong> {{ s.ai_explanation }}
                </div>
              </div>
            </div>
          </div>
        </mat-card>

        <!-- Needs Attention Section (If any) -->
        <mat-card class="attention-card" *ngIf="dashboardData.needs_attention.length > 0">
          <div class="attention-header">
            <div class="title-with-badge">
              <mat-icon class="text-danger">warning</mat-icon>
              <h3>Needs Immediate Attention ({{ dashboardData.needs_attention.length }})</h3>
            </div>
            <span class="hint-text">Mentees with failing scores, integrity flags, or pending attempts</span>
          </div>
          <div class="attention-grid">
            <div class="attention-item" *ngFor="let item of dashboardData.needs_attention">
              <div class="ase-avatar">{{ item.ase_name[0] }}</div>
              <div class="item-content">
                <div class="item-title-row">
                  <span class="ase-name">{{ item.ase_name }}</span>
                  <span class="reason-badge" [ngClass]="getReasonBadgeClass(item.reason)">{{ item.reason }}</span>
                </div>
                <div class="item-meta">
                  <span>{{ item.ase_email }}</span>
                  <span *ngIf="item.score !== undefined && item.score !== null">Score: <strong>{{ item.score | number:'1.1-1' }}%</strong></span>
                  <span *ngIf="item.score === undefined || item.score === null" class="text-muted">Not attempted</span>
                </div>
              </div>
            </div>
          </div>
        </mat-card>

        <!-- Overdue Training Modules Section (If any) -->
        <mat-card class="attention-card overdue-card" *ngIf="dashboardData.overdue_trainings && dashboardData.overdue_trainings.length > 0">
          <div class="attention-header">
            <div class="title-with-badge">
              <mat-icon class="text-danger">schedule</mat-icon>
              <h3>Overdue Training Modules ({{ dashboardData.overdue_trainings.length }})</h3>
            </div>
            <span class="hint-text">Assigned modules that have passed their target completion due date</span>
          </div>
          <div class="table-responsive">
            <table class="styled-table">
              <thead>
                <tr>
                  <th>Associate Engineer</th>
                  <th>Training Title</th>
                  <th>Due Date</th>
                  <th>Current Progress</th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let item of dashboardData.overdue_trainings">
                  <td class="font-bold">{{ item.ase_name }}</td>
                  <td>{{ item.training_title }}</td>
                  <td class="text-danger font-bold">{{ item.due_date }}</td>
                  <td>
                    <div class="mini-bar">
                      <div class="mini-bar-fill" [style.width.%]="item.progress_percent"></div>
                    </div>
                    <span class="mini-bar-text">{{ item.progress_percent }}%</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </mat-card>

        <!-- Coding Plagiarism Flags Section -->
        <mat-card class="attention-card plagiarism-card" *ngIf="plagiarismFlags.length > 0">
          <div class="attention-header">
            <div class="title-with-badge">
              <mat-icon class="text-danger">policy</mat-icon>
              <h3>Code Integrity & Plagiarism Signals ({{ plagiarismFlags.length }})</h3>
            </div>
            <span class="hint-text">Pairs of assigned mentees flagged with high source code similarity (>= 75%)</span>
          </div>
          <div class="table-responsive">
            <table class="styled-table">
              <thead>
                <tr>
                  <th>Question</th>
                  <th>Mentee 1</th>
                  <th>Mentee 2</th>
                  <th>Code Similarity</th>
                  <th>Status</th>
                  <th>Flagged Date</th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let p of plagiarismFlags">
                  <td>Question #{{ p.question_id }}</td>
                  <td class="font-bold">{{ p.ase1_name }}</td>
                  <td class="font-bold">{{ p.ase2_name }}</td>
                  <td>
                    <span class="score-badge fail">{{ p.similarity_score }}% match</span>
                  </td>
                  <td>
                    <span class="reason-badge badge-danger">{{ p.status }}</span>
                  </td>
                  <td class="text-muted">{{ p.flagged_at | date:'mediumDate' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </mat-card>

        <!-- Cohort Average Radar & Rankings Grid -->
        <div class="charts-rankings-row">
          <!-- Cohort Radar -->
          <mat-card class="panel-card radar-panel">
            <mat-card-header>
              <mat-icon mat-card-avatar color="primary">radar</mat-icon>
              <mat-card-title>Cohort Skill Distribution</mat-card-title>
              <mat-card-subtitle>Mean competence scores across skill domains</mat-card-subtitle>
            </mat-card-header>
            <mat-card-content class="radar-box">
              <div *ngIf="radarChartData.labels?.length; else emptyRadar" class="radar-canvas-wrap">
                <canvas baseChart
                  [data]="radarChartData"
                  [options]="radarChartOptions"
                  [type]="'radar'">
                </canvas>
              </div>
              <ng-template #emptyRadar>
                <div class="empty-placeholder">No attempt data available for radar plot.</div>
              </ng-template>
            </mat-card-content>
          </mat-card>

          <!-- ASE Ranking Table -->
          <mat-card class="panel-card ranking-panel">
            <mat-card-header>
              <mat-icon mat-card-avatar color="accent">leaderboard</mat-icon>
              <mat-card-title>Mentee Rankings</mat-card-title>
              <mat-card-subtitle>Ranked by overall average assessment score</mat-card-subtitle>
            </mat-card-header>
            <mat-card-content class="table-content-wrap">
              <div class="table-responsive">
                <table class="styled-table">
                  <thead>
                    <tr>
                      <th style="width: 50px;">Rank</th>
                      <th>Associate Engineer</th>
                      <th>Avg Score</th>
                      <th>Attempts</th>
                      <th>Suggested Focus</th>
                      <th style="width: 60px;">PDF</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr *ngFor="let r of dashboardData.ranking_table">
                      <td>
                        <span class="rank-badge" [class.rank-top]="r.rank === 1 || r.rank === 2 || r.rank === 3">{{ r.rank }}</span>
                      </td>
                      <td>
                        <div class="cell-user">
                          <span class="cell-name">{{ r.ase_name }}</span>
                          <span class="cell-email">{{ r.ase_email }}</span>
                        </div>
                      </td>
                      <td>
                        <div *ngIf="r.has_attempt" class="rank-progress-cell">
                          <span class="score-badge" [class.pass]="r.average_score >= 70" [class.fail]="r.average_score < 70">
                            {{ r.average_score | number:'1.1-1' }}%
                          </span>
                          <mat-progress-bar mode="determinate" [value]="r.average_score" class="rank-mini-bar"></mat-progress-bar>
                        </div>
                        <span *ngIf="!r.has_attempt" class="chip-na">Not attempted</span>
                      </td>
                      <td>{{ r.attempts_count }}</td>
                      <td>
                        <span class="focus-chip">{{ r.suggested_focus }}</span>
                      </td>
                      <td>
                        <button mat-icon-button color="primary" matTooltip="Download candidate PDF report" (click)="downloadMenteePdf(r)" [disabled]="!r.latest_attempt_id">
                          <mat-icon>picture_as_pdf</mat-icon>
                        </button>
                      </td>
                    </tr>
                    <tr *ngIf="dashboardData.ranking_table.length === 0">
                      <td colspan="6" class="text-center text-muted py-3">No mentees found.</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </mat-card-content>
          </mat-card>
        </div>

        <!-- Phase 9 Re-Assessment Growth & 30/60/90 Day Milestones -->
        <mat-card class="panel-card full-span reassessment-card">
          <div class="panel-header-row">
            <div>
              <h3>30 / 60 / 90-Day Re-Assessment Growth Diagnostics</h3>
              <p class="subtitle">Evaluate real engineering skill uplift with distinct randomized question sets to eliminate memorization bias.</p>
            </div>
            <button class="btn-schedule-reassessment" (click)="openScheduleModal()">
              <mat-icon>event_repeat</mat-icon> Schedule Re-Assessment
            </button>
          </div>

          <div class="table-responsive" *ngIf="reassessmentGrowth && reassessmentGrowth.length > 0; else noReassessments">
            <table class="styled-table">
              <thead>
                <tr>
                  <th>Associate Engineer</th>
                  <th>Milestone Interval</th>
                  <th>Original Score</th>
                  <th>Re-Assessment Score</th>
                  <th>Score Growth Uplift</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let g of reassessmentGrowth">
                  <td class="font-bold">{{ g.ase_name }}</td>
                  <td><span class="milestone-badge">{{ g.reassessment_day }}-Day Milestone</span></td>
                  <td>{{ g.original_score | number:'1.1-1' }}%</td>
                  <td>
                    <span *ngIf="g.is_completed" class="score-badge pass">{{ g.reassessment_score | number:'1.1-1' }}%</span>
                    <span *ngIf="!g.is_completed" class="chip-na">Pending</span>
                  </td>
                  <td>
                    <span *ngIf="g.is_completed" class="growth-pill" [class.growth-pos]="g.growth_pct >= 0" [class.growth-neg]="g.growth_pct < 0">
                      {{ g.growth_pct >= 0 ? '+' : '' }}{{ g.growth_pct | number:'1.1-1' }}%
                    </span>
                    <span *ngIf="!g.is_completed" class="text-muted">—</span>
                  </td>
                  <td>
                    <span class="badge" [class.badge-completed]="g.is_completed" [class.badge-pending]="!g.is_completed">
                      {{ g.is_completed ? 'Completed' : 'Scheduled' }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <ng-template #noReassessments>
            <div class="empty-reassessment-state">
              <mat-icon>trending_up</mat-icon>
              <p>No 30/60/90-day re-assessments scheduled yet. Click "Schedule Re-Assessment" above to schedule a milestone test for an assigned mentee.</p>
            </div>
          </ng-template>
        </mat-card>

        <!-- Phase 9 Schedule Re-assessment Modal -->
        <div class="modal-backdrop" *ngIf="showScheduleModal" (click)="closeScheduleModal()">
          <div class="modal-box" (click)="$event.stopPropagation()">
            <div class="modal-header">
              <h3>Schedule 30/60/90-Day Re-Assessment</h3>
              <button class="btn-close" (click)="closeScheduleModal()">✕</button>
            </div>
            <div class="modal-body">
              <p class="modal-info">A distinct, randomized question bank variant will be prepared to prevent memorization.</p>
              <div class="form-group">
                <label>Target Mentee</label>
                <select [(ngModel)]="schedTargetAseId">
                  <option *ngFor="let r of dashboardData.ranking_table" [value]="r.ase_id">{{ r.ase_name }}</option>
                </select>
              </div>
              <div class="form-group">
                <label>Milestone Category</label>
                <select [(ngModel)]="schedReassessmentDay">
                  <option [value]="30">30-Day Re-Assessment</option>
                  <option [value]="60">60-Day Re-Assessment</option>
                  <option [value]="90">90-Day Re-Assessment</option>
                </select>
              </div>
              <div class="form-group">
                <label>Schedule Execution (Days from today)</label>
                <input type="number" min="0" max="90" [(ngModel)]="schedDaysFromNow" />
              </div>
            </div>
            <div class="modal-footer">
              <button class="btn-cancel" (click)="closeScheduleModal()">Cancel</button>
              <button class="btn-confirm" [disabled]="!schedTargetAseId || isScheduling" (click)="submitScheduleReassessment()">
                {{ isScheduling ? 'Scheduling...' : 'Confirm Schedule' }}
              </button>
            </div>
          </div>
        </div>

        <!-- Weak-Area Heatmap (ASEs x Skills) -->
        <mat-card class="panel-card full-span">
          <mat-card-header>
            <mat-icon mat-card-avatar color="primary">grid_on</mat-icon>
            <mat-card-title>Skill Competence Heatmap</mat-card-title>
            <mat-card-subtitle>Matrix of mentee skill scores with diagnostic color intensity</mat-card-subtitle>
          </mat-card-header>
          <mat-card-content>
            <div class="heatmap-legend">
              <span class="legend-item"><span class="legend-dot green"></span> ≥ 70% Strong</span>
              <span class="legend-item"><span class="legend-dot yellow"></span> 50% - 69% Medium</span>
              <span class="legend-item"><span class="legend-dot red"></span> &lt; 50% Weak</span>
              <span class="legend-item"><span class="legend-dot gray"></span> Not Attempted / No Data</span>
            </div>

            <div class="table-responsive heatmap-wrapper">
              <table class="styled-table heatmap-table">
                <thead>
                  <tr>
                    <th class="sticky-col">Associate Engineer</th>
                    <th *ngFor="let skill of dashboardData.heatmap.skills" class="text-center">
                      {{ skill }}
                    </th>
                    <th class="text-center">Status</th>
                  </tr>
                </thead>
                <tbody>
                  <tr *ngFor="let row of dashboardData.heatmap.rows">
                    <td class="sticky-col">
                      <div class="cell-user">
                        <span class="cell-name">{{ row.ase_name }}</span>
                      </div>
                    </td>
                    <td *ngFor="let skill of dashboardData.heatmap.skills" class="text-center heatmap-cell" [ngClass]="getScoreHeatmapClass(row.scores[skill])">
                      {{ row.scores[skill] !== null && row.scores[skill] !== undefined ? (row.scores[skill] | number:'1.0-0') + '%' : '—' }}
                    </td>
                    <td class="text-center font-bold">
                      <span *ngIf="row.has_attempt" class="text-success">Active</span>
                      <span *ngIf="!row.has_attempt" class="chip-na">Not attempted</span>
                    </td>
                  </tr>
                  <tr *ngIf="dashboardData.heatmap.rows.length === 0">
                    <td [attr.colspan]="dashboardData.heatmap.skills.length + 2" class="text-center text-muted py-4">
                      No mentee heatmap data available.
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </mat-card-content>
        </mat-card>

      </div>
    </div>
  `,
  styles: [`
    .mentor-analytics-page {
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
      font-size: 1.75rem;
      font-weight: 700;
    }

    .subtitle {
      margin: 4px 0 0;
      color: #64748B;
      font-size: 0.95rem;
    }

    .filter-actions {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .cohort-filter {
      min-width: 220px;
    }

    .loading-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 16px;
      padding: 60px 0;
      color: #64748B;
    }

    /* Metrics */
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
    }

    .stat-card {
      display: flex;
      flex-direction: row;
      align-items: center;
      gap: 16px;
      padding: 16px 20px;
      border-radius: 12px;
      border: 1px solid #E2E8F0;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
      background: #ffffff;
    }

    .stat-icon {
      width: 48px;
      height: 48px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .stat-icon mat-icon { font-size: 26px; width: 26px; height: 26px; }
    .stat-icon.blue { background: #EFF6FF; color: var(--csm-primary); }
    .stat-icon.green { background: #ECFDF5; color: #059669; }
    .stat-icon.red { background: #FEF2F2; color: #DC2626; }
    .stat-icon.orange { background: #FFF7ED; color: #EA580C; }
    .stat-icon.purple { background: #F3E8FF; color: #7E22CE; }
    .stat-icon.teal { background: #F0FDFA; color: #0F766E; }

    .stat-text {
      display: flex;
      flex-direction: column;
    }

    .stat-text .label {
      font-size: 0.8rem;
      font-weight: 600;
      color: #64748B;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .stat-text .value {
      font-size: 1.6rem;
      font-weight: 700;
      color: #0F172A;
      line-height: 1.2;
    }

    .stat-text .hint {
      font-size: 0.75rem;
      color: #94A3B8;
      margin-top: 2px;
    }

    /* Attention Cards */
    .attention-card {
      border-radius: 12px;
      border: 1px solid #FECACA;
      background: #FFFBFB;
      padding: 16px 20px;
      box-shadow: 0 1px 3px rgba(220, 38, 38, 0.05);
    }

    .overdue-card {
      border-color: #FED7AA;
      background: #FFFDF9;
    }

    .plagiarism-card {
      border-color: #E2E8F0;
      background: #FFFFFF;
    }

    .early-warning-card {
      border-color: #CBD5E1;
      background: #F8FAFC;
    }

    .attention-header {
      margin-bottom: 14px;
    }

    .title-with-badge {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .title-with-badge h3 {
      margin: 0;
      font-size: 1rem;
      font-weight: 700;
      color: #0F172A;
    }

    .hint-text {
      font-size: 0.8rem;
      color: #64748B;
      display: block;
      margin-top: 2px;
    }

    /* Early Warning Signals List */
    .risk-signals-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .risk-item {
      background: white;
      border: 1px solid #E2E8F0;
      border-left: 4px solid #F59E0B;
      border-radius: 8px;
      padding: 14px 16px;
    }
    .risk-item-high {
      border-left-color: #EF4444;
      background: #FEF2F2;
    }
    .risk-item-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }
    .risk-user-info {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .risk-user-name {
      font-size: 15px;
      font-weight: 700;
      color: #0F172A;
    }
    .risk-level-badge {
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 4px;
    }
    .badge-high { background: #FEE2E2; color: #991B1B; }
    .badge-medium { background: #FEF3C7; color: #92400E; }
    .badge-low { background: #DCFCE7; color: #166534; }
    .btn-nudge {
      display: flex;
      align-items: center;
      gap: 6px;
      background: var(--csm-primary);
      color: white;
      border: none;
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-nudge mat-icon { font-size: 16px; width: 16px; height: 16px; }
    .btn-nudge:hover:not(:disabled) { background: #172554; }
    .btn-nudge:disabled { opacity: 0.5; cursor: not-allowed; background: #64748B; }

    .risk-factors {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 8px;
    }
    .factor-tag {
      background: #F1F5F9;
      color: #475569;
      font-size: 11px;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 4px;
    }
    .ai-coach-quote {
      display: flex;
      gap: 8px;
      background: #EFF6FF;
      border-radius: 6px;
      padding: 8px 12px;
      font-size: 12px;
      color: #1E293B;
      line-height: 1.4;
    }

    /* Re-Assessment Growth Card */
    .reassessment-card {
      margin-top: 10px;
    }
    .panel-header-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      flex-wrap: wrap;
      gap: 12px;
    }
    .panel-header-row h3 {
      margin: 0 0 4px 0;
      font-size: 17px;
      font-weight: 700;
      color: #0F172A;
    }
    .btn-schedule-reassessment {
      display: flex;
      align-items: center;
      gap: 6px;
      background: var(--csm-accent);
      color: white;
      border: none;
      padding: 8px 14px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
    }
    .btn-schedule-reassessment mat-icon { font-size: 18px; width: 18px; height: 18px; }
    .milestone-badge {
      background: #F1F5F9;
      color: var(--csm-primary);
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 4px;
    }
    .growth-pill {
      font-weight: 700;
      font-size: 12px;
      padding: 2px 8px;
      border-radius: 4px;
    }
    .growth-pos { background: #DCFCE7; color: #166534; }
    .growth-neg { background: #FEE2E2; color: #991B1B; }
    .empty-reassessment-state {
      padding: 30px;
      text-align: center;
      color: #64748B;
      mat-icon { font-size: 36px; width: 36px; height: 36px; color: #94A3B8; margin-bottom: 8px; }
      p { margin: 0; font-size: 13px; }
    }

    /* Modal Backdrop */
    .modal-backdrop {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(15, 23, 42, 0.6);
      backdrop-filter: blur(2px);
      z-index: 9999;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    .modal-box {
      background: white;
      border-radius: 12px;
      max-width: 480px;
      width: 100%;
      padding: 24px;
      box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2);
    }
    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      h3 { margin: 0; font-size: 18px; color: #0F172A; }
    }
    .btn-close {
      background: none;
      border: none;
      font-size: 18px;
      cursor: pointer;
      color: #64748B;
    }
    .modal-info {
      font-size: 13px;
      color: #64748B;
      margin-bottom: 16px;
    }
    .form-group {
      margin-bottom: 14px;
      label { display: block; font-size: 12px; font-weight: 600; color: #475569; margin-bottom: 4px; }
      select, input {
        width: 100%;
        padding: 8px 12px;
        border: 1px solid #CBD5E1;
        border-radius: 6px;
        font-size: 14px;
      }
    }
    .modal-footer {
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      margin-top: 20px;
    }
    .btn-cancel {
      background: #F1F5F9;
      color: #475569;
      border: none;
      padding: 8px 14px;
      border-radius: 6px;
      cursor: pointer;
    }
    .btn-confirm {
      background: var(--csm-primary);
      color: white;
      border: none;
      padding: 8px 16px;
      border-radius: 6px;
      font-weight: 600;
      cursor: pointer;
    }
    .btn-confirm:disabled { opacity: 0.5; cursor: not-allowed; }

    .attention-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 12px;
    }

    .attention-item {
      display: flex;
      align-items: center;
      gap: 12px;
      background: #ffffff;
      padding: 10px 14px;
      border-radius: 8px;
      border: 1px solid #FEE2E2;
    }

    .ase-avatar {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: var(--csm-primary);
      color: #ffffff;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 0.9rem;
      flex-shrink: 0;
    }

    .item-content {
      display: flex;
      flex-direction: column;
      flex-grow: 1;
      overflow: hidden;
    }

    .item-title-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .ase-name {
      font-weight: 600;
      font-size: 0.85rem;
      color: #0F172A;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .reason-badge {
      font-size: 0.7rem;
      font-weight: 600;
      padding: 2px 6px;
      border-radius: 4px;
    }

    .badge-failing { background: #FEE2E2; color: #991B1B; }
    .badge-flagged { background: #FEF3C7; color: #92400E; }
    .badge-unattempted { background: #F1F5F9; color: #475569; }

    .item-meta {
      display: flex;
      justify-content: space-between;
      font-size: 0.75rem;
      color: #64748B;
      margin-top: 2px;
    }

    /* Charts & Rankings Row */
    .charts-rankings-row {
      display: grid;
      grid-template-columns: 1fr 1.3fr;
      gap: 20px;
    }

    @media (max-width: 1024px) {
      .charts-rankings-row {
        grid-template-columns: 1fr;
      }
    }

    .panel-card {
      border-radius: 12px;
      border: 1px solid #E2E8F0;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
      background: #ffffff;
      padding: 16px;
    }

    .full-span {
      margin-top: 4px;
    }

    .radar-box {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 16px;
      min-height: 320px;
    }

    .radar-canvas-wrap {
      width: 100%;
      height: 320px;
      position: relative;
    }

    .empty-placeholder {
      color: #94A3B8;
      font-style: italic;
    }

    /* Table styles */
    .styled-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.88rem;
    }

    .styled-table th {
      text-align: left;
      padding: 10px 14px;
      font-weight: 600;
      color: #475569;
      border-bottom: 2px solid #E2E8F0;
      background: #F8FAFC;
    }

    .styled-table td {
      padding: 12px 14px;
      border-bottom: 1px solid #F1F5F9;
      color: #1E293B;
      vertical-align: middle;
    }

    .rank-badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 26px;
      height: 26px;
      border-radius: 50%;
      background: #F1F5F9;
      font-weight: 700;
      font-size: 0.8rem;
      color: #475569;
    }

    .rank-top {
      background: #FEF3C7;
      color: #B45309;
    }

    .cell-user {
      display: flex;
      flex-direction: column;
    }

    .cell-name {
      font-weight: 600;
      color: #0F172A;
    }

    .cell-email {
      font-size: 0.78rem;
      color: #64748B;
    }

    .score-badge {
      font-weight: 700;
      font-size: 0.82rem;
      padding: 3px 8px;
      border-radius: 6px;
    }

    .score-badge.pass { background: #ECFDF5; color: #065F46; }
    .score-badge.fail { background: #FEF2F2; color: #991B1B; }

    .chip-na {
      background: #F1F5F9;
      color: #64748B;
      font-size: 0.75rem;
      padding: 2px 6px;
      border-radius: 4px;
    }

    .focus-chip {
      background: #F8FAFC;
      border: 1px solid #E2E8F0;
      color: #334155;
      font-size: 0.78rem;
      padding: 3px 8px;
      border-radius: 6px;
      display: inline-block;
    }

    /* Mini progress bar */
    .mini-bar {
      height: 6px;
      background: #E2E8F0;
      border-radius: 3px;
      overflow: hidden;
      margin-bottom: 2px;
      min-width: 80px;
    }

    .mini-bar-fill {
      height: 100%;
      background: #EA580C;
      border-radius: 3px;
    }

    .mini-bar-text {
      font-size: 0.75rem;
      color: #64748B;
      font-weight: 600;
    }

    /* Heatmap styles */
    .heatmap-legend {
      display: flex;
      gap: 16px;
      padding: 10px 0 14px;
      font-size: 0.8rem;
      color: #475569;
    }

    .legend-item {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .legend-dot {
      width: 12px;
      height: 12px;
      border-radius: 3px;
    }

    .legend-dot.green { background: #ECFDF5; border: 1px solid #059669; }
    .legend-dot.yellow { background: #FEF3C7; border: 1px solid #D97706; }
    .legend-dot.red { background: #FEE2E2; border: 1px solid #DC2626; }
    .legend-dot.gray { background: #F8FAFC; border: 1px solid #CBD5E1; }

    .heatmap-wrapper {
      max-height: 400px;
      overflow: auto;
      border: 1px solid #E2E8F0;
      border-radius: 8px;
    }

    .heatmap-table th, .heatmap-table td {
      border: 1px solid #E2E8F0;
    }

    .sticky-col {
      position: sticky;
      left: 0;
      background: #ffffff;
      z-index: 2;
      min-width: 180px;
    }

    .heatmap-cell {
      font-weight: 600;
      font-size: 0.85rem;
      padding: 8px 12px !important;
    }

    .cell-green { background: var(--color-success-bg); color: var(--color-success-text); }
    .cell-yellow { background: var(--color-warning-bg); color: var(--color-warning-text); }
    .cell-red { background: var(--color-danger-bg); color: var(--color-danger-text); }
    .cell-gray { background: var(--bg-main); color: var(--text-muted); }

    .text-center { text-align: center; }
    .font-bold { font-weight: 700; }
    .text-danger { color: var(--color-danger); }
    .text-orange { color: var(--csm-accent); }
    .text-muted { color: var(--text-muted); }
    .text-success { color: var(--color-success); }
  `]
})
export class MentorDashboardComponent implements OnInit {
  dashboardData: MentorDashboardData | null = null;
  selectedCohortId: number | undefined = undefined;
  cohortAverage: number | null = null;
  loading = true;
  exportingCsv = false;

  // Phase 9 Early Warning & Nudges
  riskSignals: RiskSignal[] = [];
  isNudging: { [aseId: number]: boolean } = {};

  // Phase 9 Re-assessment Growth
  reassessmentGrowth: any[] = [];
  showScheduleModal: boolean = false;
  schedTargetAseId: number | null = null;
  schedReassessmentDay: number = 30;
  schedDaysFromNow: number = 7;
  isScheduling: boolean = false;

  radarChartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      r: { min: 0, max: 100, ticks: { stepSize: 25 } }
    },
    plugins: {
      legend: { display: false }
    }
  };
  radarChartData: ChartData<'radar'> = { labels: [], datasets: [] };

  plagiarismFlags: PlagiarismFlag[] = [];

  constructor(
    private analyticsService: AnalyticsService,
    private codingService: CodingService,
    private phase9Service: Phase9Service
  ) {}

  ngOnInit(): void {
    this.loadDashboardData();
    this.loadPlagiarismFlags();
    this.loadRiskSignals();
    this.loadReassessmentGrowth();
  }

  loadRiskSignals(): void {
    this.phase9Service.getRiskSignals().subscribe({
      next: (signals) => this.riskSignals = signals,
      error: (err) => console.error('Failed to load risk signals:', err)
    });
  }

  sendSupportiveNudge(signal: RiskSignal): void {
    this.isNudging[signal.ase_id] = true;
    this.phase9Service.sendMentorNudge(signal.ase_id).subscribe({
      next: () => {
        this.isNudging[signal.ase_id] = false;
        signal.can_nudge = false;
      },
      error: (err) => {
        this.isNudging[signal.ase_id] = false;
        alert(err.error?.detail || 'Failed to send nudge');
      }
    });
  }

  loadReassessmentGrowth(): void {
    this.phase9Service.getReassessmentGrowth(undefined, this.selectedCohortId).subscribe({
      next: (data) => this.reassessmentGrowth = data,
      error: (err) => console.error('Failed to load reassessment growth:', err)
    });
  }

  openScheduleModal(): void {
    this.showScheduleModal = true;
    if (this.dashboardData && this.dashboardData.ranking_table.length > 0) {
      this.schedTargetAseId = this.dashboardData.ranking_table[0].ase_id;
    }
  }

  closeScheduleModal(): void {
    this.showScheduleModal = false;
  }

  submitScheduleReassessment(): void {
    if (!this.schedTargetAseId) return;
    this.isScheduling = true;
    this.phase9Service.scheduleReassessment({
      ase_id: Number(this.schedTargetAseId),
      original_assignment_id: 1, // baseline link
      reassessment_day: Number(this.schedReassessmentDay),
      scheduled_days_from_now: Number(this.schedDaysFromNow)
    }).subscribe({
      next: () => {
        this.isScheduling = false;
        this.closeScheduleModal();
        this.loadReassessmentGrowth();
      },
      error: (err) => {
        this.isScheduling = false;
        alert(err.error?.detail || 'Failed to schedule re-assessment');
      }
    });
  }

  loadPlagiarismFlags(): void {
    this.codingService.getPlagiarismFlags().subscribe({
      next: (flags) => this.plagiarismFlags = flags,
      error: (err) => console.error('Failed to load plagiarism flags', err)
    });
  }

  loadDashboardData(): void {
    this.loading = true;
    this.analyticsService.getMentorDashboard(this.selectedCohortId).subscribe({
      next: (data: MentorDashboardData) => {
        this.dashboardData = data;
        this.buildRadarChart(data);
        this.computeCohortAverage(data);
        this.loading = false;
      },
      error: (err: any) => {
        console.error('Failed to load mentor dashboard', err);
        this.loading = false;
      }
    });
  }

  onCohortChange(): void {
    this.loadDashboardData();
    this.loadReassessmentGrowth();
  }

  computeCohortAverage(data: MentorDashboardData): void {
    const scores = data.ranking_table.filter(r => r.has_attempt).map(r => r.average_score);
    if (scores.length > 0) {
      this.cohortAverage = scores.reduce((a, b) => a + b, 0) / scores.length;
    } else {
      this.cohortAverage = null;
    }
  }

  buildRadarChart(data: MentorDashboardData): void {
    const primary = getCssToken('--csm-primary', '#1e3a8a');
    const accent = getCssToken('--csm-accent', '#2563eb');
    this.radarChartData = {
      labels: data.cohort_radar?.labels?.length ? data.cohort_radar.labels : ['No Data'],
      datasets: [
        {
          data: data.cohort_radar?.values?.length ? data.cohort_radar.values : [0],
          label: 'Cohort Average %',
          backgroundColor: 'rgba(30, 58, 138, 0.25)',
          borderColor: primary,
          pointBackgroundColor: accent,
          pointBorderColor: '#ffffff'
        }
      ]
    };
  }

  getScoreHeatmapClass(score: number | null | undefined): string {
    if (score === undefined || score === null) return 'cell-gray';
    if (score >= 70) return 'cell-green';
    if (score >= 50) return 'cell-yellow';
    return 'cell-red';
  }

  getReasonBadgeClass(reason: string): string {
    if (reason.toLowerCase().includes('fail') || reason.toLowerCase().includes('score')) return 'badge-failing';
    if (reason.toLowerCase().includes('violation') || reason.toLowerCase().includes('flag')) return 'badge-flagged';
    return 'badge-unattempted';
  }

  exportCohortCsv(): void {
    if (!this.selectedCohortId) return;
    this.exportingCsv = true;
    this.analyticsService.downloadCohortCsv(this.selectedCohortId).subscribe({
      next: (blob: Blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Cohort_${this.selectedCohortId}_Performance_Summary_${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
        this.exportingCsv = false;
      },
      error: (err: any) => {
        console.error('Failed to export CSV', err);
        this.exportingCsv = false;
      }
    });
  }

  downloadMenteePdf(item: MentorRankingRow): void {
    if (!item.latest_attempt_id) return;
    this.analyticsService.downloadAsePdf(item.latest_attempt_id).subscribe({
      next: (blob: Blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Candidate_Report_${item.ase_name.replace(/\\s+/g, '_')}.pdf`;
        a.click();
        window.URL.revokeObjectURL(url);
      },
      error: (err: any) => console.error('Failed to download mentee PDF', err)
    });
  }
}
