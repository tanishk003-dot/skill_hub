import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators, FormArray } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { AssessmentService } from '../../../core/services/assessment.service';
import { QuestionService } from '../../../core/services/question.service';
import { QuestionBankItem, AssessmentType } from '../../../core/models/assessment.model';

@Component({
  selector: 'app-create-assessment',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    FormsModule,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatSlideToggleModule,
    MatButtonModule,
    MatIconModule,
    MatSnackBarModule
  ],
  template: `
    <div class="create-page">
      <div class="page-header">
        <div>
          <h1>Create New Assessment</h1>
          <p>Configure evaluation parameters, custom sections with independent timers, and questions</p>
        </div>
        <a mat-stroked-button routerLink="/admin/assessments">
          <mat-icon>arrow_back</mat-icon> Back to Assessments
        </a>
      </div>

      <form [formGroup]="assessmentForm" (ngSubmit)="onSubmit()" class="form-layout">
        <!-- 1. Basic Configuration Card -->
        <div class="config-card card-shadow">
          <div class="card-title">
            <mat-icon class="icon-primary">settings</mat-icon>
            <h3>1. Assessment Parameters</h3>
          </div>

          <div class="grid-row">
            <mat-form-field appearance="outline" class="flex-2">
              <mat-label>Assessment Title</mat-label>
              <input matInput formControlName="title" placeholder="e.g. Core Engineering Aptitude & Reasoning" />
            </mat-form-field>

            <mat-form-field appearance="outline" class="flex-1">
              <mat-label>Assessment Domain</mat-label>
              <mat-select formControlName="type">
                <mat-option value="Logical Thinking">Logical Thinking</mat-option>
                <mat-option value="Reasoning">Reasoning</mat-option>
                <mat-option value="Pattern Recognition">Pattern Recognition</mat-option>
                <mat-option value="Aptitude">Aptitude</mat-option>
                <mat-option value="Psychometric">Psychometric</mat-option>
                <mat-option value="Behavioural">Behavioural</mat-option>
              </mat-select>
            </mat-form-field>
          </div>

          <div class="grid-row">
            <mat-form-field appearance="outline" class="flex-1">
              <mat-label>Total Duration (Minutes)</mat-label>
              <input matInput type="number" formControlName="total_duration_minutes" min="5" max="300" />
            </mat-form-field>

            <mat-form-field appearance="outline" class="flex-1">
              <mat-label>Passing Score Percentage (%)</mat-label>
              <input matInput type="number" formControlName="passing_percentage" min="1" max="100" />
            </mat-form-field>

            <div class="toggle-group flex-1">
              <mat-slide-toggle formControlName="randomize_questions" color="primary">
                Randomize Question Order
              </mat-slide-toggle>
              <mat-slide-toggle formControlName="randomize_options" color="primary">
                Randomize Option Order
              </mat-slide-toggle>
            </div>
          </div>
        </div>

        <!-- 2. Section & Questions Builder -->
        <div class="sections-builder-card card-shadow">
          <div class="builder-top">
            <div class="card-title">
              <mat-icon class="icon-accent">view_week</mat-icon>
              <h3>2. Sections & Timers</h3>
            </div>
            <button mat-flat-button class="btn-accent" type="button" (click)="addSection()">
              <mat-icon>add</mat-icon> Add Section
            </button>
          </div>

          <div class="sections-list" formArrayName="sections">
            @for (sec of sectionsFormArray.controls; track $index; let sIdx = $index) {
              <div class="section-box" [formGroupName]="sIdx">
                <div class="sec-box-header">
                  <span class="sec-badge">Section {{ sIdx + 1 }}</span>
                  <button
                    mat-icon-button
                    color="warn"
                    type="button"
                    (click)="removeSection(sIdx)"
                    [disabled]="sectionsFormArray.length <= 1"
                  >
                    <mat-icon>delete</mat-icon>
                  </button>
                </div>

                <div class="sec-inputs">
                  <mat-form-field appearance="outline" class="flex-2">
                    <mat-label>Section Title</mat-label>
                    <input matInput formControlName="title" placeholder="e.g. Logical & Pattern Recognition" />
                  </mat-form-field>

                  <mat-form-field appearance="outline" class="flex-1">
                    <mat-label>Section Timer (Minutes)</mat-label>
                    <input matInput type="number" formControlName="timer_minutes" min="1" max="180" />
                  </mat-form-field>
                </div>

                <!-- Selected Questions from Bank for this Section -->
                <div class="sec-questions-selector">
                  <div class="selector-head">
                    <h4>Select Questions from Question Bank ({{ getSectionQuestionCount(sIdx) }} selected)</h4>
                  </div>

                  <div class="questions-checklist">
                    @for (q of availableQuestions(); track q.id) {
                      <label class="q-check-row" [class.selected]="isQuestionSelected(sIdx, q.id)">
                        <input
                          type="checkbox"
                          [checked]="isQuestionSelected(sIdx, q.id)"
                          (change)="toggleQuestion(sIdx, q.id, $event)"
                        />
                        <div class="q-check-info">
                          <span class="q-name">{{ q.question_text }}</span>
                          <div class="q-tags">
                            <span class="badge badge-skill">{{ q.skill_category }}</span>
                            <span class="badge badge-diff">{{ q.difficulty }}</span>
                            <span class="q-mrk">{{ q.marks }} {{ q.marks === 1 ? 'mark' : 'marks' }}</span>
                          </div>
                        </div>
                      </label>
                    }
                  </div>
                </div>
              </div>
            }
          </div>
        </div>

        <div class="submit-bar">
          <button mat-flat-button class="btn-primary create-submit-btn" type="submit" [disabled]="assessmentForm.invalid || isSubmitting()">
            <mat-icon>save</mat-icon> Create & Publish Assessment
          </button>
        </div>
      </form>
    </div>
  `,
  styles: [`
    .create-page { display: flex; flex-direction: column; gap: 24px; max-width: 1100px; margin: 0 auto; }
    .page-header { display: flex; justify-content: space-between; align-items: center;
      h1 { margin: 0; font-size: 1.6rem; font-weight: 700; color: #0f172a; }
      p { margin: 4px 0 0; color: var(--text-muted); font-size: 0.9rem; }
    }
    .form-layout { display: flex; flex-direction: column; gap: 24px; }
    .config-card, .sections-builder-card { background: #ffffff; padding: 24px; border-radius: 12px; }

    .card-title { display: flex; align-items: center; gap: 10px; margin-bottom: 20px;
      h3 { margin: 0; font-size: 1.15rem; font-weight: 600; color: #0f172a; }
      .icon-primary { color: var(--csm-primary); }
      .icon-accent { color: var(--csm-accent); }
    }

    .grid-row { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 8px; }
    .flex-1 { flex: 1; min-width: 220px; }
    .flex-2 { flex: 2; min-width: 300px; }

    .toggle-group { display: flex; flex-direction: column; gap: 10px; justify-content: center; padding-bottom: 12px; }

    .builder-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }

    .sections-list { display: flex; flex-direction: column; gap: 20px; }

    .section-box {
      border: 1px solid var(--border-light);
      border-radius: 10px;
      padding: 20px;
      background: #f8fafc;

      .sec-box-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;
        .sec-badge { font-size: 0.82rem; font-weight: 700; color: var(--csm-primary); text-transform: uppercase; }
      }

      .sec-inputs { display: flex; gap: 16px; margin-bottom: 16px; }

      .sec-questions-selector {
        background: #ffffff;
        border-radius: 8px;
        padding: 16px;
        border: 1px solid var(--border-light);

        .selector-head {
          margin-bottom: 12px;
          h4 { margin: 0; font-size: 0.9rem; font-weight: 600; color: #0f172a; }
        }

        .questions-checklist {
          max-height: 240px;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 8px;

          .q-check-row {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 8px 12px;
            border-radius: 6px;
            cursor: pointer;
            border: 1px solid var(--border-light);
            background: #ffffff;

            input { width: 16px; height: 16px; accent-color: var(--csm-primary); cursor: pointer; }

            .q-check-info {
              flex: 1;
              display: flex;
              flex-direction: column;
              gap: 4px;

              .q-name { font-size: 0.88rem; font-weight: 500; color: #1e293b; }
              .q-tags {
                display: flex;
                align-items: center;
                gap: 8px;

                .badge-skill { background: #f1f5f9; color: #475569; font-size: 0.72rem; padding: 2px 6px; border-radius: 4px; }
                .badge-diff { background: #eff6ff; color: #1d4ed8; font-size: 0.72rem; padding: 2px 6px; border-radius: 4px; }
                .q-mrk { font-size: 0.75rem; color: var(--text-muted); }
              }
            }

            &:hover { background: #f8fafc; }
            &.selected { background: #eff6ff; border-color: #bfdbfe; }
          }
        }
      }
    }

    .submit-bar { display: flex; justify-content: flex-end;
      .create-submit-btn { height: 48px; padding: 0 28px; font-size: 1rem; }
    }
  `]
})
export class AdminCreateAssessmentComponent implements OnInit {
  assessmentForm: FormGroup;
  availableQuestions = signal<QuestionBankItem[]>([]);
  isSubmitting = signal(false);

