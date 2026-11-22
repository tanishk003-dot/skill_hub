import { Component, OnInit, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ChatService } from '../../../core/services/chat.service';
import { ChatMessage, StarterPrompts } from '../../../core/models/chat.model';

@Component({
  selector: 'app-chat-widget',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    MatProgressSpinnerModule
  ],
  template: `
    <!-- Floating Launcher Button -->
    <div class="chat-launcher" (click)="toggleChat()" [class.open]="isOpen">
      <mat-icon>{{ isOpen ? 'close' : 'smart_toy' }}</mat-icon>
      <span class="launcher-label" *ngIf="!isOpen">AI Coach</span>
    </div>

    <!-- Chat Drawer Panel -->
    <div class="chat-panel" *ngIf="isOpen">
      <!-- Header -->
      <div class="chat-header">
        <div class="header-info">
          <div class="bot-avatar">
            <mat-icon>smart_toy</mat-icon>
          </div>
          <div>
            <h3>SkillBot AI</h3>
            <span class="demo-pill" *ngIf="starterInfo?.demo_mode">Demo AI mode</span>
            <span class="provider-pill" *ngIf="!starterInfo?.demo_mode">{{ starterInfo?.provider }}</span>
          </div>
        </div>
        <div class="header-actions">
          <button mat-icon-button class="action-btn" matTooltip="Clear conversation" (click)="clearChat()" [disabled]="loading">
            <mat-icon>delete_outline</mat-icon>
          </button>
          <button mat-icon-button class="action-btn" matTooltip="Close chat" (click)="toggleChat()">
            <mat-icon>close</mat-icon>
          </button>
        </div>
      </div>

      <!-- Messages Body -->
      <div class="chat-body" #scrollContainer>
        <!-- Welcome banner if no messages -->
        <div class="welcome-box" *ngIf="messages.length === 0 && !loading">
          <mat-icon class="welcome-icon">psychology</mat-icon>
          <h4>Welcome to SkillBot AI</h4>
          <p>I analyze your assessment performance, explain weak skills, and suggest personalized learning tracks.</p>
        </div>

        <!-- Starter Prompt Chips -->
        <div class="starter-chips" *ngIf="messages.length <= 2 && starterInfo?.prompts?.length">
          <span class="chips-title">Suggested Prompts:</span>
          <div class="chips-list">
            <button class="chip-btn" *ngFor="let p of starterInfo?.prompts" (click)="sendStarterPrompt(p)">
              {{ p }}
            </button>
          </div>
        </div>

        <!-- Message Bubbles -->
        <div class="message-wrap" *ngFor="let msg of messages" [ngClass]="msg.sender_role.toLowerCase()">
          <!-- User Bubble -->
          <div *ngIf="msg.sender_role === 'USER'" class="bubble user-bubble">
            <div class="bubble-text">{{ msg.content }}</div>
            <span class="msg-time">{{ msg.created_at | date:'shortTime' }}</span>
          </div>

          <!-- Assistant Bubble -->
          <div *ngIf="msg.sender_role === 'ASSISTANT'" class="bubble assistant-bubble">
            <div class="bubble-header">
              <span class="disclaimer-badge">
                <mat-icon class="tiny-icon">verified_user</mat-icon>
                AI-generated, please verify
              </span>
            </div>
            <!-- Render plain text / split lines cleanly without raw HTML (XSS prevention) -->
            <div class="bubble-text safe-content">
              <p *ngFor="let line of getFormattedLines(msg.content)">{{ line }}</p>
            </div>
            
            <!-- Message Footer: Time + Feedback -->
            <div class="bubble-footer">
              <span class="msg-time">{{ msg.created_at | date:'shortTime' }}</span>
              <div class="feedback-actions">
                <button mat-icon-button class="fb-btn" [class.active-fb]="msg.feedback === 'UP'" (click)="setFeedback(msg, 'UP')" matTooltip="Helpful answer">
                  <mat-icon>thumb_up</mat-icon>
                </button>
                <button mat-icon-button class="fb-btn" [class.active-fb]="msg.feedback === 'DOWN'" (click)="setFeedback(msg, 'DOWN')" matTooltip="Needs improvement">
                  <mat-icon>thumb_down</mat-icon>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Typing skeleton indicator -->
        <div *ngIf="loading" class="typing-indicator">
          <mat-spinner diameter="18"></mat-spinner>
          <span>SkillBot is analyzing...</span>
        </div>

        <!-- Error alert -->
        <div *ngIf="errorMessage" class="error-banner">
          <mat-icon>error_outline</mat-icon>
          <span>{{ errorMessage }}</span>
        </div>
      </div>

      <!-- Input Footer -->
      <div class="chat-footer">
        <input
          type="text"
          class="chat-input"
          placeholder="Ask SkillBot about scores, trainings, or guidance..."
          [(ngModel)]="userInput"
          (keydown.enter)="sendMessage()"
          [disabled]="loading"
          maxlength="1000"
        />
        <button mat-icon-button class="send-btn" (click)="sendMessage()" [disabled]="loading || !userInput.trim()">
          <mat-icon>send</mat-icon>
        </button>
      </div>
    </div>
  `,
  styles: [`
    /* Floating Launcher */
    .chat-launcher {
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: var(--csm-primary, #1e3a8a);
      color: #ffffff !important;
      padding: 12px 20px;
      border-radius: 30px;
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      box-shadow: 0 4px 16px rgba(30, 58, 138, 0.35);
      z-index: 1200;
      transition: all 0.25s ease;
      user-select: none;
    }

    .chat-launcher:hover {
      background: #172554 !important;
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(30, 58, 138, 0.45);
    }

    .chat-launcher.open {
      padding: 12px;
      border-radius: 50%;
      background: #0F172A !important;
    }

    .launcher-label {
      font-weight: 600;
      font-size: 0.92rem;
      letter-spacing: 0.02em;
      color: #ffffff !important;
    }

    /* Chat Drawer Panel */
    .chat-panel {
      position: fixed;
      bottom: 84px;
      right: 24px;
      width: 400px;
      max-width: calc(100vw - 32px);
      height: 580px;
      max-height: calc(100vh - 110px);
      background: #ffffff;
      border-radius: 16px;
      box-shadow: 0 10px 30px rgba(15, 23, 42, 0.18);
      border: 1px solid #E2E8F0;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      z-index: 1200;
      animation: slideUp 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }

    @keyframes slideUp {
      from { opacity: 0; transform: translateY(16px); }
      to { opacity: 1; transform: translateY(0); }
    }

    /* Header */
    .chat-header {
      background: var(--csm-primary, #1e3a8a);
      color: #ffffff !important;
      padding: 14px 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .header-info {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .bot-avatar {
      width: 36px;
      height: 36px;
      background: rgba(255, 255, 255, 0.2);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .header-info h3 {
      margin: 0;
      font-size: 1rem;
      font-weight: 700;
      line-height: 1.2;
    }

    .demo-pill {
      font-size: 0.68rem;
      background: var(--csm-accent);
      color: #ffffff;
      padding: 2px 8px;
      border-radius: 10px;
      font-weight: 600;
      display: inline-block;
      margin-top: 2px;
    }

    .provider-pill {
      font-size: 0.68rem;
      background: rgba(255, 255, 255, 0.25);
      color: #ffffff;
      padding: 2px 8px;
      border-radius: 10px;
      font-weight: 600;
      display: inline-block;
      margin-top: 2px;
      text-transform: uppercase;
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .action-btn {
      color: #ffffff !important;
      width: 32px !important;
      height: 32px !important;
      line-height: 32px !important;
    }

    /* Body */
    .chat-body {
      flex: 1;
      padding: 16px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 14px;
      background: var(--bg-main);
    }

    .welcome-box {
      text-align: center;
      padding: 24px 16px;
      color: var(--text-secondary);
    }

    .welcome-icon {
      font-size: 40px;
      width: 40px;
      height: 40px;
      color: var(--csm-primary);
      margin-bottom: 8px;
    }

    .welcome-box h4 {
      margin: 0 0 6px;
      color: var(--text-primary);
      font-size: 1.05rem;
    }

    .welcome-box p {
      margin: 0;
      font-size: 0.82rem;
      line-height: 1.4;
    }

    /* Starter chips */
    .starter-chips {
      margin-top: 8px;
    }

    .chips-title {
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--text-muted);
      display: block;
      margin-bottom: 8px;
    }

    .chips-list {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .chip-btn {
      background: var(--bg-card);
      border: 1px solid var(--border-light);
      padding: 8px 12px;
      border-radius: 8px;
      font-size: 0.78rem;
      color: var(--csm-primary);
      text-align: left;
      cursor: pointer;
      transition: all 0.15s ease;
      box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }

    .chip-btn:hover {
      background: var(--primary-light);
      border-color: var(--primary-border);
    }

    /* Bubbles */
    .message-wrap {
      display: flex;
      flex-direction: column;
    }

    .message-wrap.user {
      align-items: flex-end;
    }

    .message-wrap.assistant {
      align-items: flex-start;
    }

    .bubble {
      max-width: 88%;
      padding: 10px 14px;
      border-radius: 12px;
      font-size: 0.85rem;
      line-height: 1.45;
    }

    .user-bubble {
      background: var(--csm-primary);
      color: #ffffff;
      border-bottom-right-radius: 2px;
    }

    .assistant-bubble {
      background: var(--bg-card);
      color: var(--text-primary);
      border: 1px solid var(--border-subtle);
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
      border-bottom-left-radius: 2px;
    }

    .bubble-header {
      margin-bottom: 6px;
    }

    .disclaimer-badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 0.68rem;
      color: var(--text-secondary);
      background: var(--bg-main);
      padding: 2px 6px;
      border-radius: 4px;
      font-weight: 600;
    }

    .tiny-icon {
      font-size: 13px !important;
      width: 13px !important;
      height: 13px !important;
    }

    .safe-content p {
      margin: 0 0 6px 0;
    }

    .safe-content p:last-child {
      margin: 0;
    }

    .bubble-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 6px;
      font-size: 0.72rem;
    }

    .user-bubble .msg-time {
      color: rgba(255, 255, 255, 0.7);
      font-size: 0.7rem;
      display: block;
      text-align: right;
      margin-top: 4px;
    }

    .assistant-bubble .msg-time {
      color: #94A3B8;
    }

    .feedback-actions {
      display: flex;
      gap: 2px;
    }

    .fb-btn {
      width: 26px !important;
      height: 26px !important;
      line-height: 26px !important;
      color: #94A3B8;
    }

    .fb-btn mat-icon {
      font-size: 15px !important;
      width: 15px !important;
      height: 15px !important;
    }

    .fb-btn:hover {
      color: var(--csm-primary);
    }

    .active-fb {
      color: var(--csm-accent) !important;
    }

    /* Typing indicator */
    .typing-indicator {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.78rem;
      color: #64748B;
      padding: 4px 8px;
    }

    .error-banner {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 8px 12px;
      background: var(--color-danger-bg);
      border: 1px solid var(--color-danger-border);
      border-radius: 8px;
      color: var(--color-danger-text);
      font-size: 0.78rem;
    }

    .error-banner mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
    }

    /* Footer */
    .chat-footer {
      padding: 12px;
      background: var(--bg-card);
      border-top: 1px solid var(--border-subtle);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .chat-input {
      flex: 1;
      border: 1px solid var(--border-light);
      padding: 10px 14px;
      border-radius: 20px;
      font-size: 0.85rem;
      outline: none;
      transition: border-color 0.15s ease;
      background: var(--bg-card);
      color: var(--text-primary);
    }

    .chat-input:focus {
      border-color: var(--csm-primary);
    }

    .send-btn {
      background: var(--csm-primary) !important;
      color: #ffffff !important;
      width: 38px !important;
      height: 38px !important;
      line-height: 38px !important;
    }

    .send-btn:disabled {
      background: var(--border-subtle) !important;
      color: var(--text-muted) !important;
    }
  `]
})
export class ChatWidgetComponent implements OnInit, AfterViewChecked {
  @ViewChild('scrollContainer') private scrollContainer?: ElementRef;

