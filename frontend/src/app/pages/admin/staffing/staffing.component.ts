import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { Phase11Service } from '../../../core/services/phase11.service';
import { StaffingProject, StaffingProjectMatchesResponse, CandidateProjectMatch } from '../../../core/models/phase11.model';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-staffing',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="min-h-screen bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100 p-6">
      <div class="max-w-7xl mx-auto space-y-6">

        <!-- Header -->
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
          <div>
            <div class="flex items-center space-x-3">
              <span class="p-2.5 rounded-xl bg-violet-100 dark:bg-violet-900/50 text-violet-700 dark:text-violet-300">
                <svg width="24" height="24" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
                </svg>
              </span>
              <h1 class="text-2xl font-bold">Skill-to-Project Matching & Readiness</h1>
            </div>
            <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Match candidate competencies against project requirements, compute skill deficits, and view targeted training pathways.
            </p>
          </div>

          <div class="flex items-center space-x-3">
            <button *ngIf="isAdmin" (click)="openCreateProjectModal()"
              class="px-4 py-2 bg-violet-600 hover:bg-violet-700 text-white rounded-lg text-sm font-medium transition shadow-sm flex items-center space-x-1.5">
              <svg width="16" height="16" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
              <span>Define New Project</span>
            </button>
          </div>
        </div>

        <!-- Mandatory Decision Support Disclaimer -->
        <div class="bg-amber-50/80 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/60 rounded-2xl p-4 text-xs text-amber-900 dark:text-amber-200 flex items-start space-x-3">
          <svg width="20" height="20" class="w-5 h-5 text-amber-600 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
          <div>
            <p class="font-bold text-amber-950 dark:text-amber-100">Decision Support Disclaimer</p>
            <p class="mt-0.5">
              Decision support only. Not a basis for staffing, promotion or termination decisions. Matching percentages represent historical assessment benchmarks and training curriculum alignment.
            </p>
          </div>
        </div>

        <!-- Formula Explanation Card -->
        <div class="bg-violet-50/70 dark:bg-violet-950/30 border border-violet-200 dark:border-violet-800/60 rounded-2xl p-4 text-xs text-violet-900 dark:text-violet-200 flex items-center justify-between">
          <div class="space-y-1">
            <span class="font-bold block text-sm">Matching Formula:</span>
            <code class="text-xs bg-white/80 dark:bg-slate-900/60 px-2.5 py-1 rounded-md border border-violet-200 dark:border-violet-900 inline-block">
              Match % = ( Σ min(Candidate_Level, Min_Level) * Weight / Σ (Min_Level * Weight) ) * 100
            </code>
          </div>
          <div class="text-right text-[11px] text-slate-500 dark:text-slate-400">
            <span>Default Threshold: <strong>90% = Ready Now</strong></span><br>
            <span>Gap Recovery: <strong>20 hrs/week training estimate</strong></span>
          </div>
        </div>

        <!-- Projects Selector Bar -->
        <div class="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 flex flex-wrap items-center justify-between gap-4">
          <div class="flex items-center space-x-3 text-sm">
            <span class="font-semibold text-slate-600 dark:text-slate-300">Select Project:</span>
            <select [ngModel]="selectedProjectId" (ngModelChange)="onProjectSelected($event)"
              class="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-200 font-medium text-xs">
              <option *ngFor="let p of projects" [value]="p.id">{{ p.name }} (Headcount: {{ p.headcount }})</option>
            </select>
          </div>

          <div *ngIf="projectMatchData" class="text-xs text-slate-500 dark:text-slate-400">
            <span>Evaluated Candidates: <strong>{{ projectMatchData.total_evaluated }}</strong></span>
          </div>
        </div>

        <!-- Matches & Candidates List -->
        <div *ngIf="projectMatchData" class="space-y-4">
          <div *ngFor="let cand of projectMatchData.candidates"
            class="bg-white dark:bg-slate-800 rounded-2xl p-5 border border-slate-200 dark:border-slate-700 shadow-sm space-y-4">
            
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div class="space-y-1">
                <div class="flex items-center space-x-3">
                  <h3 class="font-bold text-base text-slate-900 dark:text-slate-100">{{ cand.name || cand.pseudonymous_id }}</h3>
                  <span class="text-xs px-2.5 py-0.5 rounded-full font-bold font-mono"
                    [ngClass]="cand.is_ready_now ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300' : 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300'">
                    {{ cand.readiness_label }}
                  </span>
                </div>
                <p class="text-xs text-slate-400 font-mono">{{ cand.pseudonymous_id }} <span *ngIf="cand.email">· {{ cand.email }}</span></p>
              </div>

              <!-- Match Percentage Progress -->
              <div class="text-right">
                <span class="text-2xl font-black font-mono"
                  [ngClass]="cand.match_percentage >= 90 ? 'text-emerald-600 dark:text-emerald-400' : 'text-blue-600 dark:text-blue-400'">
                  {{ cand.match_percentage }}%
                </span>
                <span class="text-xs text-slate-400 block">Match Score</span>
              </div>
            </div>

            <!-- Skill Gaps & Breakdown -->
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 pt-2">
              <div *ngFor="let s of cand.skill_breakdowns"
                class="p-3 rounded-xl border border-slate-100 dark:border-slate-700/60 bg-slate-50/70 dark:bg-slate-900/40 text-xs space-y-1.5">
                <div class="flex items-center justify-between">
                  <span class="font-bold text-slate-800 dark:text-slate-200">{{ s.skill_name }}</span>
                  <span *ngIf="s.gap_pct === 0" class="text-emerald-600 dark:text-emerald-400 font-bold text-[10px]">✓ MET</span>
                  <span *ngIf="s.gap_pct > 0" class="text-red-500 font-bold text-[10px]">-{{ s.gap_pct }}% GAP</span>
                </div>

                <div class="flex items-center justify-between text-[11px] text-slate-500">
                  <span>Candidate: <strong>{{ s.candidate_level_pct }}%</strong></span>
                  <span>Required: <strong>{{ s.required_level_pct }}%</strong></span>
                </div>

                <!-- Training Recommendation for Gap -->
                <div *ngIf="s.gap_pct > 0 && s.recommended_training" class="mt-1 pt-1.5 border-t border-slate-200 dark:border-slate-800 text-[10px] text-violet-700 dark:text-violet-300">
                  <span class="font-semibold block">Recommended Training:</span>
                  <span class="truncate block">📚 {{ s.recommended_training.title }}</span>
                </div>
              </div>
            </div>

          </div>

          <div *ngIf="projectMatchData.candidates.length === 0" class="py-12 text-center text-slate-400">
            No candidates available in the pool.
          </div>
        </div>

        <!-- Create Project Modal -->
        <div *ngIf="showCreateModal" class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div class="bg-white dark:bg-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-xl border border-slate-200 dark:border-slate-700 max-h-[90vh] overflow-y-auto">
            <h2 class="text-xl font-bold">Define Staffing Project</h2>
            <div class="space-y-3 text-sm">
              <div>
                <label class="block text-xs font-semibold mb-1">Project Name:</label>
                <input type="text" [(ngModel)]="newProject.name" class="w-full text-xs p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-900" placeholder="e.g. Cloud Native Migration">
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-xs font-semibold mb-1">Headcount:</label>
                  <input type="number" [(ngModel)]="newProject.headcount" class="w-full text-xs p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-900">
                </div>
                <div>
                  <label class="block text-xs font-semibold mb-1">Start Date:</label>
                  <input type="date" [(ngModel)]="newProject.start_date" class="w-full text-xs p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-900">
                </div>
              </div>

              <!-- Skills Definition -->
              <div class="space-y-2 pt-2 border-t border-slate-200 dark:border-slate-700">
                <span class="text-xs font-bold block">Required Skills & Minimum Benchmark (%):</span>
                <div *ngFor="let sk of newProject.skills; let idx = index" class="flex items-center space-x-2">
                  <input type="text" [(ngModel)]="sk.skill_name" class="flex-1 text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-900" placeholder="Skill name">
                  <input type="number" [(ngModel)]="sk.min_level_pct" class="w-20 text-xs p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-900" placeholder="Min %">
                </div>
                <button (click)="addSkillRow()" class="text-xs text-violet-600 hover:underline font-semibold">+ Add Another Skill</button>
              </div>
            </div>

            <div class="flex justify-end space-x-2 pt-4 border-t border-slate-100 dark:border-slate-700">
              <button (click)="showCreateModal = false" class="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg">Cancel</button>
              <button (click)="submitCreateProject()" [disabled]="!newProject.name" class="px-4 py-2 bg-violet-600 hover:bg-violet-700 text-white text-sm font-semibold rounded-lg">Create Project</button>
            </div>
          </div>
        </div>

      </div>
    </div>
  `
})
export class StaffingComponent implements OnInit {
  projects: StaffingProject[] = [];
  selectedProjectId: number | null = null;
  projectMatchData: StaffingProjectMatchesResponse | null = null;
  showCreateModal = false;

  newProject = {
    name: '',
    headcount: 3,
    start_date: new Date().toISOString().slice(0, 10),
    ready_now_threshold_pct: 90.0,
    skills: [
      { skill_name: 'Deductive Logic', min_level_pct: 75.0, weight: 1.0 },
      { skill_name: 'Pattern Recognition', min_level_pct: 70.0, weight: 1.0 }
    ]
  };

  constructor(
    private phase11Service: Phase11Service,
    private authService: AuthService
  ) {}

  get isAdmin(): boolean {
    return this.authService.currentUser()?.role === 'ADMIN';
  }

  ngOnInit(): void {
    this.loadProjects();
  }

  loadProjects(): void {
    this.phase11Service.getStaffingProjects().subscribe(projs => {
      this.projects = projs;
      if (projs.length > 0) {
        this.selectedProjectId = projs[0].id;
        this.loadMatches(projs[0].id);
      }
    });
  }

  onProjectSelected(id: number): void {
    this.selectedProjectId = id;
    this.loadMatches(id);
  }

  loadMatches(id: number): void {
    this.phase11Service.getProjectMatches(id).subscribe(res => {
      this.projectMatchData = res;
    });
  }

  openCreateProjectModal(): void {
    this.showCreateModal = true;
  }

  addSkillRow(): void {
    this.newProject.skills.push({ skill_name: '', min_level_pct: 70.0, weight: 1.0 });
  }

  submitCreateProject(): void {
    this.phase11Service.createStaffingProject({
      name: this.newProject.name,
      headcount: this.newProject.headcount,
      start_date: new Date(this.newProject.start_date).toISOString(),
      ready_now_threshold_pct: this.newProject.ready_now_threshold_pct,
      skills: this.newProject.skills.filter(s => s.skill_name.trim().length > 0)
    }).subscribe(created => {
      this.showCreateModal = false;
      this.projects.unshift(created);
      this.selectedProjectId = created.id;
      this.loadMatches(created.id);
    });
  }
}
