import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators, AbstractControl, ValidationErrors } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule
  ],
  template: `
    <div class="login-container">
      <div class="login-card-wrapper">
        <div class="brand-header">
          <div class="brand-icon">
            <mat-icon>school</mat-icon>
          </div>
          <h1>L&K Skill Hub</h1>
          <p>Continuous Engineering Upskilling & Mentorship</p>
        </div>

        <mat-card class="login-card">
          <div class="card-logo-container">
            <img src="assets/csm-logo.png" alt="CSM Tech Logo" class="csm-card-logo" />
          </div>

          <mat-card-header>
            <mat-card-title>Sign In</mat-card-title>
            <mat-card-subtitle>Access your technical onboarding & learning portal</mat-card-subtitle>
          </mat-card-header>

          <mat-card-content>
            @if (errorMessage()) {
              <div class="error-banner">
                <mat-icon>error_outline</mat-icon>
                <span>{{ errorMessage() }}</span>
              </div>
            }

            @if (isProcessingSSO()) {
              <div class="sso-loading-banner">
                <mat-spinner diameter="28"></mat-spinner>
                <span>Completing Microsoft authentication...</span>
              </div>
            }

            <!-- Microsoft SSO Primary Action -->
            <div class="sso-section">
              <button mat-stroked-button class="ms-sso-btn" type="button" (click)="signInWithMicrosoft()" [disabled]="isLoading() || isProcessingSSO()">
                <svg class="ms-logo" viewBox="0 0 21 21" width="20" height="20">
                  <rect x="1" y="1" width="9" height="9" fill="#f25022"/>
                  <rect x="11" y="1" width="9" height="9" fill="#7fba00"/>
                  <rect x="1" y="11" width="9" height="9" fill="#00a4ef"/>
                  <rect x="11" y="11" width="9" height="9" fill="#ffb900"/>
                </svg>
                <span>Sign in with Microsoft</span>
              </button>
            </div>

            <!-- Divider -->
            <div class="or-divider">
              <span>OR</span>
            </div>

            @if (!allowLocalLogin() && !showBreakGlass()) {
              <div class="local-disabled-banner">
                <mat-icon>lock</mat-icon>
                <div class="disabled-text">
                  <strong>Password login disabled</strong>
                  <span>Your organization requires SSO. Use "Sign in with Microsoft" above.</span>
                </div>
                <button mat-button class="break-glass-link" (click)="showBreakGlass.set(true)">
                  Break-glass admin?
                </button>
              </div>
            }

            <!-- Local Password Login Form -->
            @if (allowLocalLogin() || showBreakGlass()) {
              <form [formGroup]="loginForm" (ngSubmit)="onSubmit()" class="login-form">
                @if (showBreakGlass() && !allowLocalLogin()) {
                  <div class="break-glass-badge">
                    <mat-icon>security</mat-icon> Break-Glass Administrator Login
                  </div>
                }

                <mat-form-field appearance="outline" class="full-width">
                  <mat-label>Email Address</mat-label>
                  <input
                    matInput
                    type="email"
                    formControlName="email"
                    placeholder="name@csm.tech"
                    autocomplete="email"
                  />
                  <mat-icon matPrefix>email</mat-icon>
                  @if (loginForm.get('email')?.hasError('required') && loginForm.get('email')?.touched) {
                    <mat-error>Email is required</mat-error>
                  }
                  @if (loginForm.get('email')?.hasError('email') && loginForm.get('email')?.touched) {
                    <mat-error>Please enter a valid email address</mat-error>
                  }
                  @if (loginForm.get('email')?.hasError('invalidDomain') && loginForm.get('email')?.touched) {
                    <mat-error>Use your @csm.tech email</mat-error>
                  }
                </mat-form-field>

                <mat-form-field appearance="outline" class="full-width">
                  <mat-label>Password</mat-label>
                  <input
                    matInput
                    [type]="hidePassword() ? 'password' : 'text'"
                    formControlName="password"
                    autocomplete="current-password"
                  />
                  <mat-icon matPrefix>lock</mat-icon>
                  <button
                    mat-icon-button
                    matSuffix
                    type="button"
                    (click)="hidePassword.set(!hidePassword())"
                    [attr.aria-label]="hidePassword() ? 'Show password' : 'Hide password'"
                  >
                    <mat-icon>{{ hidePassword() ? 'visibility_off' : 'visibility' }}</mat-icon>
                  </button>
                  @if (loginForm.get('password')?.hasError('required') && loginForm.get('password')?.touched) {
                    <mat-error>Password is required</mat-error>
                  }
                </mat-form-field>

                <button mat-flat-button class="submit-btn" type="submit" [disabled]="loginForm.invalid || isLoading() || isProcessingSSO()">
                  @if (isLoading()) {
                    <span>Signing in...</span>
                  } @else {
                    <span>Sign In with Password</span>
                  }
                </button>

                <div class="forgot-password-note">
                  <mat-icon>info_outline</mat-icon>
                  <span>Forgot password? Contact your administrator</span>
                </div>
              </form>
            }

            <div class="demo-accounts" *ngIf="allowLocalLogin() && !isProduction()">
              <div class="demo-divider">
                <span>QUICK LOGIN AS SEED USERS</span>
              </div>
              <div class="demo-buttons">
                <button mat-stroked-button type="button" class="demo-btn admin" (click)="fillCredentials('admin')">
                  <mat-icon>admin_panel_settings</mat-icon> Admin
                </button>
                <button mat-stroked-button type="button" class="demo-btn mentor" (click)="fillCredentials('mentor')">
                  <mat-icon>psychology</mat-icon> Mentor
                </button>
                <button mat-stroked-button type="button" class="demo-btn ase" (click)="fillCredentials('ase')">
                  <mat-icon>engineering</mat-icon> ASE
                </button>
              </div>
            </div>
          </mat-card-content>
        </mat-card>

        <div class="footer-note">
          <span>Phase 13 • Microsoft 365 Entra ID SSO & Teams Integration Active</span>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .login-container {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, #0f172a 0%, var(--csm-primary) 50%, #1e293b 100%);
      padding: 24px;
    }

    .login-card-wrapper {
      width: 100%;
      max-width: 440px;
    }

    .brand-header {
      text-align: center;
      margin-bottom: 24px;
      color: #ffffff;

      .brand-icon {
        width: 56px;
        height: 56px;
        margin: 0 auto 12px;
        background: var(--csm-accent);
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 12px rgba(249, 115, 22, 0.35);

        mat-icon {
          font-size: 32px;
          width: 32px;
          height: 32px;
          color: #ffffff;
        }
      }

      h1 {
        font-size: 1.75rem;
        font-weight: 700;
        margin: 0 0 6px;
        letter-spacing: -0.02em;
      }

      p {
        font-size: 0.875rem;
        color: #94a3b8;
        margin: 0;
      }
    }

    .login-card {
      border-radius: 16px;
      padding: 16px 8px 24px;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.2);

      .card-logo-container {
        display: flex;
        justify-content: center;
        margin-bottom: 12px;
        padding-top: 4px;

        .csm-card-logo {
          height: 38px;
          max-width: 160px;
          object-fit: contain;
        }
      }

      mat-card-title {
        font-size: 1.25rem;
        font-weight: 600;
        color: #0f172a;
      }

      mat-card-subtitle {
        color: #64748b;
        margin-top: 4px;
        margin-bottom: 16px;
      }
    }

    .sso-section {
      margin-bottom: 16px;

      .ms-sso-btn {
        width: 100%;
        height: 48px;
        border: 1.5px solid #cbd5e1;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        font-weight: 600;
        font-size: 0.95rem;
        color: #1e293b;
        background: #ffffff;
        transition: all 0.2s ease;

        &:hover {
          background: #f8fafc;
          border-color: #94a3b8;
          box-shadow: 0 2px 6px rgba(0,0,0,0.06);
        }

        .ms-logo {
          flex-shrink: 0;
        }
      }
    }

    .or-divider {
      display: flex;
      align-items: center;
      text-align: center;
      margin: 16px 0;

      &::before, &::after {
        content: '';
        flex: 1;
        border-bottom: 1px solid #e2e8f0;
      }

      span {
        padding: 0 12px;
        font-size: 0.75rem;
        font-weight: 600;
        color: #94a3b8;
        letter-spacing: 0.05em;
      }
    }

    .local-disabled-banner {
      background: #f1f5f9;
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      padding: 12px;
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      gap: 6px;
      color: #334155;
      font-size: 0.85rem;

      mat-icon {
        color: #64748b;
      }

      .break-glass-link {
        font-size: 0.75rem;
        color: #2563eb;
        text-decoration: underline;
        margin-top: 4px;
      }
    }

    .break-glass-badge {
      background: #fef2f2;
      border: 1px solid #fecaca;
      border-radius: 6px;
      padding: 6px 10px;
      font-size: 0.8rem;
      font-weight: 600;
      color: #b91c1c;
      display: flex;
      align-items: center;
      gap: 6px;
      margin-bottom: 12px;

      mat-icon {
        font-size: 16px;
        width: 16px;
        height: 16px;
      }
    }

    .sso-loading-banner {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      border-radius: 8px;
      color: #1e40af;
      margin-bottom: 16px;
      font-size: 0.875rem;
    }

    .error-banner {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 16px;
      background-color: #fee2e2;
      border: 1px solid #fecaca;
      border-radius: 8px;
      color: #991b1b;
      margin-bottom: 16px;
      font-size: 0.875rem;

      mat-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
        flex-shrink: 0;
      }
    }

    .login-form {
      display: flex;
      flex-direction: column;
      gap: 4px;

      .full-width {
        width: 100%;
      }

      .submit-btn {
        height: 48px;
        font-size: 0.95rem;
        font-weight: 600;
        border-radius: 8px;
        margin-top: 8px;
        background-color: var(--csm-accent);
        color: #ffffff;

        &:hover:not([disabled]) {
          background-color: #ea580c;
        }

        &[disabled] {
          background-color: #e2e8f0;
          color: #94a3b8;
        }
      }

      .forgot-password-note {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        margin-top: 14px;
        font-size: 0.8rem;
        color: #64748b;

        mat-icon {
          font-size: 16px;
          width: 16px;
          height: 16px;
          color: #94a3b8;
        }
      }
    }

    .demo-accounts {
      margin-top: 24px;
      padding-top: 16px;
      border-top: 1px solid #e2e8f0;

      .demo-divider {
        text-align: center;
        margin-bottom: 12px;

        span {
          font-size: 0.7rem;
          font-weight: 700;
          color: #94a3b8;
          letter-spacing: 0.08em;
        }
      }

      .demo-buttons {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;

        .demo-btn {
          height: 38px;
          font-size: 0.75rem;
          font-weight: 600;
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;

          mat-icon {
            font-size: 16px;
            width: 16px;
            height: 16px;
            margin-right: 4px;
          }

          &.admin {
            border-color: #fca5a5;
            color: #b91c1c;
            &:hover { background: #fee2e2; }
          }
          &.mentor {
            border-color: #93c5fd;
            color: #1d4ed8;
            &:hover { background: #eff6ff; }
          }
          &.ase {
            border-color: #fed7aa;
            color: #c2410c;
            &:hover { background: #fff7ed; }
          }
        }
      }
    }

    .footer-note {
      text-align: center;
      margin-top: 16px;
      font-size: 0.75rem;
      color: #94a3b8;
    }
  `]
})
export class LoginComponent implements OnInit {
  loginForm: FormGroup;
  isLoading = signal(false);
  isProcessingSSO = signal(false);
  errorMessage = signal<string | null>(null);
  hidePassword = signal(true);
  allowLocalLogin = signal(true);
  showBreakGlass = signal(false);
  isProduction = signal(false);

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute
  ) {
    this.loginForm = this.fb.group({
      email: ['', [Validators.required, Validators.email, (c: AbstractControl): ValidationErrors | null => {
        const val = (c.value || '').trim().toLowerCase();
        if (!val) return null;
        if (!val.endsWith('@csm.tech')) {
          return { invalidDomain: true };
        }
        return null;
      }]],
      password: ['', Validators.required]
    });
  }

  ngOnInit(): void {
    // 1. Fetch SSO public configuration
    this.authService.getSsoConfig().subscribe({
      next: (config) => {
        this.allowLocalLogin.set(config.allow_local_login);
        if (config.app_env && config.app_env.toLowerCase() === 'production') {
          this.isProduction.set(true);
        }
      },
      error: () => {
        this.allowLocalLogin.set(true);
      }
    });

    // 2. Check for SSO callback query params
    const code = this.route.snapshot.queryParams['code'];
    const state = this.route.snapshot.queryParams['state'];
    const isMock = this.route.snapshot.queryParams['mock_sso'];

    if (code && state) {
      this.handleCallback(code, state);
    } else if (isMock && state) {
      this.handleCallback('mock-auth-code', state);
    }
  }

  signInWithMicrosoft(): void {
    this.isLoading.set(true);
    this.errorMessage.set(null);
    const redirectUri = window.location.origin + '/auth/sso/callback';

    this.authService.initiateSso(redirectUri).subscribe({
      next: (res) => {
        this.isLoading.set(false);
        if (res.authorization_url) {
          window.location.href = res.authorization_url;
        }
      },
      error: (err) => {
        this.isLoading.set(false);
        this.errorMessage.set(err.error?.detail || 'Failed to initiate Microsoft SSO. Please try again.');
      }
    });
  }

  handleCallback(code: string, state: string): void {
    this.isProcessingSSO.set(true);
    this.errorMessage.set(null);
    const redirectUri = window.location.origin + '/auth/sso/callback';

    this.authService.handleSsoCallback(code, state, redirectUri).subscribe({
      next: (res) => {
        this.isProcessingSSO.set(false);
        this.navigateToDashboard(res.role);
      },
      error: (err) => {
        this.isProcessingSSO.set(false);
        this.errorMessage.set(err.error?.detail || 'Authentication failed. Please contact your administrator.');
      }
    });
  }

  fillCredentials(role: 'admin' | 'mentor' | 'ase'): void {
    if (role === 'admin') {
      this.loginForm.patchValue({ email: 'admin.demo@csm.tech', password: 'Admin@123' });
    } else if (role === 'mentor') {
      this.loginForm.patchValue({ email: 'mentor.demo@csm.tech', password: 'Mentor@123' });
    } else if (role === 'ase') {
      this.loginForm.patchValue({ email: 'ase.demo@csm.tech', password: 'Ase@123' });
    }
    this.errorMessage.set(null);
  }

  onSubmit(): void {
    if (this.loginForm.invalid) return;

    this.isLoading.set(true);
    this.errorMessage.set(null);

    const val = this.loginForm.value;
    const payload = {
      email: (val.email || '').trim().toLowerCase(),
      password: val.password
    };

    this.authService.login(payload).subscribe({
      next: (res) => {
        this.isLoading.set(false);
        this.navigateToDashboard(res.role);
      },
      error: (err) => {
        this.isLoading.set(false);
        const detail = err.error?.detail || 'Login failed. Please verify your email and password.';
        this.errorMessage.set(detail);
      }
    });
  }

  private navigateToDashboard(role: string): void {
    if (role === 'ADMIN') {
      this.router.navigate(['/admin/dashboard']);
    } else if (role === 'MENTOR') {
      this.router.navigate(['/mentor/dashboard']);
    } else if (role === 'ASE') {
      this.router.navigate(['/ase/dashboard']);
    }
  }
}
