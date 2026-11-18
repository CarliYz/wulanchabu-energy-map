"""Serve this worktree, including unchanged relative GLB/data URLs, on 8767 only."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

root = Path(__file__).resolve().parents[2]
handler = partial(SimpleHTTPRequestHandler, directory=str(root))
server = ThreadingHTTPServer(("127.0.0.1", 8767), handler)
print("Serving M9: http://127.0.0.1:8767/web/map-prototype/", flush=True)
server.serve_forever()
