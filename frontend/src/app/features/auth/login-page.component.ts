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
        <h1>{{ mode() === 'login' ? 'Willkommen zurück' : 'Arbeitsbereich beitreten' }}</h1>
        <p class="login-copy">{{ mode() === 'login'
          ? 'Melden Sie sich an, um auf Ihre Prozesse und Ihren Arbeitsbereich zuzugreifen.'
          : 'Geben Sie den einmaligen Einladungscode ein, den Sie von Ihrer Workspace-Administration erhalten haben.' }}</p>
        @if (mode() === 'login') {
        <form (ngSubmit)="submit()" #loginForm="ngForm">
          <label for="login-email">E-Mail-Adresse</label>
          <input id="login-email" name="email" type="email" autocomplete="username"
            [(ngModel)]="email" required email placeholder="name@unternehmen.de" />
          @if (auth.workspaces().length > 0) {
            <label for="login-workspace">Arbeitsbereich</label>
            <select id="login-workspace" name="tenantId" [(ngModel)]="tenantId" required>
              <option value="">Arbeitsbereich auswählen</option>
              @for (workspace of auth.workspaces(); track workspace.id) {
                <option [value]="workspace.id">{{ workspace.name }} · {{ workspace.role }}</option>
              }
            </select>
          }
          <label for="login-password">Passwort</label>
          <input id="login-password" name="password" type="password" autocomplete="current-password"
            [(ngModel)]="password" required placeholder="Passwort eingeben" />
          @if (auth.error()) { <div class="login-error" role="alert">{{ auth.error() }}</div> }
          @if (error()) { <div class="login-error" role="alert">{{ error() }}</div> }
          <button type="submit" [disabled]="loginForm.invalid || loading()">
            {{ loading() ? 'Anmeldung läuft …' : 'Anmelden' }}
            <span>→</span>
          </button>
        </form>
        <button class="login-mode-switch" type="button" (click)="mode.set('invite')">Einladung annehmen</button>
        } @else {
        <form (ngSubmit)="acceptInvite()" #inviteForm="ngForm">
          <label for="invite-token">Einladungscode</label>
          <input id="invite-token" name="inviteToken" type="text" autocomplete="one-time-code"
            [(ngModel)]="inviteToken" required placeholder="Einladungscode eingeben" />
          <label for="invite-name">Vollständiger Name</label>
          <input id="invite-name" name="fullName" type="text" autocomplete="name"
            [(ngModel)]="fullName" required placeholder="Ihr Name" />
          <label for="invite-password">Passwort festlegen</label>
          <input id="invite-password" name="invitePassword" type="password" autocomplete="new-password"
            [(ngModel)]="password" required minlength="12" placeholder="Mindestens 12 Zeichen" />
          @if (error()) { <div class="login-error" role="alert">{{ error() }}</div> }
          <button type="submit" [disabled]="inviteForm.invalid || loading()">
            {{ loading() ? 'Einladung wird bestätigt …' : 'Beitreten & anmelden' }}
            <span>→</span>
          </button>
        </form>
        <button class="login-mode-switch" type="button" (click)="mode.set('login')">Zurück zur Anmeldung</button>
        }
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
    .login-mode-switch { width: 100%; justify-content: center; margin: 7px 0 0; border: 1px solid #e1e5ef; color: #535fc2; background: #fff; }
    .login-mode-switch:hover { background: #f7f8ff; }
    select { width: 100%; min-height: 45px; border: 1px solid #dfe4ed; border-radius: 9px; padding: 0 12px; color: #17213a; background: #fff; font: inherit; font-size: 13px; }
    select:focus { outline: 2px solid #777bf0; outline-offset: 2px; }
    .login-footnote { display: block; margin-top: 24px; line-height: 1.5; }
    @media (max-width: 520px) { .login-card { padding: 26px 22px; } }
  `]
})
export class LoginPageComponent {
  readonly auth = inject(AuthService);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly mode = signal<'login' | 'invite'>('login');
  email = '';
  password = '';
  tenantId = '';
  inviteToken = '';
  fullName = '';

  acceptInvite(): void {
    if (!this.inviteToken.trim() || !this.password || !this.fullName.trim()) return;
    this.loading.set(true);
    this.error.set(null);
    this.auth.acceptInvitation(this.inviteToken.trim(), this.password, this.fullName).subscribe({
      next: invitation => {
        this.email = invitation.email;
        this.tenantId = '';
        this.mode.set('login');
        this.auth.login(invitation.email, this.password).subscribe({
          next: () => this.loading.set(false),
          error: response => {
            this.loading.set(false);
            const detail = response?.error?.detail;
            this.error.set(typeof detail === 'string'
              ? detail
              : 'Die Einladung wurde angenommen. Bitte melden Sie sich mit Ihren Zugangsdaten an.');
          }
        });
      },
      error: response => {
        this.loading.set(false);
        const detail = response?.error?.detail;
        this.error.set(typeof detail === 'string'
          ? detail
          : 'Die Einladung konnte nicht angenommen werden. Bitte Einladungscode prüfen.');
      }
    });
  }

  submit(): void {
    if (!this.email.trim() || !this.password) return;
    this.loading.set(true);
    this.error.set(null);
    this.auth.login(this.email, this.password, this.tenantId || undefined).subscribe({
      next: () => this.loading.set(false),
      error: response => {
        this.loading.set(false);
        const detail = response?.error?.detail;
        this.error.set(typeof detail === 'string' ? detail : 'Anmeldung nicht möglich. Bitte Zugangsdaten prüfen.');
      }
    });
  }
}
