import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { Phase11Service } from '../../../core/services/phase11.service';
import { ReportingApiToken, ReportingTokenCreatedResponse } from '../../../core/models/phase11.model';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-exports',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="min-h-screen bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100 p-6">
      <div class="max-w-7xl mx-auto space-y-6">

        <!-- Header -->
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
          <div>
            <div class="flex items-center space-x-3">
              <span class="p-2.5 rounded-xl bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300">
                <svg width="24" height="24" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
              </span>
              <h1 class="text-2xl font-bold">Data Export & Power BI Reporting</h1>
            </div>
            <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Export system entities to Excel (.xlsx) and CSV with formula injection sanitization, or generate scoped Power BI API tokens.
            </p>
          </div>

          <div class="flex items-center space-x-3">
            <button *ngIf="isAdmin" (click)="openCreateTokenModal()"
              class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-medium transition shadow-sm flex items-center space-x-1.5">
              <svg width="16" height="16" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"/></svg>
              <span>Generate Power BI Token</span>
            </button>
          </div>
        </div>

        <!-- Security & Injection Protection Notice -->
        <div class="bg-emerald-50/70 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/60 rounded-2xl p-4 text-xs text-emerald-900 dark:text-emerald-200 flex items-start space-x-3">
          <svg width="20" height="20" class="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/></svg>
          <div>
            <p class="font-semibold text-emerald-950 dark:text-emerald-100">Enterprise Export Protection & Privacy Policy</p>
            <p class="mt-0.5 text-emerald-800/90 dark:text-emerald-300/80">
              All exported files sanitize formula injection vectors (=, +, -, @) to neutralize malicious spreadsheet execution. Pseudonymous candidate IDs (e.g. ASE-B74F) are applied by default; names/emails are included only when explicitly toggled. Confidential medical accommodations, private 1-on-1 notes, and webcam footage are NEVER exported.
            </p>
          </div>
        </div>

        <!-- Tabs -->
        <div class="flex items-center space-x-2 border-b border-slate-200 dark:border-slate-800">
          <button (click)="activeTab = 'DIRECT'"
            [ngClass]="activeTab === 'DIRECT' ? 'border-b-2 border-emerald-600 text-emerald-600 dark:text-emerald-400 font-bold' : 'text-slate-500 hover:text-slate-700'"
            class="px-4 py-2.5 text-sm transition">
            Direct Spreadsheet Exports (Excel / CSV)
          </button>
          <button *ngIf="isAdmin" (click)="activeTab = 'TOKENS'"
            [ngClass]="activeTab === 'TOKENS' ? 'border-b-2 border-emerald-600 text-emerald-600 dark:text-emerald-400 font-bold' : 'text-slate-500 hover:text-slate-700'"
            class="px-4 py-2.5 text-sm transition">
            Power BI API Tokens & Connectors ({{ tokens.length }})
          </button>
        </div>

        <!-- TAB 1: DIRECT EXPORTS -->
        <div *ngIf="activeTab === 'DIRECT'" class="space-y-6">
          <!-- Admin PII Opt-in checkbox -->
          <div *ngIf="isAdmin" class="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 flex items-center justify-between">
            <div>
              <p class="text-sm font-semibold">Include Personally Identifiable Information (PII)</p>
              <p class="text-xs text-slate-400">Includes candidate real names and email addresses. When unchecked, pseudonymous IDs (e.g. ASE-A1B2) are exported.</p>
            </div>
            <label class="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" [(ngModel)]="includePii" class="sr-only peer">
              <div class="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600"></div>
            </label>
          </div>

          <!-- Entity Export Cards Grid -->
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <!-- Assessments -->
            <div class="bg-white dark:bg-slate-800 rounded-2xl p-5 border border-slate-200 dark:border-slate-700 shadow-sm space-y-4">
              <div class="flex items-center space-x-3">
                <span class="p-2 rounded-lg bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300">
                  <svg width="20" height="20" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/></svg>
                </span>
                <div>
                  <h3 class="font-bold text-sm">Assessments Metadata</h3>
                  <p class="text-xs text-slate-400">Titles, durations, passing %, webcam modes</p>
                </div>
              </div>
              <div class="flex items-center space-x-2 pt-2">
                <button (click)="download('assessments', 'xlsx')" class="flex-1 px-3 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold transition">
                  Export Excel (.xlsx)
                </button>
                <button (click)="download('assessments', 'csv')" class="px-3 py-2 border border-slate-300 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg text-xs font-semibold transition">
                  CSV
                </button>
              </div>
            </div>

            <!-- Results -->
            <div class="bg-white dark:bg-slate-800 rounded-2xl p-5 border border-slate-200 dark:border-slate-700 shadow-sm space-y-4">
              <div class="flex items-center space-x-3">
                <span class="p-2 rounded-lg bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300">
                  <svg width="20" height="20" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>
                </span>
                <div>
                  <h3 class="font-bold text-sm">Assessment Results & Attempts</h3>
                  <p class="text-xs text-slate-400">Scores, percentages, pass/fail status</p>
                </div>
              </div>
              <div class="flex items-center space-x-2 pt-2">
                <button (click)="download('results', 'xlsx')" class="flex-1 px-3 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold transition">
                  Export Excel (.xlsx)
                </button>
                <button (click)="download('results', 'csv')" class="px-3 py-2 border border-slate-300 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg text-xs font-semibold transition">
                  CSV
                </button>
              </div>
            </div>

            <!-- Cohorts -->
            <div class="bg-white dark:bg-slate-800 rounded-2xl p-5 border border-slate-200 dark:border-slate-700 shadow-sm space-y-4">
              <div class="flex items-center space-x-3">
                <span class="p-2 rounded-lg bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300">
                  <svg width="20" height="20" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/></svg>
                </span>
                <div>
                  <h3 class="font-bold text-sm">Cohorts & Memberships</h3>
                  <p class="text-xs text-slate-400">Cohort assignments and join dates</p>
                </div>
              </div>
              <div class="flex items-center space-x-2 pt-2">
                <button (click)="download('cohorts', 'xlsx')" class="flex-1 px-3 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold transition">
                  Export Excel (.xlsx)
                </button>
                <button (click)="download('cohorts', 'csv')" class="px-3 py-2 border border-slate-300 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg text-xs font-semibold transition">
                  CSV
                </button>
              </div>
            </div>

            <!-- Trainings -->
            <div class="bg-white dark:bg-slate-800 rounded-2xl p-5 border border-slate-200 dark:border-slate-700 shadow-sm space-y-4">
              <div class="flex items-center space-x-3">
                <span class="p-2 rounded-lg bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300">
                  <svg width="20" height="20" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/></svg>
                </span>
                <div>
                  <h3 class="font-bold text-sm">Trainings & Progress</h3>
                  <p class="text-xs text-slate-400">Course completion percentages, statuses</p>
                </div>
              </div>
              <div class="flex items-center space-x-2 pt-2">
                <button (click)="download('trainings', 'xlsx')" class="flex-1 px-3 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold transition">
                  Export Excel (.xlsx)
                </button>
                <button (click)="download('trainings', 'csv')" class="px-3 py-2 border border-slate-300 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg text-xs font-semibold transition">
                  CSV
                </button>
              </div>
            </div>

            <!-- Attendance -->
            <div class="bg-white dark:bg-slate-800 rounded-2xl p-5 border border-slate-200 dark:border-slate-700 shadow-sm space-y-4">
              <div class="flex items-center space-x-3">
                <span class="p-2 rounded-lg bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300">
                  <svg width="20" height="20" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
                </span>
                <div>
                  <h3 class="font-bold text-sm">Class Attendance</h3>
                  <p class="text-xs text-slate-400">Live lecture attendance confirmations</p>
                </div>
              </div>
              <div class="flex items-center space-x-2 pt-2">
                <button (click)="download('attendance', 'xlsx')" class="flex-1 px-3 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold transition">
                  Export Excel (.xlsx)
                </button>
                <button (click)="download('attendance', 'csv')" class="px-3 py-2 border border-slate-300 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg text-xs font-semibold transition">
                  CSV
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- TAB 2: POWER BI TOKENS -->
        <div *ngIf="activeTab === 'TOKENS'" class="space-y-6">
          <div class="bg-white dark:bg-slate-800 rounded-2xl p-5 border border-slate-200 dark:border-slate-700 shadow-sm">
            <h3 class="font-bold text-sm mb-3">Active Power BI API Tokens</h3>
            <div class="overflow-x-auto">
              <table class="w-full text-left text-xs">
                <thead class="bg-slate-50 dark:bg-slate-900/60 text-slate-400 uppercase font-semibold border-b border-slate-200 dark:border-slate-700">
                  <tr>
                    <th class="py-3 px-4">Token Name</th>
                    <th class="py-3 px-4">Scopes</th>
                    <th class="py-3 px-4">PII Allowed</th>
                    <th class="py-3 px-4">Expires</th>
                    <th class="py-3 px-4">Status</th>
                    <th class="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 dark:divide-slate-800">
                  <tr *ngFor="let t of tokens">
                    <td class="py-3 px-4 font-bold">{{ t.name }}</td>
                    <td class="py-3 px-4">
                      <span *ngFor="let s of t.scopes" class="inline-block mr-1 px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700 font-mono text-[10px]">
                        {{ s }}
                      </span>
                    </td>
                    <td class="py-3 px-4 font-semibold" [ngClass]="t.include_pii ? 'text-amber-500' : 'text-slate-400'">
                      {{ t.include_pii ? 'YES (Names/Emails)' : 'NO (Pseudonymous)' }}
                    </td>
                    <td class="py-3 px-4 text-slate-400">{{ formatDate(t.expires_at) }}</td>
                    <td class="py-3 px-4">
                      <span class="px-2 py-0.5 rounded-full font-bold text-[10px]"
                        [ngClass]="t.is_revoked ? 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300' : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'">
                        {{ t.is_revoked ? 'REVOKED' : 'ACTIVE' }}
                      </span>
                    </td>
                    <td class="py-3 px-4 text-right">
                      <button *ngIf="!t.is_revoked" (click)="revokeToken(t.id)" class="text-red-600 hover:underline font-semibold">
                        Revoke
                      </button>
                    </td>
                  </tr>
                  <tr *ngIf="tokens.length === 0">
                    <td colspan="6" class="py-8 text-center text-slate-400">No reporting tokens created yet.</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Token Created Display Modal -->
        <div *ngIf="createdTokenInfo" class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div class="bg-white dark:bg-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-xl border border-slate-200 dark:border-slate-700">
            <h2 class="text-xl font-bold text-emerald-600">Reporting Token Generated!</h2>
            <p class="text-xs text-slate-500">Copy this token now. For security, it will NEVER be displayed again.</p>
            <div class="p-3 bg-slate-100 dark:bg-slate-900 rounded-xl font-mono text-xs break-all border border-slate-200 dark:border-slate-800">
              {{ createdTokenInfo.token }}
            </div>
            <div class="space-y-1 text-xs text-slate-500">
              <p><strong>Authorization Header:</strong> <code>Authorization: Bearer {{ createdTokenInfo.token }}</code></p>
              <p><strong>Power BI Web Connector URL:</strong> <code>http://127.0.0.1:8001/api/v1/reporting/results</code></p>
            </div>
            <div class="flex justify-end pt-2">
              <button (click)="createdTokenInfo = null" class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-semibold">I have copied the token</button>
            </div>
          </div>
        </div>

        <!-- Create Token Modal -->
        <div *ngIf="showCreateTokenModal" class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div class="bg-white dark:bg-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-xl border border-slate-200 dark:border-slate-700">
            <h2 class="text-lg font-bold">New Power BI Reporting Token</h2>
            <div class="space-y-3 text-sm">
              <div>
                <label class="block text-xs font-semibold mb-1">Token Label:</label>
                <input type="text" [(ngModel)]="newToken.name" class="w-full text-xs p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-900" placeholder="e.g. Executive Power BI Dashboard">
              </div>
              <div>
                <label class="block text-xs font-semibold mb-1">Expiration (Days):</label>
                <input type="number" [(ngModel)]="newToken.expires_in_days" class="w-full text-xs p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-900">
              </div>
              <div>
                <label class="flex items-center space-x-2 text-xs font-semibold cursor-pointer">
                  <input type="checkbox" [(ngModel)]="newToken.include_pii" class="rounded text-emerald-600">
                  <span>Include Candidate Names & Emails (PII)</span>
                </label>
              </div>
            </div>
            <div class="flex justify-end space-x-2 pt-2">
              <button (click)="showCreateTokenModal = false" class="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg">Cancel</button>
              <button (click)="submitCreateToken()" [disabled]="!newToken.name" class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-lg">Generate Token</button>
            </div>
          </div>
        </div>

      </div>
    </div>
  `
})
export class ExportsComponent implements OnInit {
  activeTab: 'DIRECT' | 'TOKENS' = 'DIRECT';
  includePii = false;
  tokens: ReportingApiToken[] = [];
  createdTokenInfo: ReportingTokenCreatedResponse | null = null;
  showCreateTokenModal = false;

  newToken = {
    name: '',
    scopes: ['assessments', 'results', 'cohorts', 'trainings', 'attendance', 'readiness'],
    include_pii: false,
    expires_in_days: 90
  };

  constructor(
    private phase11Service: Phase11Service,
    private authService: AuthService
  ) {}

  get isAdmin(): boolean {
    const u = this.authService.currentUser();
    return u?.role === 'ADMIN';
  }

  ngOnInit(): void {
    if (this.isAdmin) {
      this.loadTokens();
    }
  }

  loadTokens(): void {
    this.phase11Service.getReportingTokens().subscribe(data => (this.tokens = data));
  }

  formatDate(dStr: string): string {
    if (!dStr) return '';
    return new Date(dStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  download(entity: string, format: 'xlsx' | 'csv'): void {
    this.phase11Service.downloadExport(entity, format, this.includePii).subscribe(blob => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `skillhub_${entity}.${format}`;
      a.click();
      window.URL.revokeObjectURL(url);
    });
  }

  openCreateTokenModal(): void {
    this.showCreateTokenModal = true;
  }

  submitCreateToken(): void {
    this.phase11Service.createReportingToken(this.newToken).subscribe(res => {
      this.createdTokenInfo = res;
      this.showCreateTokenModal = false;
      this.loadTokens();
    });
  }

  revokeToken(id: number): void {
    if (!confirm('Are you sure you want to revoke this reporting token?')) return;
    this.phase11Service.revokeReportingToken(id).subscribe(() => this.loadTokens());
  }
}
