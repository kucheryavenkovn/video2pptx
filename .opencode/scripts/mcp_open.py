import json, time
from http.client import HTTPConnection

c = HTTPConnection("127.0.0.1", 9812, timeout=5)
c.request("POST", "/", json.dumps({"jsonrpc": "2.0", "method": "tools/call",
    "params": {"name": "project_open", "arguments": {"path": "D:/git/video2pptx/out9"}}, "id": 1}),
    {"Content-Type": "application/json"})
print("Open:", json.loads(c.getresponse().read())["result"]["content"][0]["text"])
time.sleep(0.5)

c2 = HTTPConnection("127.0.0.1", 9812, timeout=5)
c2.request("POST", "/", json.dumps({"jsonrpc": "2.0", "method": "tools/call",
    "params": {"name": "get_project"}, "id": 1}), {"Content-Type": "application/json"})
p = json.loads(c2.getresponse().read())
pj = json.loads(p["result"]["content"][0]["text"])
print("Project:", pj["name"], "| Slides:", pj["slides_count"], "| Video:", bool(pj["video"]))
