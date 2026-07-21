import { Component, signal, inject, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AiService, ChatMessage } from '../../services/ai.service';

@Component({
  selector: 'app-voice',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './voice.component.html',
  styleUrls: ['./voice.component.css'],
})
export class VoiceComponent implements OnDestroy {
  private aiService = inject(AiService);

  voiceStatus = signal<'idle' | 'recording' | 'processing' | 'done'>('idle');
  isRecording = signal(false);
  isProcessing = signal(false);
  messages = signal<ChatMessage[]>([]);
  currentAudioUrl = signal<string | null>(null);

  selectedLanguage = 'en';
  textInput = '';
  sessionId = `voice-${Date.now()}`;

  audioBars = Array.from({ length: 20 }, () => 8);
  private barInterval: ReturnType<typeof setInterval> | null = null;
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];

  sampleQuestions = [
    'What is the quadratic formula?',
    "Explain Newton's laws of motion",
    'How does photosynthesis work?',
    'What is the Pythagorean theorem?',
  ];

  async toggleRecording(): Promise<void> {
    if (this.isRecording()) {
      this.stopRecording();
    } else {
      await this.startRecording();
    }
  }

  async startRecording(): Promise<void> {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.mediaRecorder = new MediaRecorder(stream);
      this.audioChunks = [];

      this.mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) this.audioChunks.push(e.data);
      };

      this.mediaRecorder.onstop = () => {
        const blob = new Blob(this.audioChunks, { type: 'audio/webm' });
        this.processAudioBlob(blob);
        stream.getTracks().forEach((t) => t.stop());
      };

      this.mediaRecorder.start(100);
      this.isRecording.set(true);
      this.voiceStatus.set('recording');
      this.animateBars();
    } catch (err) {
      // Microphone access denied — fall back to text
      console.warn('Mic access denied:', err);
    }
  }

  stopRecording(): void {
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    }
    this.isRecording.set(false);
    this.voiceStatus.set('processing');
    this.clearBarAnimation();
  }

  processAudioBlob(blob: Blob): void {
    // In a real app, upload blob to /api/v1/voice/transcribe
    // For MVP, simulate transcription
    this.isProcessing.set(true);
    const transcript = 'Explain the quadratic formula'; // Simulated

    setTimeout(() => {
      this.addMessage('user', transcript);
      this.sendToChatApi(transcript);
    }, 1000);
  }

  sendTextMessage(): void {
    if (!this.textInput.trim() || this.isProcessing()) return;
    const msg = this.textInput.trim();
    this.textInput = '';
    this.addMessage('user', msg);
    this.sendToChatApi(msg);
  }

  sendToChatApi(question: string): void {
    this.isProcessing.set(true);
    this.voiceStatus.set('processing');

    const allMessages = [...this.messages()];

    this.aiService
      .sendChatMessage(allMessages, this.sessionId, this.selectedLanguage)
      .subscribe({
        next: (res) => {
          this.addMessage('assistant', res.reply);
          this.isProcessing.set(false);
          this.voiceStatus.set('done');
          setTimeout(() => this.voiceStatus.set('idle'), 3000);
        },
        error: () => {
          this.addMessage(
            'assistant',
            'Sorry, I had trouble connecting. Please try again.',
          );
          this.isProcessing.set(false);
          this.voiceStatus.set('idle');
        },
      });
  }

  askSample(q: string): void {
    this.addMessage('user', q);
    this.sendToChatApi(q);
  }

  addMessage(role: 'user' | 'assistant', content: string): void {
    this.messages.update((msgs) => [...msgs, { role, content }]);
  }

  clearConversation(): void {
    this.messages.set([]);
    this.currentAudioUrl.set(null);
    this.sessionId = `voice-${Date.now()}`;
  }

  getStatusIcon(): string {
    const icons: Record<string, string> = {
      idle: 'mic',
      recording: 'fiber_manual_record',
      processing: 'hourglass_empty',
      done: 'check_circle',
    };
    return icons[this.voiceStatus()] ?? 'mic';
  }

  getStatusTitle(): string {
    const titles: Record<string, string> = {
      idle: 'Ready to Listen',
      recording: 'Listening...',
      processing: 'Processing...',
      done: 'Done!',
    };
    return titles[this.voiceStatus()] ?? '';
  }

  getStatusDesc(): string {
    const descs: Record<string, string> = {
      idle: 'Press the button and ask your question',
      recording: 'Speak clearly into your microphone',
      processing: 'Transcribing and generating answer...',
      done: 'Answer generated!',
    };
    return descs[this.voiceStatus()] ?? '';
  }

  private animateBars(): void {
    this.barInterval = setInterval(() => {
      this.audioBars = this.audioBars.map(() => Math.random() * 40 + 8);
    }, 100);
  }

  private clearBarAnimation(): void {
    if (this.barInterval) {
      clearInterval(this.barInterval);
      this.barInterval = null;
    }
    this.audioBars = this.audioBars.map(() => 8);
  }

  ngOnDestroy(): void {
    this.clearBarAnimation();
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    }
  }
}