  isOpen = false;
  loading = false;
  messages: ChatMessage[] = [];
  starterInfo: StarterPrompts | null = null;
  userInput = '';
  errorMessage = '';

  constructor(private chatService: ChatService) {}

  ngOnInit(): void {
    this.loadStarterPrompts();
    this.loadChatHistory();
  }

  ngAfterViewChecked(): void {
    this.scrollToBottom();
  }

  toggleChat(): void {
    this.isOpen = !this.isOpen;
    if (this.isOpen) {
      setTimeout(() => this.scrollToBottom(), 100);
    }
  }

  loadStarterPrompts(): void {
    this.chatService.getStarterPrompts().subscribe({
      next: (data) => (this.starterInfo = data),
      error: (err) => console.error('Failed to load starter prompts', err)
    });
  }

  loadChatHistory(): void {
    this.chatService.getHistory().subscribe({
      next: (session) => {
        this.messages = session.messages || [];
      },
      error: (err) => console.error('Failed to load chat history', err)
    });
  }

  clearChat(): void {
    this.chatService.clearHistory().subscribe({
      next: () => {
        this.messages = [];
        this.errorMessage = '';
      },
      error: (err) => console.error('Failed to clear chat', err)
    });
  }

  sendStarterPrompt(prompt: string): void {
    this.userInput = prompt;
    this.sendMessage();
  }

