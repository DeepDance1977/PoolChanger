import asyncio,ipaddress,os
from fastapi import FastAPI,HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field
from .miners.axeos import AxeOSMiner

app=FastAPI(title="PoolChanger",version="0.3.0")
CIDR=os.getenv("POOLCHANGER_SCAN_CIDR","192.168.0.0/24")

class Pool(BaseModel):
    url:str=Field(min_length=1)
    port:int=Field(ge=1,le=65535)
    user:str=Field(min_length=1)
    password:str="x"
    protocol:str="SV1"
    tls:bool=False
    decode_coinbase:bool=False

class Change(BaseModel):
    miners:list[str]
    primary:Pool
    fallback:Pool|None=None
    failover:bool=False

async def probe(ip):
    try:return await AxeOSMiner(ip).info()
    except:return None

@app.get("/api/miners/scan")
async def scan(cidr:str=CIDR):
    try:net=ipaddress.ip_network(cidr,strict=False)
    except ValueError:raise HTTPException(400,"Ungültiges Netzwerk")
    hosts=list(net.hosts())
    if len(hosts)>512:raise HTTPException(400,"Netzwerk zu groß")
    return [x for x in await asyncio.gather(*(probe(str(i)) for i in hosts)) if x]

def api_pool(p):
    return {
        "stratumProtocol":p.protocol,"stratumURL":p.url,"stratumPort":p.port,
        "stratumUser":p.user,"stratumPassword":p.password,
        "stratumSuggestedDifficulty":0,"stratumExtranonceSubscribe":True,
        "stratumTLS":p.tls,"stratumDecodeCoinbase":p.decode_coinbase
    }

@app.post("/api/pools/apply")
async def apply(c:Change):
    out=[]
    for ip in c.miners:
        try:
            m=AxeOSMiner(ip)
            current=await m.info()
            primary=current["primaryIndex"]
            secondary=current["secondaryIndex"]
            if primary==secondary: secondary=1 if primary!=1 else 0
            await m.set_pool(primary,api_pool(c.primary))
            if c.fallback: await m.set_pool(secondary,api_pool(c.fallback))
            await m.set_settings(primary,secondary,c.failover)
            try: await m.restart()
            except: pass
            out.append({"ip":ip,"ok":True,"primaryIndex":primary,"secondaryIndex":secondary})
        except Exception as e:
            out.append({"ip":ip,"ok":False,"error":str(e)})
    return out

@app.get("/")
async def index(): return FileResponse("frontend/index.html")
