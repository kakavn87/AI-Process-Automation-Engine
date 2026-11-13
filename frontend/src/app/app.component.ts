import { Component, OnInit, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { AuthService } from './core/services/auth.service';
import { LoginPageComponent } from './features/auth/login-page.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, LoginPageComponent],
  template: `
    @if (!auth.ready()) {
      <main class="auth-loading">
        <span class="auth-loading-mark">AI</span>
        <strong>Arbeitsbereich wird vorbereitet …</strong>
      </main>
    } @else if (auth.authRequired() && !auth.isAuthenticated()) {
      <app-login-page />
    } @else {
      <router-outlet />
    }
  `,
  styles: [`
    .auth-loading {
      display: grid;
      place-content: center;
      justify-items: center;
      gap: 14px;
      min-height: 100vh;
      color: #667085;
      background: #f4f6fb;
      font: 600 13px Inter, sans-serif;
    }
    .auth-loading-mark {
      display: grid;
      place-items: center;
      width: 44px;
      height: 44px;
      border-radius: 13px;
      color: #fff;
      background: linear-gradient(145deg, #777af0, #4b51c7);
      font-weight: 800;
    }
  `]
})
export class AppComponent implements OnInit {
  readonly auth = inject(AuthService);

  ngOnInit(): void {
    this.auth.initialize();
  }
}
