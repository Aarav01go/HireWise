import os
from dotenv import load_dotenv
from google import genai

# Load environment variables from the .env file
load_dotenv()

# Initialize the Gemini client (it automatically looks for GEMINI_API_KEY in the environment)
client = genai.Client()

def test_gemini():
    print("Sending 'say hello' to Gemini...")
    try:
        # Use the flash model to generate a response
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents='Say exactly this: Hello! The API is working perfectly.'
        )
        print("\nGemini says:")
        print(response.text)
    except Exception as e:
        print("\nError connecting to Gemini:", str(e))

if __name__ == "__main__":
    test_gemini()