  private fb = inject(FormBuilder);
  private router = inject(Router);
  private assessmentService = inject(AssessmentService);
  private questionService = inject(QuestionService);
  private snackBar = inject(MatSnackBar);

  constructor() {
    this.assessmentForm = this.fb.group({
      title: ['', Validators.required],
      type: ['Logical Thinking', Validators.required],
      total_duration_minutes: [30, [Validators.required, Validators.min(5)]],
      passing_percentage: [60.0, [Validators.required, Validators.min(1), Validators.max(100)]],
      randomize_questions: [false],
      randomize_options: [false],
      sections: this.fb.array([
        this.createSectionGroup('Section 1', 15)
      ])
    });
  }

  get sectionsFormArray(): FormArray {
    return this.assessmentForm.get('sections') as FormArray;
  }

  ngOnInit(): void {
    this.questionService.getQuestions().subscribe(res => this.availableQuestions.set(res));
  }

  createSectionGroup(title: string, timerMin: number): FormGroup {
    return this.fb.group({
      title: [title, Validators.required],
      timer_minutes: [timerMin, [Validators.required, Validators.min(1)]],
      question_ids: [[]]
    });
  }

  addSection(): void {
    const nextIdx = this.sectionsFormArray.length + 1;
    this.sectionsFormArray.push(this.createSectionGroup(`Section ${nextIdx}`, 15));
  }

