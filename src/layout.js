
import React from "react";
import { Link, useLocation } from "react-router-dom";
import { createPageUrl } from "@/utils";
import { Music, Heart } from "lucide-react";

export default function Layout({ children, currentPageName }) {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-green-50 relative overflow-hidden">
      <style>{`
        :root {
          --clay-lavender: #E8D5FF;
          --clay-mint: #B8F2D0;
          --clay-blue: #B3E5FC;
          --clay-pink: #FFE0F0;
          --clay-purple: #DDD6FE;
          --clay-shadow: rgba(0, 0, 0, 0.1);
          --clay-shadow-inner: rgba(255, 255, 255, 0.8);
        }
        
        .clay-element {
          border-radius: 20px;
          box-shadow: 
            8px 8px 16px var(--clay-shadow),
            -8px -8px 16px var(--clay-shadow-inner),
            inset 2px 2px 4px rgba(255, 255, 255, 0.8),
            inset -2px -2px 4px rgba(0, 0, 0, 0.1);
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        .clay-element:hover {
          transform: translateY(-2px);
          box-shadow: 
            12px 12px 24px var(--clay-shadow),
            -12px -12px 24px var(--clay-shadow-inner),
            inset 2px 2px 4px rgba(255, 255, 255, 0.9),
            inset -2px -2px 4px rgba(0, 0, 0, 0.05);
        }
        
        .clay-pressed {
          transform: scale(0.98);
          box-shadow: 
            4px 4px 8px var(--clay-shadow),
            -4px -4px 8px var(--clay-shadow-inner),
            inset 4px 4px 8px rgba(0, 0, 0, 0.2),
            inset -4px -4px 8px rgba(255, 255, 255, 0.8);
        }
        
        .floating-shapes {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          pointer-events: none;
          z-index: 0;
        }
        
        .floating-shape {
          position: absolute;
          border-radius: 50%;
          animation: float 6s ease-in-out infinite;
        }
        
        .floating-shape:nth-child(1) {
          width: 80px;
          height: 80px;
          background: linear-gradient(135deg, var(--clay-lavender), var(--clay-purple));
          top: 10%;
          left: 10%;
          animation-delay: 0s;
        }
        
        .floating-shape:nth-child(2) {
          width: 60px;
          height: 60px;
          background: linear-gradient(135deg, var(--clay-mint), var(--clay-blue));
          top: 20%;
          right: 20%;
          animation-delay: 2s;
        }
        
        .floating-shape:nth-child(3) {
          width: 100px;
          height: 100px;
          background: linear-gradient(135deg, var(--clay-pink), var(--clay-lavender));
          bottom: 20%;
          left: 20%;
          animation-delay: 4s;
        }
        
        .floating-shape:nth-child(4) {
          width: 70px;
          height: 70px;
          background: linear-gradient(135deg, var(--clay-blue), var(--clay-purple));
          bottom: 10%;
          right: 10%;
          animation-delay: 1s;
        }
        
        @keyframes float {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          50% { transform: translateY(-20px) rotate(180deg); }
        }
        
        .text-gradient {
          background: linear-gradient(135deg, #8B5CF6, #06B6D4, #10B981);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }
      `}</style>
      
      {/* Floating Background Shapes */}
      <div className="floating-shapes">
        <div className="floating-shape clay-element"></div>
        <div className="floating-shape clay-element"></div>
        <div className="floating-shape clay-element"></div>
        <div className="floating-shape clay-element"></div>
      </div>
      
      {/* Header */}
      <header className="relative z-10 p-6">
        <div className="max-w-6xl mx-auto">
          <div className="clay-element bg-gradient-to-r from-purple-100 to-blue-100 p-6 mb-8">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="clay-element bg-gradient-to-br from-purple-200 to-pink-200 p-4">
                  <Music className="w-8 h-8 text-purple-600" />
                </div>
                <div>
                  <h1 className="text-3xl font-bold text-gradient">Moodify</h1>
                  <p className="text-gray-600 font-medium">Your AI Music Companion</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>
      
      {/* Main Content */}
      <main className="relative z-10 pb-8">
        {children}
      </main>
      
      {/* Footer */}
      <footer className="relative z-10 p-6 mt-12">
        <div className="max-w-6xl mx-auto">
          <div className="clay-element bg-gradient-to-r from-mint-100 to-blue-100 p-6 text-center">
            <div className="flex items-center justify-center gap-2 mb-2">
              <Heart className="w-4 h-4 text-pink-500" />
              <span className="text-gray-600 font-medium">Made with love for music lovers</span>
            </div>
            <p className="text-sm text-gray-500">Discover your next favorite song</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
