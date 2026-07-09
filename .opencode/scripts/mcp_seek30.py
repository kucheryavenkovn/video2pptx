import json
from http.client import HTTPConnection
c = HTTPConnection("127.0.0.1", 9812, timeout=5)
c.request("POST", "/", json.dumps({"jsonrpc": "2.0", "method": "tools/call",
    "params": {"name": "seek", "arguments": {"ts": 30.0}}, "id": 1}),
    {"Content-Type": "application/json"})
r = json.loads(c.getresponse().read())
print("Seek 30s:", json.loads(r["result"]["content"][0]["text"]))
