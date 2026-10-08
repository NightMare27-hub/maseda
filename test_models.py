import os, time
from dotenv import load_dotenv
load_dotenv()
import litellm

candidates = [
    "gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.7-flash",
    "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite",
    "gemini-3.8-flash",
]
for name in candidates:
    t = time.time()
    try:
        r = litellm.completion(model=f"gemini/{name}",
                               messages=[{"role": "user", "content": "Say hi in 3 words"}],
                               timeout=45)
        print(f"OK    {name:28} {time.time()-t:4.1f}s  {r.choices[0].message.content.strip()[:30]}")
    except Exception as e:
        msg = str(e).lower()
        why = ("retired/closed" if "no longer available" in msg else
               "overloaded" if "503" in msg or "high demand" in msg else
               "rate limit/quota" if "429" in msg or "quota" in msg else
               "timeout" if "timeout" in msg or "timed out" in msg else "other error")
        print(f"FAIL  {name:28} {why}")