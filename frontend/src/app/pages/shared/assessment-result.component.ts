import { Component, OnInit, ElementRef, ViewChild, signal, inject, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { ExamService } from '../../core/services/exam.service';
import { CodingService } from '../../core/services/coding.service';
import { ExamResultData } from '../../core/models/assessment.model';
import { Chart, registerables } from 'chart.js';
import { getCssToken } from '../../core/utils/theme-tokens.util';

Chart.register(...registerables);

@Component({
  selector: 'app-assessment-result',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatDividerModule
  ],
  template: `
    <div class="result-container">
      @if (isLoading()) {
        <div class="loading-state">
          <mat-spinner diameter="40"></mat-spinner>
          <span>Loading performance report...</span>
        </div>
      } @else if (data()) {
        <!-- Report Header -->
        <div class="report-header card-shadow">
          <div class="header-main">
            <div>
              <span class="report-sub">Assessment Performance Report</span>
              <h1>{{ data()?.assessment_title }}</h1>
              <p class="candidate-meta">
                <span><mat-icon>person</mat-icon> {{ data()?.ase_name }} ({{ data()?.ase_email }})</span>
                <span><mat-icon>event</mat-icon> Submitted: {{ data()?.submitted_at | date:'medium' }}</span>
              </p>
            </div>
            <div class="status-stamp" [ngClass]="data()?.passed ? 'stamp-passed' : 'stamp-failed'">
              <mat-icon>{{ data()?.passed ? 'check_circle' : 'cancel' }}</mat-icon>
              <span>{{ data()?.passed ? 'PASSED' : 'FAILED' }}</span>
            </div>
          </div>

          <!-- Overall Score Grid -->
          <div class="score-summary-grid">
            <div class="metric-card">
              <span class="label">Total Score</span>
              <span class="val">{{ data()?.total_score }} / {{ data()?.max_score }}</span>
            </div>
            <div class="metric-card">
              <span class="label">Overall Percentage</span>
              <span class="val" [style.color]="data()?.passed ? '#16a34a' : '#dc2626'">
                {{ data()?.percentage }}%
              </span>
            </div>
            <div class="metric-card">
              <span class="label">Passing Requirement</span>
              <span class="val">{{ data()?.passing_percentage }}%</span>
            </div>
            <div class="metric-card">
              <span class="label">Status</span>
              <span class="val status-val">{{ data()?.status }}</span>
            </div>
          </div>
        </div>

        <!-- Charts Row -->
        <div class="charts-row">
          <!-- Skill Radar Chart -->
          <div class="chart-card card-shadow">
            <div class="card-title">
              <mat-icon class="icon-blue">radar</mat-icon>
              <h3>Skill-Wise Strength Profile</h3>
            </div>
            <p class="chart-desc">Percentage strength across tested competency domains</p>
            <div class="chart-wrapper">
              <canvas #radarCanvas></canvas>
            </div>
          </div>

          <!-- Section Bar Chart -->
          <div class="chart-card card-shadow">
            <div class="card-title">
              <mat-icon class="icon-orange">bar_chart</mat-icon>
              <h3>Section-Wise Performance</h3>
            </div>
            <p class="chart-desc">Marks obtained versus maximum achievable per section</p>
            <div class="chart-wrapper">
              <canvas #barCanvas></canvas>
            </div>
          </div>
        </div>

        <!-- Strong & Weak Competency Areas -->
        <div class="insights-grid">
          <div class="insight-card card-shadow">
            <div class="insight-header strong">
              <mat-icon>thumb_up</mat-icon>
              <h3>Strong Areas (&ge; 70%)</h3>
            </div>
            @if (data()?.strong_areas?.length === 0) {
              <p class="none-text">No skill areas scored 70% or higher.</p>
            } @else {
              <div class="chip-container">
                @for (area of data()?.strong_areas; track area) {
                  <span class="badge badge-strong">
                    <mat-icon>verified</mat-icon> {{ area }} ({{ data()?.skill_percentages?.[area] }}%)
                  </span>
                }
              </div>
            }
          </div>

          <div class="insight-card card-shadow">
            <div class="insight-header weak">
              <mat-icon>warning</mat-icon>
              <h3>Areas for Improvement (&lt; 70%)</h3>
            </div>
            @if (data()?.weak_areas?.length === 0) {
              <p class="none-text">Great job! All competency domains scored 70% or higher.</p>
            } @else {
              <div class="chip-container">
                @for (area of data()?.weak_areas; track area) {
                  <span class="badge badge-weak">
                    <mat-icon>priority_high</mat-icon> {{ area }} ({{ data()?.skill_percentages?.[area] }}%)
                  </span>
                }
              </div>
            }
          </div>
        </div>

        <!-- AI Code Quality & Architectural Review (Phase 7) -->
        <div class="review-section card-shadow ai-code-card" *ngIf="codingReviews().length > 0">
          <div class="review-header">
            <div>
              <h3><mat-icon class="ai-sparkle">auto_awesome</mat-icon> AI Code Quality & Architectural Review</h3>
              <p>Constructive automated feedback on Big-O complexity, edge cases, and engineering clean code standards</p>
            </div>
          </div>
          <div class="ai-reviews-list">
            <div *ngFor="let rev of codingReviews()" class="ai-review-box">
              <div class="review-box-header">
                <span class="badge badge-sec">Question #{{ rev.questionId }}</span>
                <span class="review-badge">AI Code Analysis</span>
              </div>
              <pre class="review-markdown">{{ rev.review }}</pre>
            </div>
          </div>
        </div>

        <!-- Detailed Question Review with Correct Answers (Post-Submission only) -->
        <div class="review-section card-shadow">
          <div class="review-header">
            <div>
              <h3>Question-by-Question Review</h3>
              <p>Detailed verification of chosen answers against answer keys</p>
            </div>
          </div>

          <div class="questions-list">
            @for (q of data()?.questions_review; track q.question_id; let idx = $index) {
              <div class="question-review-item" [ngClass]="q.is_correct ? 'item-correct' : 'item-wrong'">
                <div class="q-top">
                  <div class="q-badge-wrap">
                    <span class="q-num">Q{{ idx + 1 }}</span>
                    <span class="badge badge-sec">{{ q.section_title }}</span>
                    <span class="badge badge-skill">{{ q.skill_category }}</span>
                  </div>
                  <div class="q-score">
                    <span class="score-pill" [ngClass]="q.is_correct ? 'pill-correct' : 'pill-wrong'">
                      {{ q.marks_obtained }} / {{ q.max_marks }} marks
                    </span>
                  </div>
                </div>

                <p class="q-text">{{ q.question_text }}</p>

                <div class="options-review">
                  @for (opt of q.options; track opt.id) {
                    <div
                      class="option-row"
                      [class.opt-selected]="q.selected_options.includes(opt.id)"
                      [class.opt-correct]="q.correct_answers.includes(opt.id)"
                    >
                      <div class="opt-prefix">
                        @if (q.correct_answers.includes(opt.id)) {
                          <mat-icon class="icon-c">check_circle</mat-icon>
                        } @else if (q.selected_options.includes(opt.id)) {
                          <mat-icon class="icon-w">cancel</mat-icon>
                        } @else {
                          <span class="opt-dot"></span>
                        }
                      </div>
                      <span class="opt-text">{{ opt.text }}</span>
                      @if (q.correct_answers.includes(opt.id)) {
                        <span class="badge badge-correct-key">Correct Answer</span>
                      }
                      @if (q.selected_options.includes(opt.id) && !q.correct_answers.includes(opt.id)) {
                        <span class="badge badge-wrong-choice">Your Choice</span>
                      }
                    </div>
                  }
                </div>
              </div>
            }
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .result-container {
      display: flex;
      flex-direction: column;
      gap: 24px;
      max-width: 1200px;
      margin: 0 auto;
    }

    .report-header {
      background: #ffffff;
      padding: 28px 32px;
      border-radius: 16px;

      .header-main {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 16px;
        flex-wrap: wrap;
        border-bottom: 1px solid var(--border-light);
        padding-bottom: 20px;
        margin-bottom: 24px;

        .report-sub {
          font-size: 0.78rem;
          font-weight: 700;
          color: var(--csm-primary);
          text-transform: uppercase;
          letter-spacing: 0.06em;
        }

        h1 {
          font-size: 1.6rem;
          font-weight: 700;
          margin: 4px 0 10px;
          color: #0f172a;
        }

        .candidate-meta {
          display: flex;
          gap: 20px;
          color: var(--text-muted);
          font-size: 0.85rem;
          margin: 0;
          flex-wrap: wrap;

          span {
            display: inline-flex;
            align-items: center;
            gap: 6px;

            mat-icon {
              font-size: 16px;
              width: 16px;
              height: 16px;
            }
          }
        }

        .status-stamp {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 18px;
          border-radius: 9999px;
          font-weight: 700;
          font-size: 1rem;
          letter-spacing: 0.05em;

          &.stamp-passed {
            background-color: #dcfce7;
            color: #15803d;
            border: 2px solid #86efac;
          }

          &.stamp-failed {
            background-color: #fee2e2;
            color: #b91c1c;
            border: 2px solid #fca5a5;
          }
        }
      }

      .score-summary-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 16px;

        .metric-card {
          display: flex;
          flex-direction: column;

          .label {
            font-size: 0.75rem;
            color: var(--text-muted);
            font-weight: 600;
            text-transform: uppercase;
          }

          .val {
            font-size: 1.5rem;
            font-weight: 700;
            color: #0f172a;

            &.status-val {
              font-size: 1.1rem;
              text-transform: uppercase;
            }
          }
        }
      }
    }

    .charts-row {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(440px, 1fr));
      gap: 24px;

      .chart-card {
        background: #ffffff;
        padding: 24px;
        border-radius: 16px;

        .card-title {
          display: flex;
          align-items: center;
          gap: 10px;

          mat-icon {
            font-size: 24px;
            &.icon-blue { color: var(--csm-primary); }
            &.icon-orange { color: var(--csm-accent); }
          }

          h3 {
            margin: 0;
            font-size: 1.15rem;
            font-weight: 600;
            color: #0f172a;
          }
        }

        .chart-desc {
          margin: 4px 0 16px;
          font-size: 0.85rem;
          color: var(--text-muted);
        }

        .chart-wrapper {
          position: relative;
          height: 320px;
          width: 100%;
        }
      }
    }

    .insights-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
      gap: 24px;

      .insight-card {
        background: #ffffff;
        padding: 24px;
        border-radius: 16px;

        .insight-header {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 16px;

          &.strong { color: #15803d; }
          &.weak { color: #c2410c; }

          h3 {
            margin: 0;
            font-size: 1.1rem;
            font-weight: 600;
            color: #0f172a;
          }
        }

        .none-text {
          font-size: 0.85rem;
          color: var(--text-muted);
          font-style: italic;
        }

        .chip-container {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;

          .badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 0.82rem;
            font-weight: 600;

            mat-icon {
              font-size: 16px;
              width: 16px;
              height: 16px;
            }

            &.badge-strong {
              background-color: #dcfce7;
              color: #166534;
              border: 1px solid #bbf7d0;
            }

            &.badge-weak {
              background-color: #ffedd5;
              color: #c2410c;
              border: 1px solid #fed7aa;
            }
          }
        }
      }
    }

    .ai-code-card {
      border-left: 4px solid #38BDF8;

      .ai-sparkle {
        color: #38BDF8;
        vertical-align: middle;
      }

      .ai-reviews-list {
        display: flex;
        flex-direction: column;
        gap: 16px;
      }

      .ai-review-box {
        background: #0F172A;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 16px;
        color: #F8FAFC;

        .review-box-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
          border-bottom: 1px solid #1E293B;
          padding-bottom: 8px;

          .review-badge {
            font-size: 0.75rem;
            color: #38BDF8;
            font-weight: 700;
            text-transform: uppercase;
          }
        }

        .review-markdown {
          margin: 0;
          font-family: inherit;
          font-size: 0.9rem;
          line-height: 1.6;
          white-space: pre-wrap;
          color: #E2E8F0;
        }
      }
    }

    .review-section {
      background: #ffffff;
      padding: 28px 32px;
      border-radius: 16px;

      .review-header {
        margin-bottom: 24px;
        border-bottom: 1px solid var(--border-light);
        padding-bottom: 16px;

        h3 {
          margin: 0;
          font-size: 1.2rem;
          font-weight: 600;
          color: #0f172a;
        }

        p {
          margin: 4px 0 0;
          font-size: 0.85rem;
          color: var(--text-muted);
        }
      }

      .questions-list {
        display: flex;
        flex-direction: column;
        gap: 20px;
      }

      .question-review-item {
        border-radius: 12px;
        padding: 20px;
        border: 1px solid var(--border-light);
        background: #f8fafc;

        &.item-correct {
          border-left: 4px solid #16a34a;
        }

        &.item-wrong {
          border-left: 4px solid #ef4444;
        }

        .q-top {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;

          .q-badge-wrap {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;

            .q-num {
              font-weight: 700;
              font-size: 0.95rem;
              color: var(--csm-primary);
            }

            .badge-sec {
              background: #eff6ff;
              color: #1d4ed8;
              font-size: 0.75rem;
              padding: 2px 8px;
              border-radius: 4px;
            }

            .badge-skill {
              background: #f1f5f9;
              color: #475569;
              font-size: 0.75rem;
              padding: 2px 8px;
              border-radius: 4px;
            }
          }

          .score-pill {
            font-size: 0.8rem;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 9999px;

            &.pill-correct {
              background: #dcfce7;
              color: #15803d;
            }

            &.pill-wrong {
              background: #fee2e2;
              color: #b91c1c;
            }
          }
        }

        .q-text {
          font-size: 0.95rem;
          font-weight: 500;
          color: #0f172a;
          margin: 0 0 16px;
        }

        .options-review {
          display: flex;
          flex-direction: column;
          gap: 8px;

          .option-row {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 14px;
            border-radius: 8px;
            background: #ffffff;
            border: 1px solid var(--border-light);
            font-size: 0.88rem;

            .opt-prefix {
              display: flex;
              align-items: center;

              .icon-c { color: #16a34a; font-size: 18px; width: 18px; height: 18px; }
              .icon-w { color: #ef4444; font-size: 18px; width: 18px; height: 18px; }
              .opt-dot { width: 6px; height: 6px; border-radius: 50%; background: #cbd5e1; }
            }

            .opt-text {
              flex: 1;
              color: #1e293b;
            }

            &.opt-correct {
              background: #f0fdf4;
              border-color: #86efac;
              font-weight: 500;
            }

            &.opt-selected:not(.opt-correct) {
              background: #fef2f2;
              border-color: #fca5a5;
            }

            .badge-correct-key {
              background: #15803d;
              color: #ffffff;
              font-size: 0.72rem;
              padding: 2px 8px;
              border-radius: 4px;
            }

            .badge-wrong-choice {
              background: #b91c1c;
              color: #ffffff;
              font-size: 0.72rem;
              padding: 2px 8px;
              border-radius: 4px;
            }
          }
        }
      }
    }

    .loading-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 80px 0;
      color: var(--text-muted);
      gap: 16px;
    }
  `]
})
export class AssessmentResultComponent implements OnInit, AfterViewInit {
  @ViewChild('radarCanvas') radarCanvas!: ElementRef<HTMLCanvasElement>;
  @ViewChild('barCanvas') barCanvas!: ElementRef<HTMLCanvasElement>;

