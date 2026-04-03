#!/bin/bash
cd /home/kcpele/backend
exec .venv/bin/python -m uvicorn fastapi_app.main:app --host 0.0.0.0 --port 8888 --workers 4
