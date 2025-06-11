import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Send, Loader2 } from "lucide-react";

export default function ChatInput({ onSendMessage, isLoading }) {
  const [message, setMessage] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !isLoading) {
      onSendMessage(message);
      setMessage("");
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-3">
      <div className="flex-1 clay-element bg-gradient-to-br from-white to-blue-50">
        <Textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Tell me about your music taste, mood, or what you're looking for..."
          className="border-0 bg-transparent resize-none focus:ring-0 focus:outline-none"
          rows={2}
          disabled={isLoading}
        />
      </div>
      <Button
        type="submit"
        disabled={isLoading || !message.trim()}
        className="clay-element bg-gradient-to-br from-purple-200 to-pink-200 text-purple-700 hover:text-purple-800 border-0 px-6"
      >
        {isLoading ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Send className="w-4 h-4" />
        )}
      </Button>
    </form>
  );
}