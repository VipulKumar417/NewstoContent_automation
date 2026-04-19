import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

keys = [
    os.getenv("GEMINI_API_KEY_1"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3")
]

with open("key_diag.txt", "w", encoding="utf-8") as f:
    f.write("Testing Gemini Keys Individually...\n")
    for i, k in enumerate(keys):
        if not k:
            f.write(f"Key {i+1}: Not configured in .env\n")
            continue
        
        k = k.strip()
        f.write(f"Key {i+1}: Length {len(k)}\n")
        
        try:
            genai.configure(api_key=k)
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content("hello")
            f.write(f"Key {i+1} -> OK! (Response: {response.text.strip()[:15]}...)\n")
        except Exception as e:
            f.write(f"Key {i+1} -> ERROR: {e}\n")
