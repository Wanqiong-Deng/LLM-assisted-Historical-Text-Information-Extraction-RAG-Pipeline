import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { PlacenameRecord } from '../models/placename-record.model';
import { ClassificationResult, ClassificationStats, ClassificationType } from '../models/classification-result.model';
import { AnalysisInsight } from '../models/analysis-insight.model';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private readonly baseUrl = environment.apiBaseUrl;

  constructor(private http: HttpClient) {}

  // Pipeline
  uploadFile(file: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post(`${this.baseUrl}/pipeline/upload`, formData);
  }

  getPipelineStatus(): Observable<any> {
    return this.http.get(`${this.baseUrl}/pipeline/status`);
  }

  getAllRecords(): Observable<PlacenameRecord[]> {
    return this.http.get<PlacenameRecord[]>(`${this.baseUrl}/pipeline/records`);
  }

  searchRecords(query: string): Observable<PlacenameRecord[]> {
    const params = new HttpParams().set('q', query);
    return this.http.get<PlacenameRecord[]>(`${this.baseUrl}/pipeline/records/search`, { params });
  }

  // Classification
  runClassification(): Observable<{ [key: string]: number }> {
    return this.http.post<{ [key: string]: number }>(`${this.baseUrl}/classification/run`, {});
  }

  getClassificationStats(): Observable<ClassificationStats> {
    return this.http.get<ClassificationStats>(`${this.baseUrl}/classification/stats`);
  }

  getAllClassificationResults(): Observable<ClassificationResult[]> {
    return this.http.get<ClassificationResult[]>(`${this.baseUrl}/classification/results`);
  }

  getResultsByType(type: ClassificationType): Observable<ClassificationResult[]> {
    return this.http.get<ClassificationResult[]>(`${this.baseUrl}/classification/results/${type}`);
  }

  // Analysis
  runAnalysis(): Observable<AnalysisInsight[]> {
    return this.http.post<AnalysisInsight[]>(`${this.baseUrl}/analysis/run`, {});
  }

  getAllInsights(): Observable<AnalysisInsight[]> {
    return this.http.get<AnalysisInsight[]>(`${this.baseUrl}/analysis/insights`);
  }

  getDistribution(): Observable<AnalysisInsight> {
    return this.http.get<AnalysisInsight>(`${this.baseUrl}/analysis/distribution`);
  }

  // RAG
  queryRag(query: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/rag/query`, { query });
  }

  searchRag(query: string, topK = 5): Observable<ClassificationResult[]> {
    const params = new HttpParams().set('q', query).set('topK', topK.toString());
    return this.http.get<ClassificationResult[]>(`${this.baseUrl}/rag/search`, { params });
  }

  clearHistory(): Observable<any> {
    return this.http.post(`${this.baseUrl}/rag/clear-history`, {});
  }

  getHistory(): Observable<Array<{ role: string; content: string }>> {
    return this.http.get<Array<{ role: string; content: string }>>(`${this.baseUrl}/rag/history`);
  }
}