  data = signal<ExamResultData | null>(null);
  isLoading = signal(true);

  private route = inject(ActivatedRoute);
  private examService = inject(ExamService);
  private codingService = inject(CodingService);

  codingReviews = signal<{ questionId: number; review: string; submissionId: number }[]>([]);

  private radarChartInstance?: Chart;
  private barChartInstance?: Chart;

  ngOnInit(): void {
    const attemptId = Number(this.route.snapshot.paramMap.get('attemptId'));
    if (attemptId) {
      this.loadResult(attemptId);
    }
  }

  ngAfterViewInit(): void {
    // If data arrived before view init, render charts
    if (this.data()) {
      this.renderCharts();
    }
  }

  loadResult(attemptId: number): void {
    this.isLoading.set(true);
    this.examService.getExamResult(attemptId).subscribe({
      next: (res) => {
        this.data.set(res);
        this.isLoading.set(false);
        setTimeout(() => this.renderCharts(), 50);
        this.loadCodingReviews(attemptId);
      },
      error: () => this.isLoading.set(false)
    });
  }

  loadCodingReviews(attemptId: number): void {
    this.codingService.getAttemptSubmissions(attemptId).subscribe({
      next: (subs) => {
        subs.forEach(s => {
          if (s.ai_review) {
            this.codingReviews.update(list => [...list, { questionId: s.question_id, review: s.ai_review!, submissionId: s.id }]);
          } else {
            this.codingService.getSubmissionReview(s.id).subscribe({
              next: (rev) => {
                this.codingReviews.update(list => [...list, { questionId: s.question_id, review: rev.review, submissionId: s.id }]);
              }
            });
          }
        });
      },
      error: () => {}
    });
  }

