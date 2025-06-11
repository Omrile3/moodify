import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const Song = {
  list: async () => {
    const response = await apiClient.get('/songs');
    return response.data;
  },
  get: async (id) => {
    const response = await apiClient.get(`/songs/${id}`);
    return response.data;
  },
};

export const ChatSession = {
  filter: async (params) => {
    const response = await apiClient.get('/chat-sessions', { params });
    return response.data;
  },
  create: async (data) => {
    const response = await apiClient.post('/chat-sessions', data);
    return response.data;
  },
  update: async (id, data) => {
    const response = await apiClient.put(`/chat-sessions/${id}`, data);
    return response.data;
  },
};

export const InvokeLLM = async ({ prompt, response_json_schema }) => {
  const response = await apiClient.post('/invoke-llm', { prompt, response_json_schema });
  return response.data;
};
