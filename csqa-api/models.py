from typing import List
from pydantic import BaseModel


class Answer(BaseModel):
    answer: str
    score: float
    context: str
    title: str
    sector: str
    link: str
    given_date: str


class SearchResponseItem(BaseModel):
    title: str
    sector: str
    link: str
    given_date: str
    highlight: str


class SearchResponse(BaseModel):
    total: int
    results: List[SearchResponseItem]