from __future__ import annotations

import aiosqlite


def parse_db_path(db_url: str) -> str:
    if db_url.startswith("sqlite+aiosqlite:///"):
        return db_url.replace("sqlite+aiosqlite:///", "", 1)
    if db_url.startswith("sqlite:///"):
        return db_url.replace("sqlite:///", "", 1)
    if db_url.startswith("sqlite:"):
        return db_url.replace("sqlite:", "", 1)
    return db_url


class Database:
    def __init__(self, db_url: str) -> None:
        self.db_path = parse_db_path(db_url)

    async def execute(self, query: str, params: tuple = (), return_rowcount: bool = False) -> int | None:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, params)
            await db.commit()
            if return_rowcount:
                return cursor.rowcount
        return None

    async def executemany(self, query: str, params_list: list[tuple]) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.executemany(query, params_list)
            await db.commit()

    async def fetchone(self, query: str, params: tuple = ()) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            row = await cursor.fetchone()
            if row is None:
                return None
            return dict(row)

    async def fetchall(self, query: str, params: tuple = ()) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
