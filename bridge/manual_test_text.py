"""Test COPOM without microphone or GTA. Run while server and Ollama are active."""
import time
import requests
base = "http://127.0.0.1:8765"
response = requests.post(base + "/start", json={"mode":"copom", "identity":"COPOM", "location":"Davis", "text":"QAP, COPOM. Prefixo 111 iniciando patrulhamento. Algum QTC?"}, timeout=10)
response.raise_for_status()
jid = response.json()["id"]
for _ in range(120):
    result = requests.get(base + "/status/" + jid, timeout=10).json()
    if result["state"] in ("done", "error"):
        print(result)
        break
    time.sleep(1)
else:
    print("Timeout")
