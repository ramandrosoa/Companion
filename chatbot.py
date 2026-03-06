from groq import Groq
from pip_prompts import get_system_prompt, build_game_context
import os
import random
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])

def chat(history: list, user_message: str, stage: int, game_context: str = None) -> str:
    history.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": get_system_prompt(stage, game_context)}] + history
    )

    reply = response.choices[0].message.content
    history.append({"role": "assistant", "content": reply})
    return reply

# ── MAIN LOOP ──────────────────────────────────
stage = 1
history = []
game_context = None

print(f"Pep is ready. Stage {stage} active.")
print("Commands:")
print("  'switch 2'   — change stage, clears history")
print("  'game'       — simulate a post-game context")
print("  'nogame'     — remove game context")
print("  'reset'      — clear history")
print("  'quit'       — exit")
print("─" * 50)

while True:
    user = input("You: ").strip()

    if not user:
        continue
    elif user == "quit":
        break
    elif user.startswith("switch "):
        stage = int(user.split()[1])
        history = []
        game_context = None
        print(f"── Switched to stage {stage}, history cleared ──")
    elif user == "reset":
        history = []
        print("── History cleared ──")
    elif user == "game":
        game_context = build_game_context(
            stage=stage,
            mode="capitals",
            score=70,
            total=100,
            flagged=[
                "What is the capital of Australia?",
                "What is the capital of Egypt?"
            ]
        )
        history = []
        print(f"── Game context injected for stage {stage} ──")
    elif user == "nogame":
        game_context = None
        history = []
        print("── Game context removed ──")
    else:
        reply = chat(history, user, stage, game_context)
        print(f"Pep: {reply}\n")