  sendMessage(): void {
    const text = this.userInput.trim();
    if (!text || this.loading) return;

    this.errorMessage = '';
    this.userInput = '';

    // Optimistically show user message
    const tempUserMsg: ChatMessage = {
      id: 0,
      session_id: 0,
      sender_role: 'USER',
      content: text,
      created_at: new Date().toISOString()
    };
    this.messages.push(tempUserMsg);
    this.loading = true;

    this.chatService.sendMessage(text).subscribe({
      next: (asstMsg) => {
        this.messages.push(asstMsg);
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        if (err.status === 429) {
          this.errorMessage = err.error?.detail || 'Rate limit reached. Please wait before asking another question.';
        } else {
          this.errorMessage = err.error?.detail || 'Failed to receive AI response. Please try again.';
        }
      }
    });
  }

  setFeedback(msg: ChatMessage, type: 'UP' | 'DOWN'): void {
    if (!msg.id) return;
    this.chatService.submitFeedback(msg.id, type).subscribe({
      next: () => {
        msg.feedback = type;
      },
      error: (err) => console.error('Failed to record feedback', err)
    });
  }

  getFormattedLines(content: string): string[] {
    if (!content) return [];
    return content.split('\n').filter((l) => l.trim().length > 0);
  }

  private scrollToBottom(): void {
    try {
      if (this.scrollContainer) {
        this.scrollContainer.nativeElement.scrollTop = this.scrollContainer.nativeElement.scrollHeight;
      }
    } catch (err) {}
  }
}
