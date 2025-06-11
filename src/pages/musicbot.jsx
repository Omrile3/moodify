
import React, { useState, useEffect, useRef } from "react";
import { ChatSession, Song } from "@/entities/all";
import { InvokeLLM } from "@/integrations/Core";
import { User } from "@/entities/User";
import ChatMessage from "../components/chat/ChatMessage";
import ChatInput from "../components/chat/ChatInput";
import PreferenceTracker from "../components/chat/PreferenceTracker";
import SongRecommendation from "../components/chat/SongRecommendation";
import LoadingIndicator from "../components/chat/LoadingIndicator";
import { Music, Sparkles, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "framer-motion";

export default function MusicBot() {
  const [chatSession, setChatSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [recommendedSongs, setRecommendedSongs] = useState([]);
  const [user, setUser] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        const currentUser = await User.me();
        setUser(currentUser);
        await initializeChat(currentUser);
      } catch (error) {
        console.log("No user authenticated, starting public session.");
        await initializeChat(null);
      }
    };
    loadData();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const initializeChat = async (currentUser) => {
    try {
      if (currentUser) {
        const existingSessions = await ChatSession.filter({ created_by: currentUser.email }, "-created_date", 1);
        if (existingSessions.length > 0) {
          const session = existingSessions[0];
          setChatSession(session);
          setMessages(session.conversation_history || []);
          
          if (session.recommended_songs?.length > 0) {
            const songs = await Promise.all(
              session.recommended_songs.map(id => Song.get(id).catch(() => null))
            );
            setRecommendedSongs(songs.filter(Boolean));
          }
          return;
        }
      }
      // If no user or no session, start a new one.
      await startNewSession();
    } catch (error) {
      console.error("Error initializing chat, starting new session.", error);
      await startNewSession();
    }
  };

  const startNewSession = async () => {
    const welcomeMessage = {
      role: "bot",
      message: "🎵 Hey there! I'm Moodify, your personal music discovery companion! Tell me about your music taste, mood, or what you're looking for, and I'll help you find the perfect song. What's on your mind?",
      timestamp: new Date().toISOString()
    };

    const newSession = await ChatSession.create({
      conversation_history: [welcomeMessage],
      extracted_preferences: {
        artists: [],
        genres: [],
        moods: [],
        decade: ""
      },
      recommended_songs: [],
      is_complete: false
    });

    setChatSession(newSession);
    setMessages([welcomeMessage]);
    setRecommendedSongs([]);
  };

  const extractPreferences = async (userMessage) => {
    try {
      const prompt = `Analyze this message about music preferences and extract structured data:
      
      Message: "${userMessage}"
      
      Extract any mentioned:
      - Artists (specific artist names)
      - Genres (rock, pop, jazz, hard rock, classic rock, etc.)
      - Moods (happy, sad, energetic, chill, calm, groovy, epic, romantic, etc.)
      - Decade (70s, 80s, 90s, 2000s, etc.)
      
      Return only the JSON object with extracted data. If nothing is found for a category, use empty array or empty string.`;

      const response = await InvokeLLM({
        prompt,
        response_json_schema: {
          type: "object",
          properties: {
            artists: { type: "array", items: { type: "string" } },
            genres: { type: "array", items: { type: "string" } },
            moods: { type: "array", items: { type: "string" } },
            decade: { type: "string" }
          }
        }
      });

      return response;
    } catch (error) {
      console.error("Error extracting preferences:", error);
      return null;
    }
  };

  const generateBotResponse = async (userMessage, currentPreferences) => {
    try {
      const allSongs = await Song.list();
      const hasEnoughInfo = (
        currentPreferences.artists.length > 0 ||
        currentPreferences.genres.length > 0 ||
        currentPreferences.moods.length > 0
      );

      if (hasEnoughInfo && allSongs.length > 0) {
        return await generateRecommendation(currentPreferences, allSongs);
      } else {
        return await generateFollowUpQuestion(userMessage, currentPreferences);
      }
    } catch (error) {
      console.error("Error generating bot response:", error);
      return "I'm having trouble processing that. Could you tell me more about what kind of music you're in the mood for?";
    }
  };

  const generateFollowUpQuestion = async (userMessage, preferences) => {
    const prompt = `You are Moodify, a friendly AI music bot. Based on the user's message and current preferences, ask a natural follow-up question to gather more music preferences.

    User message: "${userMessage}"
    Current preferences: ${JSON.stringify(preferences)}
    
    Ask about missing preferences in a conversational way. Focus on:
    - Specific artists they like
    - Music genres or subgenres they enjoy
    - Current mood or desired energy level (e.g., something energetic or something chill?)
    - Time period/decade preferences
    
    Keep it friendly, conversational, and music-focused. Use emojis sparingly.`;

    const response = await InvokeLLM({ prompt });
    return response;
  };

  const generateRecommendation = async (preferences, songs) => {
    // First, find the best matching songs using our scoring logic
    const matchedSongs = findMatchingSongs(preferences, songs);
    
    // If no good matches, ask for more info
    if (matchedSongs.length === 0) {
      return await generateFollowUpQuestion("I couldn't find a perfect match. Could you provide more details, perhaps a specific artist, genre, or mood?", preferences);
    }
    
    // Take the top 5 candidates for the AI to curate
    const topCandidates = matchedSongs.slice(0, 5);

    const prompt = `You are Moodify, a music recommendation expert. Based on the user's preferences, select the best 1-3 songs from the curated list below and explain why each is a great match.

    User preferences: ${JSON.stringify(preferences)}
    
    Curated song candidates (ranked by relevance): ${JSON.stringify(topCandidates.map(s => ({ title: s.title, artist: s.artist, genre: s.genre, subgenre: s.subgenre, mood: s.mood })))}
    
    Provide a friendly, insightful recommendation message. Explain the connection to the user's taste. Include song titles and artists in your response.`;

    const response = await InvokeLLM({ prompt });
    
    setRecommendedSongs(topCandidates.slice(0, 3));
    
    return response;
  };

  const findMatchingSongs = (preferences, songs) => {
    const scoredSongs = songs.map(song => {
        let score = 0;

        // Artist match (high value)
        if (preferences.artists.length > 0 && preferences.artists.some(artist => song.artist.toLowerCase().includes(artist.toLowerCase()))) {
            score += 10;
        }

        // Genre match
        if (preferences.genres.length > 0 && preferences.genres.some(genre => song.genre.toLowerCase().includes(genre.toLowerCase()))) {
            score += 5;
        }

        // Subgenre match
        if (preferences.genres.length > 0 && song.subgenre && preferences.genres.some(genre => song.subgenre.toLowerCase().includes(genre.toLowerCase()))) {
            score += 3;
        }

        // Mood match (very important)
        if (preferences.moods.length > 0 && song.mood) {
            const moodKeywordsInSong = song.mood.toLowerCase().split(' ');
            const matchedMoods = preferences.moods.filter(prefMood => moodKeywordsInSong.includes(prefMood.toLowerCase()));
            score += matchedMoods.length * 4;
        }
        
        // Decade match
        if (preferences.decade && song.release_date) {
            const releaseYear = new Date(song.release_date).getFullYear();
            const decadeStart = parseInt(preferences.decade.substring(0, 4));
            if (releaseYear >= decadeStart && releaseYear < decadeStart + 10) {
                score += 2;
            }
        }

        return { ...song, score };
    });

    // Filter out songs with a score of 0 and sort by score
    return scoredSongs.filter(song => song.score > 0).sort((a, b) => b.score - a.score);
  };

  const handleSendMessage = async (message) => {
    if (!message.trim()) return;

    const userMessage = {
      role: "user",
      message: message.trim(),
      timestamp: new Date().toISOString()
    };

    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setIsLoading(true);

    try {
      // Extract preferences from user message
      const extractedPrefs = await extractPreferences(message);
      
      // Merge with existing preferences
      const updatedPreferences = {
        artists: [...new Set([...(chatSession.extracted_preferences.artists || []), ...(extractedPrefs?.artists || [])])],
        genres: [...new Set([...(chatSession.extracted_preferences.genres || []), ...(extractedPrefs?.genres || [])])],
        moods: [...new Set([...(chatSession.extracted_preferences.moods || []), ...(extractedPrefs?.moods || [])])],
        decade: extractedPrefs?.decade || chatSession.extracted_preferences.decade || ""
      };

      // Generate bot response
      const botResponse = await generateBotResponse(message, updatedPreferences);
      
      const botMessage = {
        role: "bot",
        message: botResponse,
        timestamp: new Date().toISOString()
      };

      const finalMessages = [...newMessages, botMessage];
      setMessages(finalMessages);

      // Update chat session
      await ChatSession.update(chatSession.id, {
        conversation_history: finalMessages,
        extracted_preferences: updatedPreferences,
        recommended_songs: recommendedSongs.map(s => s.id) // Save recommended song IDs
      });

      setChatSession({
        ...chatSession,
        conversation_history: finalMessages,
        extracted_preferences: updatedPreferences
      });

    } catch (error) {
      console.error("Error handling message:", error);
      const errorMessage = {
        role: "bot",
        message: "Sorry, I encountered an error. Let's try again! What kind of music are you looking for?",
        timestamp: new Date().toISOString()
      };
      setMessages([...newMessages, errorMessage]);
    }

    setIsLoading(false);
  };

  const handleNewChat = async () => {
    setMessages([]);
    setRecommendedSongs([]);
    setChatSession(null);
    await startNewSession();
  };

  if (!chatSession) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingIndicator />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-6">
      <div className="grid lg:grid-cols-3 gap-8">
        {/* Main Chat Area */}
        <div className="lg:col-span-2">
          <div className="clay-element bg-gradient-to-br from-white to-purple-50 p-6 h-[600px] flex flex-col">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="clay-element bg-gradient-to-br from-purple-200 to-pink-200 p-3">
                  <Music className="w-5 h-5 text-purple-600" />
                </div>
                <h2 className="text-xl font-bold text-gray-800">Music Discovery Chat</h2>
              </div>
              <Button
                onClick={handleNewChat}
                className="clay-element bg-gradient-to-r from-mint-200 to-blue-200 text-gray-700 hover:text-gray-800 border-0"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                New Chat
              </Button>
            </div>
            
            {/* Messages */}
            <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-2">
              <AnimatePresence>
                {messages.map((message, index) => (
                  <ChatMessage
                    key={index}
                    message={message}
                    isBot={message.role === "bot"}
                  />
                ))}
              </AnimatePresence>
              {isLoading && <LoadingIndicator />}
              <div ref={messagesEndRef} />
            </div>
            
            {/* Input */}
            <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
          </div>
        </div>
        
        {/* Sidebar */}
        <div className="space-y-6">
          {/* Preferences Tracker */}
          <PreferenceTracker preferences={chatSession.extracted_preferences} />
          
          {/* Song Recommendations */}
          {recommendedSongs.length > 0 && (
            <div className="clay-element bg-gradient-to-br from-white to-green-50 p-6">
              <div className="flex items-center gap-2 mb-4">
                <Sparkles className="w-5 h-5 text-green-600" />
                <h3 className="text-lg font-bold text-gray-800">Recommended Songs</h3>
              </div>
              <div className="space-y-3">
                {recommendedSongs.map((song, index) => (
                  <SongRecommendation key={song.id} song={song} index={index} />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
