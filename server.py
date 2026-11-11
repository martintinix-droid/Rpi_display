import asyncio
import hmac
import mimetypes
import os

from aiohttp import web, WSMsgType

mimetypes.add_type("application/wasm", ".wasm")

PI_TOKEN = os.environ.get("PI_TOKEN", "")
WEB_DIR = "web"

viewers = set()
last_message = None   # último dato, para mostrarlo enseguida a quien se conecte


async def pi_ws(request):
    token = request.query.get("token", "")
    if not PI_TOKEN or not hmac.compare_digest(token, PI_TOKEN):
        return web.Response(status=401, text="Token invalido")

    ws = web.WebSocketResponse(heartbeat=20)
    await ws.prepare(request)
    print("Pi conectado")

    global last_message
    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            last_message = msg.data
            await asyncio.gather(
                *(v.send_str(msg.data) for v in list(viewers)),
                return_exceptions=True,
            )
    print("Pi desconectado")
    return ws


async def view_ws(request):
    ws = web.WebSocketResponse(heartbeat=20)
    await ws.prepare(request)
    viewers.add(ws)
    print("Viewer conectado. Total:", len(viewers))
    try:
        if last_message:
            await ws.send_str(last_message)
        async for _ in ws:   # ignoramos lo que envíen
            pass
    finally:
        viewers.discard(ws)
        print("Viewer desconectado. Total:", len(viewers))
    return ws


async def index(request):
    path = os.path.join(WEB_DIR, "index.html")
    if not os.path.exists(path):
        return web.Response(text="Relay activo, pero aun no hay web exportada.")
    return web.FileResponse(path)


os.makedirs(WEB_DIR, exist_ok=True)   # evita que falle si aún no exportaste

app = web.Application()
app.router.add_get("/ws/pi", pi_ws)
app.router.add_get("/ws/view", view_ws)
app.router.add_get("/", index)
app.router.add_static("/", WEB_DIR)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)
