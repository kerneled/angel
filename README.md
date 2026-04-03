# DogSense

Canine Behavior Analysis System — PWA mobile-first para análise comportamental canina em tempo real via câmera e microfone.

## Stack

- **Backend:** FastAPI (Python 3.11+), Wav2Vec2 CPU, Librosa
- **Frontend:** Next.js 16 (App Router, TypeScript, Tailwind CSS), PWA
- **Vision:** Claude Vision API + Gemini Vision API (failover)
- **Realtime:** WebSocket (live camera + mic streaming)
- **Storage:** SQLite
- **Deploy:** Docker Compose + Cloudflare Zero Trust

## Quick Start

```bash
# 1. Configure
cp .env.example .env
# Edit .env with your API keys (ANTHROPIC_API_KEY, GEMINI_API_KEY)

# 2. Run with Docker
make up

# 3. Or run locally (dev)
# Terminal 1:
make api
# Terminal 2:
make frontend

# 4. Health check
make health
```

## Cloudflare Zero Trust Setup

Cloudflare is already installed on the Z600 server (.220).

```bash
# Create tunnel
cloudflared tunnel create dogsense

# Edit cloudflared/config.yml with your tunnel ID

# Route DNS
cloudflared tunnel route dns dogsense dogsense.yourdomain.com

# Run
cloudflared tunnel run dogsense
```

## PWA Install (Android)

1. Open `https://dogsense.yourdomain.com` in Chrome
2. Tap "Add to Home Screen"
3. Grant camera + microphone permissions

## Project Structure

```
angel/
├── docker-compose.yml
├── cloudflared/config.yml
├── .env.example
├── Makefile
├── api/
│   ├── main.py                  # FastAPI app
│   ├── startup.py               # Wav2Vec2 preload
│   ├── config.py                # Settings
│   ├── deps.py                  # Dependency injection
│   ├── routers/
│   │   ├── ws.py                # WebSocket /ws/{session}/{mode}
│   │   └── upload.py            # File upload POST /api/upload
│   ├── services/
│   │   ├── audio_processor.py   # Wav2Vec2 + Librosa fallback
│   │   ├── vision_processor.py  # Frame → LLM Vision
│   │   ├── llm_router.py        # Claude/Gemini with failover
│   │   └── session_store.py     # SQLite persistence
│   └── models/schemas.py        # Pydantic models
└── frontend/
    ├── next.config.ts           # PWA config
    ├── public/manifest.json
    └── src/app/
        ├── page.tsx
        ├── components/          # BottomNav, LiveCamera, LiveAudio, etc.
        ├── hooks/               # useWebSocket, useCamera, useWakeLock
        └── lib/api.ts
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/sessions` | GET | List sessions |
| `/api/sessions/{id}` | GET | Session detail |
| `/api/upload` | POST | Upload file for analysis |
| `/ws/{session_id}/{mode}` | WS | Live streaming (audio/video/combined) |
