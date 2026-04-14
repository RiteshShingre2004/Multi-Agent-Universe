import os
from groq import Groq
from dotenv import load_dotenv

def test_groq():
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY not found in .env")
        return

    client = Groq(api_key=api_key)
    try:
        print("Attempting to list models...")
        models = client.models.list()
        print("Models found:", [m.id for m in models.data][:5])
        
        print("\nAttempting a small completion...")
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "user", "content": "Say hello briefly."}
            ],
            model="llama-3.1-8b-instant",
        )
        print("Response:", chat_completion.choices[0].message.content)
    except Exception as e:
        print(f"\nCaught Exception: {type(e).__name__}")
        print(f"Error details: {e}")
        if hasattr(e, 'response'):
             print(f"Response Headers: {e.response.headers}")

if __name__ == "__main__":
    test_groq()
