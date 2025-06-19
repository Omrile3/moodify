# Moodify Backend Workflow

## Message Processing Flow

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI (main.py)
    participant PreferenceHandler (preferences.py)
    participant Extraction (extraction.py)
    participant GPT
    participant Memory (memory.py)

    Client->>FastAPI (main.py): POST /recommend
    FastAPI (main.py)->>PreferenceHandler (preferences.py): extract_user_preferences(message)
    PreferenceHandler (preferences.py)->>Extraction (extraction.py): extract_preferences_raw(message)
    Extraction (extraction.py)->>GPT: Call GPT with preference extraction prompt
    GPT-->>Extraction (extraction.py): Raw preferences
    Extraction (extraction.py)->>Extraction (extraction.py): process_preferences(raw)
    Extraction (extraction.py)-->>PreferenceHandler (preferences.py): Processed preferences
    PreferenceHandler (preferences.py)->>Memory (memory.py): Update session
    Memory (memory.py)-->>FastAPI (main.py): Updated session
    FastAPI (main.py)-->>Client: Response
```

## Component Responsibilities

### main.py
- Handles HTTP endpoints
- Manages session state
- Routes user messages to appropriate handlers
- Coordinates the recommendation flow

### preferences.py
- Manages preference extraction workflow
- Updates session with new preferences
- Tracks preference state (set/not set)
- Determines when all preferences are collected

### extraction.py
- Handles raw GPT API communication for preference extraction
- Processes and validates extracted preferences
- Manages preference normalization and validation
- Handles special cases (no preference, not music, etc.)

### utils.py
- Provides utility functions for chatting and recommendations
- Handles chat response generation
- Manages mood vectors and tempo conversions
- Provides fuzzy matching utilities

### prompts.py
- Centralizes all GPT prompts
- Defines system roles for different GPT contexts
- Configures GPT settings for each prompt type
- Maintains prompt templates

### constants.py
- Defines all constant values
- Maintains lists of valid moods and genres
- Stores mood vectors and API settings
- Defines UI elements and feedback types

### memory.py
- Manages session storage
- Handles preference persistence
- Tracks conversation state

## Preference Processing Flow

1. **Input Reception**
   - User sends message to `/recommend` endpoint
   - Message can be explicit preference or conversation

2. **Preference Extraction**
   ```python
   # main.py
   user_message = preference.artist_or_song or preference.genre or preference.mood or preference.tempo or ""
   extract_user_preferences(message, OPENAI_API_KEY)
   ```

3. **GPT Processing**
   - Raw message sent to GPT for initial extraction
   - GPT returns structured preference data
   - Response is processed and validated
   - Special cases are handled (no preference, not music)

4. **Session Update**
   - New preferences are merged with existing session
   - Missing preferences are tracked
   - "No preference" states are recorded

5. **Recommendation Flow**
   - Once all preferences are set, recommendation engine is triggered
   - Recommendations are filtered based on preferences
   - Response is formatted and sent back to user

## Key Concepts

### Preference Fields
- genre
- mood
- tempo
- artist_or_song

### Session States
- Awaiting feedback
- Has all preferences
- Missing preferences
- No preference markers

### Error Handling
- Invalid preferences
- GPT API failures
- Missing session data
- Malformed responses

### Prompt Management
- System roles for different contexts
- Customizable prompt templates
- GPT parameter configurations
- Fallback responses

### Data Validation
- Mood validation against known set
- Genre validation against known set
- Tempo category normalization
- Fuzzy matching for inexact inputs
