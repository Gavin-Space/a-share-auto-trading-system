import asyncio
import pandas as pd

class MarketReplayer:
    """Reads a CSV of historical ticks or bars and publishes events to an asyncio queue.
    CSV expected columns: datetime, open, high, low, close, volume
    """
    def __init__(self, csv_path: str, out_queue: asyncio.Queue):
        self.csv_path = csv_path
        self.out_queue = out_queue
        self._running = False

    async def start(self, speed: float = 1.0):
        self._running = True
        df = pd.read_csv(self.csv_path)
        # ensure datetime
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
        else:
            # try date or index
            df['datetime'] = pd.to_datetime(df.iloc[:,0])
        for _, row in df.iterrows():
            if not self._running:
                break
            tick = {
                'type': 'tick',
                'datetime': str(row['datetime']),
                'open': float(row.get('open', row.get('Open', 0))),
                'high': float(row.get('high', row.get('High', 0))),
                'low': float(row.get('low', row.get('Low', 0))),
                'close': float(row.get('close', row.get('Close', 0))),
                'volume': float(row.get('volume', row.get('Volume', 0)))
            }
            await self.out_queue.put(tick)
            # simple timing: sleep a bit to simulate speed (speed>1 faster)
            await asyncio.sleep(0.01 / speed)

    def stop(self):
        self._running = False
