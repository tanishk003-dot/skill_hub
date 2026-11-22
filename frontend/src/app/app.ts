import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { CommonModule } from '@angular/common';
import { LoadingService } from './core/services/loading.service';
import { MotivationSplashComponent } from './layout/splash/motivation-splash.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, CommonModule, MotivationSplashComponent],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  title = 'L&K Skill Hub';
  loadingService = inject(LoadingService);
}
