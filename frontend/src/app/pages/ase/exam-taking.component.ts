import { Component, OnInit, OnDestroy, signal, computed, inject, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatRadioModule } from '@angular/material/radio';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Subscription } from 'rxjs';

import { CodeQuestionEditorComponent } from './code-question-editor.component';
import { ExamService } from '../../core/services/exam.service';
import { ProctoringService } from '../../core/services/proctoring.service';
import { FaceTrackerService, FaceDetectionFrame, CalibrationProgress, CameraErrorDetail } from '../../core/services/face-tracker.service';
import { ExamStartData, SectionExamView, QuestionExamItem } from '../../core/models/assessment.model';

@Component({
  selector: 'app-ase-exam',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatRadioModule,
    MatCheckboxModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    CodeQuestionEditorComponent
  ],
  template: `
    <div class="exam-container">

      <!-- ================= PHASE 10: PRE-EXAM WEBCAM PROCTORING FLOW ================= -->
      @if (showWebcamPrecheck()) {
        <div class="webcam-precheck-card card-shadow">
          <div class="precheck-header">
            <div class="badge-row">
              <span class="badge badge-required">WEBCAM PROCTORING REQUIRED</span>
              <span *ngIf="isExemptOrOverridden()" class="badge badge-exempt">Accommodations / Override Active</span>
            </div>
            <h2>Proctored Assessment Setup & Consent</h2>
            <p class="subtitle">Please review the monitoring terms, grant camera access, and complete the 10-second calibration before beginning.</p>
          </div>

          <!-- Step 1: Consent & Disclosures -->
          @if (precheckStep() === 1) {
            <div class="precheck-body space-y-4">
              <div class="privacy-box">
                <h4><mat-icon>shield</mat-icon> Privacy Commitments & Honest Limitations</h4>
                <ul>
                  <li><strong>Local Processing:</strong> Face verification runs 100% locally in your browser memory. Your video stream is never uploaded or recorded to any server.</li>
                  <li><strong>What is Monitored:</strong> In-browser detection checks for prolonged absence, multiple people, or sustained head turns.</li>
                  <li><strong>Retention:</strong> Any temporary security telemetry is purged after 30 days and accessible strictly to assigned mentors and administrators.</li>
                  <li><strong>Human Review Signal:</strong> A face detector cannot reliably differentiate a real face from a printed photo or screen. Camera events are signals for human mentor review only, never an automatic penalty or disqualification.</li>
                </ul>
              </div>

              <div class="consent-agreement">
                <mat-checkbox [(ngModel)]="consentGiven" color="primary">
                  I understand and agree to the webcam proctoring terms for this session.
                </mat-checkbox>
              </div>

              <div class="precheck-actions">
                <a routerLink="/ase/my-assessments" mat-button class="cancel-btn">Back to Assessments</a>
                <button mat-flat-button color="primary" [disabled]="!consentGiven" (click)="proceedToCalibration()">
                  Continue to Camera Calibration <mat-icon>arrow_forward</mat-icon>
                </button>
              </div>
            </div>
          }

          <!-- Step 2: Camera Calibration & Live Check -->
          @if (precheckStep() === 2) {
            <div class="precheck-body">
              <div class="calibration-grid">
                <!-- Video Box -->
                <div class="cal-video-wrapper">
                  <video #precheckVideo autoplay playsinline muted class="cal-video"></video>
                  
                  <div class="cal-guide-box" [ngClass]="{
                    'border-good': calProgress()?.isFaceCentered,
                    'border-warn': !calProgress()?.isFaceCentered
                  }"></div>

                  @if (!isCameraActive()) {
                    <div class="video-overlay-inactive">
                      <mat-icon>videocam_off</mat-icon>
                      <p>Webcam is starting or inactive...</p>
                    </div>
                  }
                </div>

                <!-- Calibration Side Panel -->
                <div class="cal-info-panel">
                  <h3>10-Second Sensor Calibration</h3>
                  <p class="text-muted">Look straight ahead at your screen. Keep your head centered in the target outline.</p>

                  <!-- Progress -->
                  <div class="cal-progress-wrap">
                    <div class="progress-labels">
                      <span>Verification Progress</span>
                      <span>{{ calProgress()?.secondsRemaining }}s remaining ({{ calProgress()?.percentage }}%)</span>
                    </div>
                    <mat-progress-bar mode="determinate" [value]="calProgress()?.percentage || 0"></mat-progress-bar>
                  </div>

                  <!-- Checklist -->
                  <div class="cal-checklist">
                    <div class="check-item" [class.pass]="isCameraActive()">
                      <mat-icon>{{ isCameraActive() ? 'check_circle' : 'radio_button_unchecked' }}</mat-icon>
                      <span>Webcam feed active</span>
                    </div>
                    <div class="check-item" [class.pass]="calProgress()?.isFaceCentered">
                      <mat-icon>{{ calProgress()?.isFaceCentered ? 'check_circle' : 'radio_button_unchecked' }}</mat-icon>
                      <span>Face centered in frame</span>
                    </div>
                    <div class="check-item" [class.pass]="calProgress()?.lightingGood">
                      <mat-icon>{{ calProgress()?.lightingGood ? 'check_circle' : 'radio_button_unchecked' }}</mat-icon>
                      <span>Adequate lighting confirmed</span>
                    </div>
                  </div>

                  <!-- Error Banner if permission denied or error -->
                  @if (cameraError()) {
                    <div class="camera-error-banner">
                      <strong>{{ cameraError()?.message }}</strong>
                      <pre>{{ cameraError()?.solutionGuide }}</pre>
                      <button mat-stroked-button color="warn" (click)="retryCamera()">
                        <mat-icon>refresh</mat-icon> Try Again
                      </button>
                    </div>
                  }

                  <div class="cal-actions">
                    <button mat-button (click)="precheckStep.set(1)">Back</button>
                    <button mat-flat-button color="primary" class="start-exam-btn"
                      [disabled]="!calProgress()?.passed && !isExemptOrOverridden()"
                      (click)="startExamWithHandshake()">
                      <mat-icon>play_circle</mat-icon> Start Assessment
                    </button>
                  </div>
                </div>
              </div>
            </div>
          }
        </div>
      }

      <!-- ================= MAIN EXAM SCREEN ================= -->
      @else if (isLoading()) {
        <div class="loading-state">
          <mat-spinner diameter="40"></mat-spinner>
          <span>Initializing secure exam session...</span>
        </div>
      } @else if (examData()) {

        <!-- Mid-exam Camera Revoked / Blocked Overlay -->
        @if (isMidExamBlocked()) {
          <div class="blocking-overlay">
            <div class="blocking-card card-shadow animate-pulse">
              <mat-icon class="blocking-icon">videocam_off</mat-icon>
              <h2>Camera is Off or Obscured</h2>
              <p class="blocking-desc">
                Your webcam feed is disconnected or covered. Please uncover or re-enable your camera immediately to continue answering questions.
              </p>

              <div class="blocking-timer-box">
                <span class="grace-label">GRACE PERIOD REMAINING</span>
                <span class="grace-time">{{ gracePeriodRemaining() }}s</span>
                <span class="timer-warning-text">Assessment timer continues running. Questions are autosaved.</span>
              </div>

              <div class="blocking-actions">
                <button mat-flat-button color="primary" (click)="recheckCamera()">
                  <mat-icon>refresh</mat-icon> Reconnect Camera
                </button>
              </div>
            </div>
          </div>
        }

        <!-- Floating Live Proctoring Box in Top Corner -->
        @if (examData()?.webcam_mode === 'REQUIRED' || examData()?.webcam_mode === 'ADVISORY') {
          <div class="floating-webcam-card card-shadow">
            <video #examVideo autoplay playsinline muted class="floating-video"></video>
            <div class="floating-status">
              <span class="cam-dot" [ngClass]="getCamDotClass()"></span>
              <span class="cam-text">{{ getCamStatusText() }}</span>
            </div>
          </div>
        }

        <!-- Sticky Exam Topbar -->
        <header class="exam-topbar card-shadow">
          <div class="exam-meta">
            <div class="badge-row">
              <span class="badge badge-type">{{ examData()?.assessment_type }}</span>
              @if (examData()?.accommodation_applied) {
                <span class="badge badge-accommodation" title="Approved accommodations active">
                  <mat-icon class="icon-inline">verified_user</mat-icon> Standard Accommodations Active
                </span>
              }
              @if (examData()?.webcam_mode === 'REQUIRED') {
                <span class="badge badge-proctored">
                  <mat-icon class="icon-inline">videocam</mat-icon> Proctoring Active
                </span>
              }
            </div>
            <h2>{{ examData()?.assessment_title }}</h2>
          </div>

          <div class="exam-timers">
            <div class="timer-box" [ngClass]="{'timer-warning': remainingSeconds() < 300}">
              <mat-icon>timer</mat-icon>
              <div class="timer-text">
                <span class="timer-label">TOTAL TIME REMAINING</span>
                <span class="timer-val">{{ formatTime(remainingSeconds()) }}</span>
              </div>
            </div>

            <button mat-flat-button class="submit-btn" (click)="confirmManualSubmit()">
              <mat-icon>check_circle</mat-icon> Submit Exam
            </button>
          </div>

          <!-- Overall Exam Progress Bar -->
          <div class="overall-progress-bar-wrap">
            <div class="progress-bar-header">
              <span class="pb-title">Overall Exam Progress</span>
              <span class="pb-ratio">{{ getOverallAnsweredCount() }} / {{ getTotalQuestionCount() }} answered ({{ getOverallProgressPercentage() }}%)</span>
            </div>
            <mat-progress-bar mode="determinate" [value]="getOverallProgressPercentage()"></mat-progress-bar>
          </div>
        </header>

        <!-- Section Navigation Tabs -->
        <div class="section-tabs card-shadow">
          <div class="tabs-header">
            @for (sec of examData()?.sections; track sec.id; let sIdx = $index) {
              <button
                class="sec-tab-btn"
                [class.active]="currentSectionIndex() === sIdx"
                (click)="switchSection(sIdx)"
              >
                <span class="sec-pill">Section {{ sIdx + 1 }}</span>
                <span class="sec-title">{{ sec.title }}</span>
                <span class="sec-q-count">({{ sec.questions.length }} Qs)</span>
              </button>
            }
          </div>
        </div>

        <!-- Section Questions Content -->
        @if (currentSection()) {
          <div class="section-content">
            <div class="section-banner card-shadow">
              <div class="sec-banner-info">
                <h3>{{ currentSection()?.title }}</h3>
                <span class="sec-badge">
                  <mat-icon>schedule</mat-icon> Section Time: {{ currentSection()?.timer_minutes }} mins
                </span>
              </div>
              <div class="progress-wrap">
                <div class="progress-bar-header">
                  <span>Section Completion</span>
                  <span>{{ getAnsweredCountForSection() }} / {{ currentSection()?.questions?.length || 0 }}</span>
                </div>
                <mat-progress-bar mode="determinate" [value]="getSectionProgressPercentage()"></mat-progress-bar>
              </div>
            </div>

            <div class="questions-deck">
              @for (q of currentSection()?.questions; track q.id; let qIdx = $index) {
                <div class="question-card" [class.is-answered]="isAnswered(q.id)">
                  <div class="q-header">
                    <div class="q-label-group">
                      <span class="q-number">Q{{ qIdx + 1 }}.</span>
                      <span class="badge badge-skill">{{ q.skill_category }}</span>
                      @if (q.question_type === 'SINGLE_CHOICE') {
                        <span class="badge badge-single">Single Choice</span>
                      } @else if (q.question_type === 'MULTI_CHOICE') {
                        <span class="badge badge-multi">Multiple Choice (Select all that apply)</span>
                      } @else if (q.question_type === 'CODING') {
                        <span class="badge badge-coding">Coding Challenge</span>
                      }
                    </div>
                    <span class="q-marks">{{ q.marks }} {{ q.marks === 1 ? 'Mark' : 'Marks' }}</span>
                  </div>

                  <div class="q-body">
                    <p>{{ q.question_text }}</p>
                  </div>

                  @if (q.question_type === 'CODING') {
                    <app-code-question-editor
                      [question]="q"
                      [attemptId]="examData()?.attempt_id || 0"
                      (codeChanged)="onCodingAnswerChange(q.id, $event)"
                    ></app-code-question-editor>
                  } @else {
                    <div class="options-group">
                      @for (opt of q.options; track opt.id) {
                        <label
                          class="option-card"
                          [class.selected]="isOptionSelected(q.id, opt.id)"
                        >
                          @if (q.question_type === 'SINGLE_CHOICE') {
                            <input
                              type="radio"
                              [name]="'q_' + q.id"
                              [value]="opt.id"
                              [checked]="isOptionSelected(q.id, opt.id)"
                              (change)="onSingleChoiceChange(q.id, opt.id)"
                            />
                          } @else {
                            <input
                              type="checkbox"
                              [checked]="isOptionSelected(q.id, opt.id)"
                              (change)="onMultiChoiceChange(q.id, opt.id, $event)"
                            />
                          }
                          <span class="opt-text">{{ opt.text }}</span>
                        </label>
                      }
                    </div>
                  }

                  <div class="save-status">
                    @if (isAnswered(q.id)) {
                      <span class="saved-tag">
                        <mat-icon>check</mat-icon> Response Autosaved
                      </span>
                    }
                  </div>
                </div>
              }
            </div>

            <!-- Bottom Section Navigation Buttons -->
            <div class="bottom-controls">
              <button
                mat-stroked-button
                [disabled]="currentSectionIndex() === 0"
                (click)="switchSection(currentSectionIndex() - 1)"
              >
                <mat-icon>arrow_back</mat-icon> Previous Section
              </button>

              @if (currentSectionIndex() < (examData()?.sections?.length || 1) - 1) {
                <button
                  mat-flat-button
                  color="primary"
                  (click)="switchSection(currentSectionIndex() + 1)"
                >
                  Next Section <mat-icon>arrow_forward</mat-icon>
                </button>
              } @else {
                <button mat-flat-button class="submit-btn" (click)="confirmManualSubmit()">
                  <mat-icon>done_all</mat-icon> Complete & Submit
                </button>
              }
            </div>
          </div>
        }
      }
    </div>
  `,
  styles: [`
    .exam-container {
      max-width: 1100px;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      gap: 20px;
      padding-bottom: 60px;
    }

    /* WebCam Precheck Styles */
    .webcam-precheck-card {
      background: #ffffff;
      border-radius: 16px;
      padding: 32px;
      border: 1px solid #E2E8F0;
      margin-top: 20px;

      .precheck-header {
        border-bottom: 1px solid #F1F5F9;
        padding-bottom: 16px;
        margin-bottom: 24px;

        h2 {
          font-size: 1.5rem;
          font-weight: 800;
          color: #0F172A;
          margin: 8px 0 4px;
        }

        .subtitle {
          color: #64748B;
          font-size: 0.9rem;
          margin: 0;
        }
      }

      .privacy-box {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 20px;

        h4 {
          display: flex;
          align-items: center;
          gap: 8px;
          margin: 0 0 12px;
          color: var(--csm-primary);
          font-size: 0.95rem;
          font-weight: 700;
        }

        ul {
          margin: 0;
          padding-left: 20px;
          color: #334155;
          font-size: 0.85rem;
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
      }

      .consent-agreement {
        padding: 12px 0;
        font-weight: 600;
        color: #1E293B;
      }

      .precheck-actions {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-top: 16px;
        border-top: 1px solid #F1F5F9;
      }
    }

    .calibration-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;

      @media (max-width: 768px) {
        grid-template-columns: 1fr;
      }
    }

    .cal-video-wrapper {
      position: relative;
      background: #000;
      border-radius: 12px;
      aspect-ratio: 4/3;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;

      .cal-video {
        width: 100%;
        height: 100%;
        object-fit: cover;
        transform: scaleX(-1);
      }

      .cal-guide-box {
        position: absolute;
        width: 160px;
        height: 210px;
        border: 2px dashed #94A3B8;
        border-radius: 999px;
        pointer-events: none;
        transition: border-color 0.3s ease;

        &.border-good { border-color: #10B981; background: rgba(16, 185, 129, 0.05); }
        &.border-warn { border-color: #F59E0B; background: rgba(245, 158, 11, 0.05); }
      }

      .video-overlay-inactive {
        position: absolute;
        inset: 0;
        background: rgba(15, 23, 42, 0.9);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: #fff;
        gap: 8px;
        font-size: 0.85rem;
      }
    }

    .cal-info-panel {
      display: flex;
      flex-direction: column;
      gap: 16px;

      h3 { margin: 0; font-size: 1.15rem; font-weight: 700; color: #0F172A; }
      .text-muted { color: #64748B; font-size: 0.85rem; margin: 0; }
    }

    .cal-checklist {
      display: flex;
      flex-direction: column;
      gap: 8px;
      background: #F8FAFC;
      border-radius: 8px;
      padding: 12px;

      .check-item {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.85rem;
        color: #64748B;

        mat-icon { font-size: 18px; width: 18px; height: 18px; color: #94A3B8; }
        &.pass { color: #065F46; font-weight: 600; mat-icon { color: #10B981; } }
      }
    }

    .camera-error-banner {
      background: #FEF2F2;
      border: 1px solid #FCA5A5;
      border-radius: 8px;
      padding: 12px;
      color: #991B1B;
      font-size: 0.8rem;

      pre { font-family: inherit; margin: 6px 0 10px; white-space: pre-line; }
    }

    .cal-actions {
      margin-top: auto;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    /* Floating Corner Webcam Box */
    .floating-webcam-card {
      position: fixed;
      bottom: 24px;
      right: 24px;
      width: 180px;
      background: #000;
      border-radius: 12px;
      overflow: hidden;
      z-index: 1000;
      border: 2px solid #334155;
      box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3);

      .floating-video {
        width: 100%;
        height: 120px;
        object-fit: cover;
        transform: scaleX(-1);
      }

      .floating-status {
        background: rgba(15, 23, 42, 0.95);
        padding: 4px 8px;
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.7rem;
        color: #fff;
        font-weight: 600;

        .cam-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          &.dot-green { background: #10B981; }
          &.dot-yellow { background: #F59E0B; }
          &.dot-red { background: #EF4444; }
        }
      }
    }

    /* Mid-Exam Blocking Overlay */
    .blocking-overlay {
      position: fixed;
      inset: 0;
      background: rgba(15, 23, 42, 0.92);
      backdrop-filter: blur(8px);
      z-index: 9999;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }

    .blocking-card {
      background: #fff;
      border-radius: 16px;
      max-width: 460px;
      width: 100%;
      padding: 32px;
      text-align: center;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;

      .blocking-icon {
        font-size: 48px;
        width: 48px;
        height: 48px;
        color: #EF4444;
      }

      h2 { margin: 0; font-size: 1.35rem; font-weight: 800; color: #0F172A; }
      .blocking-desc { color: #64748B; font-size: 0.85rem; margin: 0; }

      .blocking-timer-box {
        background: #FEF2F2;
        border: 1px solid #FCA5A5;
        border-radius: 12px;
        padding: 16px;
        width: 100%;
        display: flex;
        flex-direction: column;
        gap: 4px;

        .grace-label { font-size: 0.65rem; font-weight: 700; color: #991B1B; letter-spacing: 0.05em; }
        .grace-time { font-size: 1.8rem; font-weight: 800; color: #DC2626; font-family: monospace; }
        .timer-warning-text { font-size: 0.72rem; color: #7F1D1D; }
      }
    }

    /* Standard Topbar & Question Styles */
    .exam-topbar {
      position: sticky;
      top: 0;
      z-index: 100;
      background: #ffffff;
      padding: 16px 28px;
      border-radius: 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;

      .badge-row {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
      }

      .exam-meta h2 {
        margin: 4px 0 0;
        font-size: 1.25rem;
        font-weight: 700;
        color: #0f172a;
      }

      .badge-type {
        background-color: #eff6ff;
        color: var(--csm-primary);
        font-size: 0.72rem;
        padding: 2px 8px;
        border-radius: 4px;
      }

      .badge-required { background: #fee2e2; color: #dc2626; font-size: 0.72rem; padding: 2px 8px; border-radius: 4px; font-weight: 700; }
      .badge-exempt { background: #ecfdf5; color: #047857; font-size: 0.72rem; padding: 2px 8px; border-radius: 4px; font-weight: 700; }
      .badge-accommodation { background: #ede9fe; color: #6d28d9; font-size: 0.72rem; padding: 2px 8px; border-radius: 4px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px; }
      .badge-proctored { background: #e0f2fe; color: #0284c7; font-size: 0.72rem; padding: 2px 8px; border-radius: 4px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px; }
      .icon-inline { font-size: 14px; width: 14px; height: 14px; }

      .exam-timers {
        display: flex;
        align-items: center;
        gap: 20px;

        .timer-box {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 8px 16px;
          border-radius: 10px;
          background: #eff6ff;
          border: 1px solid #bfdbfe;
          color: var(--csm-primary);

          mat-icon { font-size: 26px; width: 26px; height: 26px; }

          .timer-text {
            display: flex;
            flex-direction: column;
            .timer-label { font-size: 0.65rem; font-weight: 700; letter-spacing: 0.05em; color: #64748B; }
            .timer-val { font-size: 1.3rem; font-weight: 700; font-family: monospace; }
          }

          &.timer-warning {
            background: #fee2e2;
            border-color: #fca5a5;
            color: #dc2626;
            animation: pulse 1s infinite alternate;
          }
        }
      }
    }

    .section-tabs {
      background: #ffffff;
      padding: 6px 12px;
      border-radius: 12px;

      .tabs-header {
        display: flex;
        gap: 8px;
        overflow-x: auto;

        .sec-tab-btn {
          background: transparent;
          border: none;
          padding: 10px 16px;
          border-radius: 8px;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 0.88rem;
          color: #64748B;
          transition: all 0.2s ease;

          .sec-pill { font-size: 0.7rem; font-weight: 700; text-transform: uppercase; }
          .sec-title { font-weight: 600; }
          .sec-q-count { font-size: 0.78rem; opacity: 0.8; }

          &:hover { background: #f1f5f9; color: #0f172a; }
          &.active { background: #eff6ff; color: var(--csm-primary); font-weight: 700; }
        }
      }
    }

    .section-content { display: flex; flex-direction: column; gap: 20px; }

    .section-banner {
      background: #ffffff;
      padding: 18px 24px;
      border-radius: 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;

      .sec-banner-info h3 { margin: 0; font-size: 1.15rem; font-weight: 700; color: #0f172a; }
      .sec-badge { display: inline-flex; align-items: center; gap: 4px; font-size: 0.8rem; color: #64748B; margin-top: 4px; mat-icon { font-size: 16px; width: 16px; height: 16px; } }
      .progress-wrap { min-width: 260px; .progress-bar-header { display: flex; justify-content: space-between; font-size: 0.8rem; font-weight: 600; color: var(--csm-primary); margin-bottom: 4px; } }
    }

    .overall-progress-bar-wrap {
      width: 100%;
      margin-top: 8px;
      padding-top: 8px;
      border-top: 1px solid #E2E8F0;

      .progress-bar-header {
        display: flex;
        justify-content: space-between;
        font-size: 0.8rem;
        font-weight: 600;
        color: #64748B;
        margin-bottom: 4px;
        .pb-ratio { color: var(--csm-primary); font-weight: 700; }
      }
    }

    .questions-deck { display: flex; flex-direction: column; gap: 20px; }

    .question-card {
      background: #ffffff;
      padding: 24px;
      border-radius: 12px;
      border: 1px solid #E2E8F0;
      transition: all 0.2s ease;
      &.is-answered { border-left: 4px solid #10b981; }

      .q-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 14px;

        .q-label-group {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-wrap: wrap;

          .q-number { font-size: 0.95rem; font-weight: 700; color: var(--csm-primary); }
          .badge-skill { background-color: #f1f5f9; color: #475569; font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; }
          .badge-single { background-color: #eff6ff; color: #1d4ed8; font-size: 0.72rem; padding: 2px 6px; border-radius: 4px; }
          .badge-multi { background-color: #fff7ed; color: #c2410c; font-size: 0.72rem; padding: 2px 6px; border-radius: 4px; }
          .badge-coding { background-color: #f5f3ff; color: #6d28d9; font-size: 0.72rem; padding: 2px 6px; border-radius: 4px; }
        }

        .q-marks { font-size: 0.82rem; font-weight: 600; color: #64748B; }
      }

      .q-body { font-size: 1rem; font-weight: 500; color: #0f172a; line-height: 1.5; margin: 0 0 18px; }

      .options-group {
        display: flex;
        flex-direction: column;
        gap: 10px;

        .option-card {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 18px;
          border-radius: 8px;
          border: 1px solid #E2E8F0;
          background: #f8fafc;
          cursor: pointer;
          transition: all 0.15s ease;

          input { cursor: pointer; width: 18px; height: 18px; accent-color: var(--csm-primary); }
          .opt-text { font-size: 0.92rem; color: #1e293b; }
          &:hover { background: #eff6ff; border-color: #93c5fd; }
          &.selected { background: #eff6ff; border-color: var(--csm-primary); font-weight: 500; }
        }
      }

      .save-status {
        margin-top: 12px;
        min-height: 20px;
        .saved-tag { display: inline-flex; align-items: center; gap: 4px; font-size: 0.75rem; color: #059669; font-weight: 600; mat-icon { font-size: 14px; width: 14px; height: 14px; } }
      }
    }

    .bottom-controls { display: flex; justify-content: space-between; align-items: center; padding-top: 12px; }
    .loading-state { display: flex; flex-direction: column; align-items: center; padding: 80px 0; color: #64748B; gap: 16px; }

    /* Mobile Responsive for 360px phone screens */
    @media (max-width: 600px) {
      .exam-topbar {
        padding: 10px 12px;
        flex-direction: column;
        align-items: stretch;
        gap: 10px;

        .exam-meta h2 {
          font-size: 1.05rem;
        }

        .exam-timers {
          justify-content: space-between;
          width: 100%;
          gap: 8px;

          .timer-box {
            padding: 6px 10px;
            .timer-val { font-size: 1.1rem; }
            .timer-label { font-size: 0.6rem; }
          }

          .submit-btn {
            font-size: 0.82rem;
            padding: 0 12px;
            height: 36px;
          }
        }
      }

      .floating-webcam-card {
        width: 110px;
        bottom: 12px;
        right: 12px;

        .floating-video {
          height: 75px;
        }
      }

      .section-tabs .tabs-header {
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
      }

      .question-card {
        padding: 14px;

        .options-group .option-card {
          padding: 10px 12px;
        }
      }

      .section-banner {
        padding: 12px 14px;
        flex-direction: column;
        align-items: stretch;

        .progress-wrap {
          min-width: 100%;
        }
      }
    }
  `]
})
export class AseExamComponent implements OnInit, OnDestroy {
  @ViewChild('precheckVideo') precheckVideoRef!: ElementRef<HTMLVideoElement>;
  @ViewChild('examVideo') examVideoRef!: ElementRef<HTMLVideoElement>;

