import json 
import random 

def load_country_scope(max_stage: int) -> list[str]: 
    with open("games/geography/questions.json") as f: 
        data = json.load(f)
    
    countries = set()

    for stage in range(1, max_stage + 1):
        stage_key = str(stage)

        #   from capitals
        for q in data['capitals'].get(stage_key, []): 
            countries.add(q["a"])

        #   from flags
        for q in data['flags'].get(stage_key, []): 
            countries.add(q["a"])

    return sorted(countries)

    #   Add the system prompt 
def get_system_prompt(stage: int, game_context: str = None) -> str:

    countries = load_country_scope(stage)
    country_list = ", ".join(countries)

    prompts = {
            1: f"""You are Pep, a geography helper in a learning game.
    You talk like a young child. Use very simple words. Short sentences only.
    Use lots of exclamation marks. Be very excited about everything.
    You only know about these countries: {country_list}.
    If someone asks about a country NOT in that list, say you don't know that one yet.
    Only talk about geography. If someone asks about something else, say you only know about maps and countries.
    Keep all answers under 3 sentences.""",

            2: f"""You are Pep, a geography assistant in a learning game.
    You talk like a teenager. Be casual, use informal language, occasionally sarcastic but still helpful.
    You know about these countries: {country_list}.
    If asked about a country not in your list, say something like "not my area, sorry".
    Only discuss geography. Keep responses to 2-3 sentences max.""",

            3: f"""You are Pep, a geography assistant in a learning game.
    You are warm, encouraging, and friendly like a young adult.
    You know about these countries: {country_list}.
    For countries outside your list, politely say it's beyond your current scope.
    Only discuss geography. Responses should be 2-4 sentences.""",

            4: f"""You are Pep, a geography assistant in a learning game.
    You are knowledgeable and engaging, like a curious adult.
    You know about all countries in the world.
    Only discuss geography topics. Add interesting context when relevant.
    Responses can be 3-5 sentences.""",

            5: f"""You are Pep, a geography assistant in a learning game.
    You speak like a professor — measured, precise, occasionally thought-provoking.
    You know about all countries and their geographic, historical and cultural context.
    Only discuss geography. You may ask the user a follow-up question when appropriate.
    Keep responses rich but concise."""
        }
    
    base = prompts[stage]

    if game_context: 
        base += f"\n\nGame context : {game_context}"

    
    return base

def build_game_context(stage, mode, correct, wrong, total, mastered_hit, flagged):
    flagged_str = ", ".join(flagged) if flagged else "none"
    return (
        f"The user just finished a {mode} game at stage {stage}. "
        f"They got {correct}/{total} correct and {wrong} wrong. "
        f"{mastered_hit} of the correct answers were already mastered. "
        f"Questions they struggled with (wrong twice): {flagged_str}."
    )

MESSAGES = {
    1: {
        "correct": [
            "YAY!!! YOU GOT IT RIGHT!!! 🌟",
            "WOW!!! SO SMART!!! KEEP GOING!!!",
            "CORRECT!!! YOU ARE AMAZING!!! 🎉",
            "YES YES YES!!! THAT'S RIGHT!!!",
            "WOOHOO!!! YOU DID IT!!! 🌍"
        ],
        "wrong": [
            "OOPS... THAT WAS NOT RIGHT...",
            "NOOO... TRY AGAIN!! YOU CAN DO IT!!",
            "HMMMM... NOT QUITE... 😅",
            "OH NO... WRONG ONE... BUT KEEP TRYING!!",
            "ALMOST!! NOT THAT ONE THOUGH..."
        ]
    },
    2: {
        "correct": [
            "ok that was actually impressive ngl",
            "yeah you got it, not bad at all",
            "lowkey knew you'd get that one 😎",
            "alright alright, that's correct",
            "ok i'll admit that one was tricky and you nailed it"
        ],
        "wrong": [
            "bruh... that's not it",
            "nah that's wrong, happens to everyone",
            "not quite, try to think about it",
            "yikes, wrong answer but you'll get it",
            "hmm nope, better luck next time"
        ]
    },
    3: {
        "correct": [
            "Nice one! You're really getting the hang of this 😊",
            "That's correct! Keep that momentum going.",
            "Well done! Geography is starting to click for you.",
            "Great answer! You should feel good about that one.",
            "Spot on! That one trips a lot of people up."
        ],
        "wrong": [
            "Not this time, but you're learning with every attempt.",
            "So close! Don't let it discourage you.",
            "Wrong answer, but the right one is worth remembering.",
            "That one's tricky — don't worry about it.",
            "Not quite, but you'll get it next time for sure."
        ]
    },
    4: {
        "correct": [
            "Well done. That one requires real knowledge.",
            "Correct — and that's not an easy one to remember.",
            "Good. You're building a solid geography foundation.",
            "Right answer. These questions separate the serious learners.",
            "Exactly right. That fact is worth holding onto."
        ],
        "wrong": [
            "Not correct. Take a moment to register the right answer.",
            "Wrong this time — but mistakes are how we learn.",
            "That one catches a lot of people. Note the correct answer.",
            "Incorrect, but you're tackling genuinely hard material.",
            "Not quite. These questions are supposed to be challenging."
        ]
    },
    5: {
        "correct": [
            "Correct. A question few people answer confidently.",
            "Precisely right. Your knowledge at this level is impressive.",
            "Indeed. That answer reflects genuine geographic understanding.",
            "Well recalled. These details matter at this stage.",
            "Exactly. The most advanced questions demand this precision."
        ],
        "wrong": [
            "Not correct — but this is the hardest material there is.",
            "Incorrect. Even experienced geography students stumble here.",
            "Wrong, though the correct answer is genuinely obscure.",
            "Not this time. Revisit it — it will surface again.",
            "Incorrect. These questions are designed to humble even experts."
        ]
    }
}

def get_message(stage: int, result: str) -> str:
    return random.choice(MESSAGES[stage][result])