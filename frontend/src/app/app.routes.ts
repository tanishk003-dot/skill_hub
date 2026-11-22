import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { roleGuard } from './core/guards/role.guard';
import { LoginComponent } from './pages/auth/login.component';
import { MainLayoutComponent } from './layout/main-layout.component';
import { AdminDashboardComponent } from './pages/admin/dashboard/admin-dashboard.component';
import { AdminUsersComponent } from './pages/admin/users/admin-users.component';
import { AdminAssignmentsComponent } from './pages/admin/assignments/admin-assignments.component';
import { AdminAssessmentsComponent } from './pages/admin/assessments/admin-assessments.component';
import { AdminCreateAssessmentComponent } from './pages/admin/assessments/create-assessment.component';
import { AdminQuestionBankComponent } from './pages/admin/assessments/question-bank.component';
import { MentorDashboardComponent } from './pages/mentor/mentor-dashboard.component';
import { MentorAssessmentsComponent } from './pages/mentor/mentor-assessments.component';
import { MentorMenteeResultsComponent } from './pages/mentor/mentee-results.component';
import { AseDashboardComponent } from './pages/ase/ase-dashboard.component';
import { AseAssessmentsComponent } from './pages/ase/my-assessments.component';
import { AseExamComponent } from './pages/ase/exam-taking.component';
import { AssessmentResultComponent } from './pages/shared/assessment-result.component';
import { CohortListComponent } from './pages/shared/cohorts/cohort-list.component';
import { TrainingListComponent } from './pages/shared/trainings/training-list.component';
import { LiveClassListComponent } from './pages/shared/classes/live-class-list.component';
import { CalendarViewComponent } from './pages/shared/calendar/calendar-view.component';
import { MyLearningComponent } from './pages/ase/my-learning.component';
import { AdminLLMUsageComponent } from './pages/admin/llm-usage/admin-llm-usage.component';
import { AdminQuotesComponent } from './pages/admin/quotes/admin-quotes.component';
import { CEOCommandCenterComponent } from './pages/admin/ceo-command-center/ceo-command-center.component';
import { CertificateVerifyComponent } from './pages/shared/certificate-verify/certificate-verify.component';
import { CameraTestComponent } from './pages/ase/camera-test/camera-test.component';
import { AccommodationsComponent } from './pages/ase/accommodations/accommodations.component';
import { QuestionAnalyticsComponent } from './pages/mentor/question-analytics/question-analytics.component';
import { OneOnOneComponent } from './pages/mentor/one-on-one/one-on-one.component';
import { ExportsComponent } from './pages/admin/exports/exports.component';
import { StaffingComponent } from './pages/admin/staffing/staffing.component';
import { AdminAuditLogsComponent } from './pages/admin/audit-logs/admin-audit-logs.component';
import { BuddyHubComponent } from './pages/ase/buddy-hub/buddy-hub.component';
import { ForumListComponent } from './pages/forum/forum-list/forum-list.component';
import { ThreadDetailComponent } from './pages/forum/thread-detail/thread-detail.component';
import { ErrorPageComponent } from './pages/error/error-page.component';

