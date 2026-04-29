"""Run from mcp_hub/backend/: python ../run.py  OR  from mcp_hub/: python run.py"""
import sys, os, uvicorn

# ensure backend/ is on sys.path so absolute imports resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True,
                reload_dirs=[os.path.join(os.path.dirname(__file__), "backend")])
