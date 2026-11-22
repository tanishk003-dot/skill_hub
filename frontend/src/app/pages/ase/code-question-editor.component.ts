import {
  Component,
  Input,
  Output,
  EventEmitter,
  OnInit,
  OnDestroy,
  ElementRef,
  ViewChild,
  inject,
  signal
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CodingService } from '../../core/services/coding.service';
import { QuestionExamItem } from '../../core/models/assessment.model';
import {
  TestCaseResult,
  CodingRunResponse,
  CodingSubmitResponse
} from '../../core/models/coding.model';

declare const window: any;

@Component({
  selector: 'app-code-question-editor',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="coding-container">
      <!-- Top Action Bar -->
      <div class="editor-header">
        <div class="header-left">
          <label class="lang-label">Language:</label>
          <select [(ngModel)]="selectedLanguage" (change)="onLanguageChange()" class="lang-select">
            <option *ngFor="let lang of allowedLanguages" [value]="lang">
              {{ formatLanguageName(lang) }}
            </option>
          </select>
          <button type="button" class="btn-reset" (click)="resetStarterCode()" title="Reset to Starter Code">
            ↺ Reset Code
          </button>
        </div>

        <div class="header-right">
          <span *ngIf="runsRemaining() !== null" class="rate-limit-pill">
            Runs Left: <strong>{{ runsRemaining() }}</strong>
          </span>
          <span *ngIf="isAutosaving()" class="autosave-pill">
            Autosaving...
          </span>
          <button type="button" class="btn-run" [disabled]="isRunning() || isSubmitting()" (click)="runCode()">
            <span *ngIf="!isRunning()">▶ Run Sample Tests</span>
            <span *ngIf="isRunning()">Running...</span>
          </button>
          <button type="button" class="btn-submit-code" [disabled]="isRunning() || isSubmitting()" (click)="submitCode()">
            <span *ngIf="!isSubmitting()">✓ Submit Solution</span>
            <span *ngIf="isSubmitting()">Evaluating...</span>
          </button>
        </div>
      </div>

      <!-- Problem Statement & Editor Layout -->
      <div class="main-editor-split">
        <!-- Problem Statement Panel -->
        <div class="problem-panel">
          <div class="problem-title">{{ question.question_text }}</div>
          <div class="problem-meta">
            <span class="meta-pill">Marks: {{ question.marks }}</span>
            <span class="meta-pill">Time Limit: {{ question.time_limit_sec || 2.0 }}s</span>
            <span class="meta-pill">Memory Limit: {{ question.memory_limit_mb || 256 }}MB</span>
          </div>

          <div class="problem-description" [innerHTML]="formatMarkdown(question.problem_statement || question.question_text)"></div>

          <!-- Sample Test Cases Preview -->
          <div *ngIf="question.sample_test_cases && question.sample_test_cases.length > 0" class="sample-cases-section">
            <h4 class="cases-heading">Sample Test Cases</h4>
            <div *ngFor="let sc of question.sample_test_cases; let idx = index" class="sample-case-box">
              <div class="case-header">Sample #{{ idx + 1 }}</div>
              <div class="case-io">
                <div class="io-block">
                  <span class="io-label">Input:</span>
                  <pre class="io-code">{{ sc.input }}</pre>
                </div>
                <div class="io-block">
                  <span class="io-label">Expected Output:</span>
                  <pre class="io-code">{{ sc.expected_output }}</pre>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Monaco Editor Panel -->
        <div class="editor-pane">
          <div #monacoContainer class="monaco-container"></div>
          <!-- Fallback textarea if Monaco is initializing or disabled -->
          <textarea
            *ngIf="!monacoInitialized"
            [(ngModel)]="codeContent"
            (input)="onCodeInput()"
            class="code-textarea-fallback"
            placeholder="Write your solution here..."
            spellcheck="false"
          ></textarea>
        </div>
      </div>

      <!-- Console / Results Output Panel -->
      <div class="console-panel">
        <div class="console-tabbar">
          <div class="tab-title">
            <span class="terminal-icon">⌨</span> Execution Console
          </div>
          <div *ngIf="executionStatus()" class="status-indicator" [ngClass]="executionStatus()!.toLowerCase()">
            {{ executionStatus() }}
            <span *ngIf="lastScore() !== null">({{ lastScore() }} / {{ question.marks }} marks)</span>
          </div>
        </div>

        <div class="console-content">
          <!-- Error alert -->
          <div *ngIf="errorMessage()" class="console-error">
            <div class="error-title">⚠ Execution Error</div>
            <pre class="error-body">{{ errorMessage() }}</pre>
          </div>

          <!-- Test Case Results -->
          <div *ngIf="testResults().length > 0" class="test-results-grid">
            <div *ngFor="let r of testResults(); let i = index" class="test-card" [class.passed]="r.status === 'Accepted' || r.status === 'PASSED'" [class.failed]="r.status !== 'Accepted' && r.status !== 'PASSED'">
              <div class="test-header">
                <span class="test-pill">{{ r.is_sample ? 'Sample #' + (i + 1) : 'Hidden Case #' + (i + 1) }}</span>
                <span class="test-status" [class.pass]="r.status === 'Accepted' || r.status === 'PASSED'">
                  {{ r.status }}
                </span>
                <span class="test-time">{{ r.execution_time_ms }}ms</span>
              </div>

              <!-- For Sample Test Cases, display input and outputs -->
              <div *ngIf="r.is_sample" class="test-details">
                <div class="detail-row">
                  <span class="lbl">Input:</span>
                  <code>{{ r.input }}</code>
                </div>
                <div class="detail-row">
                  <span class="lbl">Expected:</span>
                  <code>{{ r.expected_output }}</code>
                </div>
                <div class="detail-row">
                  <span class="lbl">Actual:</span>
                  <code>{{ r.actual_output }}</code>
                </div>
              </div>

              <!-- For Hidden Test Cases, inputs/outputs are strictly redacted -->
              <div *ngIf="!r.is_sample" class="test-details hidden-case">
                <span class="hidden-label">🔒 Hidden test case evaluation</span>
                <span class="hidden-marks">+{{ r.marks_awarded }} marks</span>
              </div>

              <div *ngIf="r.error_message" class="test-case-error">
                <code>{{ r.error_message }}</code>
              </div>
            </div>
          </div>

          <!-- Empty Console placeholder -->
          <div *ngIf="!errorMessage() && testResults().length === 0" class="console-empty">
            Run sample tests or submit solution to view live output, execution time, and test case pass rates.
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .coding-container {
      display: flex;
      flex-direction: column;
      gap: 1rem;
      background: #0F172A;
      color: #F8FAFC;
      border-radius: 0.75rem;
      padding: 1rem;
      border: 1px solid rgba(255, 255, 255, 0.1);
      margin-top: 1rem;
    }

    .editor-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: #1E293B;
      padding: 0.6rem 1rem;
      border-radius: 0.5rem;
      border: 1px solid rgba(255, 255, 255, 0.08);
      flex-wrap: wrap;
      gap: 0.75rem;
    }

    .header-left, .header-right {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .lang-label {
      font-size: 0.85rem;
      color: #94A3B8;
      font-weight: 600;
    }

    .lang-select {
      background: #0F172A;
      color: #38BDF8;
      border: 1px solid #334155;
      padding: 0.35rem 0.75rem;
      border-radius: 0.375rem;
      font-size: 0.875rem;
      font-weight: 600;
      cursor: pointer;
    }

    .btn-reset {
      background: transparent;
      border: 1px solid #475569;
      color: #94A3B8;
      padding: 0.35rem 0.65rem;
      border-radius: 0.375rem;
      font-size: 0.8rem;
      cursor: pointer;
      transition: all 0.2s;
    }

    .btn-reset:hover {
      background: #334155;
      color: #F8FAFC;
    }

    .rate-limit-pill {
      font-size: 0.75rem;
      background: rgba(56, 189, 248, 0.12);
      color: #38BDF8;
      padding: 0.3rem 0.6rem;
      border-radius: 9999px;
      border: 1px solid rgba(56, 189, 248, 0.25);
    }

    .autosave-pill {
      font-size: 0.75rem;
      color: #10B981;
      font-style: italic;
    }

    .btn-run {
      background: #334155;
      color: #F8FAFC;
      border: 1px solid #475569;
      padding: 0.45rem 1rem;
      border-radius: 0.375rem;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }

    .btn-run:hover:not(:disabled) {
      background: #475569;
    }

    .btn-submit-code {
      background: #10B981;
      color: white;
      border: none;
      padding: 0.45rem 1.15rem;
      border-radius: 0.375rem;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
      box-shadow: 0 2px 6px rgba(16, 185, 129, 0.3);
    }

    .btn-submit-code:hover:not(:disabled) {
      background: #059669;
    }

    button:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }

    .main-editor-split {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
      min-height: 420px;
    }

    @media (max-width: 992px) {
      .main-editor-split {
        grid-template-columns: 1fr;
      }
    }

    .problem-panel {
      background: #1E293B;
      padding: 1.25rem;
      border-radius: 0.5rem;
      border: 1px solid rgba(255, 255, 255, 0.08);
      overflow-y: auto;
      max-height: 480px;
    }

    .problem-title {
      font-size: 1.15rem;
      font-weight: 700;
      color: #38BDF8;
      margin-bottom: 0.5rem;
    }

    .problem-meta {
      display: flex;
      gap: 0.5rem;
      margin-bottom: 1rem;
    }

    .meta-pill {
      font-size: 0.75rem;
      background: #334155;
      padding: 0.2rem 0.5rem;
      border-radius: 0.25rem;
      color: #94A3B8;
    }

    .problem-description {
      font-size: 0.9rem;
      line-height: 1.6;
      color: #CBD5E1;
      white-space: pre-line;
      margin-bottom: 1.25rem;
    }

    .sample-cases-section {
      border-top: 1px solid #334155;
      padding-top: 1rem;
    }

    .cases-heading {
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #94A3B8;
      margin: 0 0 0.75rem 0;
    }

    .sample-case-box {
      background: #0F172A;
      border: 1px solid #334155;
      border-radius: 0.375rem;
      padding: 0.65rem;
      margin-bottom: 0.5rem;
    }

    .case-header {
      font-size: 0.75rem;
      font-weight: 700;
      color: var(--csm-accent);
      margin-bottom: 0.35rem;
    }

    .case-io {
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
    }

    .io-label {
      font-size: 0.7rem;
      color: #64748B;
      font-weight: 600;
    }

    .io-code {
      margin: 0;
      background: #1E293B;
      padding: 0.35rem 0.5rem;
      border-radius: 0.25rem;
      font-size: 0.8rem;
      color: #E2E8F0;
      font-family: 'Consolas', 'Courier New', monospace;
    }

    .editor-pane {
      position: relative;
      background: #1E1E1E;
      border-radius: 0.5rem;
      border: 1px solid rgba(255, 255, 255, 0.08);
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }

    .monaco-container {
      width: 100%;
      height: 480px;
    }

    .code-textarea-fallback {
      width: 100%;
      height: 480px;
      background: #1E1E1E;
      color: #D4D4D4;
      font-family: 'Consolas', 'Courier New', monospace;
      font-size: 0.9rem;
      padding: 1rem;
      border: none;
      resize: vertical;
      line-height: 1.5;
    }

    .console-panel {
      background: #1E293B;
      border-radius: 0.5rem;
      border: 1px solid rgba(255, 255, 255, 0.08);
      overflow: hidden;
    }

    .console-tabbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: #0F172A;
      padding: 0.5rem 1rem;
      border-bottom: 1px solid #334155;
    }

    .tab-title {
      font-size: 0.85rem;
      font-weight: 600;
      color: #94A3B8;
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }

    .status-indicator {
      font-size: 0.8rem;
      font-weight: 700;
      padding: 0.2rem 0.6rem;
      border-radius: 9999px;
    }

    .status-indicator.accepted {
      background: #065F46;
      color: #34D399;
    }

    .status-indicator.wrong_answer, .status-indicator.compilation_error, .status-indicator.runtime_error {
      background: #991B1B;
      color: #F87171;
    }

    .console-content {
      padding: 1rem;
      min-height: 100px;
      max-height: 280px;
      overflow-y: auto;
    }

    .console-empty {
      color: #64748B;
      font-size: 0.85rem;
      font-style: italic;
      text-align: center;
      padding: 1rem;
    }

    .console-error {
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid #EF4444;
      border-radius: 0.375rem;
      padding: 0.75rem;
      margin-bottom: 0.75rem;
    }

    .error-title {
      font-size: 0.8rem;
      font-weight: 700;
      color: #F87171;
      margin-bottom: 0.25rem;
    }

    .error-body {
      margin: 0;
      color: #FCA5A5;
      font-size: 0.8rem;
      white-space: pre-wrap;
      font-family: monospace;
    }

    .test-results-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 0.75rem;
    }

    .test-card {
      background: #0F172A;
      border: 1px solid #334155;
      border-radius: 0.375rem;
      padding: 0.65rem;
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
    }

    .test-card.passed {
      border-color: #059669;
    }

    .test-card.failed {
      border-color: #DC2626;
    }

    .test-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 0.75rem;
      font-weight: 600;
    }

    .test-pill {
      color: #94A3B8;
    }

    .test-status {
      color: #EF4444;
    }

    .test-status.pass {
      color: #10B981;
    }

    .test-time {
      color: #64748B;
    }

    .test-details {
      display: flex;
      flex-direction: column;
      gap: 0.2rem;
      font-size: 0.75rem;
    }

    .detail-row {
      display: flex;
      gap: 0.4rem;
    }

    .detail-row .lbl {
      color: #64748B;
      width: 55px;
    }

    .detail-row code {
      color: #38BDF8;
      font-family: monospace;
    }

    .hidden-case {
      color: #A855F7;
      font-style: italic;
      display: flex;
      justify-content: space-between;
    }

    .test-case-error code {
      color: #F87171;
      font-size: 0.75rem;
      font-family: monospace;
    }
  `]
})
export class CodeQuestionEditorComponent implements OnInit, OnDestroy {
  @Input({ required: true }) question!: QuestionExamItem;
  @Input({ required: true }) attemptId!: number;
  @Output() codeChanged = new EventEmitter<{ code: string; language: string }>();

  @ViewChild('monacoContainer', { static: false }) monacoContainerRef?: ElementRef;

  private codingService = inject(CodingService);

  selectedLanguage = 'python';
  allowedLanguages: string[] = ['python', 'javascript', 'java'];
  codeContent = '';

  isRunning = signal<boolean>(false);
  isSubmitting = signal<boolean>(false);
  isAutosaving = signal<boolean>(false);
  runsRemaining = signal<number | null>(null);
  executionStatus = signal<string | null>(null);
  lastScore = signal<number | null>(null);
  errorMessage = signal<string | null>(null);
  testResults = signal<TestCaseResult[]>([]);

  monacoInitialized = false;
  private monacoEditorInstance: any = null;
  private autosaveDebounceTimer: any = null;

  ngOnInit(): void {
    if (this.question.allowed_languages && this.question.allowed_languages.length > 0) {
      this.allowedLanguages = this.question.allowed_languages;
      this.selectedLanguage = this.allowedLanguages[0];
    }
    this.initStarterCode();
  }

  ngAfterViewInit(): void {
    this.initMonacoEditor();
  }

  ngOnDestroy(): void {
    if (this.autosaveDebounceTimer) {
      clearTimeout(this.autosaveDebounceTimer);
    }
    if (this.monacoEditorInstance) {
      try {
        this.monacoEditorInstance.dispose();
      } catch (e) {}
    }
  }

  formatLanguageName(lang: string): string {
    const map: { [key: string]: string } = {
      python: 'Python 3',
      javascript: 'JavaScript (Node.js)',
      java: 'Java 17',
      sql: 'PostgreSQL / SQL'
    };
    return map[lang.toLowerCase()] || lang;
  }

  formatMarkdown(text: string): string {
    if (!text) return '';
    return text.replace(/\n/g, '<br/>');
  }

  initStarterCode(): void {
    if (this.question.starter_code && this.question.starter_code[this.selectedLanguage]) {
      this.codeContent = this.question.starter_code[this.selectedLanguage];
    } else {
      if (this.selectedLanguage === 'python') {
        this.codeContent = '# Write your Python solution here\n';
      } else if (this.selectedLanguage === 'javascript') {
        this.codeContent = '// Write your JavaScript solution here\n';
      } else if (this.selectedLanguage === 'java') {
        this.codeContent = 'public class Solution {\n    // Write your Java code here\n}\n';
      }
    }
    if (this.monacoEditorInstance) {
      this.monacoEditorInstance.setValue(this.codeContent);
    }
  }

  resetStarterCode(): void {
    if (confirm('Are you sure you want to reset your code to the starter template?')) {
      this.initStarterCode();
      this.emitCodeChange();
    }
  }

  onLanguageChange(): void {
    this.initStarterCode();
    if (this.monacoEditorInstance && window.monaco) {
      const mode = this.selectedLanguage === 'javascript' ? 'javascript' : (this.selectedLanguage === 'java' ? 'java' : 'python');
      window.monaco.editor.setModelLanguage(this.monacoEditorInstance.getModel(), mode);
    }
    this.emitCodeChange();
  }

  onCodeInput(): void {
    this.triggerAutosaveDebounce();
  }

  private initMonacoEditor(): void {
    // Check if monaco is already loaded on window or dynamically load locally bundled script
    if (window.monaco) {
      this.createMonacoInstance();
    } else {
      this.loadLocalMonacoScript(() => {
        this.createMonacoInstance();
      });
    }
  }

  private loadLocalMonacoScript(callback: () => void): void {
    if (document.getElementById('monaco-loader-script')) {
      const checkInterval = setInterval(() => {
        if (window.monaco) {
          clearInterval(checkInterval);
          callback();
        }
      }, 100);
      return;
    }

    const script = document.createElement('script');
    script.id = 'monaco-loader-script';
    // Local bundled path in assets without external CDN
    script.src = 'assets/monaco/vs/loader.js';
    script.onload = () => {
      if (window.require) {
        window.require.config({ paths: { vs: 'assets/monaco/vs' } });
        window.require(['vs/editor/editor.main'], () => {
          callback();
        });
      } else {
        callback();
      }
    };
    script.onerror = () => {
      // Fallback gracefully to high-performance code textarea
      this.monacoInitialized = false;
    };
    document.body.appendChild(script);
  }

  private createMonacoInstance(): void {
    if (!this.monacoContainerRef || !window.monaco) return;
    try {
      const mode = this.selectedLanguage === 'javascript' ? 'javascript' : (this.selectedLanguage === 'java' ? 'java' : 'python');
      this.monacoEditorInstance = window.monaco.editor.create(this.monacoContainerRef.nativeElement, {
        value: this.codeContent,
        language: mode,
        theme: 'vs-dark',
        automaticLayout: true,
        fontSize: 14,
        minimap: { enabled: false },
        lineNumbers: 'on',
        scrollBeyondLastLine: false,
        renderLineHighlight: 'all'
      });

      this.monacoInitialized = true;

      this.monacoEditorInstance.onDidChangeModelContent(() => {
        this.codeContent = this.monacoEditorInstance.getValue();
        this.triggerAutosaveDebounce();
      });
    } catch (e) {
      this.monacoInitialized = false;
    }
  }

  private triggerAutosaveDebounce(): void {
    if (this.autosaveDebounceTimer) {
      clearTimeout(this.autosaveDebounceTimer);
    }
    this.isAutosaving.set(true);
    // 5-second debounce autosave as required
    this.autosaveDebounceTimer = setTimeout(() => {
      this.emitCodeChange();
      this.isAutosaving.set(false);
    }, 5000);
  }

  emitCodeChange(): void {
    this.codeChanged.emit({
      code: this.codeContent,
      language: this.selectedLanguage
    });
  }

  runCode(): void {
    this.isRunning.set(true);
    this.errorMessage.set(null);
    this.executionStatus.set('RUNNING');

    this.codingService.runCode({
      attempt_id: this.attemptId,
      question_id: this.question.id,
      language: this.selectedLanguage,
      source_code: this.codeContent
    }).subscribe({
      next: (res: CodingRunResponse) => {
        this.isRunning.set(false);
        this.executionStatus.set(res.status);
        this.testResults.set(res.results);
        if (res.runs_remaining !== undefined && res.runs_remaining !== null) {
          this.runsRemaining.set(res.runs_remaining);
        }
        if (res.error) {
          this.errorMessage.set(res.error);
        }
      },
      error: (err) => {
        this.isRunning.set(false);
        this.executionStatus.set('ERROR');
        if (err.status === 503) {
          this.errorMessage.set('Code runner unavailable. Judge0 sandbox is offline or unreachable.');
        } else if (err.status === 429) {
          this.errorMessage.set(err.error?.detail || 'Run limit reached for this attempt. Please submit your solution.');
        } else if (err.status === 409) {
          this.errorMessage.set('Attempt is already closed or deadline has expired.');
        } else {
          this.errorMessage.set(err.error?.detail || 'Execution failed. Please check your syntax.');
        }
      }
    });
  }

  submitCode(): void {
    this.isSubmitting.set(true);
    this.errorMessage.set(null);
    this.executionStatus.set('EVALUATING');

    this.codingService.submitCode({
      attempt_id: this.attemptId,
      question_id: this.question.id,
      language: this.selectedLanguage,
      source_code: this.codeContent
    }).subscribe({
      next: (res: CodingSubmitResponse) => {
        this.isSubmitting.set(false);
        this.executionStatus.set(res.status);
        this.lastScore.set(res.score);
        this.testResults.set(res.results);
        if (res.error) {
          this.errorMessage.set(res.error);
        }
        this.emitCodeChange();
      },
      error: (err) => {
        this.isSubmitting.set(false);
        this.executionStatus.set('ERROR');
        if (err.status === 503) {
          this.errorMessage.set('Code runner unavailable. Judge0 sandbox is offline or unreachable.');
        } else if (err.status === 409) {
          this.errorMessage.set('Attempt is already closed or deadline has expired.');
        } else {
          this.errorMessage.set(err.error?.detail || 'Submission failed.');
        }
      }
    });
  }
}
