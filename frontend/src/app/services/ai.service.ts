import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface PhotoAnswerResponse {
  question_id: string;
  answer_id: string;
  question_text: string;
  answer_text: string;
  latex?: string;
  steps: string[];
  hints: string[];
  voice_url?: string;
  rag_sources: any[];
  confidence?: number;
  processing_time_ms: number;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatResponse {
  session_id: string;
  reply: string;
  tokens_used: number;
}

export interface ChatHistorySummary {
  session_id: string;
  title: string;
  updated_at: string;
}

export interface DashboardStats {
  user: {
    id: string;
    username: string;
    full_name: string;
    avatar_url?: string;
    xp_points: number;
    level: number;
    streak_days: number;
  };
  stats: {
    total_questions_solved: number;
    total_study_minutes: number;
    achievement_count: number;
    xp_to_next_level: number;
  };
  recent_questions: Array<{
    id: string;
    content: string;
    question_type: string;
    is_solved: boolean;
    created_at: string;
  }>;
  unread_notifications: number;
}

@Injectable({ providedIn: 'root' })
export class AiService {
  private readonly API = `${environment.apiUrl}`;

  constructor(private http: HttpClient) {}
  transcribeAudio(blob: Blob, language = 'en'): Observable<{ text: string }> {
    const formData = new FormData();
    formData.append('file', blob, 'audio.webm');
    formData.append('language', language);
    return this.http.post<{ text: string }>(`${this.API}/ai/voice/transcribe`, formData);
  }

  uploadImage(
    file: File,
  ): Observable<{
    image_id: string;
    filename: string;
    processing_status: string;
  }> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<any>(`${this.API}/ai/upload-image`, formData);
  }

  solveFromPhoto(
    imageId: string,
    options?: { language?: string; includeVoice?: boolean },
  ): Observable<PhotoAnswerResponse> {
    return this.http.post<PhotoAnswerResponse>(`${this.API}/ai/solve`, {
      image_id: imageId,
      language: options?.language ?? 'en',
      include_voice: options?.includeVoice ?? false,
    });
  }

  askQuestion(
    content: string,
    subjectId?: string,
    language = 'en',
  ): Observable<PhotoAnswerResponse> {
    return this.http.post<PhotoAnswerResponse>(`${this.API}/ai/ask`, {
      content,
      subject_id: subjectId,
      language,
    });
  }

  sendChatMessage(
    messages: ChatMessage[],
    sessionId: string,
    language = 'en',
  ): Observable<ChatResponse> {
    return this.http.post<ChatResponse>(`${this.API}/ai/chat`, {
      messages,
      session_id: sessionId,
      language,
    });
  }

  getChatHistoryList(): Observable<ChatHistorySummary[]> {
    return this.http.get<ChatHistorySummary[]>(`${this.API}/ai/chat/history`);
  }

  getChatSession(sessionId: string): Observable<ChatMessage[]> {
    return this.http.get<ChatMessage[]>(`${this.API}/ai/chat/history/${sessionId}`);
  }

  deleteChatSession(sessionId: string): Observable<any> {
    return this.http.delete(`${this.API}/ai/chat/history/${sessionId}`);
  }

  clearAllChatHistory(): Observable<any> {
    return this.http.delete(`${this.API}/ai/chat/history`);
  }

  submitFeedback(
    answerId: string,
    rating: number,
    isHelpful: boolean,
    text?: string,
  ): Observable<any> {
    return this.http.patch(`${this.API}/ai/answers/${answerId}/feedback`, {
      is_helpful: isHelpful,
      rating,
      feedback_text: text,
    });
  }

  getDashboardStats(): Observable<DashboardStats> {
    return this.http.get<DashboardStats>(`${this.API}/dashboard/stats`);
  }

  getLeaderboard(period = 'weekly', limit = 10): Observable<any> {
    return this.http.get(
      `${this.API}/dashboard/leaderboard?period=${period}&limit=${limit}`,
    );
  }

  getNotifications(unreadOnly = false): Observable<any[]> {
    return this.http.get<any[]>(
      `${this.API}/dashboard/notifications?unread_only=${unreadOnly}`,
    );
  }

  markNotificationRead(id: string): Observable<any> {
    return this.http.patch(
      `${this.API}/dashboard/notifications/${id}/read`,
      {},
    );
  }

  clearRecentQuestions(): Observable<any> {
    return this.http.delete(`${this.API}/dashboard/questions/clear`);
  }
}
