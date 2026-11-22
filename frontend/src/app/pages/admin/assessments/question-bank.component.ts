import { Component, OnInit, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators, FormArray } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { QuestionService } from '../../../core/services/question.service';
import { QuestionBankItem, AssessmentType, QuestionDifficulty, QuestionType } from '../../../core/models/assessment.model';

@Component({
  selector: 'app-question-form-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule
  ],
  template: `
    <div class="q-dialog">
      <h2 mat-dialog-title>
        <mat-icon>help_outline</mat-icon> Add Question to Question Bank
      </h2>

      <mat-dialog-content>
        <form [formGroup]="qForm" class="q-form">
          <div class="form-row">
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

            <mat-form-field appearance="outline" class="flex-1">
              <mat-label>Difficulty</mat-label>
              <mat-select formControlName="difficulty">
                <mat-option value="Easy">Easy</mat-option>
                <mat-option value="Medium">Medium</mat-option>
                <mat-option value="Hard">Hard</mat-option>
              </mat-select>
            </mat-form-field>
          </div>

          <div class="form-row">
            <mat-form-field appearance="outline" class="flex-1">
              <mat-label>Skill Category</mat-label>
              <input matInput formControlName="skill_category" placeholder="e.g. Deductive Logic, Numerical" />
            </mat-form-field>

            <mat-form-field appearance="outline" class="flex-1">
              <mat-label>Question Type</mat-label>
              <mat-select formControlName="question_type">
                <mat-option value="SINGLE_CHOICE">Single Choice</mat-option>
                <mat-option value="MULTI_CHOICE">Multiple Choice (Multi-Select)</mat-option>
              </mat-select>
            </mat-form-field>

            <mat-form-field appearance="outline" style="width: 100px;">
              <mat-label>Marks</mat-label>
              <input matInput type="number" formControlName="marks" min="1" max="10" />
            </mat-form-field>
          </div>

          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Question Text</mat-label>
            <textarea matInput formControlName="question_text" rows="3" placeholder="Enter full question statement..."></textarea>
          </mat-form-field>

          <!-- Options Builder -->
          <div class="options-builder">
            <div class="builder-head">
              <h4>Options (Mark correct answer(s))</h4>
              <button mat-button type="button" color="primary" (click)="addOption()">
                <mat-icon>add</mat-icon> Add Option
              </button>
            </div>

            @for (opt of optionsFormArray.controls; track $index; let idx = $index) {
              <div class="option-line" [formGroup]="$any(opt)">
                <input
                  type="checkbox"
                  class="correct-cb"
                  [checked]="isCorrectOption(opt.get('id')?.value)"
                  (change)="toggleCorrect(opt.get('id')?.value, $event)"
                  title="Check to mark as correct answer"
                />
                <mat-form-field appearance="outline" class="opt-input">
                  <mat-label>Option {{ idx + 1 }}</mat-label>
                  <input matInput formControlName="text" placeholder="Option text..." />
                </mat-form-field>
                <button mat-icon-button color="warn" type="button" (click)="removeOption(idx)" [disabled]="optionsFormArray.length <= 2">
                  <mat-icon>close</mat-icon>
                </button>
              </div>
            }
          </div>
        </form>
      </mat-dialog-content>

      <mat-dialog-actions align="end">
        <button mat-button mat-dialog-close>Cancel</button>
        <button mat-flat-button class="btn-primary" (click)="save()" [disabled]="qForm.invalid || correctAnswers.length === 0">
          Save Question
        </button>
      </mat-dialog-actions>
    </div>
  `,
  styles: [`
    .q-dialog { min-width: 580px; padding: 12px; }
    h2 { display: flex; align-items: center; gap: 8px; color: var(--csm-primary); font-weight: 700; }
    .q-form { display: flex; flex-direction: column; gap: 12px; }
    .form-row { display: flex; gap: 12px; }
    .flex-1 { flex: 1; }
    .full-width { width: 100%; }
    .options-builder {
      background: #f8fafc;
      padding: 16px;
      border-radius: 8px;
      border: 1px solid var(--border-light);

      .builder-head {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        h4 { margin: 0; font-size: 0.95rem; font-weight: 600; color: #0f172a; }
      }

      .option-line {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 8px;

        .correct-cb {
          width: 20px;
          height: 20px;
          cursor: pointer;
          accent-color: #16a34a;
        }

        .opt-input {
          flex: 1;
          margin-bottom: -1.25em;
        }
      }
    }
  `]
})
export class QuestionFormDialogComponent {
  qForm: FormGroup;
  correctAnswers: string[] = [];

