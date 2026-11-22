import { Component, OnInit, OnDestroy, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FaceTrackerService, FaceDetectionFrame, CalibrationProgress, CameraErrorDetail, CameraQualityMetrics } from '../../../core/services/face-tracker.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-camera-test',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <div class="min-h-screen bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100 p-6">
      <div class="max-w-5xl mx-auto space-y-6">

        <!-- Header -->
        <div class="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-4">
          <div>
            <div class="flex items-center space-x-3">
              <span class="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300">
                <svg class="w-6 h-6" width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                </svg>
              </span>
              <h1 class="text-2xl font-bold">System Check & Camera Calibration</h1>
            </div>
            <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Verify your webcam, room lighting, and face tracking alignment before starting your proctored assessment.
            </p>
          </div>
          <a routerLink="/ase/dashboard" class="px-4 py-2 text-sm font-medium rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 transition">
            Back to Dashboard
          </a>
        </div>

        <!-- Camera Testing Workspace -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">

          <!-- Left: Live Video Preview and Overlay -->
          <div class="lg:col-span-7 bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden flex flex-col">
            <div class="p-4 border-b border-slate-100 dark:border-slate-700/60 flex items-center justify-between bg-slate-50/50 dark:bg-slate-800/50">
              <span class="text-sm font-semibold flex items-center space-x-2">
                <span class="w-2.5 h-2.5 rounded-full" [ngClass]="isCameraActive ? 'bg-emerald-500 animate-pulse' : 'bg-red-400'"></span>
                <span>{{ isCameraActive ? 'Live Camera Feed' : 'Camera Disconnected' }}</span>
              </span>
              <span class="text-xs text-slate-500 dark:text-slate-400">Processed 100% locally in browser</span>
            </div>

            <!-- Video Container -->
            <div class="relative bg-black aspect-video flex items-center justify-center overflow-hidden">
              <video #videoElement autoplay playsinline muted class="w-full h-full object-cover -scale-x-100"></video>

              <!-- Camera inactive placeholder -->
              <div *ngIf="!isCameraActive" class="absolute inset-0 bg-slate-900/90 flex flex-col items-center justify-center p-6 text-center text-white">
                <svg class="w-12 h-12 text-slate-400 mb-3" width="48" height="48" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"/>
                </svg>
                <p class="font-medium text-slate-200">Camera is currently paused or inactive</p>
                <p class="text-xs text-slate-400 mt-1 max-w-sm">Click "Start Camera" below to grant browser permission and test your video feed.</p>
              </div>

              <!-- Alignment Guide Overlay -->
              <div *ngIf="isCameraActive" class="absolute inset-0 pointer-events-none flex items-center justify-center">
                <div class="w-48 h-64 border-2 border-dashed rounded-3xl transition-colors duration-300"
                  [ngClass]="{
                    'border-emerald-400 bg-emerald-500/5': detection.hasFace && !detection.lookingAway && detection.faceCount === 1,
                    'border-amber-400 bg-amber-500/5': detection.lookingAway,
                    'border-red-400 bg-red-500/10': !detection.hasFace || detection.faceCount > 1
                  }">
                </div>
              </div>

              <!-- Status Pill over video -->
              <div *ngIf="isCameraActive" class="absolute top-3 left-3 bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-full text-xs text-white flex items-center space-x-2">
                <span class="w-2 h-2 rounded-full" [ngClass]="getStatusPillColor()"></span>
                <span>{{ getStatusPillText() }}</span>
              </div>
            </div>

            <!-- Controls -->
            <div class="p-4 bg-slate-50 dark:bg-slate-800/70 border-t border-slate-100 dark:border-slate-700/60 flex flex-wrap items-center justify-between gap-3">
              <div class="flex items-center space-x-2">
                <button *ngIf="!isCameraActive" (click)="enableCamera()"
                  class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg text-sm shadow-sm transition">
                  Start Camera
                </button>
                <button *ngIf="isCameraActive" (click)="disableCamera()"
                  class="px-4 py-2 bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 font-medium rounded-lg text-sm transition">
                  Stop Camera
                </button>
                <button *ngIf="isCameraActive && !isCalibrating && !calibrationResult?.passed" (click)="runCalibration()"
                  class="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white font-medium rounded-lg text-sm shadow-sm transition">
                  Run 10s Calibration Test
                </button>
              </div>

              <div *ngIf="calibrationResult?.passed" class="text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center space-x-1">
                <svg class="w-4 h-4" width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                <span>Calibration Verified</span>
              </div>
            </div>
          </div>

          <!-- Right: Real-time Diagnostics & Checks -->
          <div class="lg:col-span-5 space-y-6">

            <!-- Real-time Diagnostics Card -->
            <div class="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-5 space-y-4">
              <h2 class="text-base font-bold flex items-center justify-between">
                <span>Real-Time Sensor Diagnostics</span>
                <span class="text-xs font-normal text-slate-400">Live Feedback</span>
              </h2>

              <div class="space-y-3">
                <!-- 1. Face Centered -->
                <div class="flex items-center justify-between p-3 rounded-xl bg-slate-50 dark:bg-slate-900/40 border border-slate-100 dark:border-slate-800">
                  <div class="flex items-center space-x-3">
                    <span class="w-2.5 h-2.5 rounded-full" [ngClass]="(detection.hasFace && !detection.lookingAway) ? 'bg-emerald-500' : 'bg-red-400'"></span>
                    <div>
                      <p class="text-sm font-medium">Face Centered & Visible</p>
                      <p class="text-xs text-slate-400">{{ (detection.hasFace && !detection.lookingAway) ? 'Aligned in target box' : 'Align face within guide' }}</p>
                    </div>
                  </div>
                  <span class="text-xs font-semibold px-2 py-1 rounded" [ngClass]="(detection.hasFace && !detection.lookingAway) ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300' : 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300'">
                    {{ (detection.hasFace && !detection.lookingAway) ? 'PASS' : 'ADJUST' }}
                  </span>
                </div>

                <!-- 2. Single Face Detection -->
                <div class="flex items-center justify-between p-3 rounded-xl bg-slate-50 dark:bg-slate-900/40 border border-slate-100 dark:border-slate-800">
                  <div class="flex items-center space-x-3">
                    <span class="w-2.5 h-2.5 rounded-full" [ngClass]="detection.faceCount === 1 ? 'bg-emerald-500' : 'bg-amber-400'"></span>
                    <div>
                      <p class="text-sm font-medium">Single Person in Frame</p>
                      <p class="text-xs text-slate-400">{{ detection.faceCount === 1 ? 'Single candidate confirmed' : (detection.faceCount > 1 ? 'Multiple faces detected' : 'No face found') }}</p>
                    </div>
                  </div>
                  <span class="text-xs font-semibold px-2 py-1 rounded" [ngClass]="detection.faceCount === 1 ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300' : 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300'">
                    {{ detection.faceCount === 1 ? 'PASS' : 'WARN' }}
                  </span>
                </div>

                <!-- 3. Room Lighting & Lens Status -->
                <div class="flex items-center justify-between p-3 rounded-xl bg-slate-50 dark:bg-slate-900/40 border border-slate-100 dark:border-slate-800">
                  <div class="flex items-center space-x-3">
                    <span class="w-2.5 h-2.5 rounded-full" [ngClass]="!detection.isBlockedOrDark ? 'bg-emerald-500' : 'bg-red-400'"></span>
                    <div>
                      <p class="text-sm font-medium">Lighting & Lens Clarity</p>
                      <p class="text-xs text-slate-400">{{ !detection.isBlockedOrDark ? 'Sufficient ambient lighting' : 'Room too dark or lens covered' }}</p>
                    </div>
                  </div>
                  <span class="text-xs font-semibold px-2 py-1 rounded" [ngClass]="!detection.isBlockedOrDark ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300' : 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300'">
                    {{ !detection.isBlockedOrDark ? 'PASS' : 'LOW LIGHT' }}
                  </span>
                </div>
              </div>

              <!-- Calibration progress bar -->
              <div *ngIf="isCalibrating" class="mt-4 p-4 rounded-xl bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 space-y-2">
                <div class="flex items-center justify-between text-xs font-semibold text-blue-900 dark:text-blue-200">
                  <span>10-Second Stability Calibration</span>
                  <span>{{ calibrationResult?.secondsRemaining }}s remaining ({{ calibrationResult?.percentage }}%)</span>
                </div>
                <div class="w-full bg-blue-200 dark:bg-blue-950 rounded-full h-2 overflow-hidden">
                  <div class="bg-blue-600 h-2 rounded-full transition-all duration-300" [style.width.%]="calibrationResult?.percentage || 0"></div>
                </div>
                <p class="text-xs text-blue-700 dark:text-blue-300">Keep looking directly at the screen during calibration.</p>
              </div>
            </div>

            <!-- Phase 11: Camera Quality Check Card -->
            <div class="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-5 space-y-4">
              <h2 class="text-base font-bold flex items-center justify-between text-slate-800 dark:text-slate-100">
                <span class="flex items-center space-x-2">
                  <svg class="w-5 h-5 text-indigo-500" width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                  <span>Camera Quality & Environment Check</span>
                </span>
                <span class="text-xs px-2.5 py-0.5 rounded-full font-mono font-medium"
                  [ngClass]="qualityMetrics.confidencePct >= 70 ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300' : 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'">
                  Confidence: {{ qualityMetrics.confidencePct }}%
                </span>
              </h2>

              <div class="grid grid-cols-2 gap-3 text-xs">
                <!-- Lighting -->
                <div class="p-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50">
                  <span class="text-slate-400 block mb-1">Room Lighting</span>
                  <span class="font-bold text-sm"
                    [ngClass]="{
                      'text-emerald-600 dark:text-emerald-400': qualityMetrics.lightingLevel === 'GOOD',
                      'text-red-500': qualityMetrics.lightingLevel === 'TOO_DARK',
                      'text-amber-500': qualityMetrics.lightingLevel === 'OVEREXPOSED'
                    }">
                    {{ qualityMetrics.lightingLevel }}
                  </span>
                </div>

                <!-- Face Size -->
                <div class="p-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50">
                  <span class="text-slate-400 block mb-1">Face Distance</span>
                  <span class="font-bold text-sm"
                    [ngClass]="{
                      'text-emerald-600 dark:text-emerald-400': qualityMetrics.faceSize === 'GOOD',
                      'text-amber-500': qualityMetrics.faceSize === 'TOO_FAR' || qualityMetrics.faceSize === 'TOO_CLOSE',
                      'text-red-500': qualityMetrics.faceSize === 'NO_FACE'
                    }">
                    {{ qualityMetrics.faceSize }}
                  </span>
                </div>
              </div>

              <!-- Actionable Tips -->
              <div *ngIf="qualityMetrics.tips.length > 0" class="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-700 space-y-1.5">
                <span class="text-xs font-semibold text-slate-700 dark:text-slate-300 block">Environmental Feedback:</span>
                <ul class="text-xs text-slate-600 dark:text-slate-400 list-disc list-inside space-y-1">
                  <li *ngFor="let tip of qualityMetrics.tips">{{ tip }}</li>
                </ul>
              </div>
            </div>

            <!-- Error Instructions Banner (if error occurred) -->
            <div *ngIf="cameraError" class="p-4 rounded-xl bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 space-y-2">
              <div class="flex items-center space-x-2 text-amber-900 dark:text-amber-200 font-semibold text-sm">
                <svg class="w-5 h-5 text-amber-600" width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
                <span>{{ cameraError.message }}</span>
              </div>
              <div class="text-xs text-amber-800 dark:text-amber-300 whitespace-pre-line font-mono bg-amber-100/50 dark:bg-amber-950/40 p-3 rounded-lg border border-amber-200/50 dark:border-amber-900/50">
                {{ cameraError.solutionGuide }}
              </div>
              <button (click)="enableCamera()" class="mt-2 text-xs font-medium px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg transition">
                Try Again
              </button>
            </div>

          </div>
        </div>

        <!-- Honest Limitations & Reasonable Accommodations Notice -->
        <div class="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-6 space-y-4">
          <div class="flex items-center space-x-2 text-slate-900 dark:text-slate-100 font-bold">
            <svg class="w-5 h-5 text-blue-600" width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            <h3 class="text-base font-semibold">Privacy Commitments & Honest Limitations</h3>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-slate-600 dark:text-slate-300">
            <div class="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-900/40 border border-slate-200/60 dark:border-slate-700/60 space-y-1.5">
              <p class="font-semibold text-slate-800 dark:text-slate-200">Zero Video Uploads</p>
              <p>Your continuous webcam stream never leaves your device. Face tracking happens 100% locally in your browser memory. Only timestamped compliance telemetry is transmitted.</p>
            </div>

            <div class="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-900/40 border border-slate-200/60 dark:border-slate-700/60 space-y-1.5">
              <p class="font-semibold text-slate-800 dark:text-slate-200">No Automated Disqualification</p>
              <p>A face detector cannot reliably tell a real face from a printed photo or screen. Camera events are signals for human review only, never an automatic penalty. All events are reviewed by your mentor or administrator.</p>
            </div>

            <div class="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-900/40 border border-slate-200/60 dark:border-slate-700/60 space-y-1.5">
              <p class="font-semibold text-slate-800 dark:text-slate-200">Hardware & Environmental Factors</p>
              <p>Strong window backlighting, external second monitors, reflective eyeglasses, or camera sensor auto-focus shifts can occasionally trigger temporary warnings. Position lights in front of you.</p>
            </div>

            <div class="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-900/40 border border-slate-200/60 dark:border-slate-700/60 space-y-1.5">
              <p class="font-semibold text-slate-800 dark:text-slate-200">Reasonable Accommodations</p>
              <p>Candidates with medical conditions, light sensitivity, or hardware constraints may submit an Accommodation Request or contact their mentor for a camera exemption or timer extension.</p>
            </div>
          </div>
        </div>

      </div>
    </div>
  `
})
export class CameraTestComponent implements OnInit, OnDestroy {
  @ViewChild('videoElement') videoElementRef!: ElementRef<HTMLVideoElement>;

  isCameraActive = false;
  isCalibrating = false;
  cameraError: CameraErrorDetail | null = null;
  detection: FaceDetectionFrame = {
    hasFace: false,
    faceCount: 0,
    lookingAway: false,
    isBlockedOrDark: false,
    confidence: 0
  };
  calibrationResult: CalibrationProgress | null = null;
  qualityMetrics: CameraQualityMetrics = {
    lightingLevel: 'GOOD',
    faceSize: 'NO_FACE',
    confidencePct: 0,
    isCentered: false,
    tips: []
  };

  private subs: Subscription[] = [];

  constructor(private faceTracker: FaceTrackerService) {}

  ngOnInit(): void {
    this.subs.push(
      this.faceTracker.cameraActive$.subscribe(active => (this.isCameraActive = active)),
      this.faceTracker.detection$.subscribe(det => (this.detection = det)),
      this.faceTracker.error$.subscribe(err => (this.cameraError = err)),
      this.faceTracker.cameraQuality$.subscribe(q => (this.qualityMetrics = q)),
      this.faceTracker.calibration$.subscribe(cal => {
        this.calibrationResult = cal;
        if (cal.passed || cal.secondsRemaining === 0) {
          this.isCalibrating = false;
        }
      })
    );
  }

  async enableCamera(): Promise<void> {
    if (this.videoElementRef && this.videoElementRef.nativeElement) {
      await this.faceTracker.startCamera(this.videoElementRef.nativeElement);
    }
  }

  disableCamera(): void {
    this.faceTracker.stopCamera();
    this.isCalibrating = false;
  }

  runCalibration(): void {
    if (!this.isCameraActive) return;
    this.isCalibrating = true;
    this.faceTracker.startCalibration();
  }

  getStatusPillColor(): string {
    if (!this.detection.hasFace || this.detection.isBlockedOrDark) return 'bg-red-500';
    if (this.detection.lookingAway || this.detection.faceCount > 1) return 'bg-amber-400';
    return 'bg-emerald-400';
  }

  getStatusPillText(): string {
    if (this.detection.isBlockedOrDark) return 'Camera Blocked / Dark';
    if (!this.detection.hasFace) return 'No Face in Frame';
    if (this.detection.faceCount > 1) return 'Multiple Faces';
    if (this.detection.lookingAway) return 'Looking Away';
    return 'Calibrated & Aligned';
  }

  ngOnDestroy(): void {
    this.subs.forEach(s => s.unsubscribe());
    this.faceTracker.stopCamera();
  }
}
