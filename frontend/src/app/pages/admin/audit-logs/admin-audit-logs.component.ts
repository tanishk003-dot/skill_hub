import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

export interface AuditLogItem {
  id: number;
  actor_id: number | null;
  actor_email: string;
  action: string;
  target_type: string;
  target_id: string | null;
  details: string | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

@Component({
  selector: 'app-admin-audit-logs',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatInputModule,
    MatFormFieldModule,
    MatProgressSpinnerModule
  ],
  template: `
    <div class="audit-container">
      <div class="page-header">
        <div>
          <h1>Administrator Governance &amp; Audit Trail</h1>
          <p class="subtitle">
            Append-only security audit log recording administrative actions, governance events, and authentication state transitions.
          </p>
        </div>
        <div class="header-actions">
          <button mat-stroked-button (click)="loadLogs()" [disabled]="isLoading()">
            <mat-icon>refresh</mat-icon> Refresh
          </button>
        </div>
      </div>

      <!-- Filter Controls -->
      <mat-card class="filter-card">
        <div class="filter-row">
          <mat-form-field appearance="outline" class="search-field">
            <mat-label>Search Actor, Action, or Target</mat-label>
            <input matInput [(ngModel)]="searchTerm" (keyup.enter)="loadLogs()" placeholder="e.g. admin@skillhub.com" />
            <button mat-icon-button matSuffix (click)="loadLogs()">
              <mat-icon>search</mat-icon>
            </button>
          </mat-form-field>

          <div class="action-chips">
            <button mat-stroked-button [class.active-chip]="!selectedAction" (click)="filterByAction(null)">All</button>
            <button mat-stroked-button [class.active-chip]="selectedAction === 'USER_CREATE'" (click)="filterByAction('USER_CREATE')">Create User</button>
            <button mat-stroked-button [class.active-chip]="selectedAction === 'USER_UPDATE'" (click)="filterByAction('USER_UPDATE')">Update User</button>
            <button mat-stroked-button [class.active-chip]="selectedAction === 'USER_DELETE'" (click)="filterByAction('USER_DELETE')">Delete User</button>
            <button mat-stroked-button [class.active-chip]="selectedAction === 'USER_UNLOCK'" (click)="filterByAction('USER_UNLOCK')">Unlock User</button>
          </div>
        </div>
      </mat-card>

      <!-- Logs Table -->
      <mat-card class="table-card">
        @if (isLoading()) {
          <div class="loading-state">
            <mat-spinner diameter="40"></mat-spinner>
            <span>Loading governance audit trail...</span>
          </div>
        } @else if (logs().length === 0) {
          <div class="empty-state">
            <mat-icon class="empty-icon">verified_user</mat-icon>
            <h3>No Audit Logs Found</h3>
            <p>No administrative governance records match the selected filters.</p>
          </div>
        } @else {
          <div class="table-responsive">
            <table mat-table [dataSource]="logs()" class="audit-table">
              <!-- Timestamp Column -->
              <ng-container matColumnDef="timestamp">
                <th mat-header-cell *matHeaderCellDef>Timestamp (UTC)</th>
                <td mat-cell *matCellDef="let row" class="time-cell">
                  {{ row.created_at | date:'yyyy-MM-dd HH:mm:ss' }}
                </td>
              </ng-container>

              <!-- Actor Column -->
              <ng-container matColumnDef="actor">
                <th mat-header-cell *matHeaderCellDef>Administrator</th>
                <td mat-cell *matCellDef="let row">
                  <strong>{{ row.actor_email }}</strong>
                </td>
              </ng-container>

              <!-- Action Column -->
              <ng-container matColumnDef="action">
                <th mat-header-cell *matHeaderCellDef>Action</th>
                <td mat-cell *matCellDef="let row">
                  <span class="action-badge" [ngClass]="getActionClass(row.action)">
                    {{ row.action }}
                  </span>
                </td>
              </ng-container>

              <!-- Target Column -->
              <ng-container matColumnDef="target">
                <th mat-header-cell *matHeaderCellDef>Target</th>
                <td mat-cell *matCellDef="let row">
                  <span class="target-type">{{ row.target_type }}</span>
                  <span *ngIf="row.target_id" class="target-id">#{{ row.target_id }}</span>
                </td>
              </ng-container>

              <!-- Details Column -->
              <ng-container matColumnDef="details">
                <th mat-header-cell *matHeaderCellDef>Event Details</th>
                <td mat-cell *matCellDef="let row" class="details-cell">
                  {{ row.details || '—' }}
                </td>
              </ng-container>

              <!-- IP Column -->
              <ng-container matColumnDef="ip">
                <th mat-header-cell *matHeaderCellDef>IP Address</th>
                <td mat-cell *matCellDef="let row" class="ip-cell">
                  <code>{{ row.ip_address || '127.0.0.1' }}</code>
                </td>
              </ng-container>

              <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
              <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
            </table>
          </div>
        }
      </mat-card>
    </div>
  `,
  styles: [`
    .audit-container {
      padding: 24px;
      max-width: 1300px;
      margin: 0 auto;
    }

    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 24px;

      h1 {
        font-size: 1.6rem;
        font-weight: 700;
        color: var(--text-primary);
        margin: 0 0 4px;
      }

      .subtitle {
        color: var(--text-secondary);
        font-size: 0.875rem;
        margin: 0;
      }
    }

    .filter-card {
      margin-bottom: 20px;
      padding: 16px 20px;
      border-radius: 12px;
      border: 1px solid var(--border-light);
      background: var(--bg-card);
    }

    .filter-row {
      display: flex;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;

      .search-field {
        flex: 1;
        min-width: 280px;
        margin-bottom: -1.25em;
      }

      .action-chips {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;

        button {
          border-radius: 20px;
          font-size: 0.8rem;
          height: 36px;
          border-color: var(--border-light);

          &.active-chip {
            background-color: var(--csm-primary);
            color: #ffffff;
            border-color: var(--csm-primary);
          }
        }
      }
    }

    .table-card {
      border-radius: 12px;
      border: 1px solid var(--border-light);
      background: var(--bg-card);
      overflow: hidden;
      padding: 0;
    }

    .table-responsive {
      overflow-x: auto;
    }

    .audit-table {
      width: 100%;

      th {
        font-weight: 600;
        color: var(--text-secondary);
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        background: var(--bg-main);
      }

      td {
        font-size: 0.875rem;
        color: var(--text-primary);
        padding: 14px 16px;
      }

      .time-cell {
        font-family: monospace;
        font-size: 0.8rem;
        color: var(--text-muted);
        white-space: nowrap;
      }

      .action-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;

        &.badge-create { background: #dcfce7; color: #166534; }
        &.badge-update { background: #dbeafe; color: #1e40af; }
        &.badge-delete { background: #fee2e2; color: #991b1b; }
        &.badge-unlock { background: #fef3c7; color: #92400e; }
        &.badge-default { background: #f1f5f9; color: #475569; }
      }

      .target-type {
        font-weight: 600;
        margin-right: 4px;
      }

      .target-id {
        color: var(--text-muted);
        font-size: 0.8rem;
      }

      .details-cell {
        max-width: 380px;
      }

      .ip-cell code {
        background: var(--bg-main);
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.8rem;
      }
    }

    .loading-state, .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 60px 24px;
      text-align: center;
      color: var(--text-muted);
      gap: 12px;

      .empty-icon {
        font-size: 48px;
        width: 48px;
        height: 48px;
        color: var(--csm-accent);
      }

      h3 {
        margin: 0;
        color: var(--text-primary);
        font-size: 1.15rem;
      }

      p {
        margin: 0;
        font-size: 0.875rem;
      }
    }
  `]
})
export class AdminAuditLogsComponent implements OnInit {
  private readonly apiUrl = 'http://localhost:8001/api/v1';
  displayedColumns = ['timestamp', 'actor', 'action', 'target', 'details', 'ip'];
  logs = signal<AuditLogItem[]>([]);
  isLoading = signal(false);
  searchTerm = '';
  selectedAction: string | null = null;

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.loadLogs();
  }

  filterByAction(action: string | null): void {
    this.selectedAction = action;
    this.loadLogs();
  }

  loadLogs(): void {
    this.isLoading.set(true);
    let params: any = { page: 1, page_size: 100 };
    if (this.selectedAction) params.action = this.selectedAction;
    if (this.searchTerm && this.searchTerm.trim()) params.search = this.searchTerm.trim();

    this.http.get<any>(`${this.apiUrl}/admin/audit-logs`, { params }).subscribe({
      next: (res) => {
        this.logs.set(res.items || []);
        this.isLoading.set(false);
      },
      error: () => {
        this.logs.set([]);
        this.isLoading.set(false);
      }
    });
  }

  getActionClass(action: string): string {
    switch (action) {
      case 'USER_CREATE': return 'badge-create';
      case 'USER_UPDATE': return 'badge-update';
      case 'USER_DELETE': return 'badge-delete';
      case 'USER_UNLOCK': return 'badge-unlock';
      default: return 'badge-default';
    }
  }
}
