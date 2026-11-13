import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { AuthService } from '../services/auth.service';

export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const auth = inject(AuthService);
  const token = auth.token();
  // Never forward a FlowPilot bearer token to a third-party URL.
  if (!token || !auth.isApiRequest(request.url) || request.headers.has('Authorization')) {
    return next(request);
  }
  return next(request.clone({
    setHeaders: { Authorization: `Bearer ${token}` }
  }));
};
