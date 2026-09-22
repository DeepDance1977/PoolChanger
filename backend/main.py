import asyncio
import ipaddress
import os
from pathlib import Path
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from .miners.axeos import AxeOSMiner, MinerError

DB_PATH = os.getenv("POOLCHANGER_DB", "/data/poolchanger.db")
DEFAULT_CIDR = os.getenv("POOLCHANGER_SCAN_CIDR", "192.168.0.0/24")
app = FastAPI(title="PoolChanger", version="0.1.0")

class Pool(BaseModel):
    name: str = Field(default="", max_length=100)
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(ge=1, le=65535)
    user: str = ""
    password: str = "x"
    tls: bool = False

class ApplyRequest(BaseModel):
    miner_ips: list[str]
    pool: Pool
    restart: bool = True

@app.get("/")
async def index():
    return FileResponse("frontend/index.html")

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": app.version}

@app.post("/api/miners/scan")
async def scan(cidr: str = DEFAULT_CIDR):
    try:
        network = ipaddress.ip_network(cidr, strict=False)
    except ValueError:
        raise HTTPException(400, "Ungültiges IPv4-Netzwerk")
    hosts = list(network.hosts())
    if len(hosts) > 1024:
        raise HTTPException(400, "Netzwerk zu groß; maximal 1024 Hosts")
    async def probe(ip):
        try:
            return await AxeOSMiner(str(ip)).info(timeout=0.6)
        except Exception:
            return None
    results = await asyncio.gather(*(probe(ip) for ip in hosts))
    return {"cidr": cidr, "miners": [r for r in results if r]}

@app.post("/api/pools/apply")
async def apply_pool(req: ApplyRequest):
    results = []
    for ip in req.miner_ips:
        try:
            miner = AxeOSMiner(ip)
            await miner.set_pool(req.pool)
            if req.restart:
                await miner.restart()
            results.append({"ip": ip, "ok": True})
        except Exception as exc:
            results.append({"ip": ip, "ok": False, "error": str(exc)})
    return {"results": results}
