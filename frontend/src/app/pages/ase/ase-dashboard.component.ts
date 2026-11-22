import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { MatDividerModule } from '@angular/material/divider';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration, ChartData } from 'chart.js';
import { getCssToken } from '../../core/utils/theme-tokens.util';
import { AnalyticsService } from '../../core/services/analytics.service';
import { AuthService } from '../../core/services/auth.service';
import { CodingService } from '../../core/services/coding.service';
import { Phase9Service } from '../../core/services/phase9.service';
import { OnboardingProgress } from '../../core/models/coding.model';
import { ASEDashboardData } from '../../core/models/analytics.model';
import {
  ReadinessResponse,
  JourneyMapResponse,
  LeaderboardEntry,
  RoadmapPlan,
  CertificateItem,
  MockInterviewSession
} from '../../core/models/phase9.model';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-ase-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatProgressBarModule,
    MatTabsModule,
    MatDividerModule,
    BaseChartDirective
  ],
  template: `
    <div class="dashboard-page">
      <!-- Header Banner -->
      <div class="welcome-banner">
        <div class="banner-content">
          <h1>Welcome back, {{ authService.currentUser()?.name }}! 👋</h1>
          <p class="subtitle">
            Track your Project-Readiness, complete your 30/60/90-day journey milestones, and practice with AI Mock Interviews.
          </p>
          <div class="banner-meta" *ngIf="journeyData">
            <span class="meta-chip">
              <mat-icon>bolt</mat-icon> {{ journeyData.profile.total_xp }} XP • Level {{ journeyData.profile.current_level }}
            </span>
            <span class="meta-chip">
              <mat-icon>local_fire_department</mat-icon> {{ journeyData.profile.streak_days }} Day Streak 🔥
            </span>
          </div>
        </div>
        <div class="banner-actions">
          <button class="btn-interview" (click)="openMockInterviewModal()">
            <mat-icon>smart_toy</mat-icon> AI Mock Interviewer
          </button>
          <button mat-raised-button color="accent" (click)="downloadLatestReport()" [disabled]="downloading" *ngIf="dashboardData?.latest_attempt_id">
            <mat-icon>picture_as_pdf</mat-icon>
            {{ downloading ? 'Generating PDF...' : 'Download My Report (PDF)' }}
          </button>
        </div>
      </div>

      <!-- Loading skeleton -->
      <div *ngIf="loading" class="skeleton-container">
        <mat-card class="stat-card shimmer" *ngFor="let i of [1,2,3,4]">
          <div style="height: 60px;"></div>
        </mat-card>
      </div>

      <!-- Content Area -->
      <div *ngIf="!loading" class="content-body">

        <!-- 1. Phase 9 Project-Readiness Score & Skill DNA Visualizer -->
        <mat-card class="readiness-card" *ngIf="readinessData">
          <div class="readiness-header">
            <div>
              <span class="tag-readiness">TRANSPARENT DIAGNOSTIC</span>
              <h2>Project-Readiness Score & Skill DNA</h2>
              <p class="subtitle">Multi-dimensional competence model calibrated across assessments, code quality, trainings, attendance, and consistency.</p>
            </div>
            <div class="score-circle-wrapper">
              <div class="score-circle" [ngClass]="getScoreCircleClass(readinessData.overall_score)">
                <span class="score-val">{{ readinessData.overall_score | number:'1.1-1' }}%</span>
                <span class="score-label">Readiness</span>
              </div>
            </div>
          </div>

          <!-- Formula and Live Inputs Breakdown -->
          <div class="formula-breakdown-box">
            <div class="formula-title">
              <mat-icon>calculate</mat-icon> Live Weighted Formula Breakdown
            </div>
            <div class="formula-equation">{{ readinessData.formula_display }}</div>
            
            <div class="breakdown-cards-grid">
              <div class="factor-card">
                <span class="factor-name">Assessments</span>
                <span class="factor-val">{{ readinessData.breakdown.assessment_pct | number:'1.0-0' }}%</span>
              </div>
              <div class="factor-card">
                <span class="factor-name">Coding Quality</span>
                <span class="factor-val">{{ readinessData.breakdown.coding_pct | number:'1.0-0' }}%</span>
              </div>
              <div class="factor-card">
                <span class="factor-name">Training Progress</span>
                <span class="factor-val">{{ readinessData.breakdown.training_pct | number:'1.0-0' }}%</span>
              </div>
              <div class="factor-card">
                <span class="factor-name">Class Attendance</span>
                <span class="factor-val">{{ readinessData.breakdown.attendance_pct | number:'1.0-0' }}%</span>
              </div>
              <div class="factor-card">
                <span class="factor-name">Daily Consistency</span>
                <span class="factor-val">{{ readinessData.breakdown.consistency_pct | number:'1.0-0' }}%</span>
              </div>
            </div>
          </div>

          <!-- Skill DNA Visualizer (Helix Dimensions) -->
          <div class="skill-dna-section">
            <h3 class="dna-title">🧬 Skill DNA Matrix</h3>
            <div class="dna-bars-grid">
              <div class="dna-bar-item">
                <div class="dna-labels">
                  <span>Technical Accuracy</span>
                  <strong>{{ readinessData.skill_dna.technical_accuracy | number:'1.0-0' }}%</strong>
                </div>
                <div class="dna-bar-bg"><div class="dna-bar-fill fill-blue" [style.width.%]="readinessData.skill_dna.technical_accuracy"></div></div>
              </div>
              <div class="dna-bar-item">
                <div class="dna-labels">
                  <span>Problem Solving</span>
                  <strong>{{ readinessData.skill_dna.problem_solving | number:'1.0-0' }}%</strong>
                </div>
                <div class="dna-bar-bg"><div class="dna-bar-fill fill-purple" [style.width.%]="readinessData.skill_dna.problem_solving"></div></div>
              </div>
              <div class="dna-bar-item">
                <div class="dna-labels">
                  <span>Code Quality</span>
                  <strong>{{ readinessData.skill_dna.code_quality | number:'1.0-0' }}%</strong>
                </div>
                <div class="dna-bar-bg"><div class="dna-bar-fill fill-green" [style.width.%]="readinessData.skill_dna.code_quality"></div></div>
              </div>
              <div class="dna-bar-item">
                <div class="dna-labels">
                  <span>Learning Velocity</span>
                  <strong>{{ readinessData.skill_dna.learning_velocity | number:'1.0-0' }}%</strong>
                </div>
                <div class="dna-bar-bg"><div class="dna-bar-fill fill-orange" [style.width.%]="readinessData.skill_dna.learning_velocity"></div></div>
              </div>
              <div class="dna-bar-item">
                <div class="dna-labels">
                  <span>Attendance & Consistency</span>
                  <strong>{{ readinessData.skill_dna.attendance_consistency | number:'1.0-0' }}%</strong>
                </div>
                <div class="dna-bar-bg"><div class="dna-bar-fill fill-teal" [style.width.%]="readinessData.skill_dna.attendance_consistency"></div></div>
              </div>
            </div>
          </div>

          <!-- Mandatory Legal Disclaimer -->
          <div class="mandatory-disclaimer">
            <mat-icon>shield</mat-icon>
            <span>{{ readinessData.legal_disclaimer }}</span>
          </div>
        </mat-card>

        <!-- 2. Phase 9 30/60/90-Day Journey Map & Leaderboard -->
        <mat-card class="journey-card" *ngIf="journeyData">
          <div class="journey-top-row">
            <div>
              <h2>30 / 60 / 90-Day Onboarding Journey Map</h2>
              <p class="subtitle">Structured milestones to accelerate your transition to client project delivery.</p>
            </div>
            <div class="badges-row">
              <span class="badge-item" *ngFor="let b of journeyData.profile.badges" [title]="b">
                🏅 {{ b }}
              </span>
            </div>
          </div>

          <!-- Milestone Timeline -->
          <div class="milestones-timeline">
            <div *ngFor="let m of journeyData.milestones" class="milestone-box" [class.completed]="m.is_completed">
              <div class="milestone-badge-day">{{ m.day_category }}-DAY</div>
              <div class="milestone-info">
                <h4>{{ m.title }}</h4>
                <p>{{ m.description }}</p>
                <div class="milestone-meta">
                  <span class="xp-tag">+{{ m.xp_reward }} XP</span>
                  <span *ngIf="m.is_completed" class="status-done">✓ Completed {{ m.completed_at | date:'shortDate' }}</span>
                  <button *ngIf="!m.is_completed" class="btn-complete-milestone" (click)="completeMilestone(m.id)">
                    Mark Completed
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Opt-In Leaderboard Section -->
          <div class="leaderboard-section">
            <div class="leaderboard-header">
              <div class="leaderboard-title">
                <h3>🏆 Peer Onboarding Leaderboard</h3>
                <span class="leaderboard-sub">Opt-in friendly ranking displaying only Name, XP, and Badges count. Scores and risk data are never shown.</span>
              </div>
              <div class="opt-in-toggle">
                <label class="switch">
                  <input type="checkbox" [checked]="journeyData.profile.is_leaderboard_opt_in" (change)="toggleLeaderboardOptIn($event)" />
                  <span class="slider round"></span>
                </label>
                <span class="toggle-label">Participate in Leaderboard</span>
              </div>
            </div>

            <div class="leaderboard-table-wrap" *ngIf="journeyData.profile.is_leaderboard_opt_in">
              <table class="leaderboard-table" *ngIf="leaderboard.length > 0; else emptyLd">
                <thead>
                  <tr>
                    <th style="width: 60px;">Rank</th>
                    <th>Engineer</th>
                    <th>Level</th>
                    <th>Total XP</th>
                    <th>Badges</th>
                  </tr>
                </thead>
                <tbody>
                  <tr *ngFor="let entry of leaderboard" [class.my-row]="entry.ase_name.includes(authService.currentUser()?.name || '')">
                    <td>
                      <span class="rank-num" [class.rank-gold]="entry.rank === 1" [class.rank-silver]="entry.rank === 2" [class.rank-bronze]="entry.rank === 3">
                        {{ entry.rank }}
                      </span>
                    </td>
                    <td><strong>{{ entry.ase_name }}</strong></td>
                    <td>Level {{ entry.current_level }}</td>
                    <td class="text-xp">{{ entry.total_xp }} XP</td>
                    <td>{{ entry.badges_count }} Badges</td>
                  </tr>
                </tbody>
              </table>
              <ng-template #emptyLd>
                <p class="text-muted p-3">No other participants have opted in yet. You are on the board!</p>
              </ng-template>
            </div>
            <div class="leaderboard-opted-out" *ngIf="!journeyData.profile.is_leaderboard_opt_in">
              <p>You are currently hidden from the public leaderboard. Toggle above to opt-in anytime!</p>
            </div>
          </div>
        </mat-card>

        <!-- 3. Phase 9 AI Learning Roadmap -->
        <mat-card class="roadmap-card" *ngIf="roadmapData">
          <div class="roadmap-header">
            <div>
              <span class="tag-ai">AI-POWERED STUDY PLAN</span>
              <h2>Weekly Learning Roadmap & Checklist</h2>
              <p class="subtitle">{{ roadmapData.summary }}</p>
            </div>
            <button class="btn-regenerate" (click)="regenerateRoadmap()" [disabled]="isRegenerating">
              <mat-icon>refresh</mat-icon>
              {{ isRegenerating ? 'Synthesizing...' : 'Regenerate Plan' }}
            </button>
          </div>

          <div class="weak-tags-row" *ngIf="roadmapData.weak_skills.length > 0">
            <span class="weak-label">Target Focus Skills:</span>
            <span class="weak-pill" *ngFor="let s of roadmapData.weak_skills">🎯 {{ s }}</span>
          </div>

          <div class="tasks-checklist">
            <div *ngFor="let t of roadmapData.tasks" class="task-row" [class.task-done]="t.is_done">
              <input type="checkbox" [checked]="t.is_done" (change)="toggleTask(t)" />
              <div class="task-info">
                <span class="task-title">{{ t.title }}</span>
                <span class="task-meta">{{ t.category }} • Est: {{ t.duration_est }}</span>
              </div>
              <span class="done-pill" *ngIf="t.is_done">Completed</span>
            </div>
          </div>
        </mat-card>

        <!-- 4. Phase 9 Verified Certificates Section -->
        <mat-card class="certificates-card" *ngIf="certificates.length > 0">
          <div class="panel-head">
            <h2>Verified Certificates & Credentials</h2>
            <p class="subtitle">Cryptographically verified credentials with public ledger verification links.</p>
          </div>
          <div class="certs-grid">
            <div *ngFor="let cert of certificates" class="cert-item">
              <div class="cert-icon">📜</div>
              <div class="cert-content">
                <h4>{{ cert.course_title }}</h4>
                <div class="cert-meta">
                  <span>Issued: {{ cert.issue_date }}</span> •
                  <span class="status-valid">{{ cert.status }}</span>
                </div>
                <div class="cert-actions">
                  <a [routerLink]="['/verify-certificate', cert.cert_uuid]" target="_blank" class="link-verify">
                    Verify Public Record ↗
                  </a>
                  <button class="btn-dl-cert" (click)="downloadCert(cert.cert_uuid)">
                    Download PDF
                  </button>
                </div>
              </div>
            </div>
          </div>
        </mat-card>

        <!-- Existing Section Performance & Skill Radar Visualizations -->
        <div class="analytics-grid" *ngIf="dashboardData?.summary?.has_attempts">
          <mat-card class="chart-card">
            <mat-card-header>
              <mat-icon mat-card-avatar color="primary">radar</mat-icon>
              <mat-card-title>Skill-Wise Mastery</mat-card-title>
              <mat-card-subtitle>Aggregated performance radar across skills</mat-card-subtitle>
            </mat-card-header>
            <mat-card-content class="chart-container">
              <div *ngIf="radarChartData.labels?.length; else emptyRadar" class="canvas-wrap">
                <canvas baseChart [data]="radarChartData" [options]="radarChartOptions" [type]="'radar'"></canvas>
              </div>
              <ng-template #emptyRadar>
                <div class="chart-empty">No skill breakdowns available.</div>
              </ng-template>
            </mat-card-content>
          </mat-card>

          <mat-card class="chart-card">
            <mat-card-header>
              <mat-icon mat-card-avatar color="primary">bar_chart</mat-icon>
              <mat-card-title>Section-Wise Performance</mat-card-title>
              <mat-card-subtitle>Average accuracy percentage across sections</mat-card-subtitle>
            </mat-card-header>
            <mat-card-content class="chart-container">
              <div *ngIf="barChartData.labels?.length; else emptyBar" class="canvas-wrap">
                <canvas baseChart [data]="barChartData" [options]="barChartOptions" [type]="'bar'"></canvas>
              </div>
              <ng-template #emptyBar>
                <div class="chart-empty">No section scores available.</div>
              </ng-template>
            </mat-card-content>
          </mat-card>
        </div>

      </div>

      <!-- Phase 9 AI Mock Interviewer Modal -->
      <div class="interview-modal-backdrop" *ngIf="showInterviewModal" (click)="closeInterviewModal()">
        <div class="interview-modal-box" (click)="$event.stopPropagation()">
          <div class="interview-header">
            <div class="interview-title-area">
              <span class="mode-badge">AI MOCK INTERVIEWER</span>
              <h3>Technical & Behavioral Practice</h3>
              <span class="demo-tag" *ngIf="activeInterview?.is_demo_mode">Demo AI mode</span>
            </div>
            <button class="btn-modal-close" (click)="closeInterviewModal()">✕</button>
          </div>

          <div class="interview-body">
            <!-- Setup view if no active session -->
            <div *ngIf="!activeInterview" class="interview-setup">
              <div class="form-row">
                <label>Interview Category</label>
                <select [(ngModel)]="interviewType">
                  <option value="TECHNICAL">Technical Deep-Dive</option>
                  <option value="BEHAVIORAL">Behavioral & Soft Skills</option>
                  <option value="SYSTEM_DESIGN">System Design Architecture</option>
                </select>
              </div>
              <div class="form-row">
                <label>Target Domain / Topic</label>
                <input type="text" [(ngModel)]="interviewTopic" placeholder="e.g. Data Structures, Python, Angular, Microservices" />
              </div>
              <div class="form-row">
                <label>Difficulty Level</label>
                <select [(ngModel)]="interviewDifficulty">
                  <option value="JUNIOR">Junior (Foundational)</option>
                  <option value="MID_LEVEL">Mid-Level (Practical Engineering)</option>
                  <option value="SENIOR">Senior (Advanced Problem Solving)</option>
                </select>
              </div>
              <button class="btn-start-interview" (click)="startInterview()" [disabled]="startingInterview">
                {{ startingInterview ? 'Initializing Session...' : 'Start Mock Interview' }}
              </button>
            </div>

            <!-- Active Q&A Dialogue view -->
            <div *ngIf="activeInterview" class="interview-dialogue">
              <div class="dialogue-scroll">
                <div *ngFor="let msg of activeInterview.messages" class="dialogue-msg" [ngClass]="msg.role === 'assistant' ? 'assistant-msg' : 'user-msg'">
                  <div class="msg-author">{{ msg.role === 'assistant' ? 'AI Interviewer' : 'You' }}</div>
                  <div class="msg-text">{{ msg.content }}</div>
                </div>
              </div>

              <!-- Answer Input -->
              <div class="dialogue-input-area" *ngIf="activeInterview.status === 'IN_PROGRESS'">
                <textarea
                  rows="3"
                  [(ngModel)]="userAnswer"
                  placeholder="Type your response here..."
                  (keydown.control.enter)="submitAnswer()"
                ></textarea>
                <div class="dialogue-actions">
                  <span class="verify-note">AI-generated, please verify</span>
                  <div class="btn-group">
                    <button class="btn-end" (click)="endInterview()">End & Evaluate</button>
                    <button class="btn-submit-ans" [disabled]="!userAnswer.trim() || answering" (click)="submitAnswer()">
                      {{ answering ? 'Analyzing...' : 'Submit Answer (Ctrl+Enter)' }}
                    </button>
                  </div>
                </div>
              </div>

              <div *ngIf="activeInterview.status === 'COMPLETED'" class="interview-completed-banner">
                <h4>Session Completed</h4>
                <p>Thank you for completing this mock interview practice session.</p>
                <button class="btn-start-interview" (click)="activeInterview = null">Start Another Session</button>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>
  `,
  styles: [`
    .dashboard-page {
      display: flex;
      flex-direction: column;
      gap: 24px;
      padding-bottom: 40px;
    }
    .welcome-banner {
      background: linear-gradient(135deg, var(--csm-primary) 0%, #172554 100%);
      color: #ffffff;
      padding: 28px 32px;
      border-radius: 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
    }
    .welcome-banner h1 { margin: 0 0 8px 0; font-size: 1.8rem; font-weight: 700; }
    .welcome-banner .subtitle { margin: 0 0 16px 0; color: #93C5FD; font-size: 0.95rem; }
    .banner-meta { display: flex; gap: 12px; flex-wrap: wrap; }
    .meta-chip {
      background: rgba(255, 255, 255, 0.15);
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 13px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .meta-chip mat-icon { font-size: 18px; width: 18px; height: 18px; }
    .banner-actions { display: flex; gap: 10px; align-items: center; }
    .btn-interview {
      background: var(--csm-accent);
      color: white;
      border: none;
      padding: 10px 18px;
      border-radius: 8px;
      font-weight: 600;
      font-size: 14px;
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      box-shadow: 0 2px 8px rgba(249, 115, 22, 0.3);
      transition: all 0.2s;
    }
    .btn-interview:hover { background: #EA580C; transform: translateY(-1px); }
    .content-body { display: flex; flex-direction: column; gap: 24px; }

    /* Readiness & Skill DNA Card */
    .readiness-card {
      background: white;
      border: 1px solid #E2E8F0;
      border-radius: 16px;
      padding: 24px 28px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    }
    .readiness-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
      margin-bottom: 20px;
    }
    .tag-readiness {
      background: #EFF6FF;
      color: var(--csm-primary);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.5px;
      padding: 3px 8px;
      border-radius: 4px;
      display: inline-block;
      margin-bottom: 6px;
    }
    .readiness-header h2 { margin: 0 0 6px 0; font-size: 22px; color: #0F172A; }
    .score-circle-wrapper { display: flex; align-items: center; justify-content: center; }
    .score-circle {
      width: 100px;
      height: 100px;
      border-radius: 50%;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      border: 4px solid var(--csm-primary);
      background: #F8FAFC;
    }
    .score-circle.circle-green { border-color: #10B981; }
    .score-circle.circle-orange { border-color: var(--csm-accent); }
    .score-circle.circle-red { border-color: #EF4444; }
    .score-val { font-size: 22px; font-weight: 800; color: #0F172A; line-height: 1; }
    .score-label { font-size: 11px; color: #64748B; font-weight: 600; text-transform: uppercase; margin-top: 2px; }

    .formula-breakdown-box {
      background: #F8FAFC;
      border: 1px solid #E2E8F0;
      border-radius: 10px;
      padding: 16px 20px;
      margin-bottom: 20px;
    }
    .formula-title {
      font-size: 13px;
      font-weight: 700;
      color: var(--csm-primary);
      display: flex;
      align-items: center;
      gap: 6px;
      margin-bottom: 6px;
    }
    .formula-title mat-icon { font-size: 18px; width: 18px; height: 18px; }
    .formula-equation {
      font-family: monospace;
      font-size: 13px;
      color: #334155;
      margin-bottom: 14px;
    }
    .breakdown-cards-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 12px;
    }
    .factor-card {
      background: white;
      border: 1px solid #CBD5E1;
      border-radius: 8px;
      padding: 10px 14px;
      display: flex;
      flex-direction: column;
    }
    .factor-name { font-size: 12px; color: #64748B; }
    .factor-val { font-size: 18px; font-weight: 700; color: #0F172A; margin-top: 2px; }

    .skill-dna-section { margin-bottom: 20px; }
    .dna-title { font-size: 15px; font-weight: 700; color: #0F172A; margin: 0 0 12px 0; }
    .dna-bars-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
    }
    .dna-labels { display: flex; justify-content: space-between; font-size: 12px; color: #475569; margin-bottom: 4px; }
    .dna-bar-bg { height: 8px; background: #F1F5F9; border-radius: 4px; overflow: hidden; }
    .dna-bar-fill { height: 100%; border-radius: 4px; }
    .fill-blue { background: var(--csm-primary); }
    .fill-purple { background: #8B5CF6; }
    .fill-green { background: #10B981; }
    .fill-orange { background: var(--csm-accent); }
    .fill-teal { background: #0D9488; }

    .mandatory-disclaimer {
      background: #FEF3C7;
      border-left: 4px solid #D97706;
      padding: 12px 16px;
      border-radius: 6px;
      font-size: 12px;
      color: #78350F;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .mandatory-disclaimer mat-icon { font-size: 20px; width: 20px; height: 20px; color: #D97706; }

    /* Journey Map Card */
    .journey-card {
      background: white;
      border: 1px solid #E2E8F0;
      border-radius: 16px;
      padding: 24px 28px;
    }
    .journey-top-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
      margin-bottom: 20px;
    }
    .journey-top-row h2 { margin: 0 0 4px 0; font-size: 20px; color: #0F172A; }
    .badges-row { display: flex; gap: 8px; flex-wrap: wrap; }
    .badge-item {
      background: #EFF6FF;
      color: var(--csm-primary);
      font-size: 12px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 12px;
    }
    .milestones-timeline {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .milestone-box {
      border: 1px solid #E2E8F0;
      border-radius: 10px;
      padding: 16px;
      background: #FAFAFA;
      position: relative;
    }
    .milestone-box.completed {
      background: #F0FDF4;
      border-color: #BBF7D0;
    }
    .milestone-badge-day {
      display: inline-block;
      background: var(--csm-primary);
      color: white;
      font-size: 10px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
      margin-bottom: 8px;
    }
    .milestone-info h4 { margin: 0 0 6px 0; font-size: 15px; color: #0F172A; }
    .milestone-info p { margin: 0 0 12px 0; font-size: 12px; color: #64748B; line-height: 1.4; }
    .milestone-meta { display: flex; justify-content: space-between; align-items: center; }
    .xp-tag { font-size: 12px; font-weight: 700; color: var(--csm-accent); }
    .status-done { font-size: 12px; font-weight: 600; color: #166534; }
    .btn-complete-milestone {
      background: var(--csm-primary);
      color: white;
      border: none;
      padding: 4px 10px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
    }

    /* Leaderboard section */
    .leaderboard-section {
      border-top: 1px solid #E2E8F0;
      padding-top: 20px;
      margin-top: 10px;
    }
    .leaderboard-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
      margin-bottom: 16px;
    }
    .leaderboard-title h3 { margin: 0 0 4px 0; font-size: 17px; color: #0F172A; }
    .leaderboard-sub { font-size: 12px; color: #64748B; }
    .opt-in-toggle { display: flex; align-items: center; gap: 10px; }
    .toggle-label { font-size: 13px; font-weight: 600; color: #334155; }
    .switch { position: relative; display: inline-block; width: 44px; height: 24px; }
    .switch input { opacity: 0; width: 0; height: 0; }
    .slider {
      position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0;
      background-color: #CBD5E1; transition: .3s; border-radius: 24px;
    }
    .slider:before {
      position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px;
      background-color: white; transition: .3s; border-radius: 50%;
    }
    input:checked + .slider { background-color: var(--csm-primary); }
    input:checked + .slider:before { transform: translateX(20px); }
    .leaderboard-table { width: 100%; border-collapse: collapse; font-size: 13px; }
    .leaderboard-table th { text-align: left; padding: 10px 12px; background: #F8FAFC; border-bottom: 1px solid #E2E8F0; color: #475569; }
    .leaderboard-table td { padding: 10px 12px; border-bottom: 1px solid #F1F5F9; }
    .my-row { background: #EFF6FF; }
    .rank-num {
      display: inline-flex; align-items: center; justify-content: center;
      width: 24px; height: 24px; border-radius: 50%; font-weight: 700; font-size: 11px;
      background: #F1F5F9; color: #475569;
    }
    .rank-gold { background: #FEF3C7; color: #92400E; }
    .rank-silver { background: #E2E8F0; color: #334155; }
    .rank-bronze { background: #FFEDD5; color: #9A3412; }
    .text-xp { font-weight: 700; color: var(--csm-accent); }
    .leaderboard-opted-out {
      background: #F8FAFC;
      border: 1px dashed #CBD5E1;
      border-radius: 8px;
      padding: 16px;
      text-align: center;
      color: #64748B;
      font-size: 13px;
    }

    /* Roadmap Card */
    .roadmap-card {
      background: white;
      border: 1px solid #E2E8F0;
      border-radius: 16px;
      padding: 24px 28px;
    }
    .roadmap-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
      margin-bottom: 16px;
    }
    .tag-ai {
      background: #FFF7ED;
      color: #EA580C;
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 4px;
      display: inline-block;
      margin-bottom: 6px;
    }
    .roadmap-header h2 { margin: 0 0 4px 0; font-size: 20px; color: #0F172A; }
    .btn-regenerate {
      display: flex;
      align-items: center;
      gap: 6px;
      background: var(--csm-primary);
      color: white;
      border: none;
      padding: 8px 14px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
    }
    .btn-regenerate mat-icon { font-size: 16px; width: 16px; height: 16px; }
    .weak-tags-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
    .weak-label { font-size: 12px; color: #64748B; font-weight: 600; }
    .weak-pill { background: #FEE2E2; color: #991B1B; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px; }
    .tasks-checklist { display: flex; flex-direction: column; gap: 10px; }
    .task-row {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 14px;
      border-radius: 8px;
      border: 1px solid #E2E8F0;
      background: #F8FAFC;
    }
    .task-row.task-done { background: #F0FDF4; border-color: #BBF7D0; }
    .task-info { flex: 1; display: flex; flex-direction: column; }
    .task-title { font-size: 14px; font-weight: 600; color: #0F172A; }
    .task-row.task-done .task-title { text-decoration: line-through; color: #64748B; }
    .task-meta { font-size: 12px; color: #64748B; }
    .done-pill { font-size: 11px; font-weight: 700; color: #166534; background: #DCFCE7; padding: 2px 8px; border-radius: 4px; }

    /* Certificates Card */
    .certificates-card {
      background: white;
      border: 1px solid #E2E8F0;
      border-radius: 16px;
      padding: 24px 28px;
    }
    .certs-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-top: 16px; }
    .cert-item {
      display: flex;
      gap: 14px;
      border: 1px solid #CBD5E1;
      border-radius: 10px;
      padding: 16px;
      background: #F8FAFC;
    }
    .cert-icon { font-size: 32px; }
    .cert-content h4 { margin: 0 0 4px 0; font-size: 15px; color: #0F172A; }
    .cert-meta { font-size: 12px; color: #64748B; margin-bottom: 12px; }
    .status-valid { color: #166534; font-weight: 700; }
    .cert-actions { display: flex; gap: 10px; align-items: center; }
    .link-verify { font-size: 12px; font-weight: 600; color: var(--csm-primary); text-decoration: none; }
    .btn-dl-cert {
      background: var(--csm-accent);
      color: white;
      border: none;
      padding: 4px 10px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
    }

    /* AI Mock Interview Modal */
    .interview-modal-backdrop {
      position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
      background: rgba(15, 23, 42, 0.7); backdrop-filter: blur(3px); z-index: 99999;
      display: flex; align-items: center; justify-content: center; padding: 20px;
    }
    .interview-modal-box {
      background: white; border-radius: 16px; max-width: 650px; width: 100%;
      height: 80vh; max-height: 700px; display: flex; flex-direction: column;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.25); overflow: hidden;
    }
    .interview-header {
      background: var(--csm-primary); color: white; padding: 18px 24px;
      display: flex; justify-content: space-between; align-items: center;
    }
    .mode-badge {
      background: var(--csm-accent); font-size: 10px; font-weight: 700;
      padding: 2px 6px; border-radius: 4px; display: inline-block; margin-bottom: 4px;
    }
    .interview-header h3 { margin: 0; font-size: 18px; }
    .demo-tag { font-size: 11px; background: rgba(255, 255, 255, 0.2); padding: 2px 6px; border-radius: 4px; margin-left: 8px; }
    .btn-modal-close { background: none; border: none; color: white; font-size: 20px; cursor: pointer; }
    .interview-body { flex: 1; display: flex; flex-direction: column; overflow: hidden; padding: 20px; }
    .interview-setup { display: flex; flex-direction: column; gap: 16px; margin: auto 0; }
    .form-row label { display: block; font-size: 13px; font-weight: 600; color: #334155; margin-bottom: 6px; }
    .form-row select, .form-row input {
      width: 100%; padding: 10px 14px; border: 1px solid #CBD5E1; border-radius: 8px; font-size: 14px;
    }
    .btn-start-interview {
      background: var(--csm-primary); color: white; border: none; padding: 12px;
      border-radius: 8px; font-weight: 700; font-size: 15px; cursor: pointer;
    }
    .interview-dialogue { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
    .dialogue-scroll { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 14px; padding-right: 8px; margin-bottom: 14px; }
    .dialogue-msg { max-width: 85%; padding: 12px 16px; border-radius: 12px; font-size: 13px; line-height: 1.5; }
    .assistant-msg { align-self: flex-start; background: #F1F5F9; color: #0F172A; }
    .user-msg { align-self: flex-end; background: var(--csm-primary); color: white; }
    .msg-author { font-size: 11px; font-weight: 700; margin-bottom: 4px; opacity: 0.8; }
    .dialogue-input-area textarea {
      width: 100%; border: 1px solid #CBD5E1; border-radius: 8px; padding: 10px;
      font-size: 13px; resize: none; outline: none; font-family: inherit;
    }
    .dialogue-actions { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; }
    .verify-note { font-size: 11px; color: #94A3B8; font-style: italic; }
    .btn-group { display: flex; gap: 8px; }
    .btn-end { background: #F1F5F9; color: #64748B; border: none; padding: 8px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; }
    .btn-submit-ans { background: var(--csm-primary); color: white; border: none; padding: 8px 16px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; }

    /* Analytics Chart Grid */
    .analytics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; }
    .chart-card { border-radius: 16px; border: 1px solid #E2E8F0; padding: 16px; background: white; }
    .chart-container { height: 300px; display: flex; align-items: center; justify-content: center; }
    .canvas-wrap { width: 100%; height: 100%; }
    .chart-empty { color: #94A3B8; font-style: italic; }
  `]
})
export class AseDashboardComponent implements OnInit {
  dashboardData: ASEDashboardData | null = null;
  loading = true;
  downloading = false;

