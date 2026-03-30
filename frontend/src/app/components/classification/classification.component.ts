import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../services/api.service';
import { ClassificationResult, ClassificationType } from '../../models/classification-result.model';

@Component({
  selector: 'app-classification',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './classification.component.html'
})
export class ClassificationComponent implements OnInit {
  stats: any = null;
  results: ClassificationResult[] = [];
  activeFilter: ClassificationType | 'ALL' = 'ALL';
  isRunning = false;
  isLoading = false;
  runResult: any = null;
  error: string | null = null;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.loadStats();
    this.loadResults();
  }

  loadStats(): void {
    this.api.getClassificationStats().subscribe({
      next: (stats) => this.stats = stats,
      error: (err) => this.error = '无法加载统计：' + err.message
    });
  }

  loadResults(filter: ClassificationType | 'ALL' = 'ALL'): void {
    this.isLoading = true;
    this.activeFilter = filter;

    const obs = filter === 'ALL'
      ? this.api.getAllClassificationResults()
      : this.api.getResultsByType(filter);

    obs.subscribe({
      next: (results) => {
        this.results = results;
        this.isLoading = false;
      },
      error: (err) => {
        this.error = '无法加载结果：' + err.message;
        this.isLoading = false;
      }
    });
  }

  runClassification(): void {
    this.isRunning = true;
    this.error = null;
    this.runResult = null;

    this.api.runClassification().subscribe({
      next: (result) => {
        this.runResult = result;
        this.isRunning = false;
        this.loadStats();
        this.loadResults();
      },
      error: (err) => {
        this.error = '分类失败：' + (err.error?.error || err.message);
        this.isRunning = false;
      }
    });
  }

  getBadgeClass(type: ClassificationType): string {
    return `badge badge-${type.toLowerCase()}`;
  }
}
