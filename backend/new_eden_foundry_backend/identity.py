"""Local grouping and identity records for independently authorized characters."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class AccountGroup:
    id: int
    label: str
    sort_order: int
    character_count: int


@dataclass(frozen=True, slots=True)
class CharacterRecord:
    character_id: int
    name: str
    account_group_id: int | None
    account_group_label: str | None
    enabled: bool
    scopes: tuple[str, ...]


def _validated_text(value: str, *, field: str, maximum: int) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise ValueError(f"{field} must contain between 1 and {maximum} characters.")
    return normalized


def create_account_group(
    connection: sqlite3.Connection,
    label: str,
    *,
    sort_order: int = 0,
) -> int:
    """Create one local label used to group independently authorized characters."""

    normalized_label = _validated_text(label, field="Account group label", maximum=80)
    if sort_order < 0:
        raise ValueError("Account group sort order must not be negative.")

    cursor = connection.execute(
        "INSERT INTO account_groups (label, sort_order) VALUES (?, ?)",
        (normalized_label, sort_order),
    )
    if cursor.lastrowid is None:
        raise RuntimeError("SQLite did not return the new account group identifier.")
    return int(cursor.lastrowid)


def upsert_character(
    connection: sqlite3.Connection,
    *,
    character_id: int,
    name: str,
    account_group_id: int | None,
    scopes: Iterable[str] = (),
    enabled: bool = True,
) -> CharacterRecord:
    """Insert or refresh one character and atomically replace its granted scopes."""

    if character_id == 0:
        raise ValueError("Character identifier must not be zero.")
    normalized_name = _validated_text(name, field="Character name", maximum=100)
    normalized_scopes = tuple(
        sorted(
            {
                _validated_text(scope, field="Character scope", maximum=200)
                for scope in scopes
            }
        )
    )

    connection.execute("BEGIN IMMEDIATE")
    try:
        connection.execute(
            """
            INSERT INTO characters (
                character_id, account_group_id, name, enabled
            ) VALUES (?, ?, ?, ?)
            ON CONFLICT(character_id) DO UPDATE SET
                account_group_id = excluded.account_group_id,
                name = excluded.name,
                enabled = excluded.enabled,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            """,
            (character_id, account_group_id, normalized_name, int(enabled)),
        )
        connection.execute(
            "DELETE FROM character_scopes WHERE character_id = ?",
            (character_id,),
        )
        connection.executemany(
            "INSERT INTO character_scopes (character_id, scope) VALUES (?, ?)",
            ((character_id, scope) for scope in normalized_scopes),
        )
        connection.execute("COMMIT")
    except BaseException:
        connection.execute("ROLLBACK")
        raise

    return next(
        character
        for character in list_characters(connection)
        if character.character_id == character_id
    )


def list_account_groups(connection: sqlite3.Connection) -> tuple[AccountGroup, ...]:
    """Return local account groups with their current character counts."""

    rows = connection.execute(
        """
        SELECT
            account_groups.id,
            account_groups.label,
            account_groups.sort_order,
            COUNT(characters.character_id) AS character_count
        FROM account_groups
        LEFT JOIN characters
            ON characters.account_group_id = account_groups.id
        GROUP BY account_groups.id
        ORDER BY account_groups.sort_order, account_groups.label COLLATE NOCASE
        """
    )
    return tuple(
        AccountGroup(
            id=int(row["id"]),
            label=str(row["label"]),
            sort_order=int(row["sort_order"]),
            character_count=int(row["character_count"]),
        )
        for row in rows
    )


def list_characters(connection: sqlite3.Connection) -> tuple[CharacterRecord, ...]:
    """Return every character with its local group and granted SSO scopes."""

    scope_rows = connection.execute(
        """
        SELECT character_id, scope
        FROM character_scopes
        ORDER BY character_id, scope
        """
    )
    scopes_by_character: dict[int, list[str]] = {}
    for row in scope_rows:
        scopes_by_character.setdefault(int(row["character_id"]), []).append(
            str(row["scope"])
        )

    character_rows = connection.execute(
        """
        SELECT
            characters.character_id,
            characters.name,
            characters.account_group_id,
            account_groups.label AS account_group_label,
            characters.enabled
        FROM characters
        LEFT JOIN account_groups
            ON account_groups.id = characters.account_group_id
        ORDER BY
            account_groups.sort_order IS NULL,
            account_groups.sort_order,
            account_groups.label COLLATE NOCASE,
            characters.name COLLATE NOCASE
        """
    )
    return tuple(
        CharacterRecord(
            character_id=int(row["character_id"]),
            name=str(row["name"]),
            account_group_id=(
                int(row["account_group_id"])
                if row["account_group_id"] is not None
                else None
            ),
            account_group_label=(
                str(row["account_group_label"])
                if row["account_group_label"] is not None
                else None
            ),
            enabled=bool(row["enabled"]),
            scopes=tuple(scopes_by_character.get(int(row["character_id"]), ())),
        )
        for row in character_rows
    )
