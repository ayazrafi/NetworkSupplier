from src.repositories.base import BaseRepository

class OptimizationRequestsRepository(BaseRepository):
    def __init__(self):
        super().__init__("OptimizationRequests")

class RequestPlantsRepository(BaseRepository):
    def __init__(self):
        super().__init__("RequestPlants")

class RequestMMCsRepository(BaseRepository):
    def __init__(self):
        super().__init__("RequestMMCs")

class RequestVehiclesRepository(BaseRepository):
    def __init__(self):
        super().__init__("RequestVehicles")

class RequestSettingsRepository(BaseRepository):
    def __init__(self):
        super().__init__("RequestSettings")