export const routes: Routes = [
  {
    path: 'login',
    component: LoginComponent
  },
  {
    path: 'auth/sso/callback',
    component: LoginComponent
  },
  {
    path: 'verify-certificate/:certUuid',
    component: CertificateVerifyComponent
  },
  {
    path: '',
    component: MainLayoutComponent,
    canActivate: [authGuard],
    children: [
      {
        path: '',
        pathMatch: 'full',
        redirectTo: 'login'
      },
      // Admin Routes
      {
        path: 'admin/dashboard',
        component: AdminDashboardComponent,
        canActivate: [roleGuard(['ADMIN'])]
      },
      {
        path: 'admin/cohorts',
        component: CohortListComponent,
        canActivate: [roleGuard(['ADMIN'])]
      },
      {
        path: 'admin/users',
        component: AdminUsersComponent,
        canActivate: [roleGuard(['ADMIN'])]
      },
      {
        path: 'admin/assignments',
        component: AdminAssignmentsComponent,
        canActivate: [roleGuard(['ADMIN'])]
      },
      {
        path: 'admin/assessments',
        component: AdminAssessmentsComponent,
        canActivate: [roleGuard(['ADMIN'])]
      },
      {
        path: 'admin/assessments/create',
        component: AdminCreateAssessmentComponent,
        canActivate: [roleGuard(['ADMIN'])]
      },
      {
        path: 'admin/assessments/question-bank',
        component: AdminQuestionBankComponent,
        canActivate: [roleGuard(['ADMIN'])]
      },
      {
        path: 'admin/trainings',
        component: TrainingListComponent,
        canActivate: [roleGuard(['ADMIN'])]
      },
      {
        path: 'admin/classes',
        component: LiveClassListComponent,
        canActivate: [roleGuard(['ADMIN'])]
      },
      {
        path: 'admin/schedule',
        component: CalendarViewComponent,
        canActivate: [roleGuard(['ADMIN'])]
      },
      {
        path: 'admin/llm-usage',
        component: AdminLLMUsageComponent,
        canActivate: [roleGuard(['ADMIN'])]
      },
      {
        path: 'admin/accommodations',
        component: AccommodationsComponent,
        canActivate: [roleGuard(['ADMIN'])]
      },
      {
        path: 'admin/quotes',
        component: AdminQuotesComponent,
        canActivate: [roleGuard(['ADMIN'])]
      },
      {
        path: 'admin/ceo-command-center',
        component: CEOCommandCenterComponent,
        canActivate: [roleGuard(['ADMIN'])]
      },
      {
        path: 'admin/question-analytics',
        component: QuestionAnalyticsComponent,
        canActivate: [roleGuard(['ADMIN'])]
      },
      {
        path: 'admin/exports',
        component: ExportsComponent,
        canActivate: [roleGuard(['ADMIN'])]
      },
      {
        path: 'admin/staffing',
        component: StaffingComponent,
        canActivate: [roleGuard(['ADMIN'])]
      },
      {
        path: 'admin/audit-logs',
        component: AdminAuditLogsComponent,
        canActivate: [roleGuard(['ADMIN'])]
      },
      // Mentor Routes
      {
        path: 'mentor/dashboard',
        component: MentorDashboardComponent,
        canActivate: [roleGuard(['MENTOR', 'ADMIN'])]
      },
      {
        path: 'mentor/cohorts',
        component: CohortListComponent,
        canActivate: [roleGuard(['MENTOR', 'ADMIN'])]
      },
      {
        path: 'mentor/mentees',
        component: MentorDashboardComponent,
        canActivate: [roleGuard(['MENTOR', 'ADMIN'])]
      },
      {
        path: 'mentor/assessments',
        component: MentorAssessmentsComponent,
        canActivate: [roleGuard(['MENTOR', 'ADMIN'])]
      },
      {
        path: 'mentor/results',
        component: MentorMenteeResultsComponent,
        canActivate: [roleGuard(['MENTOR', 'ADMIN'])]
      },
      {
        path: 'mentor/results/:attemptId',
        component: AssessmentResultComponent,
        canActivate: [roleGuard(['MENTOR', 'ADMIN'])]
      },
      {
        path: 'mentor/trainings',
        component: TrainingListComponent,
        canActivate: [roleGuard(['MENTOR', 'ADMIN'])]
      },
      {
        path: 'mentor/classes',
        component: LiveClassListComponent,
        canActivate: [roleGuard(['MENTOR', 'ADMIN'])]
      },
      {
        path: 'mentor/schedule',
        component: CalendarViewComponent,
        canActivate: [roleGuard(['MENTOR', 'ADMIN'])]
      },
      {
        path: 'mentor/accommodations',
        component: AccommodationsComponent,
        canActivate: [roleGuard(['MENTOR', 'ADMIN'])]
      },
      {
        path: 'mentor/question-analytics',
        component: QuestionAnalyticsComponent,
        canActivate: [roleGuard(['MENTOR', 'ADMIN'])]
      },
      {
        path: 'mentor/one-on-one',
        component: OneOnOneComponent,
        canActivate: [roleGuard(['MENTOR', 'ADMIN'])]
      },
      {
        path: 'mentor/exports',
        component: ExportsComponent,
        canActivate: [roleGuard(['MENTOR', 'ADMIN'])]
      },
      {
        path: 'mentor/staffing',
        component: StaffingComponent,
        canActivate: [roleGuard(['MENTOR', 'ADMIN'])]
      },
      // ASE Routes
      {
        path: 'ase/dashboard',
        component: AseDashboardComponent,
        canActivate: [roleGuard(['ASE', 'ADMIN'])]
      },
      {
        path: 'ase/one-on-one',
        component: OneOnOneComponent,
        canActivate: [roleGuard(['ASE', 'ADMIN'])]
      },
      {
        path: 'ase/camera-test',
        component: CameraTestComponent,
        canActivate: [roleGuard(['ASE', 'ADMIN'])]
      },
      {
        path: 'ase/accommodations',
        component: AccommodationsComponent,
        canActivate: [roleGuard(['ASE', 'ADMIN'])]
      },
      {
        path: 'ase/my-assessments',
        component: AseAssessmentsComponent,
        canActivate: [roleGuard(['ASE', 'ADMIN'])]
      },
      {
        path: 'ase/learning',
        component: MyLearningComponent,
        canActivate: [roleGuard(['ASE', 'ADMIN'])]
      },
      {
        path: 'ase/schedule',
        component: CalendarViewComponent,
        canActivate: [roleGuard(['ASE', 'ADMIN'])]
      },
      {
        path: 'ase/exam/:assignmentId',
        component: AseExamComponent,
        canActivate: [roleGuard(['ASE', 'ADMIN'])]
      },
      {
        path: 'ase/result/:attemptId',
        component: AssessmentResultComponent,
        canActivate: [roleGuard(['ASE', 'ADMIN'])]
      },
      // Phase 12 Buddy Hub & Doubt Forum Routes
      {
        path: 'ase/buddy',
        component: BuddyHubComponent,
        canActivate: [roleGuard(['ASE', 'ADMIN'])]
      },
      {
        path: 'mentor/buddies',
        component: BuddyHubComponent,
        canActivate: [roleGuard(['MENTOR', 'ADMIN'])]
      },
      {
        path: 'forum',
        component: ForumListComponent,
        canActivate: [roleGuard(['ASE', 'MENTOR', 'ADMIN'])]
      },
      {
        path: 'forum/thread/:id',
        component: ThreadDetailComponent,
        canActivate: [roleGuard(['ASE', 'MENTOR', 'ADMIN'])]
      }
    ]
  },
  {
    path: 'forbidden',
    component: ErrorPageComponent,
    data: { code: '403' }
  },
  {
    path: 'error',
    component: ErrorPageComponent,
    data: { code: '500' }
  },
  {
    path: 'not-found',
    component: ErrorPageComponent,
    data: { code: '404' }
  },
  {
    path: '**',
    component: ErrorPageComponent,
    data: { code: '404' }
  }
];
