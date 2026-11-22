import { Component, computed, inject, HostListener, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
import { MatBadgeModule } from '@angular/material/badge';
import { AuthService } from '../core/services/auth.service';
import { NotificationService } from '../core/services/notification.service';
import { NotificationItem } from '../core/models/notification.model';
import { ChatWidgetComponent } from '../pages/shared/chatbot/chat-widget.component';

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    MatToolbarModule,
    MatSidenavModule,
    MatListModule,
    MatIconModule,
    MatButtonModule,
    MatMenuModule,
    MatDividerModule,
    MatBadgeModule,
    ChatWidgetComponent
  ],
  template: `
    <div class="layout-container">
      <!-- Mobile Drawer Backdrop -->
      <div class="mobile-drawer-backdrop" *ngIf="isMobileDrawerOpen()" (click)="closeMobileDrawer()"></div>

      <!-- Sidebar -->
      <aside class="sidebar" [class.collapsed]="isSidebarCollapsed()" [class.mobile-open]="isMobileDrawerOpen()">
        <div class="sidebar-brand">
          <div class="brand-logo">
            <img src="assets/logo.svg" alt="CSM Tech Logo" class="brand-logo-img" />
          </div>
          <div class="brand-text" *ngIf="!isSidebarCollapsed()">
            <h2>CSM Tech</h2>
            <span>L&amp;K Skill Hub</span>
          </div>
          <button type="button" class="sidebar-toggle-btn" (click)="toggleSidebar()" [attr.aria-label]="isSidebarCollapsed() ? 'Expand sidebar' : 'Collapse sidebar'" [title]="isSidebarCollapsed() ? 'Expand sidebar' : 'Collapse sidebar'">
            <mat-icon>{{ isSidebarCollapsed() ? 'chevron_right' : 'chevron_left' }}</mat-icon>
          </button>
        </div>

        <mat-divider class="sidebar-divider"></mat-divider>

        <nav class="nav-menu">
          <!-- ADMIN LINKS -->
          @if (userRole() === 'ADMIN') {
            <div class="nav-section-label" *ngIf="!isSidebarCollapsed()">OVERVIEW</div>
            <a mat-list-item routerLink="/admin/dashboard" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Admin Dashboard' : ''">
              <mat-icon matListItemIcon>dashboard</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Admin Dashboard</span>
            </a>
            <a mat-list-item routerLink="/admin/ceo-command-center" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'CEO Command Center' : ''">
              <mat-icon matListItemIcon>insights</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">CEO Command Center</span>
            </a>

            <div class="nav-section-label" *ngIf="!isSidebarCollapsed()">CORE MANAGEMENT</div>
            <a mat-list-item routerLink="/admin/cohorts" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Cohorts' : ''">
              <mat-icon matListItemIcon>groups</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Cohorts</span>
            </a>
            <a mat-list-item routerLink="/admin/users" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'User Management' : ''">
              <mat-icon matListItemIcon>people_outline</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">User Management</span>
            </a>
            <a mat-list-item routerLink="/admin/assignments" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Mentor-ASE Mapping' : ''">
              <mat-icon matListItemIcon>link</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Mentor-ASE Mapping</span>
            </a>
            <a mat-list-item routerLink="/admin/accommodations" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Accommodations' : ''">
              <mat-icon matListItemIcon>health_and_safety</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Accommodations</span>
            </a>
            <a mat-list-item routerLink="/admin/staffing" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Staffing Matching' : ''">
              <mat-icon matListItemIcon>work_outline</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Staffing Matching</span>
            </a>

            <div class="nav-section-label" *ngIf="!isSidebarCollapsed()">ASSESSMENTS</div>
            <a mat-list-item routerLink="/admin/assessments" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Assessments' : ''">
              <mat-icon matListItemIcon>assignment</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Assessments</span>
            </a>
            <a mat-list-item routerLink="/admin/assessments/question-bank" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Question Bank' : ''">
              <mat-icon matListItemIcon>quiz</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Question Bank</span>
            </a>
            <a mat-list-item routerLink="/admin/question-analytics" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Question Analytics' : ''">
              <mat-icon matListItemIcon>analytics</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Question Analytics</span>
            </a>

            <div class="nav-section-label" *ngIf="!isSidebarCollapsed()">LEARNING &amp; SESSIONS</div>
            <a mat-list-item routerLink="/admin/trainings" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Trainings' : ''">
              <mat-icon matListItemIcon>school</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Trainings</span>
            </a>
            <a mat-list-item routerLink="/admin/classes" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Live Classes' : ''">
              <mat-icon matListItemIcon>videocam</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Live Classes</span>
            </a>
            <a mat-list-item routerLink="/admin/schedule" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Schedule' : ''">
              <mat-icon matListItemIcon>calendar_month</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Schedule</span>
            </a>
            <a mat-list-item routerLink="/admin/quotes" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Motivational Quotes' : ''">
              <mat-icon matListItemIcon>format_quote</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Motivational Quotes</span>
            </a>
            <a mat-list-item routerLink="/forum" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Doubt Forum' : ''">
              <mat-icon matListItemIcon>question_answer</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Doubt Forum</span>
            </a>

            <div class="nav-section-label" *ngIf="!isSidebarCollapsed()">SYSTEM &amp; AUDIT</div>
            <a mat-list-item routerLink="/admin/llm-usage" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'AI Token Usage' : ''">
              <mat-icon matListItemIcon>token</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">AI Token Usage</span>
            </a>
            <a mat-list-item routerLink="/admin/exports" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Data Exports & BI' : ''">
              <mat-icon matListItemIcon>download</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Data Exports & BI</span>
            </a>
            <a mat-list-item routerLink="/admin/audit-logs" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Admin Audit Logs' : ''">
              <mat-icon matListItemIcon>security</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Admin Audit Logs</span>
            </a>
          }

          <!-- MENTOR LINKS -->
          @if (userRole() === 'MENTOR') {
            <div class="nav-section-label" *ngIf="!isSidebarCollapsed()">OVERVIEW</div>
            <a mat-list-item routerLink="/mentor/dashboard" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Mentor Dashboard' : ''">
              <mat-icon matListItemIcon>dashboard</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Mentor Dashboard</span>
            </a>

            <div class="nav-section-label" *ngIf="!isSidebarCollapsed()">MENTORING</div>
            <a mat-list-item routerLink="/mentor/one-on-one" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? '1-on-1 Mentoring' : ''">
              <mat-icon matListItemIcon>forum</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">1-on-1 Mentoring</span>
            </a>
            <a mat-list-item routerLink="/mentor/mentees" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Assigned Mentees' : ''">
              <mat-icon matListItemIcon>group</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Assigned Mentees</span>
            </a>
            <a mat-list-item routerLink="/mentor/buddies" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Peer Buddy Hub' : ''">
              <mat-icon matListItemIcon>people_alt</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Peer Buddy Hub</span>
            </a>

            <div class="nav-section-label" *ngIf="!isSidebarCollapsed()">TRAINING &amp; EVALUATION</div>
            <a mat-list-item routerLink="/mentor/cohorts" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Cohorts' : ''">
              <mat-icon matListItemIcon>groups</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Cohorts</span>
            </a>
            <a mat-list-item routerLink="/mentor/trainings" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Trainings' : ''">
              <mat-icon matListItemIcon>school</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Trainings</span>
            </a>
            <a mat-list-item routerLink="/mentor/classes" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Live Classes' : ''">
              <mat-icon matListItemIcon>videocam</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Live Classes</span>
            </a>
            <a mat-list-item routerLink="/mentor/assessments" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Assign Assessments' : ''">
              <mat-icon matListItemIcon>assignment_ind</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Assign Assessments</span>
            </a>
            <a mat-list-item routerLink="/mentor/results" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Mentees Results' : ''">
              <mat-icon matListItemIcon>insights</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Mentees Results</span>
            </a>
            <a mat-list-item routerLink="/mentor/question-analytics" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Question Analytics' : ''">
              <mat-icon matListItemIcon>analytics</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Question Analytics</span>
            </a>
            <a mat-list-item routerLink="/mentor/schedule" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Schedule' : ''">
              <mat-icon matListItemIcon>calendar_month</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Schedule</span>
            </a>
            <a mat-list-item routerLink="/mentor/accommodations" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Accommodations' : ''">
              <mat-icon matListItemIcon>health_and_safety</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Accommodations</span>
            </a>

            <div class="nav-section-label" *ngIf="!isSidebarCollapsed()">COMMUNITY &amp; TOOLS</div>
            <a mat-list-item routerLink="/forum" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Doubt Forum' : ''">
              <mat-icon matListItemIcon>question_answer</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Doubt Forum</span>
            </a>
            <a mat-list-item routerLink="/mentor/exports" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Export Mentees Data' : ''">
              <mat-icon matListItemIcon>download</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Export Mentees Data</span>
            </a>
            <a mat-list-item routerLink="/mentor/staffing" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Staffing Matching' : ''">
              <mat-icon matListItemIcon>work_outline</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Staffing Matching</span>
            </a>
          }

          <!-- ASE LINKS -->
          @if (userRole() === 'ASE') {
            <div class="nav-section-label" *ngIf="!isSidebarCollapsed()">OVERVIEW</div>
            <a mat-list-item routerLink="/ase/dashboard" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'My Dashboard' : ''">
              <mat-icon matListItemIcon>dashboard</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">My Dashboard</span>
            </a>

            <div class="nav-section-label" *ngIf="!isSidebarCollapsed()">MY LEARNING &amp; TESTS</div>
            <a mat-list-item routerLink="/ase/learning" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'My Learning' : ''">
              <mat-icon matListItemIcon>school</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">My Learning</span>
            </a>
            <a mat-list-item routerLink="/ase/my-assessments" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'My Assessments' : ''">
              <mat-icon matListItemIcon>assignment_turned_in</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">My Assessments</span>
            </a>
            <a mat-list-item routerLink="/ase/schedule" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'My Schedule' : ''">
              <mat-icon matListItemIcon>calendar_month</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">My Schedule</span>
            </a>

            <div class="nav-section-label" *ngIf="!isSidebarCollapsed()">COLLABORATION &amp; SUPPORT</div>
            <a mat-list-item routerLink="/ase/one-on-one" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? '1-on-1 Notes & Goals' : ''">
              <mat-icon matListItemIcon>forum</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">1-on-1 Notes & Goals</span>
            </a>
            <a mat-list-item routerLink="/ase/buddy" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Peer Buddy Hub' : ''">
              <mat-icon matListItemIcon>handshake</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Peer Buddy Hub</span>
            </a>
            <a mat-list-item routerLink="/forum" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Cohort Doubt Forum' : ''">
              <mat-icon matListItemIcon>question_answer</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Cohort Doubt Forum</span>
            </a>
            <a mat-list-item routerLink="/ase/accommodations" routerLinkActive="active" class="nav-item" [title]="isSidebarCollapsed() ? 'Accommodations' : ''">
              <mat-icon matListItemIcon>health_and_safety</mat-icon>
              <span matListItemTitle *ngIf="!isSidebarCollapsed()">Accommodations</span>
            </a>
          }
        </nav>

        <div class="sidebar-footer">
          <div class="user-pill">
            <div class="user-avatar">{{ userInitials() }}</div>
            <div class="user-meta" *ngIf="!isSidebarCollapsed()">
              <span class="user-name">{{ currentUser()?.name }}</span>
              <span class="user-role">{{ currentUser()?.role }}</span>
            </div>
          </div>
          <button type="button" class="sidebar-logout-btn" (click)="logout()" [title]="isSidebarCollapsed() ? 'Logout' : ''" aria-label="Logout">
            <mat-icon>logout</mat-icon>
            <span *ngIf="!isSidebarCollapsed()">Logout</span>
          </button>
        </div>
      </aside>

      <!-- Main Content Area -->
      <div class="main-wrapper">
        <!-- Header -->
        <header class="topbar">
          <div class="topbar-left">
            <button mat-icon-button class="mobile-hamburger-btn" (click)="toggleMobileDrawer()" aria-label="Toggle navigation drawer">
              <mat-icon>menu</mat-icon>
            </button>
            <span class="portal-badge" [ngClass]="'badge-' + (userRole()?.toLowerCase() || 'ase')">
              {{ userRole() }} PORTAL
            </span>
            <span class="demo-ai-chip" title="Demo AI Mode with Mock Fallbacks Active">
              <mat-icon class="icon-16">smart_toy</mat-icon>
              <span>Demo AI Mode</span>
            </span>
            <button class="quick-jump-trigger" (click)="openCommandPalette()" title="Press Ctrl+K">
              <mat-icon>search</mat-icon>
              <span>Quick Jump</span>
              <kbd>Ctrl+K</kbd>
            </button>
          </div>

          <div class="topbar-right">
            <!-- Notification Bell (Phase 5) -->
            <button mat-icon-button [matMenuTriggerFor]="notifMenu" class="notif-bell-btn" title="Notifications">
              <mat-icon [matBadge]="unreadCount()" [matBadgeHidden]="unreadCount() === 0" matBadgeColor="warn">
                notifications
              </mat-icon>
            </button>

            <mat-menu #notifMenu="matMenu" class="notif-menu-panel">
              <div class="notif-header" (click)="$event.stopPropagation()">
                <div class="notif-title-box">
                  <strong>Notifications</strong>
                  <span class="unread-pill" *ngIf="unreadCount() > 0">{{ unreadCount() }} unread</span>
                </div>
                <button mat-button color="primary" class="btn-mark-all" (click)="markAllRead()" *ngIf="unreadCount() > 0">
                  Mark all read
                </button>
              </div>
              <mat-divider></mat-divider>
              <div class="notif-list-container" (click)="$event.stopPropagation()">
                <div class="notif-empty" *ngIf="notifications().length === 0">
                  <mat-icon>notifications_off</mat-icon>
                  <span>No notifications yet</span>
                </div>
                <div class="notif-item" *ngFor="let n of notifications()" [class.unread]="!n.is_read">
                  <div class="notif-icon-col" [ngClass]="'icon-' + n.type.toLowerCase()">
                    <mat-icon>{{ getNotifIcon(n.type) }}</mat-icon>
                  </div>
                  <div class="notif-text-col">
                    <div class="notif-top">
                      <span class="n-title">{{ n.title }}</span>
                      <span class="n-time">{{ n.created_at | date:'shortTime' }}</span>
                    </div>
                    <p class="n-msg">{{ n.message }}</p>
                    <div class="n-bottom">
                      <a *ngIf="n.link" [routerLink]="n.link" class="n-link" (click)="markRead(n)">View Details</a>
                      <button *ngIf="!n.is_read" mat-button class="n-btn" (click)="markRead(n)">Mark read</button>
                    </div>
                  </div>
                </div>
              </div>
            </mat-menu>

            <div class="user-dropdown-info">
              <span class="name">{{ currentUser()?.name }}</span>
              <span class="email">{{ currentUser()?.email }}</span>
            </div>

            <button mat-icon-button [matMenuTriggerFor]="userMenu" class="avatar-btn" aria-label="User menu">
              <div class="header-avatar">{{ userInitials() }}</div>
            </button>

            <mat-menu #userMenu="matMenu">
              <div class="menu-header">
                <strong>{{ currentUser()?.name }}</strong>
                <p>{{ currentUser()?.email }}</p>
                <span class="badge" [ngClass]="'badge-' + (userRole()?.toLowerCase() || 'ase')">
                  {{ userRole() }}
                </span>
              </div>
              <mat-divider></mat-divider>
              <button mat-menu-item (click)="openProfileModal()">
                <mat-icon>account_circle</mat-icon>
                <span>Profile Details</span>
              </button>
              <button mat-menu-item (click)="openNotificationPrefs()">
                <mat-icon>notifications_active</mat-icon>
                <span>Notification Preferences</span>
              </button>
              <button mat-menu-item (click)="openChangePassword()">
                <mat-icon>lock_reset</mat-icon>
                <span>Change Password</span>
              </button>
              <button mat-menu-item (click)="logout()">
                <mat-icon color="warn">logout</mat-icon>
                <span>Logout</span>
              </button>
            </mat-menu>
          </div>
        </header>

        <!-- Breadcrumbs Trail -->
        <nav class="breadcrumb-container" *ngIf="breadcrumbs().length > 1" aria-label="Breadcrumbs">
          <a routerLink="/" class="breadcrumb-item breadcrumb-home" title="Home">
            <mat-icon class="icon-16">home</mat-icon>
          </a>
          <ng-container *ngFor="let crumb of breadcrumbs(); let last = last">
            <mat-icon class="breadcrumb-separator icon-16">chevron_right</mat-icon>
            <a *ngIf="!last" [routerLink]="crumb.url" class="breadcrumb-item breadcrumb-link">{{ crumb.label }}</a>
            <span *ngIf="last" class="breadcrumb-item breadcrumb-active" aria-current="page">{{ crumb.label }}</span>
          </ng-container>
        </nav>

        <!-- Dynamic Content -->
        <main class="page-content">
          <router-outlet></router-outlet>
        </main>

        <!-- User Profile Modal -->
        <div class="cmd-palette-backdrop" *ngIf="showProfileModal" (click)="closeProfileModal()">
          <div class="profile-card" (click)="$event.stopPropagation()">
            <div class="pref-header">
              <h3><mat-icon>account_circle</mat-icon> User Profile</h3>
              <button mat-icon-button (click)="closeProfileModal()" aria-label="Close profile modal"><mat-icon>close</mat-icon></button>
            </div>
            <div class="pref-body">
              <div class="profile-avatar-row">
                <div class="profile-avatar-large">{{ userInitials() }}</div>
                <div class="profile-avatar-meta">
                  <h4>{{ currentUser()?.name }}</h4>
                  <span class="badge" [ngClass]="'badge-' + (userRole()?.toLowerCase() || 'ase')">{{ userRole() }}</span>
                </div>
              </div>
              <div class="profile-details-grid">
                <div class="profile-field">
                  <label>Email Address</label>
                  <span>{{ currentUser()?.email }}</span>
                </div>
                <div class="profile-field">
                  <label>Authorized Domain</label>
                  <span class="domain-verified"><mat-icon>verified</mat-icon> @csm.tech</span>
                </div>
                <div class="profile-field">
                  <label>Assigned Role</label>
                  <span>{{ userRole() }}</span>
                </div>
                <div class="profile-field">
                  <label>Account Status</label>
                  <span class="status-active"><mat-icon>check_circle</mat-icon> Active</span>
                </div>
              </div>
            </div>
            <div class="pref-footer">
              <button mat-flat-button color="primary" (click)="closeProfileModal()">Close</button>
            </div>
          </div>
        </div>

        <!-- Phase 6 Floating AI Chatbot Widget -->
        <app-chat-widget></app-chat-widget>

        <!-- Phase 9 Command Palette (Ctrl+K) -->
        <div class="cmd-palette-backdrop" *ngIf="isCommandPaletteOpen" (click)="closeCommandPalette()">
          <div class="cmd-palette-box" (click)="$event.stopPropagation()">
            <div class="cmd-input-header">
              <mat-icon>search</mat-icon>
              <input
                type="text"
                placeholder="Jump to section or tool..."
                [(ngModel)]="searchQuery"
                (ngModelChange)="filterNavItems()"
                #cmdInput
              />
              <span class="esc-badge" (click)="closeCommandPalette()">ESC</span>
            </div>
            <div class="cmd-results">
              <div
                *ngFor="let item of filteredNavItems; let idx = index"
                class="cmd-item"
                [class.selected]="idx === selectedIndex"
                (click)="navigateItem(item)"
              >
                <mat-icon class="cmd-item-icon">{{ item.icon }}</mat-icon>
                <div class="cmd-item-info">
                  <span class="cmd-item-title">{{ item.title }}</span>
                  <span class="cmd-item-sub">{{ item.description }}</span>
                </div>
                <span class="cmd-jump-arrow">↵</span>
              </div>
              <div *ngIf="filteredNavItems.length === 0" class="cmd-no-results">
                No matching navigation routes found.
              </div>
            </div>
            <div class="cmd-footer">
              <span>Navigation filtered for <strong>{{ userRole() }}</strong> role • Privacy Protected</span>
            </div>
          </div>
        </div>

        <!-- Phase 9 Onboarding Tour -->
        <div class="tour-backdrop" *ngIf="showTourModal">
          <div class="tour-card">
            <div class="tour-header">
              <span class="tour-step-badge">Platform Tour • Step {{ tourStep + 1 }}/3</span>
              <h2>{{ tourSteps[tourStep].title }}</h2>
            </div>
            <div class="tour-body">
              <div class="tour-illustration">{{ tourSteps[tourStep].icon }}</div>
              <p>{{ tourSteps[tourStep].text }}</p>
            </div>
            <div class="tour-footer">
              <button class="btn-tour-skip" (click)="dismissTour()">Skip Tour</button>
              <div class="tour-btn-group">
                <button *ngIf="tourStep > 0" class="btn-tour-secondary" (click)="tourStep = tourStep - 1">Back</button>
                <button *ngIf="tourStep < tourSteps.length - 1" class="btn-tour-primary" (click)="tourStep = tourStep + 1">Next</button>
                <button *ngIf="tourStep === tourSteps.length - 1" class="btn-tour-primary" (click)="dismissTour()">Got it, Start!</button>
              </div>
            </div>
          </div>
        </div>

        <!-- Phase 13: Notification Preferences Dialog -->
        <div class="cmd-palette-backdrop" *ngIf="showNotifPrefsModal" (click)="showNotifPrefsModal = false">
          <div class="notif-pref-card" (click)="$event.stopPropagation()">
            <div class="pref-header">
              <h3><mat-icon>tune</mat-icon> Notification Preferences</h3>
              <button mat-icon-button (click)="showNotifPrefsModal = false"><mat-icon>close</mat-icon></button>
            </div>
            <div class="pref-body">
              <p class="pref-desc">Manage notification channels and configure your quiet hours schedule.</p>

              <div class="pref-section">
                <label class="section-title">Delivery Channels</label>
                <div class="pref-checks">
                  <label class="cb-item">
                    <input type="checkbox" [(ngModel)]="prefInApp"> In-App Portal Notifications
                  </label>
                  <label class="cb-item">
                    <input type="checkbox" [(ngModel)]="prefEmail"> Email Updates
                  </label>
                  <label class="cb-item">
                    <input type="checkbox" [(ngModel)]="prefTeams"> Microsoft Teams Bot
                  </label>
                </div>
              </div>

              <div class="pref-section">
                <label class="section-title">Quiet Hours</label>
                <label class="cb-item">
                  <input type="checkbox" [(ngModel)]="prefQuietEnabled"> Enable Quiet Hours
                </label>
                <div class="quiet-grid" *ngIf="prefQuietEnabled">
                  <div class="input-block">
                    <span>Start Time</span>
                    <input type="text" [(ngModel)]="prefQuietStart" placeholder="22:00">
                  </div>
                  <div class="input-block">
                    <span>End Time</span>
                    <input type="text" [(ngModel)]="prefQuietEnd" placeholder="07:00">
                  </div>
                  <div class="input-block">
                    <span>Timezone</span>
                    <input type="text" [(ngModel)]="prefTimezone" placeholder="UTC">
                  </div>
                </div>
                <div class="quiet-hint" *ngIf="prefQuietEnabled">
                  <mat-icon>info</mat-icon> Routine reminders are deferred during quiet hours. Critical alerts (test or class starting) bypass quiet hours.
                </div>
              </div>
            </div>
            <div class="pref-footer">
              <button mat-button (click)="showNotifPrefsModal = false">Cancel</button>
              <button mat-flat-button color="primary" (click)="saveNotifPrefs()">Save Preferences</button>
            </div>
          </div>
        </div>

        <!-- Change Password Modal -->
        <div class="cmd-palette-backdrop" *ngIf="showChangePasswordModal" (click)="closeChangePassword()">
          <div class="change-pwd-card" (click)="$event.stopPropagation()">
            <div class="pref-header">
              <h3><mat-icon>lock_reset</mat-icon> Change Password</h3>
              <button mat-icon-button *ngIf="!forceChangePassword" (click)="closeChangePassword()"><mat-icon>close</mat-icon></button>
            </div>
            <div class="pref-body">
              <div class="force-pwd-alert" *ngIf="forceChangePassword">
                <mat-icon>security</mat-icon>
                <span>Security Notice: You must update your password before proceeding.</span>
              </div>
              <p class="pref-desc" *ngIf="!forceChangePassword">Choose a strong, unique password to secure your account.</p>

              <div class="pwd-error-banner" *ngIf="changePwdError">
                <mat-icon>error_outline</mat-icon>
                <span>{{ changePwdError }}</span>
              </div>

              <div class="pwd-input-group">
                <label>Current Password</label>
                <div class="pwd-field-wrap">
                  <input [type]="showHideCurrent ? 'text' : 'password'" [(ngModel)]="changePwdCurrent" placeholder="Enter current password" />
                  <button type="button" class="eye-btn" (click)="showHideCurrent = !showHideCurrent">
                    <mat-icon>{{ showHideCurrent ? 'visibility_off' : 'visibility' }}</mat-icon>
                  </button>
                </div>
              </div>

              <div class="pwd-input-group">
                <label>New Password</label>
                <div class="pwd-field-wrap">
                  <input [type]="showHideNew ? 'text' : 'password'" [(ngModel)]="changePwdNew" placeholder="Enter new strong password" />
                  <button type="button" class="eye-btn" (click)="showHideNew = !showHideNew">
                    <mat-icon>{{ showHideNew ? 'visibility_off' : 'visibility' }}</mat-icon>
                  </button>
                </div>
              </div>

              <div class="pwd-input-group">
                <label>Confirm New Password</label>
                <div class="pwd-field-wrap">
                  <input [type]="showHideConfirm ? 'text' : 'password'" [(ngModel)]="changePwdConfirm" placeholder="Re-enter new password" />
                  <button type="button" class="eye-btn" (click)="showHideConfirm = !showHideConfirm">
                    <mat-icon>{{ showHideConfirm ? 'visibility_off' : 'visibility' }}</mat-icon>
                  </button>
                </div>
              </div>

              <!-- Password Requirements Checklist -->
              <div class="pwd-requirements">
                <span class="req-title">Password must contain:</span>
                <ul>
                  <li [class.met]="changePwdNew.length >= 8">
                    <mat-icon>{{ changePwdNew.length >= 8 ? 'check_circle' : 'radio_button_unchecked' }}</mat-icon>
                    <span>At least 8 characters</span>
                  </li>
                  <li [class.met]="hasUpper(changePwdNew)">
                    <mat-icon>{{ hasUpper(changePwdNew) ? 'check_circle' : 'radio_button_unchecked' }}</mat-icon>
                    <span>At least one uppercase letter (A-Z)</span>
                  </li>
                  <li [class.met]="hasLower(changePwdNew)">
                    <mat-icon>{{ hasLower(changePwdNew) ? 'check_circle' : 'radio_button_unchecked' }}</mat-icon>
                    <span>At least one lowercase letter (a-z)</span>
                  </li>
                  <li [class.met]="hasDigit(changePwdNew)">
                    <mat-icon>{{ hasDigit(changePwdNew) ? 'check_circle' : 'radio_button_unchecked' }}</mat-icon>
                    <span>At least one numeric digit (0-9)</span>
                  </li>
                  <li [class.met]="hasSpecial(changePwdNew)">
                    <mat-icon>{{ hasSpecial(changePwdNew) ? 'check_circle' : 'radio_button_unchecked' }}</mat-icon>
                    <span>At least one special symbol (!@#$%^&amp;*...)</span>
                  </li>
                  <li [class.met]="changePwdConfirm.length > 0 && changePwdConfirm === changePwdNew">
                    <mat-icon>{{ changePwdConfirm.length > 0 && changePwdConfirm === changePwdNew ? 'check_circle' : 'radio_button_unchecked' }}</mat-icon>
                    <span>Passwords match</span>
                  </li>
                </ul>
              </div>
            </div>
            <div class="pref-footer">
              <button mat-button *ngIf="!forceChangePassword" (click)="closeChangePassword()">Cancel</button>
              <button mat-flat-button color="primary" [disabled]="changePwdLoading || !isChangePwdFormValid()" (click)="submitChangePassword()">
                {{ changePwdLoading ? 'Updating Password...' : 'Change Password' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .layout-container {
      display: flex;
      min-height: 100vh;
      background-color: var(--bg-main);
    }

    .sidebar {
      width: 260px;
      background-color: var(--sidebar-bg);
      color: var(--sidebar-text);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
      box-shadow: 2px 0 10px rgba(0, 0, 0, 0.1);
      transition: width 0.25s ease, left 0.25s ease;
      position: relative;
      z-index: 100;

      &.collapsed {
        width: 68px;

        .brand-text { display: none !important; }
        .nav-section-label { display: none !important; }
        .sidebar-divider { margin: 0 8px; }
        .nav-menu .nav-item {
          justify-content: center;
          padding: 0 !important;
          mat-icon { margin-right: 0 !important; }
          span[matListItemTitle] { display: none !important; }
        }
        .user-meta { display: none !important; }
        .user-pill { justify-content: center; padding: 8px 4px; }
        .sidebar-logout-btn span { display: none !important; }
        .sidebar-logout-btn { justify-content: center; }
      }
    }

    .sidebar-brand {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 20px 16px;
      gap: 8px;

      .brand-logo {
        width: 38px;
        height: 38px;
        background-color: var(--csm-accent);
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #ffffff;
        flex-shrink: 0;

        mat-icon {
          font-size: 24px;
          width: 24px;
          height: 24px;
        }
      }

      .brand-text {
        flex: 1;
        overflow: hidden;

        h2 {
          font-size: 1.15rem;
          font-weight: 700;
          color: #ffffff;
          margin: 0;
          letter-spacing: -0.02em;
        }

        span {
          font-size: 0.72rem;
          color: var(--sidebar-muted);
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
      }

      .sidebar-toggle-btn {
        background: transparent;
        border: none;
        color: var(--sidebar-muted);
        cursor: pointer;
        padding: 4px;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;

        &:hover {
          background: rgba(255, 255, 255, 0.1);
          color: #ffffff;
        }
      }
    }

    .sidebar-divider {
      border-top-color: rgba(255, 255, 255, 0.12) !important;
      margin: 0 16px;
    }

    .nav-section-label {
      padding: 20px 20px 8px;
      font-size: 0.68rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      color: #93c5fd;
    }

    .nav-menu {
      flex: 1;
      padding: 0 12px;
      display: flex;
      flex-direction: column;
      gap: 6px;

      .nav-item {
        color: #e2e8f0 !important;
        border-radius: 8px !important;
        font-weight: 500;
        transition: all 0.2s ease;
        height: 44px;
        text-decoration: none !important;

        mat-icon {
          color: #93c5fd !important;
          margin-right: 12px;
        }

        &:hover {
          background-color: rgba(255, 255, 255, 0.12) !important;
          color: #ffffff !important;
          text-decoration: none !important;
        }

        &.active {
          background-color: #2563eb !important;
          color: #ffffff !important;
          font-weight: 600;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);

          mat-icon {
            color: #ffffff !important;
          }
        }

        &:focus-visible {
          outline: 2px solid #93c5fd !important;
          outline-offset: 2px !important;
        }
      }
    }

    .sidebar-footer {
      padding: 16px;
      border-top: 1px solid rgba(255, 255, 255, 0.12);
      display: flex;
      flex-direction: column;
      gap: 10px;

      .user-pill {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 12px;
        background-color: rgba(255, 255, 255, 0.06);
        border-radius: 10px;

        .user-avatar {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          background-color: var(--csm-accent);
          color: #ffffff;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 700;
          font-size: 0.85rem;
        }

        .user-meta {
          display: flex;
          flex-direction: column;
          overflow: hidden;

          .user-name {
            font-size: 0.85rem;
            font-weight: 600;
            color: #ffffff;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          }

          .user-role {
            font-size: 0.7rem;
            color: #fdba74;
            font-weight: 600;
          }
        }
      }

      .sidebar-logout-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        width: 100%;
        padding: 8px 12px;
        background: rgba(239, 68, 68, 0.15);
        border: 1px solid rgba(239, 68, 68, 0.35);
        border-radius: 8px;
        color: #fca5a5;
        font-size: 0.82rem;
        font-weight: 600;
        cursor: pointer;
        text-decoration: none !important;
        transition: all 0.2s ease;

        mat-icon {
          font-size: 18px !important;
          width: 18px !important;
          height: 18px !important;
          color: #fca5a5;
        }

        &:hover {
          background: #dc2626;
          color: #ffffff;
          border-color: #dc2626;

          mat-icon {
            color: #ffffff;
          }
        }

        &:focus-visible {
          outline: 2px solid #f87171 !important;
          outline-offset: 2px !important;
        }
      }
    }

    .main-wrapper {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
    }

    .topbar {
      height: 64px;
      background-color: var(--bg-card);
      border-bottom: 1px solid var(--border-light);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 24px;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);

      .topbar-left {
        display: flex;
        align-items: center;
        gap: 12px;

        .mobile-hamburger-btn {
          display: none;
          color: var(--text-primary);
        }

        .portal-badge {
          padding: 5px 12px;
          border-radius: var(--radius-full);
          font-size: 0.72rem;
          font-weight: 700;
          letter-spacing: 0.05em;

          &.badge-admin {
            background-color: var(--color-danger-bg);
            color: var(--color-danger-text);
          }

          &.badge-mentor {
            background-color: var(--color-info-bg);
            color: var(--color-info-text);
          }

          &.badge-ase {
            background-color: var(--accent-light);
            color: var(--accent-hover);
          }
        }

        .demo-ai-chip {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          background: var(--primary-light);
          color: var(--csm-primary);
          border: 1px solid var(--primary-border);
          padding: 3px 8px;
          border-radius: var(--radius-full);
          font-size: 0.72rem;
          font-weight: 600;
        }
      }

      .topbar-right {
        display: flex;
        align-items: center;
        gap: 16px;

        .notif-bell-btn {
          margin-right: 8px;
          color: #475569;
        }

        .user-dropdown-info {
          display: flex;
          flex-direction: column;
          align-items: flex-end;

          .name {
            font-size: 0.875rem;
            font-weight: 600;
            color: var(--text-primary);
          }

          .email {
            font-size: 0.75rem;
            color: var(--text-muted);
          }
        }

        .avatar-btn {
          padding: 0;
          min-width: 0;
          width: 40px;
          height: 40px;
        }

        .header-avatar {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          background-color: var(--csm-primary);
          color: #ffffff;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 600;
          font-size: 0.9rem;
          cursor: pointer;
        }
      }
    }

    .menu-header {
      padding: 12px 16px;

      strong {
        display: block;
        font-size: 0.9rem;
        color: #0f172a;
      }

      p {
        margin: 2px 0 8px;
        font-size: 0.8rem;
        color: #64748b;
      }
    }

    .page-content {
      flex: 1;
      padding: 32px;
      max-width: 1320px;
      width: 100%;
      margin: 0 auto;
    }

    /* Notification Panel Styles */
    .notif-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 16px;
      min-width: 320px;
    }

    .notif-title-box {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .unread-pill {
      background: #FEF2F2;
      color: #DC2626;
      font-size: 0.72rem;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 10px;
    }

    .btn-mark-all {
      font-size: 0.75rem;
      padding: 0 8px;
      height: 28px;
    }

    .notif-list-container {
      max-height: 380px;
      overflow-y: auto;
      min-width: 340px;
    }

    .notif-empty {
      padding: 32px 16px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      color: #94A3B8;
      font-size: 0.85rem;
    }

    .notif-empty mat-icon {
      font-size: 32px;
      width: 32px;
      height: 32px;
    }

    .notif-item {
      display: flex;
      gap: 12px;
      padding: 12px 16px;
      border-bottom: 1px solid #F1F5F9;
      transition: background 0.15s ease;
    }

    .notif-item.unread {
      background: #F8FAFC;
      border-left: 3px solid var(--csm-primary);
    }

    .notif-icon-col {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .notif-icon-col mat-icon {
      font-size: 20px;
      width: 20px;
      height: 20px;
    }

    .icon-general { background: #EFF6FF; color: var(--csm-primary); }
    .icon-assessment { background: #FFF7ED; color: #EA580C; }
    .icon-training { background: #ECFDF5; color: #059669; }
    .icon-live_class { background: #F5F3FF; color: #7C3AED; }
    .icon-reminder { background: #FEF2F2; color: #DC2626; }

    .notif-text-col {
      flex: 1;
      display: flex;
      flex-direction: column;
    }

    .notif-top {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
    }

    .n-title {
      font-weight: 600;
      font-size: 0.85rem;
      color: #0F172A;
    }

    .n-time {
      font-size: 0.72rem;
      color: #94A3B8;
    }

    .n-msg {
      margin: 2px 0 6px 0;
      font-size: 0.78rem;
      color: #64748B;
      line-height: 1.3;
    }

    .n-bottom {
      display: flex;
      gap: 12px;
      align-items: center;
    }

    .n-link {
      font-size: 0.75rem;
      color: var(--csm-primary);
      font-weight: 600;
      text-decoration: none;
    }

    .n-btn {
      font-size: 0.72rem;
      padding: 0;
      height: 22px;
      min-width: 0;
      color: #64748B;
    }

    /* Phase 9 Quick Jump Button */
    .quick-jump-trigger {
      display: flex;
      align-items: center;
      gap: 6px;
      background: #F1F5F9;
      border: 1px solid #CBD5E1;
      border-radius: 6px;
      padding: 4px 10px;
      font-size: 12px;
      color: #475569;
      cursor: pointer;
      transition: all 0.2s;
      mat-icon { font-size: 16px; width: 16px; height: 16px; }
      kbd {
        background: white;
        border: 1px solid #94A3B8;
        border-radius: 4px;
        padding: 1px 4px;
        font-size: 10px;
        font-family: inherit;
        color: var(--csm-primary);
      }
    }
    .quick-jump-trigger:hover {
      background: #E2E8F0;
      border-color: #94A3B8;
    }

    /* Phase 9 Command Palette Modal */
    .cmd-palette-backdrop {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(15, 23, 42, 0.6);
      backdrop-filter: blur(2px);
      z-index: 99999;
      display: flex;
      align-items: flex-start;
      justify-content: center;
      padding-top: 15vh;
    }
    .cmd-palette-box {
      width: 100%;
      max-width: 560px;
      background: white;
      border-radius: 12px;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
      border: 1px solid #CBD5E1;
      overflow: hidden;
      animation: cmdFadeIn 0.15s ease-out;
    }
    @keyframes cmdFadeIn {
      from { opacity: 0; transform: scale(0.97); }
      to { opacity: 1; transform: scale(1); }
    }
    .cmd-input-header {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 14px 18px;
      border-bottom: 1px solid #E2E8F0;
      mat-icon { color: #64748B; }
      input {
        flex: 1;
        border: none;
        outline: none;
        font-size: 15px;
        color: #0F172A;
      }
    }
    .esc-badge {
      background: #F1F5F9;
      color: #64748B;
      font-size: 11px;
      padding: 2px 6px;
      border-radius: 4px;
      cursor: pointer;
    }
    .cmd-results {
      max-height: 320px;
      overflow-y: auto;
      padding: 8px;
    }
    .cmd-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 14px;
      border-radius: 8px;
      cursor: pointer;
      transition: background 0.15s;
    }
    .cmd-item:hover, .cmd-item.selected {
      background: #EFF6FF;
    }
    .cmd-item-icon {
      color: var(--csm-primary);
      font-size: 20px;
      width: 20px;
      height: 20px;
    }
    .cmd-item-info {
      flex: 1;
      display: flex;
      flex-direction: column;
    }
    .cmd-item-title {
      font-size: 14px;
      font-weight: 600;
      color: #0F172A;
    }
    .cmd-item-sub {
      font-size: 12px;
      color: #64748B;
    }
    .cmd-jump-arrow {
      color: #94A3B8;
      font-size: 16px;
    }
    .cmd-no-results {
      padding: 24px;
      text-align: center;
      color: #94A3B8;
      font-size: 13px;
    }
    .cmd-footer {
      padding: 10px 16px;
      background: #F8FAFC;
      border-top: 1px solid #E2E8F0;
      font-size: 11px;
      color: #64748B;
    }

    /* Phase 9 Onboarding Tour Modal */
    .tour-backdrop {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(15, 23, 42, 0.7);
      backdrop-filter: blur(3px);
      z-index: 99998;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    .tour-card {
      background: white;
      border-radius: 14px;
      width: 100%;
      max-width: 480px;
      padding: 28px;
      box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2);
    }
    .tour-step-badge {
      font-size: 11px;
      font-weight: 700;
      color: var(--csm-accent);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .tour-header h2 {
      margin: 4px 0 16px 0;
      font-size: 20px;
      color: var(--csm-primary);
    }
    .tour-body {
      display: flex;
      align-items: center;
      gap: 18px;
      margin-bottom: 24px;
    }
    .tour-illustration {
      font-size: 44px;
    }

    .notif-pref-card {
      background: #ffffff;
      border-radius: 12px;
      width: 480px;
      max-width: 95vw;
      box-shadow: 0 20px 25px -5px rgba(0,0,0,0.2);
      overflow: hidden;
    }
    .pref-header {
      padding: 16px 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid #e2e8f0;
      h3 { margin: 0; display: flex; align-items: center; gap: 8px; color: var(--csm-primary); font-size: 1.1rem; }
    }
    .pref-body { padding: 16px 20px; display: flex; flex-direction: column; gap: 16px; }
    .pref-desc { margin: 0; color: #64748b; font-size: 0.85rem; }
    .pref-section { display: flex; flex-direction: column; gap: 8px; }
    .section-title { font-weight: 600; font-size: 0.88rem; color: #1e293b; }
    .pref-checks { display: flex; flex-direction: column; gap: 6px; }
    .cb-item { display: flex; align-items: center; gap: 8px; font-size: 0.85rem; color: #334155; cursor: pointer; }
    .quiet-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 6px; }
    .input-block { display: flex; flex-direction: column; gap: 4px; span { font-size: 0.75rem; color: #64748b; } input { padding: 6px 8px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 0.85rem; } }
    .quiet-hint { font-size: 0.75rem; color: #64748b; display: flex; align-items: center; gap: 4px; mat-icon { font-size: 14px; width: 14px; height: 14px; } }
    .pref-footer { padding: 12px 20px; display: flex; justify-content: flex-end; gap: 10px; border-top: 1px solid #e2e8f0; }

    .change-pwd-card {
      background: #ffffff;
      border-radius: 12px;
      width: 480px;
      max-width: 95vw;
      box-shadow: 0 20px 25px -5px rgba(0,0,0,0.25);
      overflow: hidden;
    }
    .force-pwd-alert {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 14px;
      background: #fffbeb;
      border: 1px solid #fde68a;
      border-radius: 8px;
      color: #b45309;
      font-size: 0.85rem;
      mat-icon { color: #d97706; font-size: 20px; width: 20px; height: 20px; flex-shrink: 0; }
    }
    .pwd-error-banner {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 14px;
      background: #fee2e2;
      border: 1px solid #fecaca;
      border-radius: 8px;
      color: #991b1b;
      font-size: 0.85rem;
      mat-icon { font-size: 18px; width: 18px; height: 18px; flex-shrink: 0; }
    }
    .pwd-input-group {
      display: flex;
      flex-direction: column;
      gap: 4px;
      label { font-size: 0.8rem; font-weight: 600; color: #334155; }
      .pwd-field-wrap {
        position: relative;
        display: flex;
        align-items: center;
        input {
          width: 100%;
          height: 38px;
          border: 1.5px solid #cbd5e1;
          border-radius: 8px;
          padding: 0 38px 0 12px;
          font-size: 0.88rem;
          color: #0f172a;
          outline: none;
          box-sizing: border-box;
          &:focus { border-color: var(--csm-primary); }
        }
        .eye-btn {
          position: absolute;
          right: 8px;
          background: none;
          border: none;
          cursor: pointer;
          color: #64748b;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 4px;
          mat-icon { font-size: 18px; width: 18px; height: 18px; }
        }
      }
    }
    .pwd-requirements {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 12px;
      .req-title { font-size: 0.75rem; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.05em; display: block; margin-bottom: 6px; }
      ul {
        list-style: none;
        padding: 0;
        margin: 0;
        display: flex;
        flex-direction: column;
        gap: 4px;
        li {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 0.8rem;
          color: #64748b;
          mat-icon { font-size: 15px; width: 15px; height: 15px; color: #94a3b8; }
          &.met {
            color: #15803d;
            mat-icon { color: #16a34a; }
          }
        }
      }
    }
    .tour-body p {
      margin: 0;
      font-size: 14px;
      color: #334155;
      line-height: 1.5;
    }
    .tour-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-top: 1px solid #E2E8F0;
      padding-top: 16px;
    }
    .btn-tour-skip {
      background: none;
      border: none;
      color: #64748B;
      font-size: 13px;
      cursor: pointer;
    }
    .tour-btn-group {
      display: flex;
      gap: 8px;
    }
    .btn-tour-secondary {
      background: #F1F5F9;
      color: #475569;
      border: none;
      padding: 8px 14px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
    }
    .btn-tour-primary {
      background: var(--csm-primary);
      color: white;
      border: none;
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
    }

    /* Breadcrumbs Navigation Bar */
    .breadcrumb-container {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 10px 24px;
      background: var(--bg-card);
      border-bottom: 1px solid var(--border-subtle);
      font-size: 0.82rem;

      .breadcrumb-item {
        color: var(--text-muted);
        display: inline-flex;
        align-items: center;
        text-decoration: none;

        &.breadcrumb-link:hover {
          color: var(--primary-color);
          text-decoration: underline;
        }

        &.breadcrumb-active {
          color: var(--text-primary);
          font-weight: 600;
        }
      }

      .breadcrumb-separator {
        color: var(--border-light);
      }
    }

    /* User Profile Dialog Modal */
    .profile-card {
      background: var(--bg-card);
      border-radius: 16px;
      width: 440px;
      max-width: 90vw;
      border: 1px solid var(--border-light);
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.15);
      overflow: hidden;
      display: flex;
      flex-direction: column;

      .profile-avatar-row {
        display: flex;
        align-items: center;
        gap: 16px;
        padding-bottom: 16px;
        border-bottom: 1px solid var(--border-subtle);
        margin-bottom: 16px;

        .profile-avatar-large {
          width: 56px;
          height: 56px;
          border-radius: 50%;
          background: var(--csm-primary);
          color: #ffffff;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 1.25rem;
          font-weight: 700;
        }

        .profile-avatar-meta h4 {
          margin: 0 0 6px 0;
          font-size: 1.1rem;
          color: var(--text-primary);
        }
      }

      .profile-details-grid {
        display: flex;
        flex-direction: column;
        gap: 12px;

        .profile-field {
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 0.88rem;

          label {
            color: var(--text-secondary);
            font-weight: 500;
          }

          span {
            color: var(--text-primary);
            font-weight: 600;

            &.domain-verified {
              color: var(--color-success);
              display: inline-flex;
              align-items: center;
              gap: 4px;
              mat-icon { font-size: 16px; width: 16px; height: 16px; }
            }

            &.status-active {
              color: var(--color-success);
              display: inline-flex;
              align-items: center;
              gap: 4px;
              mat-icon { font-size: 16px; width: 16px; height: 16px; }
            }
          }
        }
      }
    }

    /* Mobile Drawer Styles & Media Queries */
    .mobile-drawer-backdrop {
      display: none;
    }

    @media (max-width: 768px) {
      .mobile-hamburger-btn {
        display: inline-flex !important;
      }

      .mobile-drawer-backdrop {
        display: block;
        position: fixed;
        inset: 0;
        background: rgba(15, 23, 42, 0.6);
        z-index: 1099;
      }

      .sidebar {
        position: fixed;
        top: 0;
        bottom: 0;
        left: -280px;
        z-index: 1100;
        width: 260px !important;
        transition: left 0.25s ease;

        &.mobile-open {
          left: 0;
        }

        &.collapsed {
          width: 260px !important;
          .brand-text { display: flex !important; }
          .nav-section-label { display: block !important; }
          .nav-item span[matListItemTitle] { display: inline !important; }
          .user-meta { display: flex !important; }
          .sidebar-logout-btn span { display: inline !important; }
        }
      }

      .user-dropdown-info {
        display: none !important;
      }
    }
  `]
})
export class MainLayoutComponent implements OnInit {
  private authService = inject(AuthService);
  private notifService = inject(NotificationService);
  private router = inject(Router);

