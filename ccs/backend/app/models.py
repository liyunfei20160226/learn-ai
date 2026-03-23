"""
SQLAlchemy 数据模型
对应 设计书 中的数据库表结构
"""

from sqlalchemy import Column, String, Integer, Date, TIMESTAMP, Interval, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

# 1. 小箱信息表 - 小箱情報テーブル
class SmallBoxInfo(Base):
    __tablename__ = "small_box_info"

    small_box_no = Column(String(20), primary_key=True, index=True, comment="小箱番号")
    system_div = Column(String(10), nullable=True, comment="システム区分")
    small_box_type = Column(String(10), nullable=True, comment="小箱種別")
    arrival_date = Column(Date, nullable=True, comment="到着日")
    envelope_count = Column(Integer, nullable=True, comment="封筒数")
    terminal_count = Column(Integer, nullable=True, comment="端末数")
    remark = Column(String(500), nullable=True, comment="備考")
    small_box_remark = Column(String(500), nullable=True, comment="小箱備考")
    register_date = Column(Date, nullable=False, comment="登録年月日")
    modify_date = Column(Date, nullable=True, comment="修正年月日")

# 2. 受理数据表 - 受付データ
class AcceptanceData(Base):
    __tablename__ = "acceptance_data"

    acceptance_ym = Column(String(6), primary_key=True, index=True, comment="受付年月 (YYYYMM)")
    small_box_no = Column(String(20), primary_key=True, index=True, comment="小箱番号")
    envelope_seq = Column(Integer, primary_key=True, comment="封筒SEQ")
    line_no = Column(Integer, primary_key=True, comment="行番号")
    envelope_no = Column(String(20), nullable=True, comment="封筒番号")
    registered_no = Column(String(20), nullable=True, comment="書留番号")
    sales_start_date = Column(Date, nullable=True, comment="売上開始日")
    sales_end_date = Column(Date, nullable=True, comment="売上終了日")
    terminal_group_no = Column(String(20), nullable=True, comment="端末グループ番号")
    terminal_id_upper = Column(String(10), nullable=True, comment="端末識別番号(上桁)")
    terminal_id_lower = Column(String(10), nullable=True, comment="端末識別番号(下桁)")
    maker_no = Column(String(10), nullable=True, comment="メーカー番号")
    system_div = Column(String(10), nullable=True, comment="システム区分")
    new_system_div = Column(String(10), nullable=True, comment="新システム区分")
    sales_count = Column(Integer, nullable=True, comment="売上枚数")
    group_cd = Column(String(10), nullable=True, comment="グループコード")
    input_date = Column(Date, nullable=True, comment="入力年月日")
    input_user_no = Column(String(10), nullable=True, comment="入力者番号")
    envelope_type = Column(Integer, nullable=True, comment="封筒種別 (0=旧封筒, 1=新封筒)")
    register_date = Column(Date, nullable=False, comment="登録年月日")
    modify_date = Column(Date, nullable=True, comment="修正年月日")
    modify_user_no = Column(String(10), nullable=True, comment="修正者番号")

# 3. 工序管理数据表 - 工程管理データ
class ProcessManagement(Base):
    __tablename__ = "process_management"

    small_box_no = Column(String(20), primary_key=True, index=True, comment="小箱番号")
    process_div = Column(String(10), primary_key=True, comment="作業工程区分")
    personal_code = Column(String(10), primary_key=True, comment="個人コード")
    start_datetime = Column(TIMESTAMP, primary_key=True, comment="開始日時")
    end_datetime = Column(TIMESTAMP, nullable=True, comment="終了日時")
    work_time = Column(Interval, nullable=True, comment="作業時間")
    modify_date = Column(Date, nullable=True, comment="修正年月日")

# 4. 小箱关联表 - 小箱関連テーブル
class SmallBoxRelation(Base):
    __tablename__ = "small_box_relation"

    small_box_no = Column(String(20), primary_key=True, index=True, comment="小箱番号")
    parent_small_box_no = Column(String(20), primary_key=True, comment="親小箱番号")
    envelope_seq = Column(Integer, primary_key=True, comment="封筒SEQ")

# 5. 箱子状态表 - 箱状態
class BoxStatus(Base):
    __tablename__ = "box_status"

    system_div = Column(String(10), primary_key=True, comment="システム区分")
    small_box_no = Column(String(20), primary_key=True, index=True, comment="小箱番号")
    infox_flag = Column(Integer, nullable=True, comment="INFOXフラグ (1=INFOX, 0=他センター)")
    header_sheet_printed_flag = Column(Integer, nullable=True, default=0, comment="ヘッダーシート印刷済フラグ")
    scan_system_linked_flag = Column(Integer, nullable=True, default=0, comment="スキャンシステム連携済フラグ")
    small_box_status_cd = Column(String(10), nullable=True, comment="小箱ステータスコード")
    small_box_div = Column(String(10), nullable=True, default="01", comment="小箱区分")
    register_date = Column(Date, nullable=False, comment="登録年月日")
    modify_date = Column(Date, nullable=True, comment="修正年月日")
