import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-login-page',
  standalone: true,
  imports: [FormsModule],
  template: `
    <main class="login-shell">
      <section class="login-card">
        <div class="login-brand">
          <span class="login-mark">AI</span>
          <span><strong>AI Process Optimierung</strong><small>KI-gestützte Prozessoptimierung</small></span>
        </div>
        <div class="login-eyebrow">GESCHÜTZTER ARBEITSBEREICH</div>
        <h1>Willkommen zurück</h1>
        <p class="login-copy">Melden Sie sich an, um auf Ihre Prozesse und Ihren Arbeitsbereich zuzugreifen.</p>
        <form (ngSubmit)="submit()" #loginForm="ngForm">
          <label for="login-email">E-Mail-Adresse</label>
          <input id="login-email" name="email" type="email" autocomplete="username"
            [(ngModel)]="email" required email placeholder="name@unternehmen.de" />
          <label for="login-password">Passwort</label>
          <input id="login-password" name="password" type="password" autocomplete="current-password"
            [(ngModel)]="password" required placeholder="Passwort eingeben" />
          @if (error()) { <div class="login-error" role="alert">{{ error() }}</div> }
          <button type="submit" [disabled]="loginForm.invalid || loading()">
            {{ loading() ? 'Anmeldung läuft …' : 'Anmelden' }}
            <span>→</span>
          </button>
        </form>
        <small class="login-footnote">Der Zugang wird durch Ihre Workspace-Administration verwaltet.</small>
      </section>
    </main>
  `,
  styles: [`
    :host { display: block; min-height: 100vh; }
    .login-shell { display: grid; place-items: center; min-height: 100vh; padding: 24px; background: #f4f6fb; }
    .login-card { width: min(100%, 440px); padding: 38px; border: 1px solid #e5e8f0; border-radius: 20px; background: #fff; box-shadow: 0 18px 50px rgba(25, 35, 65, .08); }
    .login-brand { display: flex; align-items: center; gap: 12px; margin-bottom: 38px; }
    .login-mark { display: grid; place-items: center; width: 42px; height: 42px; border-radius: 13px; color: #fff; background: linear-gradient(145deg, #777af0, #4b51c7); font-weight: 800; }
    .login-brand > span:last-child { display: grid; gap: 3px; }
    .login-brand strong { color: #18223b; font-size: 16px; }
    .login-brand small, .login-footnote { color: #8791a4; font-size: 11px; }
    .login-eyebrow { color: #6268cf; font-size: 10px; font-weight: 800; letter-spacing: .13em; }
    h1 { margin: 9px 0; color: #17213a; font-size: 27px; letter-spacing: -.04em; }
    .login-copy { margin: 0 0 25px; color: #69758b; font-size: 13px; line-height: 1.65; }
    form { display: grid; gap: 9px; }
    label { margin-top: 7px; color: #39455d; font-size: 12px; font-weight: 700; }
    input { width: 100%; min-height: 45px; border: 1px solid #dfe4ed; border-radius: 9px; padding: 0 12px; color: #17213a; font: inherit; font-size: 13px; outline: none; }
    input:focus { border-color: #777bf0; box-shadow: 0 0 0 3px #777bf01c; }
    button { display: flex; align-items: center; justify-content: space-between; margin-top: 13px; min-height: 46px; padding: 0 15px; border: 0; border-radius: 9px; color: #fff; background: #575fce; font-weight: 700; cursor: pointer; }
    button:disabled { cursor: not-allowed; opacity: .55; }
    .login-error { padding: 10px 12px; border: 1px solid #fecaca; border-radius: 8px; color: #991b1b; background: #fff5f5; font-size: 12px; }
    .login-footnote { display: block; margin-top: 24px; line-height: 1.5; }
    @media (max-width: 520px) { .login-card { padding: 26px 22px; } }
  `]
})
export class LoginPageComponent {
  readonly auth = inject(AuthService);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  email = '';
  password = '';

  submit(): void {
    if (!this.email.trim() || !this.password) return;
    this.loading.set(true);
    this.error.set(null);
    this.auth.login(this.email, this.password).subscribe({
      next: () => this.loading.set(false),
      error: response => {
        this.loading.set(false);
        const detail = response?.error?.detail;
        this.error.set(typeof detail === 'string' ? detail : 'Anmeldung nicht möglich. Bitte Zugangsdaten prüfen.');
      }
    });
  }
}
