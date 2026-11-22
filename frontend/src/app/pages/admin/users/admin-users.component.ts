import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { UserService } from '../../../core/services/user.service';
import { User, UserRole } from '../../../core/models/user.model';
import { UserFormDialogComponent } from './user-form-dialog.component';

@Component({
  selector: 'app-admin-users',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatSlideToggleModule,
    MatDialogModule,
    MatSnackBarModule,
    MatTooltipModule,
    MatProgressSpinnerModule
  ],
  template: `
    <div class="users-page">
      <div class="page-header">
        <div>
          <h1>User Management</h1>
          <p>Create, edit, manage, and soft-delete Mentors and ASEs</p>
        </div>
        <button mat-flat-button class="btn-primary" (click)="openCreateDialog()">
          <mat-icon>add</mat-icon> Add New User
        </button>
      </div>

      <!-- Filters & Controls Bar -->
      <div class="controls-card card-shadow">
        <div class="search-box">
          <mat-icon>search</mat-icon>
          <input
            type="text"
            [(ngModel)]="searchQuery"
            placeholder="Search by name or email..."
            (input)="onSearchChange()"
          />
        </div>

        <div class="filters-group">
          <mat-form-field appearance="outline" class="role-filter">
            <mat-label>Filter by Role</mat-label>
            <mat-select [(ngModel)]="selectedRole" (selectionChange)="loadUsers()">
              <mat-option value="">All Roles</mat-option>
              <mat-option value="MENTOR">Mentors</mat-option>
              <mat-option value="ASE">ASEs</mat-option>
              <mat-option value="ADMIN">Admins</mat-option>
            </mat-select>
          </mat-form-field>

          <mat-slide-toggle [(ngModel)]="includeInactive" (change)="loadUsers()" color="primary">
            Include Deactivated
          </mat-slide-toggle>
        </div>
      </div>

      <!-- Users Table -->
      <div class="table-container card-shadow">
        @if (isLoading()) {
          <div class="loading-state">
            <mat-spinner diameter="36"></mat-spinner>
            <span>Loading user directory...</span>
          </div>
        } @else if (filteredUsers().length === 0) {
          <div class="empty-state">
            <mat-icon>people_outline</mat-icon>
            <h3>No users found</h3>
            <p>Try adjusting your search query or filters.</p>
          </div>
        } @else {
          <table mat-table [dataSource]="filteredUsers()" class="users-table">
            <!-- ID Column -->
            <ng-container matColumnDef="id">
              <th mat-header-cell *matHeaderCellDef>#</th>
              <td mat-cell *matCellDef="let u">{{ u.id }}</td>
            </ng-container>

            <!-- User Info Column -->
            <ng-container matColumnDef="user">
              <th mat-header-cell *matHeaderCellDef>User Details</th>
              <td mat-cell *matCellDef="let u">
                <div class="user-cell">
                  <div class="avatar" [ngClass]="'avatar-' + u.role.toLowerCase()">
                    {{ u.name[0] }}
                  </div>
                  <div class="info">
                    <span class="name">{{ u.name }}</span>
                    <span class="email">{{ u.email }}</span>
                  </div>
                </div>
              </td>
            </ng-container>

            <!-- Role Column -->
            <ng-container matColumnDef="role">
              <th mat-header-cell *matHeaderCellDef>Role</th>
              <td mat-cell *matCellDef="let u">
                <span class="badge" [ngClass]="'badge-' + u.role.toLowerCase()">
                  {{ u.role }}
                </span>
              </td>
            </ng-container>

            <!-- Status Column -->
            <ng-container matColumnDef="status">
              <th mat-header-cell *matHeaderCellDef>Status</th>
              <td mat-cell *matCellDef="let u">
                <span class="badge" [ngClass]="u.is_active ? 'badge-active' : 'badge-inactive'">
                  {{ u.is_active ? 'Active' : 'Deactivated' }}
                </span>
              </td>
            </ng-container>

            <!-- Mentor Mapping Column (for ASEs) -->
            <ng-container matColumnDef="mentor">
              <th mat-header-cell *matHeaderCellDef>Assigned Mentor</th>
              <td mat-cell *matCellDef="let u">
                @if (u.role === 'ASE') {
                  @if (u.assigned_mentor_name) {
                    <span class="mentor-tag">
                      <mat-icon>psychology</mat-icon> {{ u.assigned_mentor_name }}
                    </span>
                  } @else {
                    <span class="unassigned-text">Unassigned</span>
                  }
                } @else {
                  <span class="dash">—</span>
                }
              </td>
            </ng-container>

            <!-- Actions Column -->
            <ng-container matColumnDef="actions">
              <th mat-header-cell *matHeaderCellDef class="text-right">Actions</th>
              <td mat-cell *matCellDef="let u" class="text-right">
                <div class="action-buttons">
                  <button mat-icon-button color="primary" matTooltip="Edit User" (click)="openEditDialog(u)">
                    <mat-icon>edit</mat-icon>
                  </button>

                  @if (u.is_active) {
                    <button mat-icon-button color="warn" matTooltip="Soft Delete (Deactivate)" (click)="confirmSoftDelete(u)">
                      <mat-icon>person_remove</mat-icon>
                    </button>
                  } @else {
                    <button mat-icon-button matTooltip="Reactivate User" class="btn-reactivate" (click)="reactivateUser(u)">
                      <mat-icon>check_circle</mat-icon>
                    </button>
                  }
                </div>
              </td>
            </ng-container>

            <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
            <tr mat-row *matRowDef="let row; columns: displayedColumns;" [class.row-inactive]="!row.is_active"></tr>
          </table>
        }
      </div>
    </div>
  `,
  styles: [`
    .users-page {
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: center;

      h1 {
        font-size: 1.6rem;
        font-weight: 700;
        margin: 0;
        color: #0f172a;
      }

      p {
        margin: 4px 0 0;
        color: var(--text-muted);
        font-size: 0.9rem;
      }
    }

    .controls-card {
      padding: 16px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;

      .search-box {
        display: flex;
        align-items: center;
        gap: 10px;
        background-color: var(--bg-main);
        padding: 8px 16px;
        border-radius: 8px;
        flex: 1;
        min-width: 260px;
        border: 1px solid var(--border-light);

        mat-icon {
          color: var(--text-muted);
          font-size: 20px;
          width: 20px;
          height: 20px;
        }

        input {
          border: none;
          background: transparent;
          outline: none;
          width: 100%;
          font-size: 0.9rem;
          color: var(--text-primary);
        }
      }

      .filters-group {
        display: flex;
        align-items: center;
        gap: 20px;

        .role-filter {
          width: 160px;
          margin-bottom: -1.25em;
        }
      }
    }

    .table-container {
      overflow-x: auto;
      background: #ffffff;
      border-radius: 12px;
    }

    .users-table {
      width: 100%;

      th {
        font-weight: 600;
        color: var(--text-secondary);
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding: 16px;
      }

      td {
        padding: 12px 16px;
      }

      .text-right {
        text-align: right;
      }

      .row-inactive {
        opacity: 0.6;
        background-color: #fafafa;
      }
    }

    .user-cell {
      display: flex;
      align-items: center;
      gap: 12px;

      .avatar {
        width: 38px;
        height: 38px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 0.9rem;
        color: #ffffff;

        &.avatar-admin { background-color: #dc2626; }
        &.avatar-mentor { background-color: #2563eb; }
        &.avatar-ase { background-color: #ea580c; }
      }

      .info {
        display: flex;
        flex-direction: column;

        .name {
          font-weight: 600;
          font-size: 0.92rem;
          color: #0f172a;
        }

        .email {
          font-size: 0.8rem;
          color: var(--text-muted);
        }
      }
    }

    .mentor-tag {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      border-radius: 6px;
      color: #1d4ed8;
      font-size: 0.82rem;
      font-weight: 500;

      mat-icon {
        font-size: 16px;
        width: 16px;
        height: 16px;
      }
    }

    .unassigned-text {
      color: var(--csm-accent);
      font-size: 0.82rem;
      font-weight: 500;
      font-style: italic;
    }

    .dash {
      color: var(--text-muted);
    }

    .action-buttons {
      display: inline-flex;
      gap: 4px;

      .btn-reactivate {
        color: #16a34a;
      }
    }

    .loading-state, .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 64px 20px;
      color: var(--text-muted);

      mat-icon {
        font-size: 48px;
        width: 48px;
        height: 48px;
        margin-bottom: 8px;
        opacity: 0.5;
      }

      h3 {
        margin: 0;
        font-size: 1.1rem;
        color: #0f172a;
      }

      p {
        margin: 4px 0 0;
        font-size: 0.85rem;
      }
    }
  `]
})
export class AdminUsersComponent implements OnInit {
  users = signal<User[]>([]);
  isLoading = signal(true);
  searchQuery = '';
  selectedRole = '';
  includeInactive = false;
  displayedColumns = ['id', 'user', 'role', 'status', 'mentor', 'actions'];

