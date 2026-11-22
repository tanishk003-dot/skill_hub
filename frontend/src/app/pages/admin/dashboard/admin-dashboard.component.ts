import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration, ChartData } from 'chart.js';
import { AnalyticsService } from '../../../core/services/analytics.service';
import { AdminDashboardData } from '../../../core/models/analytics.model';
import { getCssToken } from '../../../core/utils/theme-tokens.util';

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    BaseChartDirective
  ],
  template: `
    <div class="admin-dashboard-page">
      <!-- Header Banner -->
      <div class="page-header">
        <div>
          <h1>Administrator Analytics & Operations</h1>
          <p class="subtitle">Real-time organizational competence metrics, cohort progress, and workforce analytics</p>
        </div>
        <div class="header-actions">
          <a mat-flat-button class="btn-primary" routerLink="/admin/cohorts">
            <mat-icon>groups</mat-icon> Manage Cohorts
          </a>
          <a mat-flat-button class="btn-accent" routerLink="/admin/trainings">
            <mat-icon>school</mat-icon> Training Hub
          </a>
          <a mat-stroked-button routerLink="/admin/schedule">
            <mat-icon>calendar_month</mat-icon> Schedule
          </a>
        </div>
      </div>

      <!-- Loading State -->
      <div *ngIf="loading" class="loading-state">
        <mat-spinner diameter="40"></mat-spinner>
        <span>Computing org-wide skill metrics...</span>
      </div>

      <!-- Dashboard Body -->
      <div *ngIf="!loading && data" class="dashboard-content">
        
        <!-- Summary Stats Grid -->
        <div class="stats-grid">
          <mat-card class="stat-card">
            <div class="stat-icon blue">
              <mat-icon>people</mat-icon>
            </div>
            <div class="stat-info">
              <span class="stat-label">Total Users</span>
              <span class="stat-value">{{ data.users_summary.total_users }}</span>
              <span class="stat-sub">{{ data.users_summary.active_users }} active accounts</span>
            </div>
          </mat-card>

          <mat-card class="stat-card">
            <div class="stat-icon orange">
              <mat-icon>groups</mat-icon>
            </div>
            <div class="stat-info">
              <span class="stat-label">Active Cohorts</span>
              <span class="stat-value">{{ data.cohort_comparison.length }}</span>
              <span class="stat-sub">Across engineering units</span>
            </div>
          </mat-card>

          <mat-card class="stat-card">
            <div class="stat-icon green">
              <mat-icon>task_alt</mat-icon>
            </div>
            <div class="stat-info">
              <span class="stat-label">Assessment Rate</span>
              <span class="stat-value">{{ data.completion_rate.percentage | number:'1.1-1' }}%</span>
              <span class="stat-sub">{{ data.completion_rate.completed }} / {{ data.completion_rate.total_assigned }} submitted</span>
            </div>
          </mat-card>

          <mat-card class="stat-card">
            <div class="stat-icon purple">
              <mat-icon>school</mat-icon>
            </div>
            <div class="stat-info">
              <span class="stat-label">Training Rate</span>
              <span class="stat-value">{{ data.training_metrics ? (data.training_metrics.completion_rate | number:'1.0-0') + '%' : '0%' }}</span>
              <span class="stat-sub">{{ data.training_metrics?.completed || 0 }} / {{ data.training_metrics?.total_assigned || 0 }} modules</span>
            </div>
          </mat-card>

          <mat-card class="stat-card">
            <div class="stat-icon teal">
              <mat-icon>video_camera_front</mat-icon>
            </div>
            <div class="stat-info">
              <span class="stat-label">Class Attendance</span>
              <span class="stat-value">{{ data.attendance_metrics ? (data.attendance_metrics.attendance_rate | number:'1.0-0') + '%' : '0%' }}</span>
              <span class="stat-sub">{{ data.attendance_metrics?.total_attended || 0 }} of {{ data.attendance_metrics?.total_invited || 0 }} attended</span>
            </div>
          </mat-card>

          <mat-card class="stat-card">
            <div class="stat-icon amber">
              <mat-icon>person_off</mat-icon>
            </div>
            <div class="stat-info">
              <span class="stat-label">Inactive Users</span>
              <span class="stat-value" [class.text-amber]="data.users_summary.inactive_users > 0">{{ data.users_summary.inactive_users }}</span>
              <span class="stat-sub">{{ data.users_summary.pending_attempts }} pending attempts</span>
            </div>
          </mat-card>
        </div>

        <!-- Completion Rate Progress Bar Card -->
        <mat-card class="progress-banner-card">
          <div class="progress-header">
            <div class="progress-title">
              <mat-icon color="primary">donut_large</mat-icon>
              <div>
                <h4>Assessment Workflow Throughput</h4>
                <p>Tracking completed submissions vs total assigned evaluations</p>
              </div>
            </div>
            <span class="progress-percent">{{ data.completion_rate.percentage | number:'1.1-1' }}%</span>
          </div>
          <mat-progress-bar mode="determinate" [value]="data.completion_rate.percentage" class="custom-progress"></mat-progress-bar>
        </mat-card>

        <!-- Charts Grid: Cohort Comparison & Org Skill Gap -->
        <div class="analytics-row">
          
          <!-- Cohort Comparison Bar Chart -->
          <mat-card class="chart-panel">
            <mat-card-header>
              <mat-icon mat-card-avatar color="primary">bar_chart</mat-icon>
              <mat-card-title>Cohort Benchmarks</mat-card-title>
              <mat-card-subtitle>Average score and passing percentage across batches</mat-card-subtitle>
            </mat-card-header>
            <mat-card-content class="chart-content">
              <div *ngIf="cohortChartData.labels?.length; else emptyCohortChart" class="chart-box">
                <canvas baseChart
                  [data]="cohortChartData"
                  [options]="cohortChartOptions"
                  [type]="'bar'">
                </canvas>
              </div>
              <ng-template #emptyCohortChart>
                <div class="chart-empty">No cohort attempt data recorded yet.</div>
              </ng-template>
            </mat-card-content>
          </mat-card>

          <!-- Org Skill Gap Analysis -->
          <mat-card class="chart-panel">
            <mat-card-header>
              <mat-icon mat-card-avatar color="accent">insights</mat-icon>
              <mat-card-title>Org-Wide Skill Gap</mat-card-title>
              <mat-card-subtitle>Mean competence level per domain across all ASE submissions</mat-card-subtitle>
            </mat-card-header>
            <mat-card-content class="chart-content">
              <div *ngIf="skillGapChartData.labels?.length; else emptySkillChart" class="chart-box">
                <canvas baseChart
                  [data]="skillGapChartData"
                  [options]="skillGapChartOptions"
                  [type]="'bar'">
                </canvas>
              </div>
              <ng-template #emptySkillChart>
                <div class="chart-empty">Skill gap metrics will populate as assessments are graded.</div>
              </ng-template>
            </mat-card-content>
          </mat-card>
        </div>

        <!-- Org Overdue Trainings Section (If any) -->
        <mat-card class="overdue-card" *ngIf="data.overdue_trainings && data.overdue_trainings.length > 0">
          <div class="overdue-header">
            <div class="title-with-badge">
              <mat-icon class="text-orange">schedule</mat-icon>
              <h3>Org-Wide Overdue Training Modules ({{ data.overdue_trainings.length }})</h3>
            </div>
            <span class="hint-text">Assignments past their due date across all cohorts</span>
          </div>
          <div class="table-responsive">
            <table class="styled-table">
              <thead>
                <tr>
                  <th>Associate Engineer</th>
                  <th>Training Module</th>
                  <th>Due Date</th>
                  <th>Progress</th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let item of data.overdue_trainings">
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

        <!-- Quick Access Section -->
        <div class="quick-links-grid">
          <mat-card class="link-card" routerLink="/admin/cohorts">
            <mat-icon class="link-icon blue-text">groups</mat-icon>
            <div class="link-info">
              <h4>Cohort Directory</h4>
              <p>Create cohorts, manage student rosters, and run batch CSV exports</p>
            </div>
            <mat-icon class="arrow-icon">arrow_forward</mat-icon>
          </mat-card>

          <mat-card class="link-card" routerLink="/admin/assessments">
            <mat-icon class="link-icon orange-text">assignment</mat-icon>
            <div class="link-info">
              <h4>Assessment Engine</h4>
              <p>Draft tests, configure multi-section timers, and dispatch to cohorts</p>
            </div>
            <mat-icon class="arrow-icon">arrow_forward</mat-icon>
          </mat-card>

          <mat-card class="link-card" routerLink="/admin/trainings">
            <mat-icon class="link-icon purple-text">school</mat-icon>
            <div class="link-info">
              <h4>Training Programs</h4>
              <p>Publish modules, suggest weak ASEs, and track skill mastery</p>
            </div>
            <mat-icon class="arrow-icon">arrow_forward</mat-icon>
          </mat-card>

          <mat-card class="link-card" routerLink="/admin/classes">
            <mat-icon class="link-icon teal-text">video_camera_front</mat-icon>
            <div class="link-info">
              <h4>Live Classes</h4>
              <p>Schedule virtual sessions, integrate Teams links, and mark attendance</p>
            </div>
            <mat-icon class="arrow-icon">arrow_forward</mat-icon>
          </mat-card>

          <mat-card class="link-card" routerLink="/admin/users">
            <mat-icon class="link-icon green-text">manage_accounts</mat-icon>
            <div class="link-info">
              <h4>User Management</h4>
              <p>Provision roles, activate accounts, and track mentorship pairings</p>
            </div>
            <mat-icon class="arrow-icon">arrow_forward</mat-icon>
          </mat-card>
        </div>

      </div>
    </div>
  `,
  styles: [`
    .admin-dashboard-page {
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
      font-size: 1.7rem;
      font-weight: 700;
    }

    .subtitle {
      margin: 4px 0 0 0;
      color: #64748B;
      font-size: 0.95rem;
    }

    .header-actions {
      display: flex;
      gap: 12px;
      align-items: center;
    }

    .btn-primary {
      background: var(--csm-primary) !important;
      color: #ffffff !important;
    }

    .btn-accent {
      background: var(--csm-accent) !important;
      color: #ffffff !important;
    }

    .loading-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;
      padding: 60px 0;
      color: #64748B;
    }

    /* Stats Grid */
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
    }

    .stat-card {
      padding: 16px;
      border-radius: 12px;
      border: 1px solid #E2E8F0;
      display: flex;
      align-items: center;
      gap: 16px;
      background: #ffffff;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    .stat-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .stat-icon mat-icon {
      font-size: 26px;
      width: 26px;
      height: 26px;
    }

    .stat-icon.blue { background: #EFF6FF; color: var(--csm-primary); }
    .stat-icon.orange { background: #FFF7ED; color: var(--csm-accent); }
    .stat-icon.green { background: #ECFDF5; color: #059669; }
    .stat-icon.amber { background: #FEF3C7; color: #D97706; }
    .stat-icon.purple { background: #F5F3FF; color: #7C3AED; }
    .stat-icon.teal { background: #F0FDFA; color: #0D9488; }

    .stat-info {
      display: flex;
      flex-direction: column;
    }

    .stat-label {
      font-size: 0.78rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #64748B;
    }

    .stat-value {
      font-size: 1.6rem;
      font-weight: 700;
      color: #0F172A;
      line-height: 1.2;
    }

    .stat-sub {
      font-size: 0.75rem;
      color: #94A3B8;
      margin-top: 2px;
    }

    .text-amber { color: #D97706 !important; }
    .text-danger { color: #DC2626 !important; }
    .text-orange { color: #EA580C !important; }
    .font-bold { font-weight: 700; }

    /* Progress Banner Card */
    .progress-banner-card {
      border-radius: 12px;
      border: 1px solid #E2E8F0;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
      background: #ffffff;
      padding: 20px;
    }

    .progress-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }

    .progress-title {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .progress-title h4 {
      margin: 0;
      font-size: 1.05rem;
      font-weight: 600;
      color: #0F172A;
    }

    .progress-title p {
      margin: 2px 0 0 0;
      font-size: 0.82rem;
      color: #64748B;
    }

    .progress-percent {
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--csm-primary);
    }

    .custom-progress {
      height: 10px;
      border-radius: 5px;
    }

    /* Analytics row */
    .analytics-row {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(440px, 1fr));
      gap: 20px;
      margin-top: 4px;
    }

    .chart-panel {
      border-radius: 12px;
      border: 1px solid #E2E8F0;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
      background: #ffffff;
      padding: 16px;
    }

    .chart-content {
      padding-top: 16px;
    }

    .chart-box {
      width: 100%;
      height: 300px;
      position: relative;
    }

    .chart-empty {
      color: #94A3B8;
      font-style: italic;
      text-align: center;
      padding: 50px 0;
    }

    /* Overdue Card */
    .overdue-card {
      border-radius: 12px;
      border-left: 4px solid #EA580C;
      background: #FFFBF7;
      padding: 16px 20px;
      box-shadow: 0 1px 3px rgba(234, 88, 12, 0.1);
      margin-top: 4px;
    }

    .overdue-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      margin-bottom: 12px;
    }

    .title-with-badge {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .title-with-badge h3 {
      margin: 0;
      font-size: 1.05rem;
      font-weight: 700;
      color: #1E293B;
    }

    .hint-text {
      font-size: 0.82rem;
      color: #64748B;
    }

    .table-responsive {
      overflow-x: auto;
    }

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

    /* Quick Links */
    .quick-links-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-top: 8px;
    }

    .link-card {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 18px;
      border-radius: 12px;
      border: 1px solid #E2E8F0;
      background: #ffffff;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .link-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0,0,0,0.08);
      border-color: #CBD5E1;
    }

    .link-icon {
      font-size: 30px;
      width: 30px;
      height: 30px;
    }

    .blue-text { color: var(--csm-primary); }
    .orange-text { color: var(--csm-accent); }
    .green-text { color: #059669; }
    .purple-text { color: #7C3AED; }
    .teal-text { color: #0D9488; }

    .link-info {
      flex: 1;
    }

    .link-info h4 {
      margin: 0 0 4px 0;
      font-size: 0.95rem;
      color: #0F172A;
    }

    .link-info p {
      margin: 0;
      font-size: 0.78rem;
      color: #64748B;
    }

    .arrow-icon {
      color: #94A3B8;
    }
  `]
})
export class AdminDashboardComponent implements OnInit {
  data: AdminDashboardData | null = null;
  loading = true;

