import os 
import asyncio
from prometheus_client import start_http_server, Counter, Gauge
from redis.asyncio import Redis
from aiolimiter import AsyncLimiter
from datetime import timedelta
import aiobreaker
from adapters.database import SessionLocal, Account, Trade, init_db

trade_limiter = AsyncLimiter(1, 2)

db_breaker = aiobreaker.CircuitBreaker(
    fail_max=3, 
    timeout_duration=timedelta(seconds=30),
)

MESSAGES_PROCESSED = Counter('aegis_worker_messages_total', 'Total prices processed')
LATEST_BTC_PRICE = Gauge('aegis_btc_price', 'Current BTC price in worker')
NET_WORTH = Gauge('aegis_net_worth', 'Total value of USD + BTC')
BTC_HELD = Gauge('aegis_btc_held', 'BTC Held')
AVAIL_CASH = Gauge('aegis_cash', 'Cash Available')

@db_breaker
async def execute_trade_logic(cur_price):
    async with trade_limiter: 
        session = SessionLocal()
        try:
            account = session.query(Account).first()
            if account and account.balance_usd > 0:
                buy_amount_usd = account.balance_usd * 0.10
                btc_to_buy = buy_amount_usd / cur_price
                
                account.balance_usd -= buy_amount_usd
                account.btc_held += btc_to_buy

                new_trade = Trade(
                    symbol="BTCUSDT",
                    price=cur_price,
                    amount=btc_to_buy
                )
                session.add(new_trade)

                session.commit()
                
                print(f"PAPER TRADE: Bought {btc_to_buy:.6f} BTC. Remaining USD: ${account.balance_usd:.2f}")
        except Exception as e:
            session.rollback()
            print(f"DATABASE ERROR: Transaction rolled back. {e}")
            raise
        finally:
            session.close()

async def main():
    init_db()
    r = Redis(host=os.getenv("REDIS_HOST", "localhost"), port=6379, decode_responses=True)
    start_http_server(8000)

    last_id = '$'

    ref_price = None
    threshold = 0.0001

    print("Worker active. Watching for 0.01% price drops...")

    while True:
        try:
            events = await db_breaker.call_async(r.xread, {"market_stream": last_id}, block=1000)
            
            for _, messages in events:
                for msg_id, data in messages:
                    cur_price = float(data['p'])
                    MESSAGES_PROCESSED.inc()
                    LATEST_BTC_PRICE.set(cur_price)
                    with SessionLocal() as session:
                        acc = session.query(Account).first()
                        if acc:
                            current_net_worth = acc.balance_usd + (acc.btc_held * cur_price)
                            NET_WORTH.set(current_net_worth)
                            BTC_HELD.set(acc.btc_held)
                            AVAIL_CASH.set(acc.balance_usd)
                        else:
                            print("CRITICAL: No account found in DB. Check your seed logic.")
                    
                    if ref_price is None: 
                        ref_price = cur_price
                        print(f"Initial Reference Price set at: {ref_price}")

                    chg = (cur_price - ref_price) / ref_price

                    if chg <= -threshold:
                        print(f"ALERT: Price dropped {chg:.4%}. New Price: {cur_price}")
                        await execute_trade_logic(cur_price)
                    
                    ref_price = cur_price
                    last_id = msg_id
        except aiobreaker.CircuitBreakerError:
            print("GUARDRAIL: Circuit is OPEN. Redis is down, resting for 5s...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Other error: {e}")

if __name__=="__main__":
    asyncio.run(main())