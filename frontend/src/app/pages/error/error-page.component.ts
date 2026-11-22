import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, ActivatedRoute } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-error-page',
  standalone: true,
  imports: [CommonModule, RouterModule, MatCardModule, MatButtonModule, MatIconModule],
  template: `
    <div class="error-wrapper">
      <mat-card class="error-card">
        <div class="icon-circle" [ngClass]="iconClass">
          <mat-icon>{{ iconName }}</mat-icon>
        </div>
        <h1 class="error-code">{{ errorCode }}</h1>
        <h2 class="error-title">{{ title }}</h2>
        <p class="error-desc">{{ description }}</p>

        <div class="action-buttons">
          <a mat-flat-button color="primary" routerLink="/">
            <mat-icon>home</mat-icon> Return Home
          </a>
          <button mat-stroked-button (click)="goBack()">
            <mat-icon>arrow_back</mat-icon> Go Back
          </button>
        </div>
      </mat-card>
    </div>
  `,
  styles: [`
    .error-wrapper {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--bg-main);
      padding: 24px;
    }

    .error-card {
      max-width: 480px;
      width: 100%;
      text-align: center;
      padding: 48px 32px;
      border-radius: 16px;
      border: 1px solid var(--border-light);
      box-shadow: 0 10px 25px -5px rgba(0,0,0,0.05);
      background: var(--bg-card);
    }

    .icon-circle {
      width: 80px;
      height: 80px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 20px;

      mat-icon {
        font-size: 40px;
        width: 40px;
        height: 40px;
      }

      &.icon-403 { background: #fee2e2; color: #dc2626; }
      &.icon-404 { background: #eff6ff; color: #2563eb; }
      &.icon-500 { background: #fef3c7; color: #d97706; }
    }

    .error-code {
      font-size: 3.5rem;
      font-weight: 800;
      color: var(--csm-primary);
      margin: 0 0 8px;
      letter-spacing: -0.03em;
    }

    .error-title {
      font-size: 1.4rem;
      font-weight: 700;
      color: var(--text-primary);
      margin: 0 0 12px;
    }

    .error-desc {
      font-size: 0.95rem;
      color: var(--text-secondary);
      line-height: 1.5;
      margin: 0 0 28px;
    }

    .action-buttons {
      display: flex;
      justify-content: center;
      gap: 16px;
      flex-wrap: wrap;

      button, a {
        border-radius: 8px;
        padding: 0 20px;
        height: 42px;
      }
    }
  `]
})
export class ErrorPageComponent implements OnInit {
  errorCode = '404';
  title = 'Page Not Found';
  description = "The page or resource you requested cannot be located. It may have been moved or doesn't exist.";
  iconName = 'search_off';
  iconClass = 'icon-404';

  constructor(private route: ActivatedRoute) {}

  ngOnInit(): void {
    const code = this.route.snapshot.data['code'] || this.route.snapshot.queryParams['code'] || '404';
    this.errorCode = String(code);

    if (this.errorCode === '403') {
      this.title = 'Access Forbidden';
      this.description = 'You do not have the required role or authorization to access this protected area.';
      this.iconName = 'gpp_bad';
      this.iconClass = 'icon-403';
    } else if (this.errorCode === '500') {
      this.title = 'Server Incident';
      this.description = 'An internal system error occurred while processing your request. Our engineering team has been notified.';
      this.iconName = 'error_outline';
      this.iconClass = 'icon-500';
    } else {
      this.title = 'Page Not Found';
      this.description = "The requested URL was not found on this server. Please check the address or return to your dashboard.";
      this.iconName = 'search_off';
      this.iconClass = 'icon-404';
    }
  }

  goBack(): void {
    window.history.back();
  }
}