  examData = signal<ExamStartData | null>(null);
  isLoading = signal(true);
  currentSectionIndex = signal(0);
  remainingSeconds = signal(0);
  selectedAnswers = signal<{ [questionId: number]: string[] }>({});

  // Phase 10 State
  showWebcamPrecheck = signal(false);
  precheckStep = signal<1 | 2>(1);
  consentGiven = false;
  isExemptOrOverridden = signal(false);
  isCameraActive = signal(false);
  cameraError = signal<CameraErrorDetail | null>(null);
  calProgress = signal<CalibrationProgress | null>(null);
  detectionFrame = signal<FaceDetectionFrame | null>(null);

  // Mid-exam proctoring state
  isMidExamBlocked = signal(false);
  gracePeriodRemaining = signal(30);

  private assignmentId = 0;
  private handshakeToken: string | null = null;
  private timerInterval: any = null;
  private heartbeatInterval: any = null;
  private graceInterval: any = null;
  private subs: Subscription[] = [];

  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private examService = inject(ExamService);
  private proctoringService = inject(ProctoringService);
  private faceTracker = inject(FaceTrackerService);
  private snackBar = inject(MatSnackBar);

  currentSection = computed(() => {
    const data = this.examData();
    if (!data || !data.sections) return null;
    return data.sections[this.currentSectionIndex()] || null;
  });

