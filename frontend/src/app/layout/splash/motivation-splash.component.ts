import { Component, OnInit, OnDestroy, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { QuoteService } from '../../core/services/quote.service';
import { AuthService } from '../../core/services/auth.service';
import { DailyQuoteData } from '../../core/models/quote.model';

@Component({
  selector: 'app-motivation-splash',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div *ngIf="visible()" class="splash-overlay" role="dialog" aria-modal="true" aria-label="Daily Inspiration">
      <!-- Watermark Background: CSM Logo -->
      <div class="watermark-container">
        <img src="assets/csm-logo.png" alt="" class="csm-watermark" />
      </div>

      <!-- Backdrop overlay -->
      <div class="backdrop-tint"></div>

      <!-- Content Container -->
      <div class="splash-card">
        <div class="badge-role">
          <span class="role-pill">{{ quote()?.role }} INSPIRATION</span>
          <span class="date-text">{{ quote()?.date }}</span>
        </div>

        <div class="quote-content">
          <div class="quote-mark">“</div>
          <p class="quote-text">{{ quote()?.text }}</p>
          <div class="quote-author">— {{ quote()?.author }}</div>
        </div>

        <!-- 5-second Progress Bar -->
        <div class="auto-timer-bar">
          <div class="timer-fill" [style.animationDuration.ms]="timeoutMs"></div>
        </div>

        <!-- Actions -->
        <div class="actions-row">
          <button type="button" class="btn-skip" (click)="dismiss()">
            Skip
          </button>
          <button type="button" class="btn-continue" (click)="dismiss()">
            Continue ({{ remainingSeconds() }}s)
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .splash-overlay {
      position: fixed;
      inset: 0;
      z-index: 99999;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(15, 23, 42, 0.88);
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      animation: fadeIn 0.4s ease-out forwards;
      overflow: hidden;
      padding: 1.5rem;
    }

    .watermark-container {
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      pointer-events: none;
      overflow: hidden;
    }

    .csm-watermark {
      width: min(85vw, 680px);
      opacity: 0.08;
      filter: grayscale(100%) contrast(120%);
      transform: scale(1.05);
      user-select: none;
    }

    .backdrop-tint {
      position: absolute;
      inset: 0;
      background: radial-gradient(circle at center, transparent 30%, rgba(10, 15, 30, 0.6) 100%);
      pointer-events: none;
    }

    .splash-card {
      position: relative;
      z-index: 1;
      max-width: 680px;
      width: 100%;
      background: rgba(30, 41, 59, 0.95);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 1.25rem;
      padding: 2.5rem 2.25rem;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 0 40px rgba(30, 58, 138, 0.25);
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
      animation: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
      color: #F8FAFC;
    }

    :host-context(.light-mode) .splash-card {
      background: rgba(255, 255, 255, 0.98);
      border-color: rgba(0, 0, 0, 0.08);
      color: #0F172A;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.18);
    }

    .badge-role {
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      padding-bottom: 0.75rem;
    }

    :host-context(.light-mode) .badge-role {
      border-bottom-color: rgba(0, 0, 0, 0.08);
    }

    .role-pill {
      font-size: 0.75rem;
      font-weight: 700;
      letter-spacing: 0.06em;
      color: var(--csm-accent);
      background: var(--accent-light);
      border: 1px solid var(--accent-border);
      padding: 0.25rem 0.75rem;
      border-radius: 9999px;
    }

    .date-text {
      font-size: 0.8rem;
      color: var(--text-muted);
    }

    .quote-content {
      position: relative;
      text-align: center;
      padding: 1rem 0.5rem;
    }

    .quote-mark {
      font-size: 3.5rem;
      line-height: 1;
      font-family: Georgia, serif;
      color: var(--accent-border);
      margin-bottom: -1rem;
    }

    .quote-text {
      font-size: 1.35rem;
      line-height: 1.6;
      font-style: italic;
      font-weight: 400;
      margin: 0;
      color: var(--text-primary);
    }

    :host-context(.light-mode) .quote-text {
      color: var(--text-primary);
    }

    .quote-author {
      margin-top: 1.25rem;
      font-size: 1rem;
      font-weight: 600;
      color: var(--csm-accent);
      letter-spacing: 0.02em;
    }

    :host-context(.light-mode) .quote-author {
      color: var(--csm-primary);
    }

    .auto-timer-bar {
      width: 100%;
      height: 4px;
      background: rgba(255, 255, 255, 0.1);
      border-radius: 9999px;
      overflow: hidden;
    }

    .timer-fill {
      height: 100%;
      background: linear-gradient(90deg, var(--csm-primary), var(--csm-accent));
      width: 100%;
      animation: timerCountdown linear forwards;
    }

    .actions-row {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 1rem;
      margin-top: 0.5rem;
    }

    .btn-skip {
      background: transparent;
      border: 1px solid rgba(255, 255, 255, 0.2);
      color: #94A3B8;
      padding: 0.6rem 1.25rem;
      border-radius: 0.5rem;
      font-size: 0.9rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
    }

    .btn-skip:hover {
      background: rgba(255, 255, 255, 0.08);
      color: #F8FAFC;
    }

    :host-context(.light-mode) .btn-skip {
      border-color: rgba(0, 0, 0, 0.15);
      color: #64748B;
    }

    :host-context(.light-mode) .btn-skip:hover {
      background: rgba(0, 0, 0, 0.05);
      color: #0F172A;
    }

    .btn-continue {
      background: var(--csm-primary);
      border: 1px solid #2563EB;
      color: #FFFFFF;
      padding: 0.6rem 1.5rem;
      border-radius: 0.5rem;
      font-size: 0.9rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
      box-shadow: 0 4px 12px rgba(30, 58, 138, 0.35);
    }

    .btn-continue:hover {
      background: #2563EB;
      transform: translateY(-1px);
    }

    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    @keyframes slideUp {
      from { transform: translateY(20px); opacity: 0; }
      to { transform: translateY(0); opacity: 1; }
    }

    @keyframes timerCountdown {
      from { width: 100%; }
      to { width: 0%; }
    }

    /* Respect prefers-reduced-motion */
    @media (prefers-reduced-motion: reduce) {
      .splash-overlay, .splash-card, .timer-fill {
        animation: none !important;
        transition: none !important;
      }
    }
  `]
})
export class MotivationSplashComponent implements OnInit, OnDestroy {
  private quoteService = inject(QuoteService);
  private authService = inject(AuthService);
  private router = inject(Router);

  visible = signal<boolean>(false);
  quote = signal<DailyQuoteData | null>(null);
  remainingSeconds = signal<number>(5);
  timeoutMs = 5000;

  private dismissTimeout: any = null;
  private countdownInterval: any = null;

  ngOnInit(): void {
    this.checkAndDisplayQuote();
  }

  ngOnDestroy(): void {
    this.cleanupTimers();
  }

  checkAndDisplayQuote(): void {
    // If not authenticated or currently in an exam screen, do not show
    if (!this.authService.isAuthenticated()) return;
    if (this.router.url.includes('/ase/exam/')) return;

    this.quoteService.getDailyQuote().subscribe({
      next: (res) => {
        if (res.should_show_splash && res.quote) {
          this.quote.set(res.quote);
          this.timeoutMs = res.quote.dismiss_timeout_ms || 5000;
          this.remainingSeconds.set(Math.ceil(this.timeoutMs / 1000));
          this.visible.set(true);
          this.startCountdown();
        }
      },
      error: () => {
        // Silent failure if offline
      }
    });
  }

  startCountdown(): void {
    this.cleanupTimers();
    this.countdownInterval = setInterval(() => {
      const current = this.remainingSeconds();
      if (current > 1) {
        this.remainingSeconds.set(current - 1);
      }
    }, 1000);

    this.dismissTimeout = setTimeout(() => {
      this.dismiss();
    }, this.timeoutMs);
  }

  dismiss(): void {
    this.visible.set(false);
    this.cleanupTimers();
    this.quoteService.acknowledgeSplash().subscribe({
      error: () => {}
    });
  }

  private cleanupTimers(): void {
    if (this.dismissTimeout) {
      clearTimeout(this.dismissTimeout);
      this.dismissTimeout = null;
    }
    if (this.countdownInterval) {
      clearInterval(this.countdownInterval);
      this.countdownInterval = null;
    }
  }
}
