"""Shared response envelopes."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int = Field(description="Total rows matching the filter, ignoring pagination")
    limit: int
    offset: int


class Message(BaseModel):
    detail: str


class ErrorResponse(BaseModel):
    code: str
    detail: str
