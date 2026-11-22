import { Component, Inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { User, UserRole } from '../../../core/models/user.model';

export interface UserDialogData {
  mode: 'create' | 'edit';
  user?: User;
}

@Component({
  selector: 'app-user-form-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatSlideToggleModule,
    MatButtonModule,
    MatIconModule
  ],
  template: `
    <div class="dialog-container">
      <h2 mat-dialog-title>
        <mat-icon>{{ isEdit ? 'edit' : 'person_add' }}</mat-icon>
        {{ isEdit ? 'Edit User' : 'Create New User' }}
      </h2>

      <mat-dialog-content>
        <form [formGroup]="userForm" class="dialog-form">
          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Full Name</mat-label>
            <input matInput formControlName="name" placeholder="e.g. John Doe" />
            <mat-icon matPrefix>person</mat-icon>
            @if (userForm.get('name')?.hasError('required') && userForm.get('name')?.touched) {
              <mat-error>Name is required</mat-error>
            }
          </mat-form-field>

          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Email Address</mat-label>
            <input matInput type="email" formControlName="email" placeholder="e.g. jdoe@skillhub.com" />
            <mat-icon matPrefix>email</mat-icon>
            @if (userForm.get('email')?.hasError('required') && userForm.get('email')?.touched) {
              <mat-error>Email is required</mat-error>
            }
            @if (userForm.get('email')?.hasError('email') && userForm.get('email')?.touched) {
              <mat-error>Please enter a valid email</mat-error>
            }
          </mat-form-field>

          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Role</mat-label>
            <mat-select formControlName="role">
              <mat-option value="MENTOR">Mentor</mat-option>
              <mat-option value="ASE">ASE (Associate Engineer)</mat-option>
              <mat-option value="ADMIN">Administrator</mat-option>
            </mat-select>
            <mat-icon matPrefix>badge</mat-icon>
          </mat-form-field>

          <mat-form-field appearance="outline" class="full-width">
            <mat-label>{{ isEdit ? 'Change Password (leave blank to keep current)' : 'Password' }}</mat-label>
            <input matInput [type]="hidePassword() ? 'password' : 'text'" formControlName="password" />
            <mat-icon matPrefix>lock</mat-icon>
            <button mat-icon-button matSuffix type="button" (click)="hidePassword.set(!hidePassword())">
              <mat-icon>{{ hidePassword() ? 'visibility_off' : 'visibility' }}</mat-icon>
            </button>
            @if (userForm.get('password')?.hasError('required') && userForm.get('password')?.touched) {
              <mat-error>Password is required for new users</mat-error>
            }
          </mat-form-field>

          @if (isEdit) {
            <div class="toggle-row">
              <mat-slide-toggle formControlName="is_active" color="primary">
                Active Account
              </mat-slide-toggle>
              <span class="toggle-desc">
                {{ userForm.get('is_active')?.value ? 'User can log in' : 'Deactivated / Soft-deleted' }}
              </span>
            </div>
          }
        </form>
      </mat-dialog-content>

      <mat-dialog-actions align="end">
        <button mat-button mat-dialog-close>Cancel</button>
        <button mat-flat-button class="btn-primary" (click)="onSave()" [disabled]="userForm.invalid">
          {{ isEdit ? 'Save Changes' : 'Create User' }}
        </button>
      </mat-dialog-actions>
    </div>
  `,
  styles: [`
    .dialog-container {
      padding: 8px 16px;
      min-width: 420px;
    }

    h2 {
      display: flex;
      align-items: center;
      gap: 10px;
      margin: 0;
      font-size: 1.25rem;
      font-weight: 600;
      color: #0f172a;

      mat-icon {
        color: var(--csm-primary);
      }
    }

    .dialog-form {
      display: flex;
      flex-direction: column;
      gap: 12px;
      padding-top: 12px;
    }

    .full-width {
      width: 100%;
    }

    .toggle-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 0;

      .toggle-desc {
        font-size: 0.8rem;
        color: var(--text-muted);
      }
    }
  `]
})
export class UserFormDialogComponent {
  userForm: FormGroup;
  isEdit: boolean;
  hidePassword = signal(true);

  constructor(
    private fb: FormBuilder,
    public dialogRef: MatDialogRef<UserFormDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: UserDialogData
  ) {
    this.isEdit = data.mode === 'edit';
    const u = data.user;

    this.userForm = this.fb.group({
      name: [u?.name || '', Validators.required],
      email: [u?.email || '', [Validators.required, Validators.email]],
      role: [u?.role || 'ASE', Validators.required],
      password: ['', this.isEdit ? [] : [Validators.required, Validators.minLength(6)]],
      is_active: [u ? u.is_active : true]
    });
  }

  onSave(): void {
    if (this.userForm.invalid) return;
    const value = { ...this.userForm.value };
    // Omit password if editing and empty
    if (this.isEdit && (!value.password || !value.password.trim())) {
      delete value.password;
    }
    this.dialogRef.close(value);
  }
}
