import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ProcessStore } from '../../process.store';
import { ProcessService } from '../../process.service';

@Component({
  selector: 'app-process-page',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './process-page.component.html'
})
export class ProcessPageComponent {
  readonly store = inject(ProcessStore);
  private readonly service = inject(ProcessService);

  description = '';

  analyze() {
    this.store.setDescription(this.description);
    this.service.analyze(this.description);
  }
}
