import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { Phase9Service } from '../../../core/services/phase9.service';
import { PublicVerifyResult } from '../../../core/models/phase9.model';

@Component({
  selector: 'app-certificate-verify',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="verify-page">
      <div class="verify-card">
        <div class="logo-area">
          <div class="brand-title">L&K SKILL HUB</div>
          <div class="brand-sub">Credential Verification System</div>
        </div>

        <div *ngIf="loading" class="state-loading">
          <div class="spinner"></div>
          <p>Verifying credential authenticity...</p>
        </div>

        <div *ngIf="!loading && errorMsg" class="state-invalid">
          <div class="status-icon invalid-icon">❌</div>
          <h2>Invalid or Unrecognized Certificate</h2>
          <p>{{ errorMsg }}</p>
          <div class="notice-box">
            Please ensure the verification URL matches the UUID provided on the physical or electronic credential.
          </div>
        </div>

        <div *ngIf="!loading && result && result.valid" class="state-valid">
          <div class="status-badge" [class.badge-revoked]="result.status === 'REVOKED'" [class.badge-verified]="result.status === 'ISSUED'">
            {{ result.status === 'REVOKED' ? '⚠️ CREDENTIAL REVOKED' : '✅ AUTHENTIC & VERIFIED' }}
          </div>

          <h2 class="course-title">{{ result.course_title }}</h2>
          <div class="cert-type-pill">{{ result.cert_type }}</div>

          <div class="details-grid">
            <div class="detail-row">
              <span class="detail-label">Recipient</span>
              <span class="detail-value highlight">{{ result.recipient_display_name }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Issue Date</span>
              <span class="detail-value">{{ result.issue_date }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Credential UUID</span>
              <span class="detail-value mono">{{ result.cert_uuid }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Issuing Authority</span>
              <span class="detail-value">L&K Skill Hub Certification Board</span>
            </div>
          </div>

          <div class="privacy-notice">
            🔒 <strong>Privacy Statement:</strong> This public verification record contains minimal disclosure (recipient first name and last initial, certification title, and issue date). No personal identifiable emails, internal IDs, or assessment score breakdowns are exposed on this public ledger.
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .verify-page {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #F1F5F9;
      padding: 24px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .verify-card {
      background: white;
      max-width: 580px;
      width: 100%;
      border-radius: 14px;
      border: 1px solid #E2E8F0;
      padding: 36px 32px;
      box-shadow: 0 8px 30px rgba(0, 0, 0, 0.06);
      text-align: center;
    }
    .logo-area {
      margin-bottom: 24px;
      border-bottom: 1px solid #F1F5F9;
      padding-bottom: 16px;
    }
    .brand-title {
      font-size: 20px;
      font-weight: 800;
      letter-spacing: 1.5px;
      color: var(--csm-primary);
    }
    .brand-sub {
      font-size: 12px;
      color: #64748B;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-top: 2px;
    }
    .state-loading {
      padding: 40px 0;
      color: #64748B;
    }
    .spinner {
      border: 4px solid #E2E8F0;
      border-top: 4px solid var(--csm-primary);
      border-radius: 50%;
      width: 40px;
      height: 40px;
      animation: spin 1s linear infinite;
      margin: 0 auto 16px auto;
    }
    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    .status-badge {
      display: inline-block;
      padding: 6px 16px;
      border-radius: 20px;
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.5px;
      margin-bottom: 16px;
    }
    .badge-verified {
      background: #DCFCE7;
      color: #166534;
      border: 1px solid #BBF7D0;
    }
    .badge-revoked {
      background: #FEE2E2;
      color: #991B1B;
      border: 1px solid #FECACA;
    }
    .course-title {
      font-size: 22px;
      font-weight: 700;
      color: #0F172A;
      margin: 0 0 8px 0;
    }
    .cert-type-pill {
      display: inline-block;
      background: #EFF6FF;
      color: var(--csm-primary);
      padding: 4px 10px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 600;
      margin-bottom: 24px;
      text-transform: uppercase;
    }
    .details-grid {
      background: #F8FAFC;
      border: 1px solid #E2E8F0;
      border-radius: 8px;
      padding: 16px 20px;
      margin-bottom: 24px;
      text-align: left;
    }
    .detail-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 10px 0;
      border-bottom: 1px solid #EDF2F7;
    }
    .detail-row:last-child {
      border-bottom: none;
    }
    .detail-label {
      font-size: 13px;
      color: #64748B;
    }
    .detail-value {
      font-size: 14px;
      color: #0F172A;
      font-weight: 600;
    }
    .detail-value.highlight {
      color: var(--csm-primary);
      font-size: 15px;
    }
    .detail-value.mono {
      font-family: monospace;
      font-size: 11px;
      color: #475569;
    }
    .privacy-notice {
      background: #F1F5F9;
      border-radius: 6px;
      padding: 12px 14px;
      font-size: 11px;
      color: #475569;
      line-height: 1.5;
      text-align: left;
    }
    .state-invalid {
      padding: 20px 0;
    }
    .invalid-icon {
      font-size: 40px;
      margin-bottom: 12px;
    }
    .notice-box {
      margin-top: 16px;
      background: #FEF2F2;
      border: 1px solid #FEE2E2;
      padding: 12px;
      border-radius: 6px;
      font-size: 12px;
      color: #991B1B;
    }
  `]
})
export class CertificateVerifyComponent implements OnInit {
  result: PublicVerifyResult | null = null;
  loading: boolean = true;
  errorMsg: string = '';

  constructor(
    private route: ActivatedRoute,
    private phase9Service: Phase9Service
  ) {}

  ngOnInit(): void {
    const certUuid = this.route.snapshot.paramMap.get('certUuid');
    if (!certUuid) {
      this.loading = false;
      this.errorMsg = 'No certificate identifier provided in request URL.';
      return;
    }

    this.phase9Service.verifyCertificatePublic(certUuid).subscribe({
      next: (data) => {
        this.result = data;
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.errorMsg = err.error?.detail || 'This certificate could not be verified or does not exist.';
      }
    });
  }
}