  filteredUsers = computed(() => {
    const query = this.searchQuery.trim().toLowerCase();
    return this.users().filter(u => {
      const matchesSearch = !query ||
        u.name.toLowerCase().includes(query) ||
        u.email.toLowerCase().includes(query);
      return matchesSearch;
    });
  });

  constructor(
    private userService: UserService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.loadUsers();
  }

  loadUsers(): void {
    this.isLoading.set(true);
    const roleParam = (this.selectedRole ? this.selectedRole as UserRole : undefined);
    this.userService.getUsers(roleParam, this.includeInactive).subscribe({
      next: (res) => {
        this.users.set(res);
        this.isLoading.set(false);
      },
      error: () => this.isLoading.set(false)
    });
  }

  onSearchChange(): void {
    // Computed signal updates automatically
  }

  openCreateDialog(): void {
    const dialogRef = this.dialog.open(UserFormDialogComponent, {
      data: { mode: 'create' }
    });

    dialogRef.afterClosed().subscribe((res) => {
      if (res) {
        this.userService.createUser(res).subscribe({
          next: (newUser) => {
            this.snackBar.open(`User '${newUser.name}' created successfully`, 'Close', {
              duration: 3500,
              panelClass: ['snack-success']
            });
            this.loadUsers();
          },
          error: (err) => {
            const detail = err.error?.detail || 'Failed to create user';
            this.snackBar.open(detail, 'Close', { duration: 4000, panelClass: ['snack-error'] });
          }
        });
      }
    });
  }

