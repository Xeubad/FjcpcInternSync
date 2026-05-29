from enum import Enum


class ReportType(str, Enum):
    day = "day"
    week = "week"
    month = "month"
