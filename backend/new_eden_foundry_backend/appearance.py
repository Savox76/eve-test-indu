"""Persistent, bounded appearance preferences for the desktop UI."""

from __future__ import annotations

import sqlite3
from enum import StrEnum


FONT_SCALE_SETTING = "font_scale"


class FontScale(StrEnum):
    VERY_SMALL = "very-small"
    SMALL = "small"
    NORMAL = "normal"
    LARGE = "large"
    VERY_LARGE = "very-large"


def _parse_font_scale(value: object) -> FontScale:
    if not isinstance(value, str):
        raise TypeError("Font scale must be text.")
    try:
        return FontScale(value)
    except ValueError as error:
        raise ValueError("The selected font scale is unsupported.") from error


def read_font_scale(connection: sqlite3.Connection) -> FontScale:
    """Return the saved font scale or the safe default for existing databases."""

    row = connection.execute(
        "SELECT value FROM app_settings WHERE key = ?",
        (FONT_SCALE_SETTING,),
    ).fetchone()
    if row is None:
        return FontScale.NORMAL
    try:
        return _parse_font_scale(row["value"])
    except (TypeError, ValueError):
        return FontScale.NORMAL


def set_font_scale(connection: sqlite3.Connection, value: object) -> FontScale:
    """Validate and persist one of the five global font-size stages."""

    font_scale = _parse_font_scale(value)
    connection.execute(
        """
        INSERT INTO app_settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        """,
        (FONT_SCALE_SETTING, font_scale.value),
    )
    return font_scale


def appearance_payload(font_scale: FontScale) -> dict[str, str]:
    return {"fontScale": font_scale.value}