  // Cohort comparison bar chart
  cohortChartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      y: { min: 0, max: 100, ticks: { stepSize: 20 } }
    },
    plugins: {
      legend: { display: true, position: 'top' }
    }
  };
  cohortChartData: ChartData<'bar'> = { labels: [], datasets: [] };

  // Org skill gap bar chart
  skillGapChartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: 'y', // horizontal bar
    scales: {
      x: { min: 0, max: 100, ticks: { stepSize: 20 } }
    },
    plugins: {
      legend: { display: false }
    }
  };
  skillGapChartData: ChartData<'bar'> = { labels: [], datasets: [] };

  constructor(private analyticsService: AnalyticsService) {}

  ngOnInit(): void {
    this.loadAdminData();
  }

  loadAdminData(): void {
    this.loading = true;
    this.analyticsService.getAdminDashboard().subscribe({
      next: (res: AdminDashboardData) => {
        this.data = res;
        this.buildCharts(res);
        this.loading = false;
      },
      error: (err: any) => {
        console.error('Failed to load admin dashboard data', err);
        this.loading = false;
      }
    });
  }

  buildCharts(res: AdminDashboardData): void {
    const primary = getCssToken('--csm-primary', '#1e3a8a');
    const accent = getCssToken('--csm-accent', '#2563eb');
    const success = getCssToken('--color-success', '#15803d');
    const warning = getCssToken('--color-warning', '#b45309');
    const danger = getCssToken('--color-danger', '#b91c1c');

    // 1. Cohort comparison
    const cohorts = res.cohort_comparison || [];
    this.cohortChartData = {
      labels: cohorts.map(c => c.cohort_name),
      datasets: [
        {
          label: 'Average Score %',
          data: cohorts.map(c => c.average_score),
          backgroundColor: primary,
          borderRadius: 4
        },
        {
          label: 'Passing %',
          data: cohorts.map(c => c.passing_rate),
          backgroundColor: accent,
          borderRadius: 4
        }
      ]
    };

    // 2. Org skill gap chart
    const skillGaps = res.org_skill_gaps || [];
    this.skillGapChartData = {
      labels: skillGaps.length ? skillGaps.map(g => g.skill) : ['No data'],
      datasets: [
        {
          label: 'Average Score %',
          data: skillGaps.length ? skillGaps.map(g => g.average_score) : [0],
          backgroundColor: skillGaps.map(g => g.average_score >= 70 ? success : (g.average_score >= 50 ? warning : danger)),
          borderRadius: 4
        }
      ]
    };
  }
}
