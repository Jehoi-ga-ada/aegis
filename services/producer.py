import os 
import asyncio
import logging
from binance_sdk_spot.spot import Spot, SPOT_WS_STREAMS_PROD_URL, ConfigurationWebSocketStreams
from redis.asyncio import Redis
from datetime import timedelta
import aiobreaker

# Initialize Redis Client
r = Redis(host=os.getenv("REDIS_HOST", "localhost"), port=6379, decode_responses=True)

# Initialize Spot client
configuration_ws_streams = ConfigurationWebSocketStreams(
    stream_url=os.getenv("STREAM_URL", SPOT_WS_STREAMS_PROD_URL)
)
client = Spot(config_ws_streams=configuration_ws_streams)

db_breaker = aiobreaker.CircuitBreaker(
    fail_max=3, 
    timeout_duration=timedelta(seconds=30),
)

async def handle_message(msg):
    try:
        if "p" in msg:
            await db_breaker.call_async(r.xadd, "market_stream", {"s": msg['s'], "p": msg['p']})
            print(f"Captured {msg['s']}: {msg['p']}")
    except aiobreaker.CircuitBreakerError:
        print("GUARDRAIL: Circuit is OPEN inside background task. Skipping message.")
    except Exception as e:
        print(f"TASK ERROR: {e}")

async def trade():
    stop_event = asyncio.Event()
    connection = None
    try:
        connection = await client.websocket_streams.create_connection()

        stream = await connection.trade(
            symbol="btcusdt",
        )
        
        stream.on("message", lambda data: asyncio.create_task(handle_message(data.to_dict())))

        await stop_event.wait()
        await stream.unsubscribe()
    except Exception as e:
        logging.error(f"trade() error: {e}")
    finally:
        if connection:
            await connection.close_connection(close_session=True)

if __name__ == "__main__":
    asyncio.run(trade())