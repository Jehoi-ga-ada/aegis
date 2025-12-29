from fastapi import FastAPI, Depends
from adapters.database import PostgresTradeAdapter
from prometheus_client import make_asgi_app

app = FastAPI(title="Aegis Vault API")

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

def get_repo():
    return PostgresTradeAdapter()

@app.get("/trades")
async def read_trades(limit: int = 50, repo: PostgresTradeAdapter = Depends(get_repo)):
    trades = repo.get_all_trades(limit)
    return {"count": len(trades), "history": trades}

@app.get("/balance")
async def read_balance(repo: PostgresTradeAdapter = Depends(get_repo)):
    account = repo.get_balance()
    return {
        "usd": account.balance_usd,
        "btc": account.btc_held,
    }

@app.get("/health")
async def health():
    return {"status": "Vault is online"}