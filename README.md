# PoolChanger

Local-network mining-pool manager for Bitaxe/AxeOS-compatible miners.

## MVP
- LAN discovery
- Miner status
- Pool slot 0 changes through AxeOS REST API
- Restart after change
- Docker / 5tratumOS ready
- Pool presets planned in the next UI iteration

## Run
docker compose up -d --build

Then open http://<5tratumOS-IP>:8090

The default scan network is 192.168.0.0/24.

PoolChanger is designed for trusted local networks; it does not expose miners to the Internet.
