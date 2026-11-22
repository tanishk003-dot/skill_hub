import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { Phase11Service } from '../../../core/services/phase11.service';
import { AuthService } from '../../../core/services/auth.service';
import {
  OneOnOneMeeting,
  OneOnOneGoal,
  OneOnOneActionItem,
  OneOnOneComment
} from '../../../core/models/phase11.model';

@Component({
  selector: 'app-one-on-one',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="min-h-screen bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100 p-6">
      <div class="max-w-7xl mx-auto space-y-6">

        <!-- Header -->
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
          <div>
            <div class="flex items-center space-x-3">
              <span class="p-2.5 rounded-xl bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300">
                <svg width="24" height="24" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>
                </svg>
              </span>
              <h1 class="text-2xl font-bold">1-on-1 Mentoring, Notes & Action Goals</h1>
            </div>
            <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Structured bilateral notes, target goals, action checklists, and privacy-isolated encrypted records.
            </p>
          </div>

          <div class="flex items-center space-x-3">
            <button *ngIf="isMentor" (click)="openCreateMeetingModal()"
              class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition shadow-sm flex items-center space-x-1.5">
              <svg width="16" height="16" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
              <span>Schedule 1-on-1 Meeting</span>
            </button>
            <button *ngIf="isMentor" (click)="openCreateGoalModal()"
              class="px-4 py-2 bg-slate-200 hover:bg-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 rounded-lg text-sm font-medium transition flex items-center space-x-1.5">
              <span>Add Goal</span>
            </button>
          </div>
        </div>

        <!-- Privacy & Encryption Architecture Callout -->
        <div class="bg-blue-50/70 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800/60 rounded-2xl p-4 text-xs text-blue-900 dark:text-blue-200 flex items-start space-x-3">
          <svg width="20" height="20" class="w-5 h-5 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>
          <div>
            <p class="font-semibold text-blue-950 dark:text-blue-100">End-to-End Private Note Protection</p>
            <p class="mt-0.5 text-blue-800/90 dark:text-blue-300/80">
              Notes marked "Private to mentor" are encrypted at rest with AES/Fernet. They are never sent to ASEs, administrators, chat context, readiness formulas, or general exports.
            </p>
          </div>
        </div>

        <!-- Tabs -->
        <div class="flex items-center space-x-2 border-b border-slate-200 dark:border-slate-800">
          <button (click)="activeTab = 'MEETINGS'"
            [ngClass]="activeTab === 'MEETINGS' ? 'border-b-2 border-blue-600 text-blue-600 dark:text-blue-400 font-bold' : 'text-slate-500 hover:text-slate-700'"
            class="px-4 py-2.5 text-sm transition">
            Meetings & Note Threads ({{ meetings.length }})
          </button>
          <button (click)="activeTab = 'GOALS'"
            [ngClass]="activeTab === 'GOALS' ? 'border-b-2 border-blue-600 text-blue-600 dark:text-blue-400 font-bold' : 'text-slate-500 hover:text-slate-700'"
            class="px-4 py-2.5 text-sm transition">
            Goals & Milestones ({{ goals.length }})
          </button>
          <button (click)="activeTab = 'ACTIONS'"
            [ngClass]="activeTab === 'ACTIONS' ? 'border-b-2 border-blue-600 text-blue-600 dark:text-blue-400 font-bold' : 'text-slate-500 hover:text-slate-700'"
            class="px-4 py-2.5 text-sm transition">
            Action Items & Checklists ({{ actionItems.length }})
          </button>
        </div>

        <!-- TAB 1: MEETINGS -->
        <div *ngIf="activeTab === 'MEETINGS'" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div *ngFor="let m of meetings" class="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-5 space-y-4 hover:shadow-md transition flex flex-col justify-between">
            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <span class="text-xs px-2.5 py-0.5 rounded-full font-semibold"
                  [ngClass]="m.status === 'COMPLETED' ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300' : 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300'">
                  {{ m.status }}
                </span>
                <span class="text-xs text-slate-400">{{ formatDate(m.meeting_date) }}</span>
              </div>
              <h3 class="font-bold text-base text-slate-900 dark:text-slate-100">{{ m.title }}</h3>

              <!-- Shared notes snippet -->
              <div class="p-3 bg-slate-50 dark:bg-slate-900/50 rounded-xl border border-slate-100 dark:border-slate-800 text-xs text-slate-600 dark:text-slate-300">
                <span class="font-semibold block text-slate-500 mb-1">Shared Notes:</span>
                <p class="line-clamp-3">{{ m.shared_notes || 'No shared notes recorded yet.' }}</p>
              </div>

              <!-- Private notes indicator (mentor only) -->
              <div *ngIf="isMentor && m.private_notes" class="p-2.5 bg-amber-50 dark:bg-amber-950/30 rounded-xl border border-amber-200 dark:border-amber-900 text-xs text-amber-800 dark:text-amber-300 flex items-center space-x-2">
                <svg width="16" height="16" class="w-4 h-4 shrink-0 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>
                <span class="truncate">Private Notes Encrypted (Mentor only)</span>
              </div>

              <!-- AI Summary if present -->
              <div *ngIf="m.ai_summary_shared" class="p-2.5 bg-indigo-50 dark:bg-indigo-950/40 rounded-xl border border-indigo-200 dark:border-indigo-800 text-xs text-indigo-900 dark:text-indigo-200">
                <span class="font-bold block text-[10px] text-indigo-600 uppercase tracking-wider mb-1">AI-Generated Summary, Please Verify</span>
                <p class="whitespace-pre-line text-[11px]">{{ m.ai_summary_shared }}</p>
              </div>
            </div>

            <div class="pt-3 border-t border-slate-100 dark:border-slate-700/60 flex items-center justify-between">
              <button (click)="viewMeetingDetail(m)" class="text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline">
                View & Edit Details →
              </button>
              <button *ngIf="isMentor && !m.ai_summary_shared" (click)="triggerAISummary(m, 'shared')" [disabled]="summarizingId === m.id"
                class="px-2.5 py-1 text-xs bg-indigo-50 hover:bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300 rounded font-medium transition">
                {{ summarizingId === m.id ? 'Summarizing...' : 'AI Summary' }}
              </button>
            </div>
          </div>

          <div *ngIf="meetings.length === 0" class="col-span-full py-12 text-center text-slate-400">
            No 1-on-1 meetings recorded yet.
          </div>
        </div>

        <!-- TAB 2: GOALS -->
        <div *ngIf="activeTab === 'GOALS'" class="space-y-4">
          <div *ngFor="let g of goals" class="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div class="space-y-1">
              <div class="flex items-center space-x-3">
                <span class="text-xs font-bold px-2.5 py-0.5 rounded-full"
                  [ngClass]="{
                    'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300': g.status === 'ACHIEVED',
                    'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300': g.status === 'IN_PROGRESS',
                    'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300': g.status === 'NOT_STARTED',
                    'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300': g.status === 'ABANDONED'
                  }">
                  {{ g.status }}
                </span>
                <span class="text-xs text-slate-400">Target: {{ formatDate(g.target_date) }}</span>
              </div>
              <h3 class="font-bold text-base text-slate-900 dark:text-slate-100">{{ g.title }}</h3>
              <p *ngIf="g.description" class="text-xs text-slate-500 dark:text-slate-400">{{ g.description }}</p>
            </div>

            <!-- Status Changer -->
            <div class="flex items-center space-x-2">
              <select [ngModel]="g.status" (ngModelChange)="changeGoalStatus(g, $event)"
                class="text-xs font-medium px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200">
                <option value="NOT_STARTED">Not Started</option>
                <option value="IN_PROGRESS">In Progress</option>
                <option value="ACHIEVED">Achieved</option>
                <option value="ABANDONED">Abandoned</option>
              </select>
            </div>
          </div>

          <div *ngIf="goals.length === 0" class="py-12 text-center text-slate-400">
            No active development goals defined yet.
          </div>
        </div>

        <!-- TAB 3: ACTION ITEMS -->
        <div *ngIf="activeTab === 'ACTIONS'" class="space-y-3">
          <div *ngFor="let a of actionItems" class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-4 flex items-center justify-between">
            <div class="flex items-center space-x-3">
              <input type="checkbox" [checked]="a.is_completed" (change)="toggleAction(a)"
                class="w-4 h-4 text-blue-600 rounded border-slate-300 focus:ring-blue-500 cursor-pointer">
              <div>
                <p class="text-sm font-medium" [ngClass]="{'line-through text-slate-400': a.is_completed}">
                  {{ a.task }}
                </p>
                <span class="text-xs text-slate-400">Assigned to {{ a.assigned_to }}</span>
              </div>
            </div>

            <span *ngIf="a.is_completed" class="text-xs text-emerald-600 dark:text-emerald-400 font-medium">
              ✓ Completed
            </span>
          </div>

          <div *ngIf="actionItems.length === 0" class="py-12 text-center text-slate-400">
            No action items pending.
          </div>
        </div>

        <!-- Meeting Modal -->
        <div *ngIf="selectedMeeting" class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div class="bg-white dark:bg-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-xl border border-slate-200 dark:border-slate-700 max-h-[90vh] overflow-y-auto">
            <div class="flex items-center justify-between">
              <h2 class="text-xl font-bold">{{ selectedMeeting.title }}</h2>
              <button (click)="selectedMeeting = null" class="text-slate-400 hover:text-slate-600 text-lg">✕</button>
            </div>

            <div class="space-y-4 text-sm">
              <div>
                <label class="block text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1">Shared Notes (Visible to Mentor & ASE):</label>
                <textarea *ngIf="isMentor" [(ngModel)]="selectedMeeting.shared_notes" rows="4" class="w-full text-xs p-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900"></textarea>
                <div *ngIf="!isMentor" class="p-3 bg-slate-50 dark:bg-slate-900 rounded-xl text-xs whitespace-pre-line">{{ selectedMeeting.shared_notes || 'No shared notes recorded.' }}</div>
              </div>

              <div *ngIf="isMentor">
                <label class="block text-xs font-semibold text-amber-700 dark:text-amber-300 mb-1 flex items-center space-x-1">
                  <svg width="16" height="16" class="w-4 h-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>
                  <span>Encrypted Private Notes (Mentor Only - AES Encrypted at Rest):</span>
                </label>
                <textarea [(ngModel)]="selectedMeeting.private_notes" rows="4" class="w-full text-xs p-3 rounded-xl border border-amber-200 dark:border-amber-900 bg-amber-50/50 dark:bg-amber-950/20 text-slate-800 dark:text-slate-200" placeholder="Confidential observations, potential risks, and development notes..."></textarea>
              </div>

              <!-- AI Summary box -->
              <div *ngIf="selectedMeeting.ai_summary_shared" class="p-4 bg-indigo-50 dark:bg-indigo-950/40 rounded-xl border border-indigo-200 dark:border-indigo-800 text-xs text-indigo-900 dark:text-indigo-200">
                <span class="font-bold text-xs text-indigo-600 uppercase tracking-wider block mb-1">AI-Generated Summary, Please Verify</span>
                <p class="whitespace-pre-line">{{ selectedMeeting.ai_summary_shared }}</p>
              </div>
            </div>

            <div class="flex items-center justify-end space-x-3 pt-4 border-t border-slate-100 dark:border-slate-700">
              <button (click)="selectedMeeting = null" class="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg">Close</button>
              <button *ngIf="isMentor" (click)="saveMeeting()" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg">Save Changes</button>
            </div>
          </div>
        </div>

        <!-- Create Meeting Modal -->
        <div *ngIf="showCreateMeetingModal" class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div class="bg-white dark:bg-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-xl border border-slate-200 dark:border-slate-700">
            <h2 class="text-xl font-bold">Schedule 1-on-1 Meeting</h2>
            <div class="space-y-3 text-sm">
              <div>
                <label class="block text-xs font-semibold mb-1">Mentee ID / User:</label>
                <input type="number" [(ngModel)]="newMeeting.mentee_id" class="w-full text-xs p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-900" placeholder="e.g. 3">
              </div>
              <div>
                <label class="block text-xs font-semibold mb-1">Title:</label>
                <input type="text" [(ngModel)]="newMeeting.title" class="w-full text-xs p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-900" placeholder="e.g. Bi-weekly Sprint 4 Review">
              </div>
              <div>
                <label class="block text-xs font-semibold mb-1">Meeting Date & Time:</label>
                <input type="datetime-local" [(ngModel)]="newMeeting.meeting_date" class="w-full text-xs p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-900">
              </div>
              <div>
                <label class="block text-xs font-semibold mb-1">Shared Notes:</label>
                <textarea [(ngModel)]="newMeeting.shared_notes" rows="3" class="w-full text-xs p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-900" placeholder="Topics to cover, goals, homework..."></textarea>
              </div>
              <div>
                <label class="block text-xs font-semibold text-amber-700 dark:text-amber-300 mb-1">Private Notes (Encrypted at rest):</label>
                <textarea [(ngModel)]="newMeeting.private_notes" rows="2" class="w-full text-xs p-2.5 rounded-lg border border-amber-200 dark:border-amber-900 bg-amber-50/50 dark:bg-amber-950/20" placeholder="Mentor private observations..."></textarea>
              </div>
            </div>
            <div class="flex items-center justify-end space-x-2 pt-2">
              <button (click)="showCreateMeetingModal = false" class="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg">Cancel</button>
              <button (click)="submitCreateMeeting()" [disabled]="!newMeeting.title" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg">Create Meeting</button>
            </div>
          </div>
        </div>

      </div>
    </div>
  `
})
export class OneOnOneComponent implements OnInit {
  activeTab: 'MEETINGS' | 'GOALS' | 'ACTIONS' = 'MEETINGS';
  meetings: OneOnOneMeeting[] = [];
  goals: OneOnOneGoal[] = [];
  actionItems: OneOnOneActionItem[] = [];

  selectedMeeting: OneOnOneMeeting | null = null;
  summarizingId: number | null = null;

  showCreateMeetingModal = false;
  newMeeting = {
    mentee_id: 3,
    title: '',
    meeting_date: new Date().toISOString().slice(0, 16),
    shared_notes: '',
    private_notes: ''
  };

  showCreateGoalModal = false;

  constructor(
    private phase11Service: Phase11Service,
    private authService: AuthService
  ) {}

  get isMentor(): boolean {
    const user = this.authService.currentUser();
    return user?.role === 'MENTOR';
  }

  ngOnInit(): void {
    this.loadAll();
  }

  loadAll(): void {
    this.phase11Service.getMeetings().subscribe(data => (this.meetings = data));
    this.phase11Service.getGoals().subscribe(data => (this.goals = data));
    this.phase11Service.getActionItems().subscribe(data => (this.actionItems = data));
  }

  formatDate(dateStr: string): string {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  viewMeetingDetail(m: OneOnOneMeeting): void {
    this.phase11Service.getMeeting(m.id).subscribe(detail => {
      this.selectedMeeting = detail;
    });
  }

  saveMeeting(): void {
    if (!this.selectedMeeting) return;
    this.phase11Service.updateMeeting(this.selectedMeeting.id, {
      title: this.selectedMeeting.title,
      shared_notes: this.selectedMeeting.shared_notes,
      private_notes: this.selectedMeeting.private_notes
    }).subscribe(updated => {
      const idx = this.meetings.findIndex(m => m.id === updated.id);
      if (idx >= 0) this.meetings[idx] = updated;
      this.selectedMeeting = null;
    });
  }

  triggerAISummary(m: OneOnOneMeeting, target: 'shared' | 'private'): void {
    this.summarizingId = m.id;
    this.phase11Service.summarizeMeeting(m.id, target).subscribe({
      next: (res) => {
        m.ai_summary_shared = res.summary;
        this.summarizingId = null;
      },
      error: () => {
        this.summarizingId = null;
      }
    });
  }

  changeGoalStatus(g: OneOnOneGoal, newStatus: string): void {
    this.phase11Service.updateGoalStatus(g.id, newStatus).subscribe(updated => {
      g.status = updated.status;
    });
  }

  toggleAction(a: OneOnOneActionItem): void {
    const nextState = !a.is_completed;
    this.phase11Service.toggleActionItem(a.id, nextState).subscribe(updated => {
      a.is_completed = updated.is_completed;
    });
  }

  openCreateMeetingModal(): void {
    this.showCreateMeetingModal = true;
  }

  submitCreateMeeting(): void {
    this.phase11Service.createMeeting(this.newMeeting).subscribe(created => {
      this.meetings.unshift(created);
      this.showCreateMeetingModal = false;
      this.newMeeting.title = '';
      this.newMeeting.shared_notes = '';
      this.newMeeting.private_notes = '';
    });
  }

  openCreateGoalModal(): void {
    // simplified goal prompt
    const title = prompt('Enter Goal Title:');
    if (title) {
      this.phase11Service.createGoal({
        mentee_id: 3,
        title,
        target_date: new Date(Date.now() + 14 * 86400000).toISOString()
      }).subscribe(g => this.goals.unshift(g));
    }
  }
}
