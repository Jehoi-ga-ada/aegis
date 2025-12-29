from abc import ABC, abstractmethod

class TradeRepositoryPort(ABC):
    @abstractmethod
    def get_all_trades(self, limit: int): pass

    @abstractmethod
    def get_balance(self): pass