  currentUser = this.authService.currentUser;
  userRole = this.authService.userRole;

  isSidebarCollapsed = signal(false);
  isMobileDrawerOpen = signal(false);
  showProfileModal = false;
  breadcrumbs = signal<{ label: string; url: string }[]>([]);

  unreadCount = computed(() => {
    return this.notifData.unread_count;
  });

  notifications = computed(() => {
    return this.notifData.items;
  });

  private notifData: { unread_count: number; items: NotificationItem[] } = { unread_count: 0, items: [] };

  // Phase 9 Command Palette State
  isCommandPaletteOpen = false;
  searchQuery = '';
  selectedIndex = 0;
  filteredNavItems: { title: string; description: string; link: string; icon: string }[] = [];

  // Phase 9 Onboarding Tour State
  showTourModal = false;
  tourStep = 0;
  tourSteps: { title: string; icon: string; text: string }[] = [];

  constructor() {
    this.notifService.notifications$.subscribe(data => {
      this.notifData = data;
    });

    this.router.events.pipe(
      filter(e => e instanceof NavigationEnd)
    ).subscribe((e: any) => {
      this.updateBreadcrumbs(e.urlAfterRedirects || e.url);
      this.isMobileDrawerOpen.set(false);
    });
    this.updateBreadcrumbs(this.router.url);
  }

