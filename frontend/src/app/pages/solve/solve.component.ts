import { Component, signal, inject, ElementRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AiService, PhotoAnswerResponse } from '../../services/ai.service';

@Component({
  selector: 'app-solve',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './solve.component.html',
  styleUrls: ['./solve.component.css']
})
export class SolveComponent {
  private aiService = inject(AiService);

  inputMode = signal<'photo' | 'text'>('photo');
  isDragging = signal(false);
  uploadedFile = signal<File | null>(null);
  previewUrl = signal<string | null>(null);
  isSolving = signal(false);
  error = signal('');
  answer = signal<PhotoAnswerResponse | null>(null);
  feedbackSubmitted = signal(false);

  language = 'en';
  includeVoice = false;
  textQuestion = '';

  imageId: string | null = null;

  pipelineSteps = [
    { label: '👁️ Vision Enhancement', done: false, active: false },
    { label: '📝 OCR Extraction', done: false, active: false },
    { label: '🧮 Math Analysis', done: false, active: false },
    { label: '📚 RAG Knowledge Search', done: false, active: false },
    { label: '🤖 LLM Answer Generation', done: false, active: false },
  ];

  onDragOver(e: DragEvent): void {
    e.preventDefault();
    this.isDragging.set(true);
  }

  onDrop(e: DragEvent): void {
    e.preventDefault();
    this.isDragging.set(false);
    const file = e.dataTransfer?.files?.[0];
    if (file) this.setFile(file);
  }

  onFileSelected(e: Event): void {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file) this.setFile(file);
  }

  setFile(file: File): void {
    this.uploadedFile.set(file);
    const reader = new FileReader();
    reader.onload = (e) => this.previewUrl.set(e.target?.result as string);
    reader.readAsDataURL(file);
    this.answer.set(null);
    this.error.set('');
  }

  clearFile(e: Event): void {
    e.stopPropagation();
    this.uploadedFile.set(null);
    this.previewUrl.set(null);
    this.imageId = null;
  }

  async solvePhoto(): Promise<void> {
    const file = this.uploadedFile();
    if (!file) return;

    this.isSolving.set(true);
    this.error.set('');
    this.answer.set(null);
    this.simulatePipeline();

    // Upload image first
    this.aiService.uploadImage(file).subscribe({
      next: (uploadRes) => {
        this.imageId = uploadRes.image_id;

        // Then run pipeline
        this.aiService.solveFromPhoto(uploadRes.image_id, {
          language: this.language,
          includeVoice: this.includeVoice,
        }).subscribe({
          next: (ans) => {
            this.answer.set(ans);
            this.isSolving.set(false);
            this.resetPipeline();
          },
          error: (err) => {
            this.error.set(err?.error?.detail ?? 'Failed to solve. Please try again.');
            this.isSolving.set(false);
            this.resetPipeline();
          },
        });
      },
      error: (err) => {
        this.error.set(err?.error?.detail ?? 'Upload failed.');
        this.isSolving.set(false);
        this.resetPipeline();
      },
    });
  }

  solveText(): void {
    if (!this.textQuestion.trim()) return;
    this.isSolving.set(true);
    this.error.set('');
    this.answer.set(null);

    this.aiService.askQuestion(this.textQuestion, undefined, this.language).subscribe({
      next: (ans) => {
        this.answer.set(ans);
        this.isSolving.set(false);
      },
      error: (err) => {
        this.error.set(err?.error?.detail ?? 'Failed to get answer.');
        this.isSolving.set(false);
      },
    });
  }

  submitFeedback(isHelpful: boolean, rating: number): void {
    const ans = this.answer();
    if (!ans) return;
    this.aiService.submitFeedback(ans.answer_id, rating, isHelpful).subscribe();
    this.feedbackSubmitted.set(true);
  }

  private simulatePipeline(): void {
    this.resetPipeline();
    let i = 0;
    const interval = setInterval(() => {
      if (i > 0) { this.pipelineSteps[i - 1].active = false; this.pipelineSteps[i - 1].done = true; }
      if (i < this.pipelineSteps.length) {
        this.pipelineSteps[i].active = true;
        i++;
      } else {
        clearInterval(interval);
      }
    }, 1500);
  }

  private resetPipeline(): void {
    this.pipelineSteps.forEach(s => { s.done = false; s.active = false; });
  }
}
