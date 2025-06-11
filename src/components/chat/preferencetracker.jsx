
import React from "react";
import { Badge } from "@/components/ui/badge";
import { Music, Heart, Zap, Calendar, Palette } from "lucide-react";
import { motion } from "framer-motion";

export default function PreferenceTracker({ preferences }) {
  const hasPreferences = Object.values(preferences).some(val => 
    Array.isArray(val) ? val.length > 0 : val !== ""
  );

  if (!hasPreferences) {
    return (
      <div className="clay-element bg-gradient-to-br from-white to-mint-50 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Heart className="w-5 h-5 text-mint-600" />
          <h3 className="text-lg font-bold text-gray-800">Your Preferences</h3>
        </div>
        <p className="text-gray-500 text-sm">
          I'll track your music preferences as we chat!
        </p>
      </div>
    );
  }

  return (
    <div className="clay-element bg-gradient-to-br from-white to-mint-50 p-6">
      <div className="flex items-center gap-2 mb-4">
        <Heart className="w-5 h-5 text-mint-600" />
        <h3 className="text-lg font-bold text-gray-800">Your Preferences</h3>
      </div>
      
      <div className="space-y-4">
        {preferences.artists?.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Music className="w-4 h-4 text-purple-600" />
              <span className="text-sm font-semibold text-gray-700">Artists</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {preferences.artists.map((artist, index) => (
                <motion.div
                  key={artist}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: index * 0.1 }}
                >
                  <Badge className="clay-element bg-gradient-to-r from-purple-100 to-pink-100 text-purple-700 border-0">
                    {artist}
                  </Badge>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {preferences.genres?.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Palette className="w-4 h-4 text-blue-600" />
              <span className="text-sm font-semibold text-gray-700">Genres</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {preferences.genres.map((genre, index) => (
                <motion.div
                  key={genre}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: index * 0.1 }}
                >
                  <Badge className="clay-element bg-gradient-to-r from-blue-100 to-mint-100 text-blue-700 border-0">
                    {genre}
                  </Badge>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {preferences.moods?.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Heart className="w-4 h-4 text-pink-600" />
              <span className="text-sm font-semibold text-gray-700">Moods</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {preferences.moods.map((mood, index) => (
                <motion.div
                  key={mood}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: index * 0.1 }}
                >
                  <Badge className="clay-element bg-gradient-to-r from-pink-100 to-purple-100 text-pink-700 border-0">
                    {mood}
                  </Badge>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {preferences.decade && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Calendar className="w-4 h-4 text-green-600" />
              <span className="text-sm font-semibold text-gray-700">Era</span>
            </div>
            <Badge className="clay-element bg-gradient-to-r from-green-100 to-mint-100 text-green-700 border-0">
              {preferences.decade}
            </Badge>
          </div>
        )}
      </div>
    </div>
  );
}
