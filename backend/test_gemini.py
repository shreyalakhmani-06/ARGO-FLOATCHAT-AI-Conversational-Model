import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
key = os.getenv("GEMINI_API_KEY")
if not key:
    raise SystemExit("GEMINI_API_KEY not found. Check that backend/.env exists and is saved.")

client = genai.Client(api_key=key)

MODELS = ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite"]

working = None
for m in MODELS:
    try:
        r = client.models.generate_content(
            model=m, contents="In one sentence, what is an Argo float?")
        print(f"[OK] {m}\n{r.text}\n")
        working = m
        break
    except Exception as e:
        print(f"[FAILED] {m}: {str(e)[:150]}\n")

if not working:
    raise SystemExit("No model worked. Paste the errors above into the chat.")

# Second test: ask for JSON output (this is what the real app will need)
r = client.models.generate_content(
    model=working,
    contents=('Extract filters from: "temperature in the Arabian Sea in March 2023". '
              'Return JSON with keys: parameter, region, month, year.'),
    config=types.GenerateContentConfig(response_mime_type="application/json"),
)
print("JSON test:", r.text)
print("\nUse this model name from now on:", working)