  constructor(
    private fb: FormBuilder,
    private dialogRef: MatDialogRef<QuestionFormDialogComponent>
  ) {
    this.qForm = this.fb.group({
      type: ['Logical Thinking', Validators.required],
      difficulty: ['Medium', Validators.required],
      skill_category: ['', Validators.required],
      question_type: ['SINGLE_CHOICE', Validators.required],
      marks: [1, [Validators.required, Validators.min(1)]],
      question_text: ['', Validators.required],
      options: this.fb.array([
        this.createOptionGroup('opt1', ''),
        this.createOptionGroup('opt2', ''),
        this.createOptionGroup('opt3', ''),
        this.createOptionGroup('opt4', '')
      ])
    });
  }

  get optionsFormArray(): FormArray {
    return this.qForm.get('options') as FormArray;
  }

  createOptionGroup(id: string, text: string): FormGroup {
    return this.fb.group({
      id: [id],
      text: [text, Validators.required]
    });
  }

  addOption(): void {
    const nextId = 'opt' + (this.optionsFormArray.length + 1);
    this.optionsFormArray.push(this.createOptionGroup(nextId, ''));
  }

  removeOption(index: number): void {
    const removedId = this.optionsFormArray.at(index).get('id')?.value;
    this.correctAnswers = this.correctAnswers.filter(id => id !== removedId);
    this.optionsFormArray.removeAt(index);
  }

  isCorrectOption(optId: string): boolean {
    return this.correctAnswers.includes(optId);
  }

  toggleCorrect(optId: string, event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    const isSingle = this.qForm.get('question_type')?.value === 'SINGLE_CHOICE';

    if (isSingle) {
      this.correctAnswers = checked ? [optId] : [];
    } else {
      if (checked) {
        if (!this.correctAnswers.includes(optId)) this.correctAnswers.push(optId);
      } else {
        this.correctAnswers = this.correctAnswers.filter(id => id !== optId);
      }
    }
  }

  save(): void {
    if (this.qForm.invalid || this.correctAnswers.length === 0) return;
    const val = this.qForm.value;
    this.dialogRef.close({
      ...val,
      correct_answers: this.correctAnswers
    });
  }
}

