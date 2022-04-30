from enum import Enum

import strawberry
from sqlalchemy import asc, desc
from sqlalchemy.sql.selectable import Select


@strawberry.enum
class SortDirection(str, Enum):
    ASC = "ASC"
    DESC = "DESC"


@strawberry.input
class BaseSorter:
    direction: SortDirection = SortDirection.ASC

    def get_sqlalchemy_sorter(self):
        func_map = {SortDirection.ASC: asc, SortDirection.DESC: desc}
        return func_map[self.direction]

    def validate(self) -> bool:
        return True  # no validation by default

    def _add_sorters(self, query: Select) -> Select:
        raise NotImplementedError

    def add_sorters(self, query: Select) -> Select:
        if self.validate():
            return self._add_sorters(query)

    @staticmethod
    def default():
        return {}


@strawberry.input
class BaseFilter:
    def validate(self) -> bool:
        return True  # no validation by default

    def _add_filters(self, query: Select) -> Select:
        raise NotImplementedError

    def add_filters(self, query: Select) -> Select:
        if self.validate():
            return self._add_filters(query)

    @staticmethod
    def default():
        return {}