  renderCharts(): void {
    const result = this.data();
    if (!result) return;

    // 1. Render Radar Chart (Skill-wise strength)
    if (this.radarCanvas && this.radarCanvas.nativeElement) {
      if (this.radarChartInstance) this.radarChartInstance.destroy();

      const skillKeys = Object.keys(result.skill_percentages || {});
      const skillValues = skillKeys.map(k => result.skill_percentages[k]);

      const primary = getCssToken('--csm-primary', '#1e3a8a');
      const accent = getCssToken('--csm-accent', '#2563eb');
      const borderSubtle = getCssToken('--border-subtle', '#bfdbfe');

      this.radarChartInstance = new Chart(this.radarCanvas.nativeElement, {
        type: 'radar',
        data: {
          labels: skillKeys,
          datasets: [{
            label: 'Strength (%)',
            data: skillValues,
            fill: true,
            backgroundColor: 'rgba(30, 58, 138, 0.2)',
            borderColor: primary,
            pointBackgroundColor: accent,
            pointBorderColor: '#ffffff',
            pointHoverBackgroundColor: '#ffffff',
            pointHoverBorderColor: accent,
            pointRadius: 4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            r: {
              beginAtZero: true,
              max: 100,
              ticks: { stepSize: 20 },
              pointLabels: {
                font: { size: 11, weight: 'bold' },
                color: '#1e293b'
              }
            }
          },
          plugins: {
            legend: { display: false }
          }
        }
      });
    }

    // 2. Render Bar Chart (Section-wise Score vs Max)
    if (this.barCanvas && this.barCanvas.nativeElement) {
      if (this.barChartInstance) this.barChartInstance.destroy();

      const secTitles = (result.section_scores || []).map(s => s.title);
      const secObtained = (result.section_scores || []).map(s => s.score);
      const secMax = (result.section_scores || []).map(s => s.max);
      const primary = getCssToken('--csm-primary', '#1e3a8a');
      const accentLight = getCssToken('--accent-light', '#dbeafe');

      this.barChartInstance = new Chart(this.barCanvas.nativeElement, {
        type: 'bar',
        data: {
          labels: secTitles,
          datasets: [
            {
              label: 'Marks Obtained',
              data: secObtained,
              backgroundColor: primary,
              borderRadius: 6
            },
            {
              label: 'Maximum Marks',
              data: secMax,
              backgroundColor: accentLight,
              borderRadius: 6
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: true,
              ticks: { precision: 0 }
            }
          },
          plugins: {
            legend: {
              position: 'top',
              labels: { font: { weight: 'bold' } }
            }
          }
        }
      });
    }
  }
}