  ngOnInit(): void {
    this.assignmentId = Number(this.route.snapshot.paramMap.get('assignmentId'));
    if (this.assignmentId) {
      this.setupSubscriptions();
      this.checkAssessmentRequirements();
    }
  }

  ngOnDestroy(): void {
    this.cleanupTimers();
    this.subs.forEach(s => s.unsubscribe());
    this.faceTracker.stopCamera();
  }

  private setupSubscriptions(): void {
    this.subs.push(
      this.faceTracker.cameraActive$.subscribe(active => {
        this.isCameraActive.set(active);
        if (this.examData() && !active && (this.examData()?.webcam_mode === 'REQUIRED')) {
          this.triggerMidExamBlock('CAMERA_REVOKED');
        }
      }),
      this.faceTracker.error$.subscribe(err => this.cameraError.set(err)),
      this.faceTracker.calibration$.subscribe(cal => this.calProgress.set(cal)),
      this.faceTracker.detection$.subscribe(det => {
        this.detectionFrame.set(det);
        if (this.examData() && this.examData()?.webcam_mode === 'REQUIRED') {
          this.evaluateDetectionInExam(det);
        }
      })
    );
  }

  private checkAssessmentRequirements(): void {
    this.isLoading.set(true);

    // Initial check: attempt start or resume
    this.examService.startOrResumeExam(this.assignmentId).subscribe({
      next: (res) => {
        // Exam started directly (e.g. exempt, overridden, or OFF/ADVISORY already in progress)
        this.onExamLoaded(res);
      },
      error: (err) => {
        if (err.status === 403 && (err.error?.detail?.includes('Webcam') || err.error?.detail?.includes('handshake'))) {
          // Assessment requires Webcam Proctoring handshake!
          this.isLoading.set(false);
          this.showWebcamPrecheck.set(true);
        } else {
          this.isLoading.set(false);
          const detail = err.error?.detail || 'Unable to start assessment.';
          this.snackBar.open(detail, 'Close', { duration: 5000, panelClass: ['snack-error'] });
          this.router.navigate(['/ase/my-assessments']);
        }
      }
    });
  }

