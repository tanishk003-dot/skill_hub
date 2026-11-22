import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import * as faceapi from '@vladmandic/face-api';

export interface FaceDetectionFrame {
  hasFace: boolean;
  faceCount: number;
  lookingAway: boolean;
  isBlockedOrDark: boolean;
  confidence: number;
  box?: { x: number; y: number; width: number; height: number };
}

export interface CalibrationProgress {
  percentage: number;
  secondsRemaining: number;
  isFaceCentered: boolean;
  lightingGood: boolean;
  isStable: boolean;
  passed: boolean;
}

export interface CameraQualityMetrics {
  lightingLevel: 'TOO_DARK' | 'GOOD' | 'OVEREXPOSED';
  faceSize: 'TOO_FAR' | 'GOOD' | 'TOO_CLOSE' | 'NO_FACE';
  confidencePct: number;
  isCentered: boolean;
  tips: string[];
}

export interface CameraErrorDetail {
  type: 'PERMISSION_DENIED' | 'NOT_FOUND' | 'IN_USE' | 'UNSUPPORTED' | 'UNKNOWN';
  message: string;
  solutionGuide: string;
}

@Injectable({
  providedIn: 'root'
})
export class FaceTrackerService {
  private videoElement: HTMLVideoElement | null = null;
  private canvasElement: HTMLCanvasElement | null = null;
  private stream: MediaStream | null = null;
  private isTracking = false;
  private isProcessing = false;
  private lastDetectionTimestamp = 0;
  private isTabHidden = false;

  // Pretrained model state
  public usePretrainedModel = true;
  private modelsLoaded = false;
  private isModelLoading = false;

  // Modest target frame rate: 3-4 FPS (~280ms interval) to keep low-end laptops smooth
  private readonly DETECTION_INTERVAL_MS = 280;

  // Subjects
  private readonly detectionSubject = new BehaviorSubject<FaceDetectionFrame>({
    hasFace: false,
    faceCount: 0,
    lookingAway: false,
    isBlockedOrDark: false,
    confidence: 0
  });
  public readonly detection$: Observable<FaceDetectionFrame> = this.detectionSubject.asObservable();

  private readonly cameraActiveSubject = new BehaviorSubject<boolean>(false);
  public readonly cameraActive$: Observable<boolean> = this.cameraActiveSubject.asObservable();

  private readonly errorSubject = new BehaviorSubject<CameraErrorDetail | null>(null);
  public readonly error$: Observable<CameraErrorDetail | null> = this.errorSubject.asObservable();

  private readonly cameraQualitySubject = new BehaviorSubject<CameraQualityMetrics>({
    lightingLevel: 'GOOD',
    faceSize: 'NO_FACE',
    confidencePct: 0,
    isCentered: false,
    tips: ['Position yourself facing the camera.']
  });
  public readonly cameraQuality$: Observable<CameraQualityMetrics> = this.cameraQualitySubject.asObservable();

  // Calibration state
  private calibrationTimer: any = null;
  private calibrationSecondsElapsed = 0;
  private readonly calibrationSubject = new BehaviorSubject<CalibrationProgress>({
    percentage: 0,
    secondsRemaining: 10,
    isFaceCentered: false,
    lightingGood: false,
    isStable: false,
    passed: false
  });
  public readonly calibration$: Observable<CalibrationProgress> = this.calibrationSubject.asObservable();