  toggleSidebar(): void {
    this.isSidebarCollapsed.set(!this.isSidebarCollapsed());
  }

  toggleMobileDrawer(): void {
    this.isMobileDrawerOpen.set(!this.isMobileDrawerOpen());
  }

  closeMobileDrawer(): void {
    this.isMobileDrawerOpen.set(false);
  }

  openProfileModal(): void {
    this.showProfileModal = true;
  }

  closeProfileModal(): void {
    this.showProfileModal = false;
  }

  private updateBreadcrumbs(url: string): void {
    const raw = (url || '').split('?')[0].split('#')[0];
    const segments = raw.split('/').filter(Boolean);
    const crumbs: { label: string; url: string }[] = [];
    let accum = '';
    for (const seg of segments) {
      accum += `/${seg}`;
      const label = seg
        .replace(/-/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());
      crumbs.push({ label, url: accum });
    }
    this.breadcrumbs.set(crumbs);
  }

  ngOnInit(): void {
    this.initTour();
    if (this.currentUser()?.must_change_password) {
      this.forceChangePassword = true;
      this.showChangePasswordModal = true;
    }
    this.authService.getMe().subscribe({
      next: (u) => {
        if (u.must_change_password) {
          this.forceChangePassword = true;
          this.showChangePasswordModal = true;
        }
      },
      error: () => {}
    });
  }

