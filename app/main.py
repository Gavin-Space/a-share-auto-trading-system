from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import os
from trading.replayer import MarketReplayer
from trading.strategy import Strategy
from trading.execution import PaperExecutor

app = FastAPI(title="A-Share Auto Trading System")

# Simple in-process event bus
EVENT_QUEUE: asyncio.Queue = asyncio.Queue()

replayer: MarketReplayer | None = None
strategy: Strategy | None = None
executor: PaperExecutor | None = None

# Serve static dashboard
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse('<a href="/dashboard">Open Dashboard</a>')

@app.get("/dashboard")
async def dashboard():
    return FileResponse("frontend/index.html")

@app.post("/start_replay")
async def start_replay(csv_path: str, speed: float = 1.0, background_tasks: BackgroundTasks = None):
    global replayer
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=400, detail="csv_path not found")
    replayer = MarketReplayer(csv_path, EVENT_QUEUE)
    # run in background
    loop = asyncio.get_event_loop()
    loop.create_task(replayer.start(speed))
    return {"status": "replay_started", "csv": csv_path}

@app.post("/start_strategy")
async def start_strategy():
    global strategy, executor
    if EXECUTOR := globals().get('executor'):
        executor = EXECUTOR
    else:
        executor = PaperExecutor(EVENT_QUEUE)
        globals()['executor'] = executor
    strategy = Strategy(EVENT_QUEUE, executor)
    loop = asyncio.get_event_loop()
    loop.create_task(strategy.run())
    return {"status": "strategy_started"}

@app.post("/start_executor")
async def start_executor():
    global executor
    executor = PaperExecutor(EVENT_QUEUE)
    globals()['executor'] = executor
    return {"status": "executor_started"}

@app.websocket('/ws/market')
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        # send existing events to client as they come
        while True:
            event = await EVENT_QUEUE.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        return