  removeSection(idx: number): void {
    this.sectionsFormArray.removeAt(idx);
  }

  getSectionQuestionCount(sIdx: number): number {
    const ids = this.sectionsFormArray.at(sIdx).get('question_ids')?.value || [];
    return ids.length;
  }

  isQuestionSelected(sIdx: number, qId: number): boolean {
    const ids = this.sectionsFormArray.at(sIdx).get('question_ids')?.value || [];
    return ids.includes(qId);
  }

  toggleQuestion(sIdx: number, qId: number, event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    const currentControl = this.sectionsFormArray.at(sIdx).get('question_ids');
    const cur = currentControl?.value || [];

    if (checked) {
      if (!cur.includes(qId)) currentControl?.setValue([...cur, qId]);
    } else {
      currentControl?.setValue(cur.filter((id: number) => id !== qId));
    }
  }

  onSubmit(): void {
    if (this.assessmentForm.invalid) return;

    const val = this.assessmentForm.value;
    // Check that every section has at least 1 question
    for (let i = 0; i < val.sections.length; i++) {
      if (!val.sections[i].question_ids || val.sections[i].question_ids.length === 0) {
        this.snackBar.open(`Section #${i + 1} must have at least one question assigned`, 'OK', { duration: 4000, panelClass: ['snack-error'] });
        return;
      }
    }

    this.isSubmitting.set(true);
    this.assessmentService.createAssessment(val).subscribe({
      next: (res) => {
        this.snackBar.open(`Assessment '${res.title}' created successfully!`, 'Close', { duration: 3500, panelClass: ['snack-success'] });
        this.router.navigate(['/admin/assessments']);
      },
      error: (err) => {
        this.isSubmitting.set(false);
        const detail = err.error?.detail || 'Failed to create assessment';
        this.snackBar.open(detail, 'Close', { duration: 4000, panelClass: ['snack-error'] });
      }
    });
  }
}
