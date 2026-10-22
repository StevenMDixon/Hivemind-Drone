from abc import ABC, abstractmethod

class BaseDisplayProvider(ABC):
    @abstractmethod
    def discover_displays(self):
        pass