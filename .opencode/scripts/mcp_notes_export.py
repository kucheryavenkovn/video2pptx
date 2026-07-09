import json, time
from http.client import HTTPConnection

c = HTTPConnection("127.0.0.1", 9812, timeout=30)

# 1. Process Notes
print("=== Processing Notes ===")
c.request("POST", "/", json.dumps({"jsonrpc": "2.0", "method": "tools/call",
    "params": {"name": "notes", "arguments": {}}, "id": 1}),
    {"Content-Type": "application/json"})
r = json.loads(c.getresponse().read())
print("Notes:", json.loads(r["result"]["content"][0]["text"]))
time.sleep(2)

# 2. Export PPTX
print("=== Exporting PPTX ===")
c2 = HTTPConnection("127.0.0.1", 9812, timeout=30)
c2.request("POST", "/", json.dumps({"jsonrpc": "2.0", "method": "tools/call",
    "params": {"name": "export_pptx", "arguments": {}}, "id": 2}),
    {"Content-Type": "application/json"})
r2 = json.loads(c2.getresponse().read())
print("Export:", json.loads(r2["result"]["content"][0]["text"]))
time.sleep(2)

# 3. Check project state
c3 = HTTPConnection("127.0.0.1", 9812, timeout=5)
c3.request("POST", "/", json.dumps({"jsonrpc": "2.0", "method": "tools/call",
    "params": {"name": "get_project", "arguments": {}}, "id": 3}),
    {"Content-Type": "application/json"})
r3 = json.loads(c3.getresponse().read())
pj = json.loads(r3["result"]["content"][0]["text"])
print(f"State: detect_done={pj['state']['detect_done']} notes_done={pj['state']['notes_done']}")
