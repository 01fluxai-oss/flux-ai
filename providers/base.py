from abc import ABC, abstractmethod


class BaseProvider:
    @abstractmethod
    def get_match_data(self, team1: str, team2: str):
        """
        Возвращает все данные о матче
        """
        pass
