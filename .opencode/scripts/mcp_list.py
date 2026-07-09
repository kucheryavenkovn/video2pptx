import json
from http.client import HTTPConnection
c = HTTPConnection("127.0.0.1", 9812, timeout=5)
c.request("POST", "/", json.dumps({"jsonrpc": "2.0", "method": "tools/list", "id": 1}), {"Content-Type": "application/json"})
tools = json.loads(c.getresponse().read())["result"]["tools"]
print("Tools:", len(tools))
for t in tools:
    print(f"  {t['name']}: {t['description'][:60]}")
