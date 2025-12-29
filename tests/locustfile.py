from locust import HttpUser, task

class AegisStressTest(HttpUser):
    @task(3) # This task happens 3x more often (checking status)
    def check_system_health(self):
        self.client.get("/health")