import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../services/api.service';
import { AnalysisInsight } from '../../models/analysis-insight.model';

@Component({
  selector: 'app-analysis',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './analysis.component.html'
})
export class AnalysisComponent implements OnInit {
  insights: AnalysisInsight[] = [];
  isRunning = false;
  isLoading = false;
  error: string | null = null;
  runMessage: string | null = null;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.loadInsights();
  }

  loadInsights(): void {
    this.isLoading = true;
    this.api.getAllInsights().subscribe({
      next: (insights) => {
        this.insights = insights;
        this.isLoading = false;
      },
      error: (err) => {
        this.error = '无法加载分析：' + err.message;
        this.isLoading = false;
      }
    });
  }

  runAnalysis(): void {
    this.isRunning = true;
    this.error = null;
    this.runMessage = null;

    this.api.runAnalysis().subscribe({
      next: (insights) => {
        this.insights = insights;
        this.isRunning = false;
        this.runMessage = `分析完成，生成了 ${insights.length} 条洞察`;
      },
      error: (err) => {
        this.error = '分析失败：' + (err.error?.error || err.message);
        this.isRunning = false;
      }
    });
  }

  parseDataJson(dataJson: string): any {
    try {
      return JSON.parse(dataJson);
    } catch {
      return null;
    }
  }

  objectEntries(obj: any): [string, any][] {
    return obj ? Object.entries(obj) : [];
  }

  getInsightIcon(type: string): string {
    const icons: { [key: string]: string } = {
      'basic_distribution': '📊',
      'strong_subtypes': '💪',
      'weak_sources': '📚',
      'none_patterns': '📍'
    };
    return icons[type] || '📈';
  }
}
