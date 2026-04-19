import config
import google.generativeai as genai

genai.configure(api_key=config.GEMINI_API_KEY)
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)