  proceedToCalibration(): void {
    this.precheckStep.set(2);
    // Record consent
    this.proctoringService.submitConsent(this.assignmentId, true).subscribe({
      next: () => {
        setTimeout(() => this.startPrecheckCamera(), 100);
      },
      error: () => {
        setTimeout(() => this.startPrecheckCamera(), 100);
      }
    });
  }

  async startPrecheckCamera(): Promise<void> {
    if (this.precheckVideoRef && this.precheckVideoRef.nativeElement) {
      const ok = await this.faceTracker.startCamera(this.precheckVideoRef.nativeElement);
      if (ok) {
        this.faceTracker.startCalibration();
      }
    }
  }

  retryCamera(): void {
    this.startPrecheckCamera();
  }

  startExamWithHandshake(): void {
    this.isLoading.set(true);
    this.showWebcamPrecheck.set(false);

    // Request short-lived handshake token
    this.proctoringService.requestHandshake(this.assignmentId).subscribe({
      next: (hs) => {
        this.handshakeToken = hs.handshake_token;
        this.examService.startOrResumeExam(this.assignmentId, this.handshakeToken).subscribe({
          next: (res) => {
            this.onExamLoaded(res);
            // Connect camera to corner floating box
            setTimeout(() => this.connectExamVideoBox(), 300);
          },
          error: (err) => {
            this.isLoading.set(false);
            const detail = err.error?.detail || 'Failed to start exam after camera handshake.';
            this.snackBar.open(detail, 'Close', { duration: 5000, panelClass: ['snack-error'] });
            this.router.navigate(['/ase/my-assessments']);
          }
        });
      },
      error: (err) => {
        this.isLoading.set(false);
        this.showWebcamPrecheck.set(true);
        this.snackBar.open(err.error?.detail || 'Handshake failed', 'Close', { duration: 5000 });
      }
    });
  }

