import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Phase9Service } from '../../../core/services/phase9.service';
import { CEOOverview, ReadinessConfig } from '../../../core/models/phase9.model';

@Component({
  selector: 'app-ceo-command-center',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="ceo-container">
      <!-- Header Banner -->
      <div class="header-card">
        <div class="header-content">
          <div class="title-group">
            <span class="badge-ceo">EXECUTIVE SUITE</span>
            <h1>CEO Command Center</h1>
            <p class="subtitle">Organization-wide Engineering Readiness, Time-to-Productivity & Training ROI Diagnostics</p>
          </div>
          <div class="header-actions">
            <button class="btn-export" (click)="downloadPdf()" [disabled]="isExporting">
              <span *ngIf="!isExporting">📊 Export PDF Diagnostic</span>
              <span *ngIf="isExporting">Generating Report...</span>
            </button>
          </div>
        </div>
      </div>

      <div *ngIf="loading" class="loading-state">
        <div class="spinner"></div>
        <p>Synthesizing organizational diagnostics...</p>
      </div>

      <div *ngIf="!loading && overview" class="dashboard-body">
        <!-- Top Metrics Cards -->
        <div class="metrics-grid">
          <div class="metric-card">
            <div class="metric-icon readiness-icon">🎯</div>
            <div class="metric-info">
              <div class="metric-label">Org-Wide Readiness</div>
              <div class="metric-value">{{ overview.org_readiness_avg }}%</div>
              <div class="metric-sub">Across {{ overview.total_ases }} Active ASEs</div>
            </div>
          </div>

          <div class="metric-card">
            <div class="metric-icon time-icon">⏱️</div>
            <div class="metric-info">
              <div class="metric-label">Time-to-Productivity</div>
              <div class="metric-value">
                <span *ngIf="overview.time_to_productivity_days !== null && overview.time_to_productivity_days !== undefined">
                  {{ overview.time_to_productivity_days }} Days
                </span>
                <span *ngIf="overview.time_to_productivity_days === null || overview.time_to_productivity_days === undefined" class="text-muted" style="font-size: 1.1rem; font-weight: 500;">
                  Insufficient data
                </span>
              </div>
              <div class="metric-sub">{{ overview.time_to_productivity_status || 'Target Benchmark: 45 Days' }}</div>
            </div>
          </div>

          <div class="metric-card">
            <div class="metric-icon roi-icon">🚀</div>
            <div class="metric-info">
              <div class="metric-label">Training ROI Uplift</div>
              <div class="metric-value text-orange">
                <span *ngIf="overview.training_roi_uplift_pct !== null && overview.training_roi_uplift_pct !== undefined">
                  +{{ overview.training_roi_uplift_pct }}%
                </span>
                <span *ngIf="overview.training_roi_uplift_pct === null || overview.training_roi_uplift_pct === undefined" class="text-muted" style="font-size: 1.1rem; font-weight: 500;">
                  Insufficient data
                </span>
              </div>
              <div class="metric-sub">{{ overview.training_roi_status || 'Pre vs Post-Training Performance' }}</div>
            </div>
          </div>

          <div class="metric-card">
            <div class="metric-icon risk-icon">🛡️</div>
            <div class="metric-info">
              <div class="metric-label">High-Risk ASEs</div>
              <div class="metric-value" [class.text-danger]="overview.high_risk_count > 0">{{ overview.high_risk_count }}</div>
              <div class="metric-sub">Requiring Mentor Intervention</div>
            </div>
          </div>
        </div>

        <!-- Formulas and Causation Notice Banner -->
        <div class="disclaimer-banner">
          <div class="banner-title">
            <span class="info-icon">ℹ️</span> Scientific Operational Metric Standard
          </div>
          <p class="banner-text">
            <strong>Time-to-Productivity:</strong> {{ overview.formulas['time_to_productivity'] }}<br/>
            <strong>Training ROI Uplift:</strong> {{ overview.formulas['training_roi'] }}<br/>
            <strong>Readiness Index:</strong> {{ overview.formulas['readiness_index'] }}
          </p>
          <div class="banner-notice">
            ⚠️ <em>{{ overview.correlation_disclaimer }}</em>
          </div>
        </div>

        <!-- Two Column Section: Cohort Benchmarks & Skill Gap Heatmap -->
        <div class="two-col-grid">
          <!-- Cohort Benchmarking Table with Privacy Masking -->
          <div class="panel-card">
            <div class="panel-header">
              <h2>Cohort Benchmarks & Privacy Governance</h2>
              <span class="privacy-note">Privacy rule: Cohorts with &lt; 3 ASEs are masked to prevent individual disclosure</span>
            </div>
            <div class="table-container">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Cohort</th>
                    <th>Engineers</th>
                    <th>Avg Readiness</th>
                    <th>Risk Profile</th>
                  </tr>
                </thead>
                <tbody>
                  <tr *ngFor="let c of overview.cohorts" [class.masked-row]="c.is_masked">
                    <td>
                      <strong>{{ c.cohort_name }}</strong>
                      <span *ngIf="c.is_masked" class="tag-masked">Privacy Protected</span>
                    </td>
                    <td>{{ c.member_count }}</td>
                    <td>
                      <span class="readiness-pill" [class.pill-masked]="c.is_masked">
                        {{ c.average_readiness }}
                      </span>
                    </td>
                    <td>
                      <span class="badge" [ngClass]="getRiskBadgeClass(c.risk_profile)">
                        {{ c.risk_profile }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Skill Gap Heatmap -->
          <div class="panel-card">
            <div class="panel-header">
              <h2>Org Skill Gap Diagnostics</h2>
              <span class="privacy-note">Lower index = Critical upskilling priority</span>
            </div>
            <div class="heatmap-list">
              <div *ngFor="let item of skillGapList" class="heatmap-item">
                <div class="heatmap-labels">
                  <span class="skill-name">{{ item.skill }}</span>
                  <span class="skill-pct" [class.text-alert]="item.index < 70">{{ item.index }}% Index</span>
                </div>
                <div class="progress-bar-bg">
                  <div class="progress-bar-fill" [style.width.%]="item.index" [ngClass]="getHeatmapBarClass(item.index)"></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Admin Readiness Weights Governance Panel -->
        <div class="panel-card weights-panel">
          <div class="panel-header">
            <h2>Readiness Score Formula Weight Governance (Admin Only)</h2>
            <span class="privacy-note">All weights must strictly sum to 1.0 (100%). Audited on every update.</span>
          </div>
          <div class="weights-grid" *ngIf="readinessConfig">
            <div class="weight-item">
              <label>Assessments Weight (0 - 1.0)</label>
              <input type="number" step="0.05" min="0" max="1" [(ngModel)]="readinessConfig.assessment_weight" (change)="checkWeightSum()" />
            </div>
            <div class="weight-item">
              <label>Coding Submissions Weight</label>
              <input type="number" step="0.05" min="0" max="1" [(ngModel)]="readinessConfig.coding_weight" (change)="checkWeightSum()" />
            </div>
            <div class="weight-item">
              <label>Training Progress Weight</label>
              <input type="number" step="0.05" min="0" max="1" [(ngModel)]="readinessConfig.training_weight" (change)="checkWeightSum()" />
            </div>
            <div class="weight-item">
              <label>Live Class Attendance Weight</label>
              <input type="number" step="0.05" min="0" max="1" [(ngModel)]="readinessConfig.attendance_weight" (change)="checkWeightSum()" />
            </div>
            <div class="weight-item">
              <label>Daily Streak Consistency Weight</label>
              <input type="number" step="0.05" min="0" max="1" [(ngModel)]="readinessConfig.consistency_weight" (change)="checkWeightSum()" />
            </div>
          </div>

          <div class="weights-footer">
            <div class="sum-indicator" [class.sum-valid]="isSumValid" [class.sum-invalid]="!isSumValid">
              Total Weight: {{ currentWeightSum | number:'1.2-2' }} / 1.00 ({{ (currentWeightSum * 100) | number:'1.0-0' }}%)
              <span *ngIf="!isSumValid" class="err-text">❌ Sum must be exactly 1.00</span>
              <span *ngIf="isSumValid" class="success-text">✅ Valid Configuration</span>
            </div>
            <button class="btn-save" [disabled]="!isSumValid || isSavingWeights" (click)="saveWeights()">
              {{ isSavingWeights ? 'Saving Weights...' : 'Save & Publish Weights' }}
            </button>
          </div>
          <p *ngIf="saveMsg" class="feedback-msg" [class.success]="saveSuccess" [class.error]="!saveSuccess">{{ saveMsg }}</p>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .ceo-container {
      padding: 24px;
      max-width: 1300px;
      margin: 0 auto;
    }
    .header-card {
      background: linear-gradient(135deg, var(--csm-primary) 0%, #0F172A 100%);
      color: white;
      padding: 28px 32px;
      border-radius: 12px;
      margin-bottom: 24px;
      box-shadow: 0 4px 16px rgba(15, 23, 42, 0.15);
    }
    .header-content {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
    }
    .badge-ceo {
      background: var(--csm-accent);
      color: white;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 1px;
      padding: 3px 8px;
      border-radius: 4px;
      display: inline-block;
      margin-bottom: 8px;
    }
    .title-group h1 {
      margin: 0 0 6px 0;
      font-size: 28px;
      font-weight: 700;
    }
    .subtitle {
      margin: 0;
      color: #94A3B8;
      font-size: 14px;
    }
    .btn-export {
      background: var(--csm-accent);
      color: white;
      border: none;
      padding: 12px 20px;
      border-radius: 8px;
      font-weight: 600;
      font-size: 14px;
      cursor: pointer;
      box-shadow: 0 2px 8px rgba(249, 115, 22, 0.3);
      transition: all 0.2s;
    }
    .btn-export:hover:not(:disabled) {
      background: #EA580C;
      transform: translateY(-1px);
    }
    .btn-export:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .metric-card {
      background: white;
      border: 1px solid #E2E8F0;
      border-radius: 10px;
      padding: 20px;
      display: flex;
      align-items: center;
      gap: 16px;
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03);
    }
    .metric-icon {
      font-size: 28px;
      width: 52px;
      height: 52px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #F8FAFC;
      border-radius: 10px;
    }
    .metric-label {
      font-size: 13px;
      color: #64748B;
      font-weight: 500;
    }
    .metric-value {
      font-size: 26px;
      font-weight: 700;
      color: var(--csm-primary);
      margin: 2px 0;
    }
    .text-orange { color: var(--csm-accent); }
    .text-danger { color: #EF4444; }
    .metric-sub {
      font-size: 12px;
      color: #94A3B8;
    }
    .disclaimer-banner {
      background: #EFF6FF;
      border-left: 4px solid var(--csm-primary);
      padding: 16px 20px;
      border-radius: 8px;
      margin-bottom: 24px;
    }
    .banner-title {
      font-size: 14px;
      font-weight: 700;
      color: var(--csm-primary);
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .banner-text {
      font-size: 13px;
      color: #334155;
      line-height: 1.5;
      margin: 0 0 8px 0;
    }
    .banner-notice {
      font-size: 12px;
      color: #64748B;
      border-top: 1px solid #DBEAFE;
      padding-top: 6px;
    }
    .two-col-grid {
      display: grid;
      grid-template-columns: 1.4fr 1fr;
      gap: 20px;
      margin-bottom: 24px;
    }
    @media (max-width: 900px) {
      .two-col-grid { grid-template-columns: 1fr; }
    }
    .panel-card {
      background: white;
      border: 1px solid #E2E8F0;
      border-radius: 10px;
      padding: 20px;
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03);
    }
    .panel-header {
      margin-bottom: 16px;
    }
    .panel-header h2 {
      margin: 0 0 4px 0;
      font-size: 17px;
      font-weight: 700;
      color: #0F172A;
    }
    .privacy-note {
      font-size: 12px;
      color: #64748B;
    }
    .table-container {
      overflow-x: auto;
    }
    .data-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }
    .data-table th {
      text-align: left;
      padding: 10px 12px;
      background: #F8FAFC;
      color: #475569;
      border-bottom: 1px solid #E2E8F0;
    }
    .data-table td {
      padding: 12px;
      border-bottom: 1px solid #F1F5F9;
      color: #1E293B;
    }
    .masked-row {
      background: #FAFAFA;
      font-style: italic;
    }
    .tag-masked {
      display: block;
      font-size: 10px;
      color: #64748B;
      margin-top: 2px;
    }
    .readiness-pill {
      font-weight: 600;
      color: var(--csm-primary);
    }
    .pill-masked {
      color: #64748B;
      font-weight: normal;
    }
    .badge {
      display: inline-block;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 600;
    }
    .badge-green { background: var(--color-success-bg); color: var(--color-success-text); }
    .badge-yellow { background: var(--color-warning-bg); color: var(--color-warning-text); }
    .badge-red { background: var(--color-danger-bg); color: var(--color-danger-text); }
    .badge-muted { background: var(--bg-main); color: var(--text-muted); }

    .heatmap-list {
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .heatmap-labels {
      display: flex;
      justify-content: space-between;
      font-size: 13px;
      font-weight: 500;
      margin-bottom: 4px;
    }
    .text-alert { color: var(--color-danger); font-weight: 700; }
    .progress-bar-bg {
      background: var(--bg-main);
      border-radius: 6px;
      height: 8px;
      overflow: hidden;
    }
    .progress-bar-fill {
      height: 100%;
      border-radius: 6px;
      transition: width 0.3s ease;
    }
    .fill-green { background: var(--color-success); }
    .fill-blue { background: var(--csm-primary); }
    .fill-yellow { background: var(--color-warning); }
    .fill-red { background: var(--color-danger); }

    .weights-panel {
      margin-top: 24px;
    }
    .weights-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 16px;
      margin: 16px 0;
    }
    .weight-item label {
      display: block;
      font-size: 12px;
      font-weight: 600;
      color: #475569;
      margin-bottom: 4px;
    }
    .weight-item input {
      width: 100%;
      padding: 8px 12px;
      border: 1px solid #CBD5E1;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 600;
    }
    .weights-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 16px;
      padding-top: 14px;
      border-top: 1px solid #E2E8F0;
    }
    .sum-indicator {
      font-size: 14px;
      font-weight: 600;
    }
    .sum-valid { color: #166534; }
    .sum-invalid { color: #DC2626; }
    .btn-save {
      background: var(--csm-primary);
      color: white;
      border: none;
      padding: 10px 18px;
      border-radius: 6px;
      font-weight: 600;
      cursor: pointer;
    }
    .btn-save:hover:not(:disabled) {
      background: #172554;
    }
    .btn-save:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    .feedback-msg {
      margin-top: 10px;
      font-size: 13px;
      font-weight: 600;
    }
    .feedback-msg.success { color: #166534; }
    .feedback-msg.error { color: #DC2626; }
    .loading-state {
      text-align: center;
      padding: 60px 0;
      color: #64748B;
    }
    .spinner {
      border: 4px solid #E2E8F0;
      border-top: 4px solid var(--csm-primary);
      border-radius: 50%;
      width: 36px;
      height: 36px;
      animation: spin 1s linear infinite;
      margin: 0 auto 12px auto;
    }
    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
  `]
})
export class CEOCommandCenterComponent implements OnInit {
  overview: any = null;
  loading: boolean = true;
  isExporting: boolean = false;
  readinessConfig: ReadinessConfig | null = null;
  currentWeightSum: number = 1.0;
  isSumValid: boolean = true;
  isSavingWeights: boolean = false;
  saveMsg: string = '';
  saveSuccess: boolean = false;

  skillGapList: { skill: string; index: number }[] = [];

  constructor(private phase9Service: Phase9Service) {}

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.loading = true;
    this.phase9Service.getCEOOverview().subscribe({
      next: (data) => {
        this.overview = data;
        if (data.skill_gap_heatmap) {
          this.skillGapList = Object.entries(data.skill_gap_heatmap).map(([skill, index]) => ({
            skill,
            index: Number(index)
          }));
        }
        this.loading = false;
      },
      error: (err) => {
        console.error('Failed to load CEO overview:', err);
        this.loading = false;
      }
    });

    this.phase9Service.getReadinessConfig().subscribe({
      next: (cfg) => {
        this.readinessConfig = cfg;
        this.checkWeightSum();
      },
      error: (err) => console.error('Failed to load readiness config:', err)
    });
  }

  checkWeightSum(): void {
    if (!this.readinessConfig) return;
    const sum =
      Number(this.readinessConfig.assessment_weight || 0) +
      Number(this.readinessConfig.coding_weight || 0) +
      Number(this.readinessConfig.training_weight || 0) +
      Number(this.readinessConfig.attendance_weight || 0) +
      Number(this.readinessConfig.consistency_weight || 0);

    this.currentWeightSum = Math.round(sum * 100) / 100;
    this.isSumValid = Math.abs(this.currentWeightSum - 1.0) < 0.001;
  }

  saveWeights(): void {
    if (!this.readinessConfig || !this.isSumValid) return;
    this.isSavingWeights = true;
    this.saveMsg = '';
    this.phase9Service.updateReadinessConfig(this.readinessConfig).subscribe({
      next: () => {
        this.isSavingWeights = false;
        this.saveSuccess = true;
        this.saveMsg = 'Weights updated and logged in readiness audit successfully!';
        this.loadData();
      },
      error: (err) => {
        this.isSavingWeights = false;
        this.saveSuccess = false;
        this.saveMsg = err.error?.detail || 'Failed to update weights.';
      }
    });
  }

  downloadPdf(): void {
    this.isExporting = true;
    this.phase9Service.downloadExecutiveReport().subscribe({
      next: (blob) => {
        this.isExporting = false;
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ceo_executive_report_${Date.now()}.pdf`;
        a.click();
        window.URL.revokeObjectURL(url);
      },
      error: (err) => {
        this.isExporting = false;
        console.error('Failed to download executive report PDF:', err);
      }
    });
  }

  getRiskBadgeClass(profile: string): string {
    if (profile === 'Low Risk') return 'badge-green';
    if (profile === 'Medium Risk') return 'badge-yellow';
    if (profile === 'High Risk') return 'badge-red';
    return 'badge-muted';
  }

  getHeatmapBarClass(index: number): string {
    if (index >= 80) return 'fill-green';
    if (index >= 70) return 'fill-blue';
    if (index >= 60) return 'fill-yellow';
    return 'fill-red';
  }
}
