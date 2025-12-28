import os 
import asyncio
from prometheus_client import start_http_server, Counter, Gauge
from redis.asyncio import Redis
from aiolimiter import AsyncLimiter
from datetime import timedelta
import aiobreaker

trade_limiter = AsyncLimiter(1, 2)

db_breaker = aiobreaker.CircuitBreaker(
    fail_max=3, 
    timeout_duration=timedelta(seconds=30),
)

MESSAGES_PROCESSED = Counter('aegis_worker_messages_total', 'Total prices processed')
LATEST_BTC_PRICE = Gauge('aegis_btc_price', 'Current BTC price in worker')
NET_WORTH = Gauge('aegis_net_worth', 'Total value of USD + BTC')

@db_breaker
async def execute_trade_logic(cur_price, balance_usd, btc_held):
    async with trade_limiter: 
        if balance_usd > 0:
            buy_amount_usd = balance_usd * 0.10
            btc_to_buy = buy_amount_usd / cur_price
            
            balance_usd -= buy_amount_usd
            btc_held += btc_to_buy
            
            print(f"PAPER TRADE: Bought {btc_to_buy:.6f} BTC. Remaining USD: ${balance_usd:.2f}")
            return balance_usd, btc_held

async def main():
    r = Redis(host=os.getenv("REDIS_HOST", "localhost"), port=6379, decode_responses=True)

    start_http_server(8000)

    last_id = '$'

    ref_price = None
    threshold = 0.0001

    balance_usd = 1000.0
    btc_held = 0.0

    print("Worker active. Watching for 0.01% price drops...")

    while True:
        try:
            events = await db_breaker.call_async(r.xread, {"market_stream": last_id}, block=1000)
            
            for _, messages in events:
                for msg_id, data in messages:
                    cur_price = float(data['p'])
                    MESSAGES_PROCESSED.inc()
                    LATEST_BTC_PRICE.set(float(data['p']))
                    NET_WORTH.set(balance_usd + (btc_held * cur_price))
                    
                    if ref_price is None: 
                        ref_price = cur_price
                        print(f"Initial Reference Price set at: {ref_price}")

                    chg = (cur_price - ref_price) / ref_price

                    if chg <= -threshold:
                        print(f"ALERT: Price dropped {chg:.4%}. New Price: {cur_price}")

                        balance_usd, btc_held = await execute_trade_logic(cur_price, balance_usd, btc_held)
                    
                    ref_price = cur_price
                    last_id = msg_id
        except aiobreaker.CircuitBreakerError:
            print("GUARDRAIL: Circuit is OPEN. Redis is down, resting for 5s...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Other error: {e}")

if __name__=="__main__":
    asyncio.run(main())