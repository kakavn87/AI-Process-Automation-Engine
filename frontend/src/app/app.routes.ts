import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./features/process/pages/process-page/process-page.component')
        .then(m => m.ProcessPageComponent)
  },
  {
    path: 'sessions/:sessionId',
    loadComponent: () =>
      import('./features/workflow-session/workflow-session-page.component')
        .then(m => m.WorkflowSessionPageComponent)
  },
  { path: '**', redirectTo: '' }
];