  private onExamLoaded(res: ExamStartData): void {
    this.examData.set(res);
    this.remainingSeconds.set(res.remaining_total_seconds);
    this.selectedAnswers.set({ ...res.saved_responses });
    this.isLoading.set(false);
    this.startTimer();
    this.startHeartbeatLoop();
  }

  private async connectExamVideoBox(): Promise<void> {
    if (this.examVideoRef && this.examVideoRef.nativeElement) {
      await this.faceTracker.startCamera(this.examVideoRef.nativeElement);
    }
  }

  private startHeartbeatLoop(): void {
    if (this.heartbeatInterval) clearInterval(this.heartbeatInterval);

    this.heartbeatInterval = setInterval(() => {
      const attemptId = this.examData()?.attempt_id;
      if (!attemptId) return;

      const currentStatus = this.isCameraActive() ? 'ACTIVE' : 'BLOCKED';
      this.proctoringService.sendHeartbeat(attemptId, currentStatus, 'Client heartbeat').subscribe({
        next: (hb) => {
          if (hb.remaining_seconds) {
            // Keep timer synchronized with server authority clock
            this.remainingSeconds.set(hb.remaining_seconds);
          }
        },
        error: () => {}
      });
    }, 12000);
  }

  private evaluateDetectionInExam(det: FaceDetectionFrame): void {
    if (!this.examData() || this.isMidExamBlocked()) return;

    if (det.isBlockedOrDark) {
      this.triggerMidExamBlock('CAMERA_BLOCKED');
    }
  }

