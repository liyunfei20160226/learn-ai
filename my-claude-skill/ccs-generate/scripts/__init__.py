"""CCS Generate - 翻译和命名转换工具"""

from .translator import (
    japanese_to_chinese,
    japanese_to_english,
    to_snake_case,
    convert_table_name,
    convert_column_name,
    to_pascal_case,
    to_kebab_case,
    map_db_type,
    get_translation,
    TRANSLATION_TABLE,
)

__all__ = [
    "japanese_to_chinese",
    "japanese_to_english",
    "to_snake_case",
    "convert_table_name",
    "convert_column_name",
    "to_pascal_case",
    "to_kebab_case",
    "map_db_type",
    "get_translation",
    "TRANSLATION_TABLE",
]
