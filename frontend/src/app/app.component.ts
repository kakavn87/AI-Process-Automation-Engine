import { Component } from '@angular/core';
import { ProcessPageComponent } from './features/process/pages/process-page/process-page.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [ProcessPageComponent],
  template: '<app-process-page />'
})
export class AppComponent {}
