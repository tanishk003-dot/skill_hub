import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ProctoringService } from '../../../core/services/proctoring.service';
import { AuthService } from '../../../core/services/auth.service';
import { AccommodationRequestItem, AccommodationCreatePayload } from '../../../core/models/proctoring.model';

@Component({
  selector: 'app-accommodations',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="min-h-screen bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100 p-6">
      <div class="max-w-5xl mx-auto space-y-6">

        <!-- Header -->
        <div class="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-4">
          <div>
            <div class="flex items-center space-x-3">
              <span class="p-2 rounded-lg bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300">
                <svg width="24" height="24" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
                </svg>
              </span>
              <h1 class="text-2xl font-bold">Reasonable Accommodations & Inclusion</h1>
            </div>
            <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Request equitable exam adjustments including camera exemptions, extended session timers, or rest breaks.
            </p>
          </div>
          <button (click)="openRequestModal()"
            class="px-4 py-2 text-sm font-medium rounded-lg bg-blue-600 hover:bg-blue-700 text-white shadow-sm transition">
            + Request Accommodation
          </button>
        </div>

        <!-- Privacy & Protection Policy Card -->
        <div class="bg-blue-50/60 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900/50 rounded-2xl p-4 flex items-start space-x-3">
          <svg width="20" height="20" class="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
          </svg>
          <div class="text-xs text-blue-900 dark:text-blue-200 space-y-1">
            <p class="font-semibold">Confidentiality Guarantee</p>
            <p>
              Medical notes and personal diagnostic details submitted here are strictly confidential to the candidate and system HR Administrators. Mentors and peers receive only the neutral active accommodation status ("Standard Accommodations Active") without diagnostic exposure.
            </p>
          </div>
        </div>

        <!-- Accommodations List -->
        <div class="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
          <div class="p-4 border-b border-slate-100 dark:border-slate-700/60 flex items-center justify-between">
            <h2 class="text-base font-bold">Accommodation Requests & Status</h2>
            <span class="text-xs text-slate-400">{{ accommodations.length }} Record(s)</span>
          </div>

          <div *ngIf="loading" class="p-8 text-center text-slate-400 text-sm">
            Loading accommodations...
          </div>

          <div *ngIf="!loading && accommodations.length === 0" class="p-8 text-center space-y-2">
            <p class="text-slate-500 dark:text-slate-400 text-sm">No accommodation requests on file.</p>
            <p class="text-xs text-slate-400">If you have specific medical, cognitive, or physical requirements, please submit a request.</p>
          </div>

          <div *ngIf="!loading && accommodations.length > 0" class="divide-y divide-slate-100 dark:divide-slate-700/50">
            <div *ngFor="let acc of accommodations" class="p-4 hover:bg-slate-50/50 dark:hover:bg-slate-750 transition flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div class="space-y-1.5">
                <div class="flex items-center space-x-2">
                  <span class="text-sm font-semibold">{{ getTypeName(acc.accommodation_type) }}</span>
                  <span class="text-xs px-2 py-0.5 rounded-full font-medium"
                    [ngClass]="{
                      'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300': acc.status === 'APPROVED',
                      'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300': acc.status === 'PENDING',
                      'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300': acc.status === 'REJECTED'
                    }">
                    {{ acc.status }}
                  </span>
                  <span *ngIf="acc.extra_time_percent" class="text-xs bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 px-2 py-0.5 rounded font-mono">
                    +{{ acc.extra_time_percent }}% Extra Time
                  </span>
                </div>

                <div class="text-xs text-slate-500 dark:text-slate-400 flex flex-wrap gap-x-4 gap-y-1">
                  <span>Candidate: <strong>{{ acc.ase_name || 'You' }}</strong></span>
                  <span>Category: {{ acc.reason_category }}</span>
                  <span>Requested: {{ acc.created_at | date:'mediumDate' }}</span>
                </div>

                <!-- Medical notes (displayed if visible to current user) -->
                <div *ngIf="acc.medical_notes" class="text-xs p-2.5 rounded-lg bg-slate-50 dark:bg-slate-900/60 border border-slate-200/50 dark:border-slate-800 text-slate-700 dark:text-slate-300 max-w-2xl font-mono">
                  {{ acc.medical_notes }}
                </div>

                <!-- Admin decision note -->
                <div *ngIf="acc.admin_notes" class="text-xs text-slate-600 dark:text-slate-400 italic">
                  Reviewer Note: "{{ acc.admin_notes }}"
                </div>
              </div>

              <!-- Admin Decision Actions -->
              <div *ngIf="isAdmin && acc.status === 'PENDING'" class="flex items-center space-x-2 shrink-0">
                <button (click)="decide(acc.id, true)"
                  class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-medium rounded-lg shadow-sm transition">
                  Approve
                </button>
                <button (click)="decide(acc.id, false)"
                  class="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs font-medium rounded-lg shadow-sm transition">
                  Reject
                </button>
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- Request Modal -->
      <div *ngIf="showModal" class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div class="bg-white dark:bg-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-xl border border-slate-200 dark:border-slate-700">
          <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-700 pb-3">
            <h3 class="text-lg font-bold">New Accommodation Request</h3>
            <button (click)="closeRequestModal()" class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
              <svg width="20" height="20" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>

          <form (ngSubmit)="submitRequest()" class="space-y-4 text-sm">
            <div>
              <label class="block font-medium mb-1">Accommodation Type</label>
              <select [(ngModel)]="form.accommodation_type" name="type" class="w-full p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-100">
                <option value="CAMERA_EXEMPTION">Camera Exemption (Physician or Hardware waiver)</option>
                <option value="EXTRA_TIME_PCT">Extended Assessment Duration (+25% to +100%)</option>
                <option value="REST_BREAKS">Rest Breaks & Pause Allowance</option>
                <option value="ALTERNATIVE_PROCTORING">Alternative Proctoring Verification</option>
                <option value="OTHER">Other Custom Reasonable Accommodation</option>
              </select>
            </div>

            <div *ngIf="form.accommodation_type === 'EXTRA_TIME_PCT'">
              <label class="block font-medium mb-1">Extra Time Percentage (%)</label>
              <input type="number" [(ngModel)]="form.extra_time_percent" name="extra_time" min="10" max="150" step="5"
                class="w-full p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-100"/>
              <p class="text-xs text-slate-400 mt-1">E.g., 50% turns a 30-minute assessment into 45 minutes.</p>
            </div>

            <div>
              <label class="block font-medium mb-1">Reason Category</label>
              <select [(ngModel)]="form.reason_category" name="category" class="w-full p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-100">
                <option value="MEDICAL">Medical Condition / Light Sensitivity</option>
                <option value="COGNITIVE">Cognitive / Processing Style / Neurodiversity</option>
                <option value="PHYSICAL">Physical / Visual / Motor Requirement</option>
                <option value="HARDWARE_CONSTRAINT">Camera Hardware Malfunction / Restricted Device</option>
                <option value="OTHER">Other Ground</option>
              </select>
            </div>

            <div>
              <label class="block font-medium mb-1">Confidential Documentation / Medical Notes (Optional)</label>
              <textarea [(ngModel)]="form.medical_notes" name="notes" rows="3" placeholder="Provide relevant details for HR Reviewer. These details remain strictly private to you and the Admin."
                class="w-full p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-100 text-xs font-mono"></textarea>
            </div>

            <div class="flex items-center justify-end space-x-2 pt-2 border-t border-slate-100 dark:border-slate-700">
              <button type="button" (click)="closeRequestModal()" class="px-4 py-2 border border-slate-300 dark:border-slate-700 rounded-lg text-xs font-medium">Cancel</button>
              <button type="submit" [disabled]="submitting" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-medium shadow-sm transition">
                {{ submitting ? 'Submitting...' : 'Submit Request' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  `
})
export class AccommodationsComponent implements OnInit {
  accommodations: AccommodationRequestItem[] = [];
  loading = false;
  submitting = false;
  showModal = false;
  isAdmin = false;
  currentUserId = 0;

  form: AccommodationCreatePayload = {
    ase_id: 0,
    accommodation_type: 'CAMERA_EXEMPTION',
    extra_time_percent: 50,
    reason_category: 'MEDICAL',
    medical_notes: ''
  };

  constructor(
    private proctoringService: ProctoringService,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    const user = this.authService.currentUser();
    if (user) {
      this.isAdmin = user.role === 'ADMIN';
      this.currentUserId = user.user_id;
      this.form.ase_id = user.user_id;
    }
    this.loadAccommodations();
  }

  loadAccommodations(): void {
    this.loading = true;
    this.proctoringService.listAccommodations().subscribe({
      next: res => {
        this.accommodations = res;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      }
    });
  }

  getTypeName(type: string): string {
    switch (type) {
      case 'EXTRA_TIME_PCT': return 'Extended Timer Allowance';
      case 'CAMERA_EXEMPTION': return 'Webcam Proctoring Exemption';
      case 'REST_BREAKS': return 'Rest Breaks Allowance';
      case 'ALTERNATIVE_PROCTORING': return 'Alternative Verification';
      default: return type;
    }
  }

  openRequestModal(): void {
    this.showModal = true;
  }

  closeRequestModal(): void {
    this.showModal = false;
  }

  submitRequest(): void {
    this.submitting = true;
    this.proctoringService.requestAccommodation(this.form).subscribe({
      next: () => {
        this.submitting = false;
        this.closeRequestModal();
        this.loadAccommodations();
      },
      error: err => {
        alert(err?.error?.detail || 'Failed to submit accommodation request');
        this.submitting = false;
      }
    });
  }

  decide(id: number, approved: boolean): void {
    const note = prompt(approved ? 'Optional approval note:' : 'Mandatory rejection reason:');
    if (!approved && (!note || note.trim().length === 0)) {
      alert('Please document a reason for rejection.');
      return;
    }
    this.proctoringService.reviewAccommodation(id, approved, note || undefined).subscribe({
      next: () => this.loadAccommodations(),
      error: err => alert(err?.error?.detail || 'Action failed')
    });
  }
}