@Component({
  selector: 'app-admin-question-bank',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatDialogModule,
    MatSnackBarModule,
    MatProgressSpinnerModule
  ],
  template: `
    <div class="qb-page">
      <div class="page-header">
        <div>
          <h1>Question Bank Repository</h1>
          <p>Maintain competency questions, multiple-choice options, and difficulty levels</p>
        </div>
        <button mat-flat-button class="btn-primary" (click)="openAddDialog()">
          <mat-icon>add</mat-icon> Add Question
        </button>
      </div>

      <!-- Filters Row -->
      <div class="filters-card card-shadow">
        <div class="search-box">
          <mat-icon>search</mat-icon>
          <input
            type="text"
            [(ngModel)]="searchQuery"
            placeholder="Search questions or skill category..."
            (input)="loadQuestions()"
          />
        </div>

        <mat-form-field appearance="outline" class="filter-field">
          <mat-label>Domain Type</mat-label>
          <mat-select [(ngModel)]="selectedType" (selectionChange)="loadQuestions()">
            <mat-option value="">All Domains</mat-option>
            <mat-option value="Logical Thinking">Logical Thinking</mat-option>
            <mat-option value="Reasoning">Reasoning</mat-option>
            <mat-option value="Pattern Recognition">Pattern Recognition</mat-option>
            <mat-option value="Aptitude">Aptitude</mat-option>
            <mat-option value="Psychometric">Psychometric</mat-option>
            <mat-option value="Behavioural">Behavioural</mat-option>
          </mat-select>
        </mat-form-field>

        <mat-form-field appearance="outline" class="filter-field">
          <mat-label>Difficulty</mat-label>
          <mat-select [(ngModel)]="selectedDifficulty" (selectionChange)="loadQuestions()">
            <mat-option value="">All Difficulties</mat-option>
            <mat-option value="Easy">Easy</mat-option>
            <mat-option value="Medium">Medium</mat-option>
            <mat-option value="Hard">Hard</mat-option>
          </mat-select>
        </mat-form-field>
      </div>

      <!-- Questions Table -->
      <div class="table-container card-shadow">
        @if (isLoading()) {
          <div class="loading-state">
            <mat-spinner diameter="36"></mat-spinner>
            <span>Loading questions...</span>
          </div>
        } @else if (questions().length === 0) {
          <div class="empty-state">
            <mat-icon>help_outline</mat-icon>
            <h3>No questions found</h3>
            <p>Try resetting your search filters or click "Add Question" above.</p>
          </div>
        } @else {
          <table mat-table [dataSource]="questions()" class="qb-table">
            <ng-container matColumnDef="id">
              <th mat-header-cell *matHeaderCellDef>#</th>
              <td mat-cell *matCellDef="let q">{{ q.id }}</td>
            </ng-container>

            <ng-container matColumnDef="question">
              <th mat-header-cell *matHeaderCellDef>Question Text</th>
              <td mat-cell *matCellDef="let q">
                <div class="q-cell">
                  <span class="q-text">{{ q.question_text }}</span>
                  <div class="q-meta">
                    <span class="badge badge-skill">{{ q.skill_category }}</span>
                    <span class="badge badge-type">{{ q.type }}</span>
                    <span class="opts-count">{{ q.options?.length }} options</span>
                  </div>
                </div>
              </td>
            </ng-container>

            <ng-container matColumnDef="difficulty">
              <th mat-header-cell *matHeaderCellDef>Difficulty</th>
              <td mat-cell *matCellDef="let q">
                <span class="badge" [ngClass]="'badge-' + q.difficulty.toLowerCase()">
                  {{ q.difficulty }}
                </span>
              </td>
            </ng-container>

            <ng-container matColumnDef="marks">
              <th mat-header-cell *matHeaderCellDef>Marks</th>
              <td mat-cell *matCellDef="let q">{{ q.marks }}</td>
            </ng-container>

            <ng-container matColumnDef="actions">
              <th mat-header-cell *matHeaderCellDef class="text-right">Actions</th>
              <td mat-cell *matCellDef="let q" class="text-right">
                <button mat-icon-button color="warn" (click)="deleteQuestion(q)">
                  <mat-icon>delete_outline</mat-icon>
                </button>
              </td>
            </ng-container>

            <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
            <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
          </table>
        }
      </div>
    </div>
  `,
  styles: [`
    .qb-page { display: flex; flex-direction: column; gap: 20px; }
    .page-header { display: flex; justify-content: space-between; align-items: center;
      h1 { margin: 0; font-size: 1.6rem; font-weight: 700; color: #0f172a; }
      p { margin: 4px 0 0; color: var(--text-muted); font-size: 0.9rem; }
    }
    .filters-card {
      padding: 16px 20px;
      display: flex;
      align-items: center;
      gap: 16px;
      background: #ffffff;
      border-radius: 12px;
      flex-wrap: wrap;

      .search-box {
        display: flex;
        align-items: center;
        gap: 10px;
        background-color: var(--bg-main);
        padding: 8px 16px;
        border-radius: 8px;
        flex: 1;
        min-width: 260px;
        border: 1px solid var(--border-light);

        mat-icon { color: var(--text-muted); font-size: 20px; }
        input { border: none; background: transparent; outline: none; width: 100%; font-size: 0.9rem; }
      }

      .filter-field { width: 180px; margin-bottom: -1.25em; }
    }

    .table-container { background: #ffffff; border-radius: 12px; overflow-x: auto; }
    .qb-table { width: 100%;
      th { font-weight: 600; color: var(--text-secondary); font-size: 0.8rem; text-transform: uppercase; padding: 16px; }
      td { padding: 12px 16px; }
      .text-right { text-align: right; }
    }

    .q-cell {
      display: flex;
      flex-direction: column;
      gap: 6px;

      .q-text { font-weight: 600; font-size: 0.92rem; color: #0f172a; }
      .q-meta {
        display: flex;
        gap: 8px;
        align-items: center;

        .badge-skill { background: #f1f5f9; color: #475569; font-size: 0.72rem; padding: 2px 8px; border-radius: 4px; }
        .badge-type { background: #eff6ff; color: var(--csm-primary); font-size: 0.72rem; padding: 2px 8px; border-radius: 4px; }
        .opts-count { font-size: 0.75rem; color: var(--text-muted); }
      }
    }

    .badge-easy { background: #dcfce7; color: #166534; }
    .badge-medium { background: #fef3c7; color: #b45309; }
    .badge-hard { background: #fee2e2; color: #b91c1c; }

    .loading-state, .empty-state {
      display: flex; flex-direction: column; align-items: center; padding: 64px 20px; color: var(--text-muted);
      mat-icon { font-size: 48px; width: 48px; height: 48px; opacity: 0.5; margin-bottom: 8px; }
      h3 { margin: 0; color: #0f172a; }
      p { margin: 4px 0 0; }
    }
  `]
})
export class AdminQuestionBankComponent implements OnInit {
  questions = signal<QuestionBankItem[]>([]);
  isLoading = signal(true);
  searchQuery = '';
  selectedType: any = '';
  selectedDifficulty: any = '';
  displayedColumns = ['id', 'question', 'difficulty', 'marks', 'actions'];

