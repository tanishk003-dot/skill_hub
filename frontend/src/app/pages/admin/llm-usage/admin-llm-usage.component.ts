import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ChatService } from '../../../core/services/chat.service';
import { AdminLLMUsageSummary } from '../../../core/models/chat.model';

@Component({
  selector: 'app-admin-llm-usage',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatTableModule,
    MatButtonModule,
    MatProgressSpinnerModule
  ],
  template: `
    <div class="llm-usage-page">
      <div class="page-header">
        <div>
          <h1>AI Token Usage & Cost Management</h1>
          <p class="subtitle">Monitor organizational AI inference consumption, rate-limit policies, and token audit logs</p>
        </div>
        <button mat-stroked-button color="primary" (click)="loadUsageData()" [disabled]="loading">
          <mat-icon>refresh</mat-icon> Refresh
        </button>
      </div>

      <!-- Loading skeleton -->
      <div *ngIf="loading" class="loading-state">
        <mat-spinner diameter="40"></mat-spinner>
        <span>Loading AI token consumption telemetry...</span>
      </div>

      <div *ngIf="!loading && usageData" class="usage-content">
        <!-- KPI Cards -->
        <div class="stats-grid">
          <mat-card class="stat-card">
            <div class="stat-icon purple">
              <mat-icon>token</mat-icon>
            </div>
            <div class="stat-info">
              <span class="label">Total Tokens</span>
              <span class="value">{{ usageData.total_tokens | number }}</span>
              <span class="hint">Across all user queries</span>
            </div>
          </mat-card>

          <mat-card class="stat-card">
            <div class="stat-icon blue">
              <mat-icon>input</mat-icon>
            </div>
            <div class="stat-info">
              <span class="label">Prompt Tokens</span>
              <span class="value">{{ usageData.total_prompt_tokens | number }}</span>
              <span class="hint">Context & system prompts</span>
            </div>
          </mat-card>

          <mat-card class="stat-card">
            <div class="stat-icon green">
              <mat-icon>output</mat-icon>
            </div>
            <div class="stat-info">
              <span class="label">Completion Tokens</span>
              <span class="value">{{ usageData.total_completion_tokens | number }}</span>
              <span class="hint">Model-generated answers</span>
            </div>
          </mat-card>

          <mat-card class="stat-card">
            <div class="stat-icon orange">
              <mat-icon>chat</mat-icon>
            </div>
            <div class="stat-info">
              <span class="label">Total Queries</span>
              <span class="value">{{ usageData.total_requests }}</span>
              <span class="hint">Limit: {{ usageData.rate_limit_per_hour }}/hr per user</span>
            </div>
          </mat-card>
        </div>

        <!-- Privacy & Model Configuration Banner -->
        <mat-card class="info-banner">
          <div class="info-flex">
            <div class="model-badge-wrap">
              <span class="badge-title">Active AI Provider:</span>
              <span class="provider-pill">{{ usageData.provider }} ({{ usageData.model }})</span>
              <span class="demo-tag" *ngIf="usageData.demo_mode">Demo AI Mode</span>
            </div>
            <div class="privacy-note">
              <mat-icon class="shield-icon">security</mat-icon>
              <span><strong>Privacy Protection Guarantee:</strong> Only token volume and timing are logged. Message contents, user prompts, and personal data are strictly excluded from administrative logs.</span>
            </div>
          </div>
        </mat-card>

        <!-- Audit Log Table -->
        <mat-card class="table-card">
          <mat-card-header>
            <mat-icon mat-card-avatar color="primary">history</mat-icon>
            <mat-card-title>Recent Inference Requests</mat-card-title>
            <mat-card-subtitle>Latest 50 token usage entries across engineering units</mat-card-subtitle>
          </mat-card-header>
          <mat-card-content>
            <div class="table-responsive">
              <table class="styled-table">
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Role</th>
                    <th>Provider</th>
                    <th>Model</th>
                    <th class="text-right">Prompt Tokens</th>
                    <th class="text-right">Completion Tokens</th>
                    <th class="text-right">Total Tokens</th>
                    <th>Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  <tr *ngFor="let log of usageData.recent_logs">
                    <td class="font-bold">{{ log.user_name }}</td>
                    <td><span class="role-chip" [ngClass]="log.role.toLowerCase()">{{ log.role }}</span></td>
                    <td>{{ log.provider }}</td>
                    <td>{{ log.model }}</td>
                    <td class="text-right">{{ log.prompt_tokens | number }}</td>
                    <td class="text-right">{{ log.completion_tokens | number }}</td>
                    <td class="text-right font-bold">{{ log.total_tokens | number }}</td>
                    <td class="text-muted">{{ log.created_at | date:'yyyy-MM-dd HH:mm' }}</td>
                  </tr>
                  <tr *ngIf="usageData.recent_logs.length === 0">
                    <td colspan="8" class="text-center text-muted py-4">No AI token usage recorded yet.</td>
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
    .llm-usage-page {
      display: flex;
      flex-direction: column;
      gap: 20px;
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
      font-size: 1.7rem;
      font-weight: 700;
      color: #0F172A;
    }

    .subtitle {
      margin: 4px 0 0;
      color: #64748B;
      font-size: 0.95rem;
    }

    .loading-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;
      padding: 60px 0;
      color: #64748B;
    }

    .usage-content {
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    /* Grid */
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
    }

    .stat-card {
      padding: 18px;
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

    .stat-icon.purple { background: #F5F3FF; color: #7C3AED; }
    .stat-icon.blue { background: #EFF6FF; color: var(--csm-primary); }
    .stat-icon.green { background: #ECFDF5; color: #059669; }
    .stat-icon.orange { background: #FFF7ED; color: var(--csm-accent); }

    .stat-info {
      display: flex;
      flex-direction: column;
    }

    .stat-info .label {
      font-size: 0.78rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #64748B;
    }

    .stat-info .value {
      font-size: 1.6rem;
      font-weight: 700;
      color: #0F172A;
      line-height: 1.2;
    }

    .stat-info .hint {
      font-size: 0.75rem;
      color: #94A3B8;
      margin-top: 2px;
    }

    /* Info banner */
    .info-banner {
      border-radius: 12px;
      border: 1px solid #E2E8F0;
      padding: 16px 20px;
      background: #ffffff;
    }

    .info-flex {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
    }

    .model-badge-wrap {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .badge-title {
      font-weight: 600;
      color: #475569;
      font-size: 0.88rem;
    }

    .provider-pill {
      background: #EFF6FF;
      color: var(--csm-primary);
      border: 1px solid #BFDBFE;
      padding: 4px 10px;
      border-radius: 6px;
      font-weight: 700;
      font-size: 0.85rem;
    }

    .demo-tag {
      background: #FEF3C7;
      color: #B45309;
      border: 1px solid #FDE68A;
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 600;
    }

    .privacy-note {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.82rem;
      color: #475569;
      max-width: 600px;
    }

    .shield-icon {
      color: #059669;
      font-size: 20px;
      width: 20px;
      height: 20px;
    }

    /* Table */
    .table-card {
      border-radius: 12px;
      border: 1px solid #E2E8F0;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
      background: #ffffff;
      padding: 16px;
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
      padding: 12px 14px;
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

    .role-chip {
      font-size: 0.72rem;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 4px;
    }

    .role-chip.admin { background: #FEF3C7; color: #B45309; }
    .role-chip.mentor { background: #EFF6FF; color: var(--csm-primary); }
    .role-chip.ase { background: #ECFDF5; color: #065F46; }

    .text-right { text-align: right; }
    .text-center { text-align: center; }
    .text-muted { color: #94A3B8; }
    .font-bold { font-weight: 700; }
  `]
})
export class AdminLLMUsageComponent implements OnInit {
  usageData: AdminLLMUsageSummary | null = null;
  loading = true;

  constructor(private chatService: ChatService) {}

  ngOnInit(): void {
    this.loadUsageData();
  }

  loadUsageData(): void {
    this.loading = true;
    this.chatService.getAdminLLMUsage().subscribe({
      next: (data) => {
        this.usageData = data;
        this.loading = false;
      },
      error: (err) => {
        console.error('Failed to load LLM usage telemetry', err);
        this.loading = false;
      }
    });
  }
}
