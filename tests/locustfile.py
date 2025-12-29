from locust import HttpUser, task

class AegisStressTest(HttpUser):
    # This simulates a producer sending trade data to your system
    @task
    def simulate_trade_signal(self):
        self.client.post("/ingest", json={
            "symbol": "BTC/USD",
            "price": 95000.00,
            "volume": 0.1,
            "signal": "BUY"
        })

    @task(3) # This task happens 3x more often (checking status)
    def check_system_health(self):
        self.client.get("/health")