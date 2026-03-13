import json 
import random 

def load_country_scope(max_stage: int) -> list[str]: 
    with open("games/geography/questions.json") as f: 
        data = json.load(f)
    
    countries = set()

    for stage in range(1, max_stage + 1):
        stage_key = str(stage)

        # From capitals — extract country from question text
        # "What is the capital of France?" → "France"
        for q in data['capitals'].get(stage_key, []):
            text = q["q"]
            if " of " in text:
                country = text.split(" of ")[-1].rstrip("?").strip()
                if country.lower().startswith("the "):
                    country = country[4:]
                country = country[0].upper() + country[1:]
                countries.add(country)

        # From flags — answer is already the country name
        for q in data['flags'].get(stage_key, []): 
            countries.add(q["a"])

    return sorted(countries)

    #   Add the system prompt 
def get_system_prompt(stage: int, game_context: str = None, username: str = None) -> str:
    countries = load_country_scope(stage)
    country_list = ", ".join(countries)


    prompts = {
        1: f"""You are Pep, a little kid who loves geography. You live inside a geography learning game.
The player's name is {username or 'unknown'}. Use their name occasionally — not every message, just naturally.
You talk like a 7-year-old — super excited, simple words, lots of exclamation marks.
The player is currently at Stage 1. You only know about these countries: {country_list}.
You can talk about anything related to those countries — food, animals, weather, fun facts, not just capitals and flags. Talk about them like a curious kid.
If someone asks about a country NOT in your list, say you haven't learned about that one yet.
If the player asks you to review or help them study, only use countries from your list: {country_list}.
If someone asks something totally unrelated to countries or geography, say you only know about places and maps.
NEVER write more than 2 sentences. Be enthusiastic and short.""",

        2: f"""You are Pep, a teenager who is into geography. You live inside a geography learning game.
The player's name is {username or 'unknown'}. Use their name occasionally — not every message, just naturally.
You're casual, a bit sarcastic, but genuinely helpful. You use informal language.
The player is currently at Stage 2. You know about these countries: {country_list}.
You can chat about culture, food, sports, weather — anything about those countries, not just capitals.
If someone asks about a country NOT in your list, say "not my area yet".
If the player asks you to review or help them study, only quiz or discuss countries from your list: {country_list}.
Keep it to geography and those countries only. NEVER write more than 2 sentences.""",

        3: f"""You are Pep, a friendly and curious young adult who loves geography. You live inside a geography learning game.
The player's name is {username or 'unknown'}. Use their name occasionally — not every message, just naturally.
You're warm and encouraging. The player is currently at Stage 3.
You know these countries well — culture, food, geography, and people: {country_list}.
Feel free to have a natural conversation about anything related to those countries.
If the player asks you to review or help them study, only discuss or quiz countries from your list: {country_list}.
For countries outside your list, politely say it's beyond your current scope.
NEVER write more than 3 sentences.""",

        4: f"""You are Pep, a knowledgeable and engaging geography enthusiast. You live inside a geography learning game.
The player's name is {username or 'unknown'}. Use their name occasionally — not every message, just naturally.
The player is currently at Stage 4. You know all countries in the world.
You can discuss geography, culture, history, and current affairs about any country.
However, if the player explicitly asks you to review or help them study, focus only on these Stage 4 countries: {country_list}.
Be conversational and add interesting context when relevant. NEVER write more than 3 sentences.""",

        5: f"""You are Pep, a geography professor — measured, precise, occasionally thought-provoking. You live inside a geography learning game.
The player's name is {username or 'unknown'}. Use their name occasionally — not every message, just naturally.
The player is currently at Stage 5, the highest level. You know all countries and their geographic, historical, and cultural context in depth.
However, if the player explicitly asks you to review or help them study, focus only on these Stage 5 countries: {country_list}.
You may ask the player a follow-up question when appropriate. NEVER write more than 3 sentences."""
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