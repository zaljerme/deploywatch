import asyncio
import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

if os.getenv("ENVIRONMENT", "development") != "development":
    raise RuntimeError("demo service is development-only")

app = FastAPI(title="DeployWatch demo target")
mode = "healthy"


class Mode(BaseModel):
    mode: str


@app.put("/mode")
def change_mode(body: Mode):
    global mode
    if body.mode not in {"healthy", "failing", "slow"}:
        raise HTTPException(422, "mode must be healthy, failing, or slow")
    mode = body.mode
    return {"mode": mode}


@app.get("/health")
async def health():
    current = mode
    if current == "slow":
        await asyncio.sleep(10)
    return JSONResponse({"mode": current}, status_code=503 if current == "failing" else 200)