  openEditDialog(user: User): void {
    const dialogRef = this.dialog.open(UserFormDialogComponent, {
      data: { mode: 'edit', user }
    });

    dialogRef.afterClosed().subscribe((res) => {
      if (res) {
        this.userService.updateUser(user.id, res).subscribe({
          next: (updated) => {
            this.snackBar.open(`User '${updated.name}' updated successfully`, 'Close', {
              duration: 3500,
              panelClass: ['snack-success']
            });
            this.loadUsers();
          },
          error: (err) => {
            const detail = err.error?.detail || 'Failed to update user';
            this.snackBar.open(detail, 'Close', { duration: 4000, panelClass: ['snack-error'] });
          }
        });
      }
    });
  }

  confirmSoftDelete(user: User): void {
    if (confirm(`Are you sure you want to deactivate and soft-delete '${user.name}'? They will no longer be able to log in.`)) {
      this.userService.deleteUser(user.id).subscribe({
        next: () => {
          this.snackBar.open(`User '${user.name}' soft-deleted (is_active=false)`, 'Close', {
            duration: 3500,
            panelClass: ['snack-success']
          });
          this.loadUsers();
        },
        error: (err) => {
          const detail = err.error?.detail || 'Failed to soft delete user';
          this.snackBar.open(detail, 'Close', { duration: 4000, panelClass: ['snack-error'] });
        }
      });
    }
  }

  reactivateUser(user: User): void {
    this.userService.updateUser(user.id, { is_active: true }).subscribe({
      next: () => {
        this.snackBar.open(`User '${user.name}' reactivated successfully`, 'Close', {
          duration: 3500,
          panelClass: ['snack-success']
        });
        this.loadUsers();
      },
      error: (err) => {
        const detail = err.error?.detail || 'Failed to reactivate user';
        this.snackBar.open(detail, 'Close', { duration: 4000, panelClass: ['snack-error'] });
      }
    });
  }
}
