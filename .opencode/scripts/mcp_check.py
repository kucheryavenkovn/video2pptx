import json
from http.client import HTTPConnection

c = HTTPConnection("127.0.0.1", 9812, timeout=5)
c.request("POST", "/", json.dumps({"jsonrpc": "2.0", "method": "tools/call",
    "params": {"name": "get_state"}, "id": 1}), {"Content-Type": "application/json"})
r = json.loads(c.getresponse().read())
s = json.loads(r["result"]["content"][0]["text"])
print("Duration:", s["duration"])
for k, v in s["tracks"].items():
    print(f"  {k}: {v['clip_count']} clips")
