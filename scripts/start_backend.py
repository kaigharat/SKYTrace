import sys
import os
import asyncio
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn
import traceback
from backend.app.main import app

async def main():
    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )
    server = uvicorn.Server(config)
    # Override signal handler installation to prevent background process auto-exit
    server.install_signal_handlers = lambda: None
    print(f"[Launcher] Starting SkyTrace FastAPI backend on http://127.0.0.1:8000 (Root: {PROJECT_ROOT}) ...", flush=True)
    await server.serve()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"[Launcher Error] {e}", file=sys.stderr, flush=True)
        traceback.print_exc()
