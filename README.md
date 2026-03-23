# 🌍 Companion

> A Flask-based geography learning game where the UI transforms across 5 stages as the player masters world capitals and flags, paired with an AI companion powered by Groq.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=flat&logo=flask&logoColor=white)
![Redis](https://img.shields.io/badge/Upstash_Redis-REST_API-DC382D?style=flat&logo=redis&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-LLaMA_3-F55036?style=flat&logo=groq&logoColor=white)
![Vercel](https://img.shields.io/badge/Deployed_on-Vercel-000000?style=flat&logo=vercel&logoColor=white)
![Mobile](https://img.shields.io/badge/Mobile-Responsive-39ff14?style=flat&logo=safari&logoColor=white)

---

## 🗺️ Overview

Companion is a single-player quiz game that grows with you. The interface starts as a monochrome retro terminal and evolves into a sleek, modern UI as you progress through 5 stages. Each stage unlocks new features, harder questions, and a more expressive version of Pep — your AI companion.

---

## ✨ Features

- 🌱 **5 evolving stages** — Seed → Sprout → Sapling → Tree → Ancient, each with a distinct visual identity
- 🏛️ **Two quiz modes** — Capitals and Flags, 10 questions per session
- 🎯 **Mastery system** — each question has a 10 XP lifetime cap; questions are fully mastered once the cap is reached
- ⚡ **XP and streak tracking** — session XP, streak, best streak, and accuracy metrics
- 💡 **Hint system** — available from Stage 3, with XP penalties per hint used
- 🐱 **Pep** — an AI companion powered by Groq that knows your stage, your country list, and your quiz results; personality evolves across stages
- 🔐 **Authentication** — login via username + email, stored in Upstash Redis
- 🎉 **Completion screen** — confetti celebration when all 5 stages are fully mastered
- 🎊 **Stage-up transitions** — animated confetti on every stage unlock
- 
---

| Layer | Technology |
|---|---|
| 🐍 Backend | Python / Flask |
| 🗄️ Database | Upstash Redis (REST API) |
| 🤖 AI companion | Groq API (LLaMA 3) |
| 🎨 Frontend | Jinja2 templates, vanilla CSS + JS |
| 🚀 Deployment | Vercel |

---

## 📁 Project Structure

```
Companion/
├── app.py                        # Main Flask application, all routes
├── pip_prompts.py                # Pep's system prompts and pre-written messages
├── requirements.txt
│
├── core/
│   ├── context.py                # Builds template context from user data
│   ├── redis_client.py           # Upstash Redis connection
│   ├── session.py                # In-session game state (Flask session keys)
│   ├── stage.py                  # Stage logic: XP thresholds, can_stage_up, is_game_complete
│   └── user.py                   # User CRUD: load, save, award_xp, mastered_count
│
├── games/
│   └── geography/
│       ├── game.py               # Question loading, hint logic, XP worth, fuzzy matching
│       └── questions.json        # All quiz questions (capitals + flags, stages 1–5)
│
├── static/
│   ├── css/
│   │   ├── s1.css                # Stage 1 — monochrome green retro terminal
│   │   ├── s2.css                # Stage 2 — user-chosen tint color
│   │   ├── s3.css                # Stage 3 — full color palette
│   │   ├── s4.css                # Stage 4 — modern dark UI
│   │   └── s5.css                # Stage 5 — cosmic / ancient, sparkle background
│   └── js/
│       ├── companion.js          # XP toast, answer button disable logic
│       └── pep.js                # Pep widget: toggle, send message, auto-open logic
│
└── templates/
    ├── base.html                 # Shared layout, top bar, XP bar, Pep widget
    ├── login.html                # Login page (username or email)
    ├── signup.html               # Sign up page
    ├── menu.html                 # Main menu
    ├── complete.html             # Game completion screen
    ├── stage_up.html             # Stage transition screen
    ├── dev.html
    └── games/
        ├── geo_menu.html         # Geography mode selector
        ├── question.html         # Quiz question screen
        └── results.html          # Session results screen
```

---

## 🎮 Game Mechanics

### 🌱 Stages

| Stage | Name | Features unlocked |
|---|---|---|
| 1 | 🌱 Seed | 2-option questions, monochrome UI |
| 2 | 🌿 Sprout | 3-option questions, color tint choice |
| 3 | 🌳 Sapling | 4-option questions, full color palette, hints |
| 4 | 🌲 Tree | 4-option questions, modern UI, hints |
| 5 | ✨ Ancient | Free-type answers, cosmic UI, hints |

### ⚡ XP and Mastery

- Each question has a **10 XP lifetime cap**
- Correct answer = full XP (or reduced if hints were used)
- Once a question reaches 10 XP it is **mastered** — it still appears in sessions but earns 0 XP
- Stage up requires: **all 20 questions mastered** (10 capitals + 10 flags) AND **200 XP total**

### 💡 Hints (Stage 3+)

| Stage | Hint effect | XP |
|---|---|---|
| 🌳 3 | Removes one wrong option | 10 → 5 |
| 🌲 4 | First hint removes one option, second removes another | 10 → 6 → 2 |
| ✨ 5 | Type-answer mode — each hint reveals a wrong option | 10 → 7 → 4 → 1 |

### 📊 Accuracy

Accuracy is calculated as `theoretical XP earned / max possible XP × 100`. It reflects session performance regardless of mastery — a mastered question that earns 0 XP still counts toward theoretical XP.

### 🐱 Pep

Pep is an AI companion that lives in the bottom-right corner of every screen as an animated cat. Personality and knowledge scope evolve per stage:

| Stage | Personality | Knowledge scope |
|---|---|---|
| 🌱 1 | Excited 7-year-old | Stage 1 countries only |
| 🌿 2 | Casual teenager | Up to Stage 2 countries |
| 🌳 3 | Friendly young adult | Broader cultural knowledge |
| 🌲 4 | Knowledgeable adult | All countries |
| ✨ 5 | Measured professor | All countries + follow-up questions |

Pep auto-opens after sessions with performance feedback, on stage-up with congratulations, and on the menu with a personalised welcome-back message using the player's username.

---

## ⚙️ Setup

### Prerequisites

- Python 3.10+
- A [Groq](https://console.groq.com) API key
- An [Upstash Redis](https://upstash.com) database (free tier works)

### Installation

```bash
git clone https://github.com/ramandrosoa/Companion.git
cd companion
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 🔑 Environment variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key
UPSTASH_REDIS_URL=https://your-url.upstash.io
UPSTASH_REDIS_TOKEN=your_token
FLASK_SECRET_KEY=your_secret_key
```

### ▶️ Run locally

```bash
python app.py
```

---

## 🚀 Deployment

The app is deployed on Vercel.

Environment variables must be added in the Vercel dashboard under **Settings → Environment Variables**.

---