  private questionService = inject(QuestionService);
  private dialog = inject(MatDialog);
  private snackBar = inject(MatSnackBar);

  ngOnInit(): void {
    this.loadQuestions();
  }

  loadQuestions(): void {
    this.isLoading.set(true);
    this.questionService.getQuestions({
      type: this.selectedType || undefined,
      difficulty: this.selectedDifficulty || undefined,
      search: this.searchQuery || undefined
    }).subscribe({
      next: (res) => {
        this.questions.set(res);
        this.isLoading.set(false);
      },
      error: () => this.isLoading.set(false)
    });
  }

  openAddDialog(): void {
    const dialogRef = this.dialog.open(QuestionFormDialogComponent);
    dialogRef.afterClosed().subscribe((res) => {
      if (res) {
        this.questionService.createQuestion(res).subscribe({
          next: () => {
            this.snackBar.open('Question added to Question Bank', 'Close', { duration: 3000, panelClass: ['snack-success'] });
            this.loadQuestions();
          },
          error: (err) => {
            const detail = err.error?.detail || 'Failed to add question';
            this.snackBar.open(detail, 'Close', { duration: 4000, panelClass: ['snack-error'] });
          }
        });
      }
    });
  }

  deleteQuestion(q: QuestionBankItem): void {
    if (confirm(`Delete question #${q.id}?`)) {
      this.questionService.deleteQuestion(q.id).subscribe({
        next: () => {
          this.snackBar.open('Question deleted', 'Close', { duration: 3000, panelClass: ['snack-success'] });
          this.loadQuestions();
        },
        error: (err) => {
          const detail = err.error?.detail || 'Failed to delete question';
          this.snackBar.open(detail, 'Close', { duration: 4000, panelClass: ['snack-error'] });
        }
      });
    }
  }
}