  private triggerMidExamBlock(eventType: string): void {
    if (this.isMidExamBlocked()) return;
    this.isMidExamBlocked.set(true);

    const grace = this.examData()?.camera_grace_period_seconds || 30;
    this.gracePeriodRemaining.set(grace);

    if (this.graceInterval) clearInterval(this.graceInterval);
    this.graceInterval = setInterval(() => {
      const cur = this.gracePeriodRemaining();
      if (cur <= 1) {
        clearInterval(this.graceInterval);
        this.gracePeriodRemaining.set(0);
        this.reportGracePeriodViolation(eventType);
      } else {
        this.gracePeriodRemaining.set(cur - 1);
      }
    }, 1000);
  }

  private reportGracePeriodViolation(eventType: string): void {
    const attemptId = this.examData()?.attempt_id;
    if (!attemptId) return;

    const snapshot = this.faceTracker.captureSnapshotBase64();
    this.proctoringService.reportCameraEvent({
      attempt_id: attemptId,
      event_type: eventType,
      duration_seconds: this.examData()?.camera_grace_period_seconds || 30,
      snapshot_base64: snapshot,
      is_warning: false
    }).subscribe({
      next: (res) => {
        if (res.auto_submitted) {
          this.snackBar.open('Assessment auto-submitted due to security violation.', 'OK', { duration: 5000 });
          this.router.navigate([`/ase/result/${attemptId}`]);
        }
      }
    });
  }

