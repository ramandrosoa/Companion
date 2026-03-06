from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])

while True:
    user = input("You: ")
    if user.lower() == "quit":
        break

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": user}]
    )

    print("AI:", response.choices[0].message.content)