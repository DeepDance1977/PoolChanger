import asyncio
import httpx

class MinerError(Exception):
    pass

class AxeOSMiner:
    """Adapter for the AxeOS REST API."""

    def __init__(self, ip: str):
        self.ip = ip.strip().replace("http://", "").replace("https://", "").rstrip("/")
        self.base = f"http://{self.ip}"

    async def _request(self, method: str, path: str, **kwargs):
        try:
            async with httpx.AsyncClient(timeout=kwargs.pop("timeout", 2.0), follow_redirects=False) as client:
                response = await client.request(method, self.base + path, **kwargs)
        except (httpx.HTTPError, asyncio.TimeoutError) as exc:
            raise MinerError(f"{self.ip}: {exc}") from exc
        if response.status_code >= 400:
            raise MinerError(f"{self.ip}: HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError:
            return {}

    async def info(self, timeout: float = 2.0):
        data = await self._request("GET", "/api/system/info", timeout=timeout)
        return {
            "ip": self.ip,
            "name": data.get("hostname") or data.get("boardName") or self.ip,
            "model": data.get("boardName") or data.get("board") or "AxeOS",
            "version": data.get("version") or data.get("axeOSVersion") or "",
            "hashrate": data.get("hashRate") or data.get("hashrate") or 0,
            "temperature": _temperature(data),
            "power": _power(data),
            "pool": _pool(data),
        }

    async def set_pool(self, pool):
        payload = {
            "stratumProtocol": "SV1",
            "stratumURL": pool.host,
            "stratumPort": pool.port,
            "stratumUser": pool.user,
            "stratumPassword": pool.password,
            "stratumSuggestedDifficulty": 0,
            "stratumExtranonceSubscribe": True,
            "stratumTLS": 1 if pool.tls else 0,
            "stratumDecodeCoinbase": True,
        }
        return await self._request("PUT", "/api/system/pools/0", json=payload, timeout=3.0)

    async def restart(self):
        return await self._request("POST", "/api/system/restart", timeout=3.0)

def _temperature(data):
    temps = data.get("temps")
    if isinstance(temps, dict):
        return temps.get("asic") or temps.get("board") or temps.get("vr")
    return data.get("temp") or data.get("temperature")

def _power(data):
    power = data.get("power")
    return power.get("power") if isinstance(power, dict) else power

def _pool(data):
    for key in ("pool", "stratumURL", "stratumUrl"):
        if data.get(key):
            return data[key]
    return ""
