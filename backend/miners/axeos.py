import httpx

class AxeOSMiner:
    def __init__(self, ip, timeout=3):
        self.ip=ip
        self.base=f"http://{ip}"
        self.timeout=timeout

    async def request(self, method, path, **kwargs):
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r=await c.request(method,self.base+path,**kwargs)
            r.raise_for_status()
            return r.json() if r.content else {}

    async def info(self):
        d=await self.request("GET","/api/system/info")
        pools=d.get("pools") or []
        primary=d.get("primaryPoolIndex",0)
        secondary=d.get("secondaryPoolIndex",1)
        def getpool(i):
            return pools[i] if isinstance(i,int) and 0<=i<len(pools) else {}
        return {
            "ip":self.ip,
            "hostname":d.get("hostname") or self.ip,
            "model":d.get("deviceModel") or d.get("boardVersion") or d.get("ASICModel") or "AxeOS Miner",
            "firmware":d.get("version") or d.get("axeOSVersion") or "",
            "hashrate":d.get("hashRate_1m") or d.get("hashRate") or 0,
            "hashrate_10m":d.get("hashRate_10m") or 0,
            "hashrate_1h":d.get("hashRate_1h") or 0,
            "temperature":d.get("temp"),
            "vrTemp":d.get("vrTemp"),
            "power":d.get("power"),
            "wifiRSSI":d.get("wifiRSSI"),
            "accepted":d.get("sharesAccepted",0),
            "rejected":d.get("sharesRejected",0),
            "poolDifficulty":d.get("poolDifficulty"),
            "fallbackActive":bool(d.get("isUsingFallbackStratum")),
            "failover":bool(d.get("useFallbackStratum")),
            "primaryIndex":primary,
            "secondaryIndex":secondary,
            "primary":getpool(primary),
            "fallback":getpool(secondary),
            "pools":pools,
            "online":True
        }

    async def set_pool(self,index,pool):
        payload=dict(pool)
        payload.setdefault("stratumProtocol","SV1")
        payload.setdefault("stratumPassword","x")
        payload.setdefault("stratumSuggestedDifficulty",0)
        payload.setdefault("stratumExtranonceSubscribe",True)
        payload.setdefault("stratumTLS",False)
        payload.setdefault("stratumDecodeCoinbase",False)
        return await self.request("PUT",f"/api/system/pools/{int(index)}",json=payload)

    async def set_settings(self,primary,secondary,use_fallback):
        return await self.request("PATCH","/api/system",json={
            "primaryPoolIndex":int(primary),
            "secondaryPoolIndex":int(secondary),
            "useFallbackStratum":1 if use_fallback else 0
        })

    async def restart(self):
        return await self.request("POST","/api/system/restart")
