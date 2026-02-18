export interface APIResponse<T = any> {
  status: "SUCCESS" | "FAIL";
  message: string;
  data: T;
}

export interface LoginRequest {
  username?: string;
  email?: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  name: string;
  email: string;
  password: string;
}

export interface User {
  id: string;
  username: string;
  name: string;
  email: string;
}

export interface TokenResponse extends APIResponse<{
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: {
    id: string;
    username: string;
    name: string;
    email: string;
  }
}> {}

export interface UserResponse extends APIResponse<User> {}

export interface SessionResponse extends APIResponse<Session> {}

export interface SessionsResponse extends APIResponse<Session[]> {}

export interface Session {
  id: string;
  user_id: string;
  title: string;
  model_name: string;
  created_at: string;
  updated_at: string;
}

export interface MessageResponse extends APIResponse<Message> {}

export interface MessagesResponse extends APIResponse<Message[]> {}

export interface FileAttachment {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  file_url: string;
  created_at: string;
}

export interface Message {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  extra_metadata?: Record<string, any>;
  files?: FileAttachment[];
  created_at: string;
  updated_at: string;
}

export interface SessionCreate {
  title?: string;
  model_name?: string;
  message?: string;
}

export interface SessionUpdate {
  title?: string;
  model_name?: string;
}

export interface ChatRequest {
  content: string;
}

export interface Model {
  id: string;
  name: string;
  context_length: number;
  description: string;
}

export interface ModelsResponse extends APIResponse<Model[]> {}

export interface TranscribeResponse extends APIResponse<{
  text: string;
}> {}