  // Phase 9 Models
  readinessData: ReadinessResponse | null = null;
  journeyData: JourneyMapResponse | null = null;
  leaderboard: LeaderboardEntry[] = [];
  roadmapData: RoadmapPlan | null = null;
  certificates: CertificateItem[] = [];
  isRegenerating = false;

  // Phase 9 Mock Interview
  showInterviewModal = false;
  activeInterview: MockInterviewSession | null = null;
  interviewType = 'TECHNICAL';
  interviewDifficulty = 'MID_LEVEL';
  interviewTopic = 'Data Structures and Algorithms';
  startingInterview = false;
  answering = false;
  userAnswer = '';

  radarChartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      r: { min: 0, max: 100, ticks: { stepSize: 20 }, pointLabels: { font: { size: 12, weight: 'bold' } } }
    },
    plugins: { legend: { display: false } }
  };
  radarChartData: ChartData<'radar'> = { labels: [], datasets: [] };

  barChartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    scales: { y: { min: 0, max: 100, ticks: { stepSize: 25 } } },
    plugins: { legend: { display: false } }
  };
  barChartData: ChartData<'bar'> = { labels: [], datasets: [] };

  onboardingProgress: OnboardingProgress | null = null;

  constructor(
    public authService: AuthService,
    private analyticsService: AnalyticsService,
    private codingService: CodingService,
    private phase9Service: Phase9Service
  ) {}

  ngOnInit(): void {
    this.loadDashboard();
    this.loadOnboardingProgress();
    this.loadPhase9Features();
  }

  loadPhase9Features(): void {
    // 1. Readiness & Skill DNA
    this.phase9Service.getReadiness().subscribe({
      next: (data) => this.readinessData = data,
      error: (err) => console.error('Failed to load readiness:', err)
    });

    // 2. Journey Map & Gamification
    this.phase9Service.getJourneyMap().subscribe({
      next: (data) => {
        this.journeyData = data;
        if (data.profile.is_leaderboard_opt_in) {
          this.loadLeaderboard();
        }
      },
      error: (err) => console.error('Failed to load journey map:', err)
    });

    // 3. AI Learning Roadmap
    this.phase9Service.getRoadmap().subscribe({
      next: (data) => this.roadmapData = data,
      error: (err) => console.error('Failed to load roadmap:', err)
    });

    // 4. Certificates
    this.phase9Service.getCertificates().subscribe({
      next: (data) => this.certificates = data,
      error: (err) => console.error('Failed to load certificates:', err)
    });
  }

  loadLeaderboard(): void {
    this.phase9Service.getLeaderboard().subscribe({
      next: (data) => this.leaderboard = data,
      error: (err) => console.error('Failed to load leaderboard:', err)
    });
  }

  toggleLeaderboardOptIn(event: any): void {
    const isChecked = event.target.checked;
    this.phase9Service.toggleLeaderboardOptIn(isChecked).subscribe({
      next: () => {
        if (this.journeyData) {
          this.journeyData.profile.is_leaderboard_opt_in = isChecked;
        }
        if (isChecked) {
          this.loadLeaderboard();
        }
      },
      error: (err) => console.error('Failed to toggle opt-in:', err)
    });
  }

  completeMilestone(milestoneId: number): void {
    this.phase9Service.completeMilestone(milestoneId).subscribe({
      next: () => {
        this.phase9Service.getJourneyMap().subscribe(j => this.journeyData = j);
      },
      error: (err) => console.error('Failed to complete milestone:', err)
    });
  }

  regenerateRoadmap(): void {
    this.isRegenerating = true;
    this.phase9Service.generateRoadmap().subscribe({
      next: (plan) => {
        this.roadmapData = plan;
        this.isRegenerating = false;
      },
      error: (err) => {
        console.error('Failed to regenerate roadmap:', err);
        this.isRegenerating = false;
      }
    });
  }

  toggleTask(task: any): void {
    task.is_done = !task.is_done;
    this.phase9Service.toggleRoadmapTask(task.id, task.is_done).subscribe({
      error: (err) => console.error('Failed to toggle task:', err)
    });
  }

  downloadCert(certUuid: string): void {
    this.phase9Service.downloadCertificatePdf(certUuid).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Certificate_${certUuid.slice(0, 8)}.pdf`;
        a.click();
        window.URL.revokeObjectURL(url);
      },
      error: (err) => console.error('Failed to download certificate PDF:', err)
    });
  }

  // Mock Interview Methods
  openMockInterviewModal(): void {
    this.showInterviewModal = true;
  }

  closeInterviewModal(): void {
    this.showInterviewModal = false;
  }

  startInterview(): void {
    this.startingInterview = true;
    this.phase9Service.startMockInterview({
      interview_type: this.interviewType,
      difficulty: this.interviewDifficulty,
      topic: this.interviewTopic
    }).subscribe({
      next: (session) => {
        this.activeInterview = session;
        this.startingInterview = false;
        this.userAnswer = '';
      },
      error: (err) => {
        this.startingInterview = false;
        alert(err.error?.detail || 'Failed to start interview');
      }
    });
  }

  submitAnswer(): void {
    if (!this.activeInterview || !this.userAnswer.trim()) return;
    this.answering = true;
    const ans = this.userAnswer;
    this.userAnswer = '';
    this.phase9Service.answerMockInterview(this.activeInterview.session_id, ans).subscribe({
      next: (session) => {
        this.activeInterview = session;
        this.answering = false;
      },
      error: (err) => {
        this.answering = false;
        alert(err.error?.detail || 'Failed to submit answer');
      }
    });
  }

  endInterview(): void {
    if (!this.activeInterview) return;
    this.phase9Service.endMockInterview(this.activeInterview.session_id).subscribe({
      next: (session) => this.activeInterview = session,
      error: (err) => console.error('Failed to end interview:', err)
    });
  }

  getScoreCircleClass(score: number): string {
    if (score >= 80) return 'circle-green';
    if (score >= 60) return 'circle-orange';
    return 'circle-red';
  }

  loadOnboardingProgress(): void {
    const user = this.authService.currentUser();
    const uid = user ? (user.user_id || (user as any).id) : null;
    if (uid) {
      this.codingService.getOnboardingProgress(uid).subscribe({
        next: (prog) => this.onboardingProgress = prog,
        error: (err) => console.error('Failed to load onboarding progress', err)
      });
    }
  }

  loadDashboard(): void {
    this.loading = true;
    this.analyticsService.getAseDashboard().subscribe({
      next: (data: ASEDashboardData) => {
        this.dashboardData = data;
        this.buildCharts(data);
        this.loading = false;
      },
      error: (err: any) => {
        console.error('Failed to load ASE dashboard', err);
        this.loading = false;
      }
    });
  }

  buildCharts(data: ASEDashboardData): void {
    const primary = getCssToken('--csm-primary', '#1e3a8a');
    const accent = getCssToken('--csm-accent', '#2563eb');
    this.radarChartData = {
      labels: data.radar_skills?.labels?.length ? data.radar_skills.labels : ['No Data'],
      datasets: [
        {
          data: data.radar_skills?.values?.length ? data.radar_skills.values : [0],
          label: 'Skill %',
          backgroundColor: 'rgba(30, 58, 138, 0.2)',
          borderColor: primary,
          pointBackgroundColor: accent,
          pointBorderColor: '#ffffff'
        }
      ]
    };

    this.barChartData = {
      labels: data.section_scores?.labels?.length ? data.section_scores.labels : ['No Data'],
      datasets: [
        {
          data: data.section_scores?.scores?.length ? data.section_scores.scores : [0],
          label: 'Section %',
          backgroundColor: accent,
          borderRadius: 6
        }
      ]
    };
  }

  downloadLatestReport(): void {
    if (!this.dashboardData?.latest_attempt_id) return;
    this.downloading = true;
    this.analyticsService.downloadAsePdf(this.dashboardData.latest_attempt_id).subscribe({
      next: (blob: Blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Performance_Report_${this.authService.currentUser()?.name?.replace(/\\s+/g, '_')}.pdf`;
        a.click();
        window.URL.revokeObjectURL(url);
        this.downloading = false;
      },
      error: (err: any) => {
        console.error('Failed to download PDF', err);
        this.downloading = false;
      }
    });
  }
}
