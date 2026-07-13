from src.repositories.base import BaseRepository

class OptimizationResultsRepository(BaseRepository):
    def __init__(self):
        super().__init__("OptimizationResults")

class OptimizerRequestResultRepository(BaseRepository):
    def __init__(self):
        super().__init__("OptimizerRequestResult")
