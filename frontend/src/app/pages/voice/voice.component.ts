import { Component, signal, inject, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AiService, ChatMessage, ChatHistorySummary } from '../../services/ai.service';

@Component({
  selector: 'app-voice',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './voice.component.html',
  styleUrls: ['./voice.component.css'],
})
export class VoiceComponent implements OnInit, OnDestroy {
  private aiService = inject(AiService);

  voiceStatus = signal<'idle' | 'recording' | 'processing' | 'done'>('idle');
  isRecording = signal(false);
  isProcessing = signal(false);
  messages = signal<ChatMessage[]>([]);
  currentAudioUrl = signal<string | null>(null);

  selectedLanguage = 'en';
  textInput = '';
  sessionId = `voice-${Date.now()}`;
  
  chatHistoryList = signal<ChatHistorySummary[]>([]);

  // Confirmation modal state
  showConfirmModal = signal(false);
  confirmModalTitle = signal('');
  confirmModalMessage = signal('');
  private pendingConfirmAction: (() => void) | null = null;

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

  ngOnInit(): void {
    this.loadHistoryList();
  }

  loadHistoryList(): void {
    this.aiService.getChatHistoryList().subscribe({
      next: (list) => this.chatHistoryList.set(list),
      error: (err) => console.error('Failed to load history', err)
    });
  }

  loadChatSession(id: string): void {
    console.log('Loading session:', id);
    this.isProcessing.set(true);
    this.sessionId = id;
    this.aiService.getChatSession(id).subscribe({
      next: (msgs) => {
        console.log('Received msgs:', msgs);
        this.messages.set(msgs);
        this.isProcessing.set(false);
      },
      error: (err) => {
        console.error('Failed to load chat', err);
        this.isProcessing.set(false);
      }
    });
  }

  createNewChat(): void {
    this.clearConversation();
  }

  deleteSession(event: Event, sessionId: string): void {
    event.stopPropagation();
    this.openConfirmModal(
      'Delete Chat',
      'Are you sure you want to delete this conversation? This cannot be undone.',
      () => {
        this.aiService.deleteChatSession(sessionId).subscribe({
          next: () => {
            if (this.sessionId === sessionId) this.clearConversation();
            this.loadHistoryList();
          },
          error: (err) => console.error('Failed to delete session', err)
        });
      }
    );
  }

  clearAllHistory(): void {
    this.openConfirmModal(
      'Clear All History',
      'Are you sure you want to delete ALL your chat history? This action is permanent and cannot be undone.',
      () => {
        this.aiService.clearAllChatHistory().subscribe({
          next: () => {
            this.clearConversation();
            this.chatHistoryList.set([]);
          },
          error: (err) => console.error('Failed to clear history', err)
        });
      }
    );
  }

  openConfirmModal(title: string, message: string, action: () => void): void {
    this.confirmModalTitle.set(title);
    this.confirmModalMessage.set(message);
    this.pendingConfirmAction = action;
    this.showConfirmModal.set(true);
  }

  confirmAction(): void {
    if (this.pendingConfirmAction) this.pendingConfirmAction();
    this.dismissModal();
  }

  dismissModal(): void {
    this.showConfirmModal.set(false);
    this.pendingConfirmAction = null;
  }

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
    this.isProcessing.set(true);
    
    this.aiService.transcribeAudio(blob, this.selectedLanguage).subscribe({
      next: (res: { text: string }) => {
        const transcript = res.text || 'Could not understand audio.';
        this.addMessage('user', transcript);
        this.sendToChatApi(transcript);
      },
      error: (err: any) => {
        console.error('Transcription failed:', err);
        this.addMessage('assistant', 'Sorry, I had trouble hearing you. Please try again.');
        this.isProcessing.set(false);
        this.voiceStatus.set('idle');
      }
    });
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
          this.loadHistoryList(); // refresh history list
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
