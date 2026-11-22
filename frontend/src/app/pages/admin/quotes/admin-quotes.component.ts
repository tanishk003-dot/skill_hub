import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { QuoteService } from '../../../core/services/quote.service';
import { MotivationalQuote } from '../../../core/models/quote.model';

@Component({
  selector: 'app-admin-quotes',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="quotes-page">
      <!-- Header -->
      <div class="page-header">
        <div>
          <h1 class="page-title">Motivational Quotes Management</h1>
          <p class="page-subtitle">Manage role-specific daily inspirational quotes displayed on the welcome splash.</p>
        </div>
        <button type="button" class="btn-primary" (click)="openCreateModal()">
          + Add New Quote
        </button>
      </div>

      <!-- Filters -->
      <div class="filters-card">
        <div class="filter-group">
          <label>Filter by Role:</label>
          <select [(ngModel)]="selectedRole" (change)="loadQuotes()" class="form-select">
            <option value="">All Roles</option>
            <option value="ADMIN">Admin</option>
            <option value="MENTOR">Mentor</option>
            <option value="ASE">ASE</option>
          </select>
        </div>

        <div class="filter-group">
          <label>Filter by Status:</label>
          <select [(ngModel)]="selectedStatus" (change)="loadQuotes()" class="form-select">
            <option value="">All Statuses</option>
            <option value="true">Active Only</option>
            <option value="false">Inactive</option>
          </select>
        </div>

        <div class="stats-counter">
          Total Quotes: <strong>{{ quotes().length }}</strong>
        </div>
      </div>

      <!-- Quotes Table -->
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th style="width: 80px;">Role</th>
              <th>Quote Text</th>
              <th style="width: 180px;">Author</th>
              <th style="width: 100px;">Status</th>
              <th style="width: 140px;">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let q of quotes()">
              <td>
                <span class="role-badge" [ngClass]="q.role.toLowerCase()">
                  {{ q.role }}
                </span>
              </td>
              <td class="quote-text-cell">“{{ q.text }}”</td>
              <td class="author-cell">{{ q.author }}</td>
              <td>
                <span class="status-badge" [class.active]="q.is_active" [class.inactive]="!q.is_active">
                  {{ q.is_active ? 'Active' : 'Disabled' }}
                </span>
              </td>
              <td>
                <div class="action-buttons">
                  <button type="button" class="btn-sm btn-edit" (click)="openEditModal(q)">
                    Edit
                  </button>
                  <button type="button" class="btn-sm btn-toggle" (click)="toggleQuote(q)">
                    {{ q.is_active ? 'Disable' : 'Enable' }}
                  </button>
                </div>
              </td>
            </tr>
            <tr *ngIf="quotes().length === 0">
              <td colspan="5" class="empty-state">No motivational quotes found matching the selected filters.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Modal Dialog -->
      <div *ngIf="modalVisible()" class="modal-overlay">
        <div class="modal-card">
          <h2 class="modal-title">{{ isEditing() ? 'Edit Quote' : 'Add New Motivational Quote' }}</h2>
          
          <div class="modal-form">
            <div class="form-group">
              <label>Target Role *</label>
              <select [(ngModel)]="currentForm.role" class="form-control">
                <option value="ADMIN">Admin (Leadership, vision, building teams)</option>
                <option value="MENTOR">Mentor (Teaching, guiding, patience, growth)</option>
                <option value="ASE">ASE (Learning, practice, consistency, coding)</option>
              </select>
            </div>

            <div class="form-group">
              <label>Quote Text *</label>
              <textarea [(ngModel)]="currentForm.text" rows="4" class="form-control" placeholder="Enter inspiring quote text..."></textarea>
            </div>

            <div class="form-group">
              <label>Author *</label>
              <input type="text" [(ngModel)]="currentForm.author" class="form-control" placeholder="e.g. Warren Bennis or L&K Team" />
              <small class="form-hint">Only use 100% verified authentic quotes, or attribute to 'L&K Team'.</small>
            </div>

            <div class="form-group-checkbox">
              <input type="checkbox" id="quoteActive" [(ngModel)]="currentForm.is_active" />
              <label for="quoteActive">Is Active</label>
            </div>

            <div class="modal-actions">
              <button type="button" class="btn-cancel" (click)="closeModal()">Cancel</button>
              <button type="button" class="btn-save" (click)="saveQuote()">Save Quote</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .quotes-page {
      padding: 1.5rem 2rem;
      max-width: 1200px;
      margin: 0 auto;
    }

    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.5rem;
    }

    .page-title {
      font-size: 1.75rem;
      font-weight: 700;
      color: var(--csm-primary);
      margin: 0;
    }

    .page-subtitle {
      color: #64748B;
      font-size: 0.95rem;
      margin-top: 0.25rem;
    }

    .btn-primary {
      background: var(--csm-primary);
      color: white;
      border: none;
      padding: 0.65rem 1.25rem;
      border-radius: 0.5rem;
      font-weight: 600;
      font-size: 0.9rem;
      cursor: pointer;
      transition: background 0.2s;
    }

    .btn-primary:hover {
      background: #2563EB;
    }

    .filters-card {
      background: white;
      border: 1px solid #E2E8F0;
      border-radius: 0.75rem;
      padding: 1rem 1.5rem;
      display: flex;
      align-items: center;
      gap: 1.5rem;
      margin-bottom: 1.5rem;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    .filter-group {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.875rem;
      font-weight: 500;
      color: #475569;
    }

    .form-select {
      padding: 0.4rem 0.75rem;
      border: 1px solid #CBD5E1;
      border-radius: 0.375rem;
      font-size: 0.875rem;
      background: white;
    }

    .stats-counter {
      margin-left: auto;
      font-size: 0.875rem;
      color: #64748B;
    }

    .table-container {
      background: white;
      border: 1px solid #E2E8F0;
      border-radius: 0.75rem;
      overflow: hidden;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    .data-table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
    }

    .data-table th {
      background: #F8FAFC;
      padding: 0.85rem 1rem;
      font-size: 0.8rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #64748B;
      border-bottom: 1px solid #E2E8F0;
    }

    .data-table td {
      padding: 0.85rem 1rem;
      font-size: 0.9rem;
      border-bottom: 1px solid #F1F5F9;
      color: #334155;
    }

    .role-badge {
      display: inline-block;
      padding: 0.2rem 0.5rem;
      border-radius: 0.25rem;
      font-size: 0.75rem;
      font-weight: 700;
      letter-spacing: 0.05em;
    }

    .role-badge.admin {
      background: #EEF2FF;
      color: #4F46E5;
    }

    .role-badge.mentor {
      background: #ECFDF5;
      color: #059669;
    }

    .role-badge.ase {
      background: #FFF7ED;
      color: #EA580C;
    }

    .quote-text-cell {
      font-style: italic;
      line-height: 1.5;
    }

    .author-cell {
      font-weight: 600;
      color: var(--csm-primary);
    }

    .status-badge {
      display: inline-block;
      padding: 0.2rem 0.5rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
    }

    .status-badge.active {
      background: #DCFCE7;
      color: #166534;
    }

    .status-badge.inactive {
      background: #F1F5F9;
      color: #94A3B8;
    }

    .action-buttons {
      display: flex;
      gap: 0.5rem;
    }

    .btn-sm {
      padding: 0.3rem 0.6rem;
      border-radius: 0.375rem;
      font-size: 0.8rem;
      font-weight: 500;
      cursor: pointer;
      border: 1px solid transparent;
    }

    .btn-edit {
      background: #F8FAFC;
      border-color: #CBD5E1;
      color: #334155;
    }

    .btn-edit:hover {
      background: #F1F5F9;
    }

    .btn-toggle {
      background: #FEF3C7;
      border-color: #FDE68A;
      color: #B45309;
    }

    .btn-toggle:hover {
      background: #FDE68A;
    }

    .empty-state {
      text-align: center;
      padding: 2.5rem;
      color: #94A3B8;
    }

    /* Modal */
    .modal-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 10000;
    }

    .modal-card {
      background: white;
      border-radius: 0.75rem;
      width: 100%;
      max-width: 540px;
      padding: 1.75rem;
      box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1);
    }

    .modal-title {
      font-size: 1.25rem;
      font-weight: 700;
      color: var(--csm-primary);
      margin: 0 0 1.25rem 0;
    }

    .modal-form {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .form-group {
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
    }

    .form-group label {
      font-size: 0.85rem;
      font-weight: 600;
      color: #334155;
    }

    .form-control {
      padding: 0.5rem 0.75rem;
      border: 1px solid #CBD5E1;
      border-radius: 0.375rem;
      font-size: 0.9rem;
      font-family: inherit;
    }

    .form-hint {
      font-size: 0.75rem;
      color: #64748B;
    }

    .form-group-checkbox {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.9rem;
      font-weight: 500;
    }

    .modal-actions {
      display: flex;
      justify-content: flex-end;
      gap: 0.75rem;
      margin-top: 1rem;
    }

    .btn-cancel {
      padding: 0.5rem 1rem;
      background: #F1F5F9;
      border: 1px solid #E2E8F0;
      color: #475569;
      border-radius: 0.375rem;
      cursor: pointer;
    }

    .btn-save {
      padding: 0.5rem 1.25rem;
      background: var(--csm-primary);
      color: white;
      border: none;
      border-radius: 0.375rem;
      font-weight: 600;
      cursor: pointer;
    }
  `]
})
export class AdminQuotesComponent implements OnInit {
  private quoteService = inject(QuoteService);

  quotes = signal<MotivationalQuote[]>([]);
  selectedRole = '';
  selectedStatus = '';

  modalVisible = signal<boolean>(false);
  isEditing = signal<boolean>(false);
  editingId: number | null = null;

  currentForm: {
    role: 'ADMIN' | 'MENTOR' | 'ASE';
    text: string;
    author: string;
    is_active: boolean;
  } = {
    role: 'ADMIN',
    text: '',
    author: 'L&K Team',
    is_active: true
  };

  ngOnInit(): void {
    this.loadQuotes();
  }

  loadQuotes(): void {
    const roleParam = this.selectedRole || undefined;
    const statusParam = this.selectedStatus === '' ? undefined : this.selectedStatus === 'true';
    this.quoteService.listQuotesAdmin(roleParam, statusParam).subscribe({
      next: (data) => this.quotes.set(data),
      error: (err) => console.error('Failed to load quotes:', err)
    });
  }

  openCreateModal(): void {
    this.isEditing.set(false);
    this.editingId = null;
    this.currentForm = {
      role: 'ADMIN',
      text: '',
      author: 'L&K Team',
      is_active: true
    };
    this.modalVisible.set(true);
  }

  openEditModal(quote: MotivationalQuote): void {
    this.isEditing.set(true);
    this.editingId = quote.id;
    this.currentForm = {
      role: quote.role,
      text: quote.text,
      author: quote.author,
      is_active: quote.is_active
    };
    this.modalVisible.set(true);
  }

  closeModal(): void {
    this.modalVisible.set(false);
  }

  saveQuote(): void {
    if (!this.currentForm.text.trim()) {
      alert('Please enter quote text');
      return;
    }

    if (this.isEditing() && this.editingId) {
      this.quoteService.updateQuote(this.editingId, this.currentForm).subscribe({
        next: () => {
          this.closeModal();
          this.loadQuotes();
        },
        error: (err) => alert('Failed to update quote')
      });
    } else {
      this.quoteService.createQuote(this.currentForm).subscribe({
        next: () => {
          this.closeModal();
          this.loadQuotes();
        },
        error: (err) => alert('Failed to create quote')
      });
    }
  }

  toggleQuote(quote: MotivationalQuote): void {
    this.quoteService.updateQuote(quote.id, { is_active: !quote.is_active }).subscribe({
      next: () => this.loadQuotes(),
      error: () => alert('Failed to toggle quote')
    });
  }
}
