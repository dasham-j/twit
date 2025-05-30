import base64
import json

with open("ls.json", "r") as f:
    encoded = base64.b64encode(f.read().encode()).decode()
    print(encoded)

