import { Component, OnInit, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: string[];
  retrievedDocs?: number;
  timestamp: Date;
}

@Component({
  selector: 'app-rag-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './rag-chat.component.html'
})
export class RagChatComponent implements OnInit, AfterViewChecked {
  @ViewChild('chatContainer') chatContainer!: ElementRef;

  messages: ChatMessage[] = [];
  userInput = '';
  isLoading = false;
  error: string | null = null;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getHistory().subscribe({
      next: (history) => {
        this.messages = history.map(h => ({
          role: h['role'] as 'user' | 'assistant',
          content: h['content'],
          timestamp: new Date()
        }));
      },
      error: () => {} // Ignore history load errors
    });
  }

  ngAfterViewChecked(): void {
    this.scrollToBottom();
  }

  sendMessage(): void {
    const query = this.userInput.trim();
    if (!query || this.isLoading) return;

    this.messages.push({ role: 'user', content: query, timestamp: new Date() });
    this.userInput = '';
    this.isLoading = true;
    this.error = null;

    this.api.queryRag(query).subscribe({
      next: (response) => {
        this.messages.push({
          role: 'assistant',
          content: response.answer,
          sources: response.sources,
          retrievedDocs: response.retrievedDocs,
          timestamp: new Date()
        });
        this.isLoading = false;
      },
      error: (err) => {
        this.error = '查询失败：' + (err.error?.error || err.message);
        this.isLoading = false;
      }
    });
  }

  clearHistory(): void {
    this.api.clearHistory().subscribe({
      next: () => {
        this.messages = [];
        this.error = null;
      },
      error: (err) => this.error = '清除失败：' + err.message
    });
  }

  private scrollToBottom(): void {
    try {
      const el = this.chatContainer?.nativeElement;
      if (el) el.scrollTop = el.scrollHeight;
    } catch {}
  }

  onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }
}
