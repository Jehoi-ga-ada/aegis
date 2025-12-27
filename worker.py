import os 
import asyncio
from redis.asyncio import Redis

async def main():
    r = Redis(host=os.getenv("REDIS_HOST", "localhost"), port=6379, decode_responses=True)
    last_id = '$'

    ref_price = None
    threshold = 0.0001

    print("Worker active. Watching for 0.01% price drops...")

    while True:
        events = await r.xread({"market_stream": last_id}, block=1000)
        for _, messages in events:
            for msg_id, data in messages:
                cur_price = float(data['p'])
                
                if ref_price is None: 
                    ref_price = cur_price
                    print(f"Initial Reference Price set at: {ref_price}")

                chg = (cur_price - ref_price) / ref_price

                if chg <= -threshold:
                    print(f"ALERT: Price dropped {chg:.4%}. New Price: {cur_price}")
                    ref_price = cur_price

                last_id = msg_id

if __name__=="__main__":
    asyncio.run(main())