  recheckCamera(): void {
    this.connectExamVideoBox().then(() => {
      if (this.isCameraActive()) {
        this.isMidExamBlocked.set(false);
        if (this.graceInterval) clearInterval(this.graceInterval);
      }
    });
  }

  getCamDotClass(): string {
    const det = this.detectionFrame();
    if (!this.isCameraActive() || !det || det.isBlockedOrDark || !det.hasFace) return 'dot-red';
    if (det.lookingAway || det.faceCount > 1) return 'dot-yellow';
    return 'dot-green';
  }

  getCamStatusText(): string {
    const det = this.detectionFrame();
    if (!this.isCameraActive()) return 'Camera Inactive';
    if (!det || det.isBlockedOrDark) return 'Feed Blocked';
    if (!det.hasFace) return 'No Face Detected';
    if (det.faceCount > 1) return 'Multiple Faces';
    if (det.lookingAway) return 'Face Off-Center';
    return 'Proctoring OK';
  }

  startTimer(): void {
    if (this.timerInterval) clearInterval(this.timerInterval);

    this.timerInterval = setInterval(() => {
      const cur = this.remainingSeconds();
      if (cur <= 1) {
        clearInterval(this.timerInterval);
        this.remainingSeconds.set(0);
        this.onTimeoutSubmit();
      } else {
        this.remainingSeconds.set(cur - 1);
      }
    }, 1000);
  }

