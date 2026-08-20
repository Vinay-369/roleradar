"""
Auth-related DB document shapes (informal — MongoDB is schemaless, but
these document the expected structure for the `users` collection).
"""
from datetime import datetime
from typing import TypedDict


class UserDocument(TypedDict, total=False):
    _id: str
    email: str
    password_hash: str
    full_name: str
    phone: str | None
    created_at: datetime
    updated_at: datetime
