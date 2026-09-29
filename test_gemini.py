import os
from dotenv import load_dotenv
from google import genai

# Load environment variables from .env file
load_dotenv()

# Get the API key
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: GEMINI_API_KEY not found. Please check your .env file.")
else:
    print("API Key found. Testing Gemini...")
    try:
        # Initialize the client
        client = genai.Client(api_key=api_key)
        
        # Call the Gemini Flash model
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents='Say a quick hello to a student building an HRMS project!'
        )
        print("\nGemini says:")
        print(response.text)
    except Exception as e:
        print(f"\nError calling Gemini: {e}")