  private cleanupTimers(): void {
    if (this.timerInterval) clearInterval(this.timerInterval);
    if (this.heartbeatInterval) clearInterval(this.heartbeatInterval);
    if (this.graceInterval) clearInterval(this.graceInterval);
  }

  formatTime(totalSec: number): string {
    const m = Math.floor(totalSec / 60);
    const s = totalSec % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }

  switchSection(index: number): void {
    this.currentSectionIndex.set(index);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  isAnswered(questionId: number): boolean {
    const arr = this.selectedAnswers()[questionId];
    return !!arr && arr.length > 0;
  }

  isOptionSelected(questionId: number, optionId: string): boolean {
    const arr = this.selectedAnswers()[questionId] || [];
    return arr.includes(optionId);
  }

  getAnsweredCountForSection(): number {
    const sec = this.currentSection();
    if (!sec) return 0;
    return sec.questions.filter(q => this.isAnswered(q.id)).length;
  }

  getTotalQuestionCount(): number {
    return this.examData()?.sections?.reduce((acc, s) => acc + s.questions.length, 0) || 0;
  }

  getOverallAnsweredCount(): number {
    return Object.values(this.selectedAnswers()).filter(a => a && a.length > 0).length;
  }

  getOverallProgressPercentage(): number {
    const total = this.getTotalQuestionCount();
    if (total === 0) return 0;
    return Math.round((this.getOverallAnsweredCount() / total) * 100);
  }

  getSectionProgressPercentage(): number {
    const sec = this.currentSection();
    if (!sec || !sec.questions || sec.questions.length === 0) return 0;
    return Math.round((this.getAnsweredCountForSection() / sec.questions.length) * 100);
  }

  onCodingAnswerChange(questionId: number, event: { code: string; language: string }): void {
    const updated = { ...this.selectedAnswers() };
    updated[questionId] = [event.code];
    this.selectedAnswers.set(updated);
  }

  onSingleChoiceChange(questionId: number, optionId: string): void {
    const updated = { ...this.selectedAnswers() };
    updated[questionId] = [optionId];
    this.selectedAnswers.set(updated);
    this.triggerAutosave(questionId, [optionId]);
  }

  onMultiChoiceChange(questionId: number, optionId: string, event: Event): void {
    const isChecked = (event.target as HTMLInputElement).checked;
    const currentList = this.selectedAnswers()[questionId] || [];
    let updatedList: string[];

    if (isChecked) {
      updatedList = [...currentList, optionId];
    } else {
      updatedList = currentList.filter(id => id !== optionId);
    }

    const updated = { ...this.selectedAnswers() };
    updated[questionId] = updatedList;
    this.selectedAnswers.set(updated);
    this.triggerAutosave(questionId, updatedList);
  }

  triggerAutosave(questionId: number, selectedOptions: string[]): void {
    const attemptId = this.examData()?.attempt_id;
    if (!attemptId) return;

    this.examService.autosave(attemptId, questionId, selectedOptions).subscribe({
      next: () => {},
      error: (err) => {
        if (err.status === 400 && err.error?.detail?.includes('auto-submitted')) {
          this.router.navigate([`/ase/result/${attemptId}`]);
        }
      }
    });
  }

  confirmManualSubmit(): void {
    const totalQ = this.examData()?.sections.reduce((acc, s) => acc + s.questions.length, 0) || 0;
    const answeredQ = Object.values(this.selectedAnswers()).filter(a => a && a.length > 0).length;

    const msg = `Submit Assessment? You have answered ${answeredQ} out of ${totalQ} questions. Each ASE is allowed only 1 attempt.`;
    if (confirm(msg)) {
      this.doSubmit();
    }
  }

  onTimeoutSubmit(): void {
    this.snackBar.open('Assessment timer expired! Submitting your answers...', 'OK', {
      duration: 3000,
      panelClass: ['snack-error']
    });
    this.doSubmit();
  }

  private doSubmit(): void {
    const attemptId = this.examData()?.attempt_id;
    if (!attemptId) return;

    this.cleanupTimers();

    this.examService.submitExam(attemptId).subscribe({
      next: (result) => {
        this.router.navigate([`/ase/result/${result.attempt_id}`]);
      },
      error: () => {
        this.router.navigate([`/ase/result/${attemptId}`]);
      }
    });
  }
}
