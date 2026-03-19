"""
翻译和命名转换工具
- 日文 → 中文: 用于生成解析文档
- 日文 → 英文: 用于数据库表名、字段名、代码命名
"""

from typing import Dict, Optional

# 翻译对照表: 日文 → (中文, 英文)
TRANSLATION_TABLE: Dict[str, tuple[str, str]] = {
    "一覧": ("列表", "list"),
    "状況": ("状态", "status"),
    "小箱": ("小箱", "small_box"),
    "売上": ("销售", "sales"),
    "受付": ("受理", "receipt"),
    "入力": ("输入", "input"),
    "郵便": ("邮政", "postal"),
    "番号": ("编号", "number"),
    "名称": ("名称", "name"),
    "日付": ("日期", "date"),
    "金額": ("金额", "amount"),
    "住所": ("地址", "address"),
    "電話": ("电话", "phone"),
    "メール": ("邮箱", "email"),
    "コード": ("代码", "code"),
    "作成日": ("创建时间", "created_at"),
    "更新日": ("更新时间", "updated_at"),
    "削除": ("删除", "deleted"),
    "画面": ("页面", "screen"),
    "項目": ("字段", "item"),
    "処理": ("处理", "process"),
    "定義": ("定义", "definition"),
    "設計": ("设计", "design"),
    "機能": ("功能", "function"),
    "検索": ("搜索", "search"),
    "登録": ("注册", "register"),
    "更新": ("更新", "update"),
    "削除": ("删除", "delete"),
    "表示": ("显示", "display"),
    "非表示": ("隐藏", "hidden"),
    "必須": ("必填", "required"),
    "任意": ("可选", "optional"),
    "初期値": ("默认值", "default"),
    "最大桁数": ("最大长度", "max_length"),
    "説明": ("说明", "description"),
    "備考": ("备注", "notes"),
    "主キー": ("主键", "primary_key"),
    "外部キー": ("外键", "foreign_key"),
    "インデックス": ("索引", "index"),
    "ユニーク": ("唯一", "unique"),
    "NOT NULL": ("非空", "not_null"),
    "NULL": ("可空", "nullable"),
    "文字": ("字符串", "varchar"),
    "文字列": ("字符串", "varchar"),
    "数値": ("数值", "numeric"),
    "整数": ("整数", "integer"),
    "小数": ("小数", "decimal"),
    "日時": ("时间戳", "timestamp"),
    "真偽値": ("布尔", "boolean"),
    "テキスト": ("文本", "text"),
    "レイアウト": ("布局", "layout"),
    "概要": ("概要", "summary"),
    "プログラム概要": ("程序概要", "program_summary"),
    "処理説明": ("处理说明", "process_description"),
    "帳票": ("报表", "report"),
    "出力": ("输出", "output"),
    "印刷": ("打印", "print"),
    "CSV": ("CSV", "csv"),
    "Excel": ("Excel", "excel"),
    "PDF": ("PDF", "pdf"),
}


def japanese_to_chinese(text: str) -> str:
    """日文术语翻译为中文"""
    result = text
    for jp, (cn, _) in TRANSLATION_TABLE.items():
        result = result.replace(jp, cn)
    return result


def japanese_to_english(text: str) -> str:
    """日文术语翻译为英文"""
    result = text
    for jp, (_, en) in TRANSLATION_TABLE.items():
        result = result.replace(jp, en)
    return result


def to_snake_case(text: str) -> str:
    """转换为 snake_case 命名"""
    # 替换空格和特殊字符
    result = text.replace(" ", "_").replace("-", "_")
    # 如果已经是 snake_case，直接返回
    if "_" in result:
        return result.lower()
    # 驼峰转 snake_case
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', result)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def convert_table_name(japanese_name: str) -> str:
    """转换日文表名为英文 snake_case"""
    english = japanese_to_english(japanese_name)
    return to_snake_case(english)


def convert_column_name(japanese_name: str) -> str:
    """转换日文字段名为英文 snake_case"""
    english = japanese_to_english(japanese_name)
    return to_snake_case(english)


def to_pascal_case(text: str) -> str:
    """转换为 PascalCase（用于类名）"""
    snake = to_snake_case(text)
    return ''.join(word.capitalize() for word in snake.split('_'))


def to_kebab_case(text: str) -> str:
    """转换为 kebab-case（用于URL路径）"""
    snake = to_snake_case(text)
    return snake.replace('_', '-')


def map_db_type(japanese_type: str, length: Optional[int] = None) -> str:
    """映射设计书类型到 PostgreSQL 类型"""
    japanese_type = japanese_type.strip()

    mapping = {
        "文字列": f"VARCHAR({length})" if length else "VARCHAR(255)",
        "文字": f"VARCHAR({length})" if length else "VARCHAR(255)",
        "数値/整数": "INTEGER",
        "整数": "INTEGER",
        "数値/小数": "NUMERIC(18,2)",
        "小数": "NUMERIC(18,2)",
        "数値": "NUMERIC(18,2)",
        "日付": "DATE",
        "日時": "TIMESTAMP",
        "真偽値": "BOOLEAN",
        "テキスト": "TEXT",
    }

    for key, value in mapping.items():
        if key in japanese_type:
            if "VARCHAR" in value and length is None:
                return "VARCHAR(255)"
            return value

    # 默认返回 VARCHAR
    return f"VARCHAR({length})" if length else "VARCHAR(255)


def get_translation(japanese_term: str) -> Optional[tuple[str, str]]:
    """获取翻译，如果不存在返回 None"""
    return TRANSLATION_TABLE.get(japanese_term)
