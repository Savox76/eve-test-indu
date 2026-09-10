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

    def as_api_payload(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "sortOrder": self.sort_order,
            "characterCount": self.character_count,
        }


@dataclass(frozen=True, slots=True)
class CharacterRecord:
    character_id: int
    name: str
    alias: str | None
    account_group_id: int | None
    account_group_label: str | None
    enabled: bool
    scopes: tuple[str, ...]

    def as_api_payload(self) -> dict[str, object]:
        return {
            "characterId": self.character_id,
            "name": self.name,
            "alias": self.alias,
            "accountGroupId": self.account_group_id,
            "accountGroupLabel": self.account_group_label,
            "enabled": self.enabled,
            "scopes": list(self.scopes),
        }


def _validated_text(value: str, *, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text.")
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise ValueError(f"{field} must contain between 1 and {maximum} characters.")
    return normalized


def _validated_identifier(value: int, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value == 0:
        raise ValueError(f"{field} must be a non-zero integer.")
    return value


def _optional_alias(value: str | None) -> str | None:
    if value is None:
        return None
    return _validated_text(value, field="Character alias", maximum=80)


def create_account_group(
    connection: sqlite3.Connection,
    label: str,
    *,
    sort_order: int = 0,
) -> int:
    """Create one local label used to group independently authorized characters."""

    normalized_label = _validated_text(label, field="Account group label", maximum=80)
    if isinstance(sort_order, bool) or not isinstance(sort_order, int) or sort_order < 0:
        raise ValueError("Account group sort order must be a non-negative integer.")

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

    character_id = _validated_identifier(character_id, field="Character identifier")
    normalized_name = _validated_text(name, field="Character name", maximum=100)
    if not isinstance(enabled, bool):
        raise ValueError("Character enabled state must be boolean.")
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



def update_account_group(
    connection: sqlite3.Connection,
    group_id: int,
    *,
    label: str,
) -> AccountGroup:
    """Rename one local group without changing character authorization."""

    group_id = _validated_identifier(group_id, field="Account group identifier")
    normalized_label = _validated_text(label, field="Account group label", maximum=80)
    cursor = connection.execute(
        """
        UPDATE account_groups
        SET label = ?,
            updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        WHERE id = ?
        """,
        (normalized_label, group_id),
    )
    if cursor.rowcount != 1:
        raise LookupError("account-group-not-found")
    return next(group for group in list_account_groups(connection) if group.id == group_id)


def delete_account_group(connection: sqlite3.Connection, group_id: int) -> bool:
    """Delete only the local group; SQLite unassigns its characters."""

    group_id = _validated_identifier(group_id, field="Account group identifier")
    cursor = connection.execute("DELETE FROM account_groups WHERE id = ?", (group_id,))
    return cursor.rowcount == 1


def update_character(
    connection: sqlite3.Connection,
    character_id: int,
    *,
    alias: str | None,
    account_group_id: int | None,
    enabled: bool,
) -> CharacterRecord:
    """Update only user-controlled character metadata in one transaction."""

    character_id = _validated_identifier(character_id, field="Character identifier")
    normalized_alias = _optional_alias(alias)
    if account_group_id is not None:
        account_group_id = _validated_identifier(
            account_group_id,
            field="Account group identifier",
        )
    if not isinstance(enabled, bool):
        raise ValueError("Character enabled state must be boolean.")

    connection.execute("BEGIN IMMEDIATE")
    try:
        cursor = connection.execute(
            """
            UPDATE characters
            SET alias = ?,
                account_group_id = ?,
                enabled = ?,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE character_id = ?
            """,
            (normalized_alias, account_group_id, int(enabled), character_id),
        )
        if cursor.rowcount != 1:
            raise LookupError("character-not-found")
        connection.execute("COMMIT")
    except BaseException:
        connection.execute("ROLLBACK")
        raise

    return next(
        character
        for character in list_characters(connection)
        if character.character_id == character_id
    )


def delete_character(connection: sqlite3.Connection, character_id: int) -> bool:
    """Delete a character and every SQLite row linked through cascade rules."""

    character_id = _validated_identifier(character_id, field="Character identifier")
    cursor = connection.execute(
        "DELETE FROM characters WHERE character_id = ?",
        (character_id,),
    )
    return cursor.rowcount == 1


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
            characters.alias,
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
            COALESCE(characters.alias, characters.name) COLLATE NOCASE
        """
    )
    return tuple(
        CharacterRecord(
            character_id=int(row["character_id"]),
            name=str(row["name"]),
            alias=(str(row["alias"]) if row["alias"] is not None else None),
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
