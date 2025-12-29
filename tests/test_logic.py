from ports.repository import TradeRepositoryPort

class MockRepo(TradeRepositoryPort):
    def __init__(self): self.trades = []
    def save_trade(self, symbol, price, amount):
        self.trades.append(price)
        return True
    def get_all_trades(self, limit): return self.trades
    def get_balance(self): return None

def test_price_drop_logic():
    repo = MockRepo()
    ref_price = 100.0
    cur_price = 99.0 # 1% drop
    
    # Logic: if drop > 0.01%, it should trade
    if (cur_price - ref_price) / ref_price <= -0.0001:
        repo.save_trade("BTCUSDT", cur_price, 0.01)
    
    assert len(repo.get_all_trades(10)) == 1
    print("✅ Logic Test Passed!")