  @HostListener('window:keydown', ['$event'])
  handleKeyboardEvent(event: KeyboardEvent): void {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      this.openCommandPalette();
    } else if (event.key === 'Escape') {
      if (this.isCommandPaletteOpen) this.closeCommandPalette();
      if (this.showProfileModal) this.closeProfileModal();
      if (this.showNotifPrefsModal) this.showNotifPrefsModal = false;
      if (this.showChangePasswordModal && !this.forceChangePassword) this.closeChangePassword();
      if (this.showTourModal) this.dismissTour();
      if (this.isMobileDrawerOpen()) this.closeMobileDrawer();
    }
  }

  openCommandPalette(): void {
    this.isCommandPaletteOpen = true;
    this.searchQuery = '';
    this.selectedIndex = 0;
    this.filterNavItems();
  }

  closeCommandPalette(): void {
    this.isCommandPaletteOpen = false;
  }

  filterNavItems(): void {
    const role = this.userRole();
    let allItems: { title: string; description: string; link: string; icon: string }[] = [];

    if (role === 'ADMIN') {
      allItems = [
        { title: 'CEO Command Center', description: 'Org-wide readiness, ROI & diagnostics', link: '/admin/ceo-command-center', icon: 'insights' },
        { title: 'Admin Dashboard', description: 'Metrics, overview & operations', link: '/admin/dashboard', icon: 'dashboard' },
        { title: 'Cohorts', description: 'Manage training cohorts & members', link: '/admin/cohorts', icon: 'groups' },
        { title: 'User Management', description: 'Admin, Mentor & ASE user directory', link: '/admin/users', icon: 'people_outline' },
        { title: 'Mentor-ASE Mapping', description: 'Assign mentees to mentors', link: '/admin/assignments', icon: 'link' },
        { title: 'Assessments', description: 'Manage and publish tests', link: '/admin/assessments', icon: 'assignment' },
        { title: 'Question Bank', description: 'Coding & MCQ item repositories', link: '/admin/assessments/question-bank', icon: 'quiz' },
        { title: 'Trainings', description: 'Curriculum modules & syllabi', link: '/admin/trainings', icon: 'school' },
        { title: 'Live Classes', description: 'Virtual lecture sessions', link: '/admin/classes', icon: 'videocam' },
        { title: 'Schedule', description: 'Company training calendar', link: '/admin/schedule', icon: 'calendar_month' },
        { title: 'AI Token Usage', description: 'LLM consumption telemetry', link: '/admin/llm-usage', icon: 'token' },
        { title: 'Motivational Quotes', description: 'Daily quote management', link: '/admin/quotes', icon: 'format_quote' }
      ];
    } else if (role === 'MENTOR') {
      allItems = [
        { title: 'Mentor Dashboard', description: 'Early warnings, mentees & nudges', link: '/mentor/dashboard', icon: 'dashboard' },
        { title: 'Assigned Mentees', description: 'View mentee progress & risk signals', link: '/mentor/mentees', icon: 'group' },
        { title: 'Cohorts', description: 'Mentored cohort batches', link: '/mentor/cohorts', icon: 'groups' },
        { title: 'Trainings', description: 'Course modules & materials', link: '/mentor/trainings', icon: 'school' },
        { title: 'Live Classes', description: 'Lecture schedules & summaries', link: '/mentor/classes', icon: 'videocam' },
        { title: 'Assign Assessments', description: 'Create and issue tests', link: '/mentor/assessments', icon: 'assignment_ind' },
        { title: 'Mentees Results', description: 'Exams, scores & growth analytics', link: '/mentor/results', icon: 'insights' },
        { title: 'Schedule', description: 'Mentorship calendar', link: '/mentor/schedule', icon: 'calendar_month' }
      ];
    } else {
      allItems = [
        { title: 'My Dashboard', description: 'Readiness, Skill DNA, Journey & Leaderboard', link: '/ase/dashboard', icon: 'dashboard' },
        { title: 'My Assessments', description: 'Take pending exams & tests', link: '/ase/my-assessments', icon: 'assignment_turned_in' },
        { title: 'My Learning', description: 'Course modules, labs & transcripts', link: '/ase/learning', icon: 'school' },
        { title: 'My Schedule', description: 'Classes, deadlines & calendar', link: '/ase/schedule', icon: 'calendar_month' }
      ];
    }

    if (!this.searchQuery.trim()) {
      this.filteredNavItems = allItems;
    } else {
      const q = this.searchQuery.toLowerCase();
      this.filteredNavItems = allItems.filter(i =>
        i.title.toLowerCase().includes(q) || i.description.toLowerCase().includes(q)
      );
    }
  }

  navigateItem(item: { link: string }): void {
    this.closeCommandPalette();
    this.router.navigateByUrl(item.link);
  }

  private initTour(): void {
    const user = this.currentUser();
    if (!user) return;
    const tourKey = `lk_tour_seen_${user.user_id}`;
    if (localStorage.getItem(tourKey)) return;

    const role = user.role;
    if (role === 'ADMIN') {
      this.tourSteps = [
        { title: 'Welcome, Executive!', icon: '🏛️', text: 'Welcome to L&K Skill Hub. As an Administrator, you have complete governance over users, cohorts, and organizational upskilling.' },
        { title: 'CEO Command Center', icon: '📊', text: 'Track real-time Org-Wide Readiness, Time-to-Productivity benchmarks, and Training ROI Uplift with full privacy safeguards.' },
        { title: 'Quick Navigation', icon: '⚡', text: 'Press Ctrl+K (or Cmd+K) anywhere on the platform to instantly jump to any tool, report, or configuration screen.' }
      ];
    } else if (role === 'MENTOR') {
      this.tourSteps = [
        { title: 'Welcome, Mentor!', icon: '🌱', text: 'Guide your assigned ASEs from day 1 to full project deployment with specialized AI insights and early warning signals.' },
        { title: 'Early Warning Center', icon: '🛡️', text: 'Identify struggling mentees through rule-based risk signals and send 1-click supportive encouragement nudges.' },
        { title: 'AI Class Summaries', icon: '📝', text: 'Generate automatic summaries and assessment draft banks directly from class notes or transcripts.' }
      ];
    } else {
      this.tourSteps = [
        { title: 'Welcome to Your Engineering Journey!', icon: '🚀', text: 'L&K Skill Hub accelerates your onboarding with your transparent Project-Readiness Score and unique Skill DNA helix.' },
        { title: '30/60/90 Journey & Leaderboard', icon: '🏆', text: 'Complete milestones, gain XP, earn badges, maintain daily streaks, and optionally join the opt-in leaderboard.' },
        { title: 'AI Study Roadmap & Mock Interviews', icon: '🤖', text: 'Get personalized weekly study checklists targeting your weak skill areas and practice anytime with the AI Mock Interviewer!' }
      ];
    }
    this.tourStep = 0;
    this.showTourModal = true;
  }

  dismissTour(): void {
    this.showTourModal = false;
    const user = this.currentUser();
    if (user) {
      localStorage.setItem(`lk_tour_seen_${user.user_id}`, 'true');
    }
  }

  userInitials = computed(() => {
    const name = this.currentUser()?.name || '';
    const parts = name.split(' ');
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase() || 'U';
  });

  getNotifIcon(type: string): string {
    switch (type) {
      case 'LIVE_CLASS': return 'videocam';
      case 'ASSESSMENT': return 'quiz';
      case 'TRAINING': return 'school';
      case 'REMINDER': return 'alarm';
      default: return 'notifications';
    }
  }

  markRead(n: NotificationItem): void {
    if (!n.is_read) {
      this.notifService.markAsRead(n.id).subscribe({
        next: () => {
          n.is_read = true;
          this.notifService.refresh();
        }
      });
    }
  }

  markAllRead(): void {
    this.notifService.markAllAsRead().subscribe({
      next: () => this.notifService.refresh()
    });
  }

  logout(): void {
    this.authService.logout();
  }

  showNotifPrefsModal = false;
  prefInApp = true;
  prefEmail = true;
  prefTeams = false;
  prefQuietEnabled = false;
  prefQuietStart = '22:00';
  prefQuietEnd = '07:00';
  prefTimezone = 'UTC';

  openNotificationPrefs(): void {
    this.notifService.getPreferences().subscribe({
      next: (prefs) => {
        const channels = prefs.preferred_channels || [];
        this.prefInApp = channels.includes('IN_APP');
        this.prefEmail = channels.includes('EMAIL');
        this.prefTeams = channels.includes('TEAMS');
        this.prefQuietEnabled = prefs.quiet_hours_enabled;
        this.prefQuietStart = prefs.quiet_hours_start || '22:00';
        this.prefQuietEnd = prefs.quiet_hours_end || '07:00';
        this.prefTimezone = prefs.timezone || 'UTC';
        this.showNotifPrefsModal = true;
      },
      error: () => {
        this.showNotifPrefsModal = true;
      }
    });
  }

  saveNotifPrefs(): void {
    const channels: string[] = [];
    if (this.prefInApp) channels.push('IN_APP');
    if (this.prefEmail) channels.push('EMAIL');
    if (this.prefTeams) channels.push('TEAMS');

    this.notifService.updatePreferences({
      preferred_channels: channels.length ? channels : ['IN_APP'],
      quiet_hours_enabled: this.prefQuietEnabled,
      quiet_hours_start: this.prefQuietStart,
      quiet_hours_end: this.prefQuietEnd,
      timezone: this.prefTimezone
    }).subscribe({
      next: () => {
        this.showNotifPrefsModal = false;
        alert('Notification preferences updated successfully!');
      },
      error: (err) => alert(err.error?.detail || 'Failed to save notification preferences')
    });
  }

  showChangePasswordModal = false;
  forceChangePassword = false;
  changePwdCurrent = '';
  changePwdNew = '';
  changePwdConfirm = '';
  changePwdError = '';
  changePwdLoading = false;
  showHideCurrent = false;
  showHideNew = false;
  showHideConfirm = false;

  hasUpper(val: string): boolean {
    return /[A-Z]/.test(val || '');
  }

  hasLower(val: string): boolean {
    return /[a-z]/.test(val || '');
  }

  hasDigit(val: string): boolean {
    return /[0-9]/.test(val || '');
  }

  hasSpecial(val: string): boolean {
    return /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?/`~]/.test(val || '');
  }

  isChangePwdFormValid(): boolean {
    if (!this.changePwdCurrent || !this.changePwdNew || !this.changePwdConfirm) return false;
    if (this.changePwdNew.length < 8) return false;
    if (!this.hasUpper(this.changePwdNew)) return false;
    if (!this.hasLower(this.changePwdNew)) return false;
    if (!this.hasDigit(this.changePwdNew)) return false;
    if (!this.hasSpecial(this.changePwdNew)) return false;
    if (this.changePwdNew !== this.changePwdConfirm) return false;
    return true;
  }

  openChangePassword(): void {
    this.changePwdCurrent = '';
    this.changePwdNew = '';
    this.changePwdConfirm = '';
    this.changePwdError = '';
    this.showHideCurrent = false;
    this.showHideNew = false;
    this.showHideConfirm = false;
    this.showChangePasswordModal = true;
  }

  closeChangePassword(): void {
    if (this.forceChangePassword) return;
    this.showChangePasswordModal = false;
  }

  submitChangePassword(): void {
    if (!this.isChangePwdFormValid()) return;
    this.changePwdLoading = true;
    this.changePwdError = '';

    this.authService.changePassword({
      current_password: this.changePwdCurrent,
      new_password: this.changePwdNew,
      confirm_password: this.changePwdConfirm
    }).subscribe({
      next: () => {
        this.changePwdLoading = false;
        this.forceChangePassword = false;
        this.showChangePasswordModal = false;
        this.authService.updateCurrentUser({ must_change_password: false });
        alert('Password changed successfully!');
      },
      error: (err) => {
        this.changePwdLoading = false;
        this.changePwdError = err.error?.detail || 'Failed to change password. Please verify current password.';
      }
    });
  }
}
