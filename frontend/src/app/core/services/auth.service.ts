import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../../environments/environment';

declare global {
  interface Window {
    __FLOWPILOT_RUNTIME_CONFIG__?: {
      apiBaseUrl?: string;
      isPreview?: boolean;
    };
  }
}

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  tenant: { id: string; name: string };
  role: string;
}

interface AuthLoginResponse {
  access_token?: string;
  token_type?: string;
  expires_in?: number;
  user?: AuthUser;
  requires_workspace_selection?: boolean;
  workspaces?: Array<{ id: string; name: string; role: string }>;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly baseUrl = (
    window.__FLOWPILOT_RUNTIME_CONFIG__?.apiBaseUrl ?? environment.apiBaseUrl
  ).trim().replace(/\/+$/, '');

  private readonly tokenKey = 'flowpilot_access_token';
  readonly ready = signal(false);
  readonly authRequired = signal(false);
  readonly token = signal<string | null>(this.readToken());
  readonly user = signal<AuthUser | null>(null);
  readonly workspaces = signal<Array<{ id: string; name: string; role: string }>>([]);
  readonly isAuthenticated = signal(false);
  readonly error = signal<string | null>(null);

  constructor(private readonly http: HttpClient) {}

  initialize(): void {
    this.error.set(null);
    this.http.get<{ authenticationRequired: boolean }>(this.url('/auth/config')).subscribe({
      next: config => {
        this.authRequired.set(config.authenticationRequired);
        const currentToken = this.token();
        if (!config.authenticationRequired) {
          this.clearToken();
          this.ready.set(true);
          return;
        }
        if (!currentToken) {
          this.ready.set(true);
          return;
        }
        this.http.get<{ authenticated: boolean; user?: { id: string; email: string; full_name: string }; tenant?: { id: string; name: string }; role?: string }>(
          this.url('/auth/me')
        ).subscribe({
          next: result => {
            if (!result.authenticated || !result.user || !result.tenant) {
              this.clearToken();
            } else {
              this.user.set({
                ...result.user,
                tenant: result.tenant,
                role: result.role ?? 'member'
              });
              this.isAuthenticated.set(true);
            }
            this.ready.set(true);
          },
          error: () => {
            this.clearToken();
            this.ready.set(true);
          }
        });
      },
      error: () => {
        // Fail closed: do not expose the workspace when the authentication
        // mode cannot be confirmed with the Backend.
        this.authRequired.set(true);
        this.error.set('Der Anmeldestatus konnte nicht geprüft werden. Bitte Backend-Verbindung prüfen.');
        this.ready.set(true);
      }
    });
  }

  login(email: string, password: string, tenantId?: string): Observable<AuthLoginResponse> {
    this.error.set(null);
    return this.http.post<AuthLoginResponse>(this.url('/auth/login'), {
      email: email.trim().toLowerCase(),
      password,
      ...(tenantId ? { tenant_id: tenantId } : {})
    }).pipe(tap(response => {
      if (response.access_token && response.user) {
        this.storeToken(response.access_token);
        this.user.set(response.user);
        this.workspaces.set([]);
        this.isAuthenticated.set(true);
        this.ready.set(true);
      } else if (response.requires_workspace_selection) {
        this.workspaces.set(response.workspaces ?? []);
      }
    }));
  }

  createWorkspace(name: string): Observable<AuthLoginResponse> {
    return this.http.post<AuthLoginResponse>(this.url('/auth/workspaces'), { name: name.trim() }).pipe(tap(response => {
      if (response.access_token && response.user) {
        this.storeToken(response.access_token);
        this.user.set(response.user);
        this.workspaces.set([]);
        this.isAuthenticated.set(true);
        this.ready.set(true);
      }
    }));
  }

  acceptInvitation(
    token: string,
    password: string,
    fullName: string
  ): Observable<{ accepted: boolean; email: string; tenant: { id: string; name: string } }> {
    this.error.set(null);
    return this.http.post<{ accepted: boolean; email: string; tenant: { id: string; name: string } }>(
      this.url('/auth/invitations/accept'),
      { token, password, full_name: fullName }
    );
  }

  logout(): void {
    this.clearToken();
    this.error.set(null);
  }

  private storeToken(value: string): void {
    this.token.set(value);
    try {
      sessionStorage.setItem(this.tokenKey, value);
    } catch {
      // The current tab can continue with in-memory authentication if storage is blocked.
    }
  }

  private clearToken(): void {
    this.token.set(null);
    this.user.set(null);
    this.workspaces.set([]);
    this.isAuthenticated.set(false);
    try {
      sessionStorage.removeItem(this.tokenKey);
    } catch {
      // Ignore browser storage restrictions.
    }
  }

  private readToken(): string | null {
    try {
      return sessionStorage.getItem(this.tokenKey);
    } catch {
      return null;
    }
  }

  isApiRequest(url: string): boolean {
    return !!this.baseUrl && url.startsWith(this.baseUrl + '/api/');
  }

  private url(path: string): string {
    return this.baseUrl + '/api' + path;
  }
}