  constructor() {
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', () => {
        this.isTabHidden = document.hidden;
      });
    }
  }

  /**
   * Loads genuine pretrained weights from local assets directory.
   * Zero external network calls at runtime.
   */
  async loadModels(): Promise<boolean> {
    if (this.modelsLoaded) return true;
    if (this.isModelLoading) return false;
    this.isModelLoading = true;

    try {
      const modelUri = '/assets/models/face-detector';
      await faceapi.nets.tinyFaceDetector.loadFromUri(modelUri);
      await faceapi.nets.faceLandmark68TinyNet.loadFromUri(modelUri);
      this.modelsLoaded = true;
      this.isModelLoading = false;
      return true;
    } catch (err) {
      console.warn('Face-api models failed to initialize from local assets, falling back to local heuristic tracker:', err);
      this.modelsLoaded = false;
      this.isModelLoading = false;
      return false;
    }
  }

  /**
   * Initializes local user media stream with constraints
   */
  async startCamera(videoElement: HTMLVideoElement): Promise<boolean> {
    this.stopCamera();
    this.videoElement = videoElement;
    this.errorSubject.next(null);

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      this.errorSubject.next({
        type: 'UNSUPPORTED',
        message: 'Your browser does not support webcam media access.',
        solutionGuide: 'Please use an updated version of Google Chrome, Microsoft Edge, or Mozilla Firefox.'
      });
      return false;
    }

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user'
        },
        audio: false
      });

      this.videoElement.srcObject = this.stream;
      await this.videoElement.play();

      // Listen for camera disconnect or revocation
      this.stream.getVideoTracks().forEach(track => {
        track.onended = () => {
          this.cameraActiveSubject.next(false);
          this.errorSubject.next({
            type: 'PERMISSION_DENIED',
            message: 'Webcam feed was disconnected or permission revoked.',
            solutionGuide: 'Please reconnect your camera and refresh the page to restore monitoring.'
          });
        };
      });

      this.cameraActiveSubject.next(true);

      // Trigger asynchronous model loading in background
      this.loadModels().catch(() => {});

      this.startFaceDetectionLoop();
      return true;
    } catch (err: any) {
      this.cameraActiveSubject.next(false);
      this.handleCameraError(err);
      return false;
    }
  }

  /**
   * Translates native browser getUserMedia DOMExceptions to structured guides
   */
  private handleCameraError(err: any): void {
    const name = err.name || '';
    if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
      this.errorSubject.next({
        type: 'PERMISSION_DENIED',
        message: 'Webcam access was denied by the browser.',
        solutionGuide:
          '1. Chrome/Edge: Click the camera/lock icon in the address bar -> toggle Camera to "Allow" -> Reload.\n' +
          '2. Firefox: Click the permissions icon next to the URL -> Clear block -> Reload.\n' +
          '3. Windows Settings: Settings > Privacy & security > Camera > Ensure "Camera access" & "Let desktop apps access your camera" are ON.'
      });
    } else if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
      this.errorSubject.next({
        type: 'NOT_FOUND',
        message: 'No video capture device detected.',
        solutionGuide: 'Check that your external webcam is securely plugged in or your laptop camera privacy shutter is open.'
      });
    } else if (name === 'NotReadableError' || name === 'TrackStartError') {
      this.errorSubject.next({
        type: 'IN_USE',
        message: 'Webcam is currently in use by another application.',
        solutionGuide: 'Close applications that may be occupying the camera (Microsoft Teams, Zoom, Skype, Discord, OBS, or another browser window).'
      });
    } else {
      this.errorSubject.next({
        type: 'UNKNOWN',
        message: err.message || 'Unable to access camera hardware.',
        solutionGuide: 'Please restart your browser or computer and try again.'
      });
    }
  }

  /**
   * Starts non-blocking, throttled real-time frame analysis loop.
   * Runs at modest 3-4 FPS and pauses when tab is hidden to ensure low CPU usage.
   */
  private startFaceDetectionLoop(): void {
    if (this.isTracking) return;
    this.isTracking = true;

    if (!this.canvasElement) {
      this.canvasElement = document.createElement('canvas');
      this.canvasElement.width = 160;
      this.canvasElement.height = 120;
    }

    const processTick = async () => {
      if (!this.isTracking) return;

      const now = performance.now();
      const elapsed = now - this.lastDetectionTimestamp;

      // Skip tick if tab is hidden, or if interval hasn't passed, or if previous run is still processing
      if (this.isTabHidden || elapsed < this.DETECTION_INTERVAL_MS || this.isProcessing) {
        if (this.isTracking) {
          setTimeout(processTick, 40);
        }
        return;
      }

      if (!this.videoElement || this.videoElement.paused || this.videoElement.ended || this.videoElement.readyState < 2) {
        if (this.isTracking) {
          setTimeout(processTick, 50);
        }
        return;
      }

      this.isProcessing = true;
      this.lastDetectionTimestamp = now;

      try {
        let frameResult: FaceDetectionFrame;

        if (this.usePretrainedModel && this.modelsLoaded) {
          frameResult = await this.detectWithPretrainedModel();
        } else {
          frameResult = this.detectWithLocalHeuristic();
        }

        this.detectionSubject.next(frameResult);
        this.updateQualityMetrics(frameResult);
      } catch (err) {
        // Fallback on error
        try {
          const fallbackResult = this.detectWithLocalHeuristic();
          this.detectionSubject.next(fallbackResult);
          this.updateQualityMetrics(fallbackResult);
        } catch {
          // ignore
        }
      } finally {
        this.isProcessing = false;
        if (this.isTracking) {
          setTimeout(processTick, 40);
        }
      }
    };

    setTimeout(processTick, 50);
  }

  /**
   * Real pretrained TinyFaceDetector + 68 Landmarks evaluation
   */
  private async detectWithPretrainedModel(): Promise<FaceDetectionFrame> {
    if (!this.videoElement) return this.detectWithLocalHeuristic();

    const brightness = this.measureAverageBrightness();
    const isBlockedOrDark = brightness < 18 || brightness > 248;

    if (isBlockedOrDark) {
      return {
        hasFace: false,
        faceCount: 0,
        lookingAway: false,
        isBlockedOrDark: true,
        confidence: 0
      };
    }

    const options = new faceapi.TinyFaceDetectorOptions({ inputSize: 160, scoreThreshold: 0.35 });
    const detections = await faceapi.detectAllFaces(this.videoElement, options).withFaceLandmarks(true);

    const faceCount = detections.length;
    if (faceCount === 0) {
      return {
        hasFace: false,
        faceCount: 0,
        lookingAway: false,
        isBlockedOrDark: false,
        confidence: 0.05
      };
    }

    // Pick dominant face
    const dominant = detections[0];
    const score = dominant.detection.score || 0.85;
    const box = dominant.detection.box;

    // Estimate head pose / turned away using landmark geometry
    let lookingAway = false;
    if (dominant.landmarks) {
      const positions = dominant.landmarks.positions;
      if (positions.length >= 31) {
        const jawLeft = positions[0];
        const jawRight = positions[16];
        const nose = positions[30];

        const distLeft = Math.abs(nose.x - jawLeft.x);
        const distRight = Math.abs(jawRight.x - nose.x);
        const totalSpan = distLeft + distRight;

        if (totalSpan > 0) {
          const ratio = distLeft / totalSpan;
          lookingAway = ratio < 0.28 || ratio > 0.72;
        }
      }
    }

    return {
      hasFace: true,
      faceCount,
      lookingAway,
      isBlockedOrDark: false,
      confidence: Math.round(score * 100) / 100,
      box: {
        x: box.x,
        y: box.y,
        width: box.width,
        height: box.height
      }
    };
  }

  /**
   * Measures brightness from a small canvas snapshot
   */
  private measureAverageBrightness(): number {
    if (!this.videoElement || !this.canvasElement) return 128;
    const ctx = this.canvasElement.getContext('2d', { willReadFrequently: true });
    if (!ctx) return 128;

    try {
      ctx.drawImage(this.videoElement, 0, 0, 80, 60);
      const data = ctx.getImageData(0, 0, 80, 60).data;
      let totalLuminance = 0;
      const count = data.length / 4;
      for (let i = 0; i < data.length; i += 8) {
        totalLuminance += 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
      }
      return totalLuminance / (count / 2);
    } catch {
      return 128;
    }
  }

  /**
   * Lightweight local skin-tone chrominance and spatial luminosity clustering fallback
   */
  private detectWithLocalHeuristic(): FaceDetectionFrame {
    if (!this.videoElement || !this.canvasElement) {
      return { hasFace: false, faceCount: 0, lookingAway: false, isBlockedOrDark: false, confidence: 0 };
    }
    const ctx = this.canvasElement.getContext('2d', { willReadFrequently: true });
    if (!ctx) return { hasFace: false, faceCount: 0, lookingAway: false, isBlockedOrDark: false, confidence: 0 };

    ctx.drawImage(this.videoElement, 0, 0, 160, 120);
    const imgData = ctx.getImageData(0, 0, 160, 120);
    const data = imgData.data;
    const width = imgData.width;
    const height = imgData.height;
    const totalPixels = width * height;

    let totalLuminance = 0;
    let skinPixelsCount = 0;
    let minX = width;
    let maxX = 0;
    let minY = height;
    let maxY = 0;

    for (let y = 0; y < height; y += 2) {
      for (let x = 0; x < width; x += 2) {
        const idx = (y * width + x) * 4;
        const r = data[idx];
        const g = data[idx + 1];
        const b = data[idx + 2];

        const lum = 0.299 * r + 0.587 * g + 0.114 * b;
        totalLuminance += lum;

        const maxVal = Math.max(r, g, b);
        const minVal = Math.min(r, g, b);
        const isSkin =
          r > 45 && g > 30 && b > 20 &&
          (maxVal - minVal) > 12 &&
          r > g && r > b &&
          Math.abs(r - g) > 8;

        if (isSkin) {
          skinPixelsCount++;
          if (x < minX) minX = x;
          if (x > maxX) maxX = x;
          if (y < minY) minY = y;
          if (y > maxY) maxY = y;
        }
      }
    }

    const sampledPixels = totalPixels / 4;
    const avgLuminance = totalLuminance / sampledPixels;
    const skinRatio = skinPixelsCount / sampledPixels;
    const isBlockedOrDark = avgLuminance < 18 || avgLuminance > 248;
    const hasFace = !isBlockedOrDark && skinRatio > 0.05 && skinRatio < 0.65;
    const faceSpanWidth = maxX - minX;
    const multipleFaces = hasFace && (skinRatio > 0.45 || faceSpanWidth > width * 0.88);
    const centroidX = (minX + maxX) / 2;
    const normalizedCentroidX = centroidX / width;
    const lookingAway = hasFace && (normalizedCentroidX < 0.24 || normalizedCentroidX > 0.76);

    return {
      hasFace,
      faceCount: multipleFaces ? 2 : (hasFace ? 1 : 0),
      lookingAway,
      isBlockedOrDark,
      confidence: hasFace ? Math.min(0.95, 0.5 + skinRatio) : 0.05,
      box: hasFace ? { x: minX, y: minY, width: maxX - minX, height: maxY - minY } : undefined
    };
  }

  /**
   * Updates quality check metrics for the "Camera Quality Check" view
   */
  private updateQualityMetrics(frame: FaceDetectionFrame): void {
    const brightness = this.measureAverageBrightness();
    let lightingLevel: 'TOO_DARK' | 'GOOD' | 'OVEREXPOSED' = 'GOOD';
    if (brightness < 40) lightingLevel = 'TOO_DARK';
    else if (brightness > 220) lightingLevel = 'OVEREXPOSED';

    let faceSize: 'TOO_FAR' | 'GOOD' | 'TOO_CLOSE' | 'NO_FACE' = 'NO_FACE';
    let isCentered = false;
    const tips: string[] = [];

    if (!frame.hasFace) {
      faceSize = 'NO_FACE';
      tips.push('No face detected. Sit facing the webcam in a well-lit area.');
    } else {
      const box = frame.box;
      if (box) {
        const heightRatio = box.height / 120;
        if (heightRatio < 0.22) {
          faceSize = 'TOO_FAR';
          tips.push('You appear too far from the camera. Move closer.');
        } else if (heightRatio > 0.80) {
          faceSize = 'TOO_CLOSE';
          tips.push('You are very close to the lens. Move back slightly.');
        } else {
          faceSize = 'GOOD';
        }

        const centerX = (box.x + box.width / 2) / 160;
        isCentered = centerX >= 0.30 && centerX <= 0.70;
        if (!isCentered) {
          tips.push('Center your face in the camera preview frame.');
        }
      }
    }

    if (lightingLevel === 'TOO_DARK') {
      tips.push('Room is too dark. Turn on a front-facing light or sit near a window.');
    } else if (lightingLevel === 'OVEREXPOSED') {
      tips.push('Harsh backlight detected. Avoid bright windows directly behind you.');
    }

    if (frame.faceCount > 1) {
      tips.push('Multiple faces detected. Ensure only you are in view of the camera.');
    }

    if (frame.lookingAway) {
      tips.push('Head turned away. Keep your focus on the screen.');
    }

    if (tips.length === 0) {
      tips.push('Camera setup and lighting are optimal!');
    }

    this.cameraQualitySubject.next({
      lightingLevel,
      faceSize,
      confidencePct: Math.round(frame.confidence * 100),
      isCentered,
      tips
    });
  }

  /**
   * Runs the 10-second calibration routine required before REQUIRED proctored exams
   */
  startCalibration(): void {
    this.calibrationSecondsElapsed = 0;
    if (this.calibrationTimer) clearInterval(this.calibrationTimer);

    let consecutiveGoodChecks = 0;

    this.calibrationTimer = setInterval(() => {
      this.calibrationSecondsElapsed += 1;
      const current = this.detectionSubject.value;

      const isCentered = current.hasFace && !current.lookingAway && current.faceCount === 1;
      const lightingGood = !current.isBlockedOrDark && current.confidence > 0.2;
      if (isCentered && lightingGood) consecutiveGoodChecks++;

      const percentage = Math.min(100, Math.round((this.calibrationSecondsElapsed / 10) * 100));
      const passed = this.calibrationSecondsElapsed >= 10 && consecutiveGoodChecks >= 7;

      this.calibrationSubject.next({
        percentage,
        secondsRemaining: Math.max(0, 10 - this.calibrationSecondsElapsed),
        isFaceCentered: isCentered,
        lightingGood,
        isStable: consecutiveGoodChecks >= 5,
        passed
      });

      if (this.calibrationSecondsElapsed >= 10) {
        clearInterval(this.calibrationTimer);
        this.calibrationTimer = null;
      }
    }, 1000);
  }

  /**
   * Captures a low-resolution compressed snapshot for verified violations (if snapshot enabled)
   */
  captureSnapshotBase64(): string | undefined {
    if (!this.videoElement || !this.canvasElement) return undefined;
    const ctx = this.canvasElement.getContext('2d');
    if (!ctx) return undefined;

    try {
      ctx.drawImage(this.videoElement, 0, 0, 160, 120);
      return this.canvasElement.toDataURL('image/jpeg', 0.6);
    } catch (e) {
      return undefined;
    }
  }

  /**
   * Clean resource teardown
   */
  stopCamera(): void {
    this.isTracking = false;
    this.isProcessing = false;
    if (this.calibrationTimer) {
      clearInterval(this.calibrationTimer);
      this.calibrationTimer = null;
    }
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    if (this.videoElement) {
      this.videoElement.srcObject = null;
    }
    this.cameraActiveSubject.next(false);
  }
}
