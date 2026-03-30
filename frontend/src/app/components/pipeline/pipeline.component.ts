import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { PlacenameRecord } from '../../models/placename-record.model';

@Component({
  selector: 'app-pipeline',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './pipeline.component.html'
})
export class PipelineComponent implements OnInit {
  status: any = null;
  records: PlacenameRecord[] = [];
  searchQuery = '';
  isUploading = false;
  isLoading = false;
  uploadResult: any = null;
  error: string | null = null;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.loadStatus();
    this.loadRecords();
  }

  loadStatus(): void {
    this.api.getPipelineStatus().subscribe({
      next: (status) => this.status = status,
      error: (err) => this.error = '无法加载状态：' + err.message
    });
  }

  loadRecords(): void {
    this.isLoading = true;
    this.api.getAllRecords().subscribe({
      next: (records) => {
        this.records = records;
        this.isLoading = false;
      },
      error: (err) => {
        this.error = '无法加载记录：' + err.message;
        this.isLoading = false;
      }
    });
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    this.isUploading = true;
    this.error = null;
    this.uploadResult = null;

    this.api.uploadFile(file).subscribe({
      next: (result) => {
        this.uploadResult = result;
        this.isUploading = false;
        this.loadStatus();
        this.loadRecords();
      },
      error: (err) => {
        this.error = '上传失败：' + (err.error?.error || err.message);
        this.isUploading = false;
      }
    });
  }

  search(): void {
    if (!this.searchQuery.trim()) {
      this.loadRecords();
      return;
    }
    this.isLoading = true;
    this.api.searchRecords(this.searchQuery).subscribe({
      next: (records) => {
        this.records = records;
        this.isLoading = false;
      },
      error: (err) => {
        this.error = '搜索失败：' + err.message;
        this.isLoading = false;
      }
    });
  }

  clearSearch(): void {
    this.searchQuery = '';
    this.loadRecords();
  }
}
