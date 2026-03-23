-- ===========================================
-- CCS 数据库创建脚本
-- 基于设计书 DB 项目编辑仕様整理
-- ===========================================

-- 1. 小箱信息表 - 小箱情報テーブル
CREATE TABLE IF NOT EXISTS small_box_info (
    small_box_no      VARCHAR(20)  NOT NULL,  -- 小箱番号
    system_div        VARCHAR(10)          ,  -- システム区分
    small_box_type    VARCHAR(10)          ,  -- 小箱種別
    arrival_date     DATE                 ,  -- 到着日
    envelope_count    INTEGER              ,  -- 封筒数
    terminal_count    INTEGER              ,  -- 端末数
    remark           VARCHAR(500)         ,  -- 備考
    small_box_remark  VARCHAR(500)         ,  -- 小箱備考
    register_date    DATE          NOT NULL,  -- 登録年月日
    modify_date      DATE                 ,  -- 修正年月日
    -- 主键
    CONSTRAINT pk_small_box_info PRIMARY KEY (small_box_no)
);

-- 2. 受理数据表 - 受付データ
CREATE TABLE IF NOT EXISTS acceptance_data (
    acceptance_ym     VARCHAR(6)   NOT NULL,  -- 受付年月 (YYYYMM)
    small_box_no      VARCHAR(20)  NOT NULL,  -- 小箱番号
    envelope_seq      INTEGER      NOT NULL,  -- 封筒SEQ
    line_no          INTEGER      NOT NULL,  -- 行番号
    envelope_no      VARCHAR(20)          ,  -- 封筒番号
    registered_no    VARCHAR(20)          ,  -- 書留番号
    sales_start_date  DATE                 ,  -- 売上開始日
    sales_end_date    DATE                 ,  -- 売上終了日
    terminal_group_no VARCHAR(20)         ,  -- 端末グループ番号
    terminal_id_upper VARCHAR(10)         ,  -- 端末識別番号(上桁)
    terminal_id_lower VARCHAR(10)         ,  -- 端末識別番号(下桁)
    maker_no         VARCHAR(10)         ,  -- メーカー番号
    system_div        VARCHAR(10)         ,  -- システム区分
    new_system_div    VARCHAR(10)         ,  -- 新システム区分
    sales_count       INTEGER              ,  -- 売上枚数
    group_cd         VARCHAR(10)         ,  -- グループコード
    input_date       DATE                 ,  -- 入力年月日
    input_user_no     VARCHAR(10)         ,  -- 入力者番号
    envelope_type    INTEGER              ,  -- 封筒種別 (0=旧封筒, 1=新封筒)
    register_date    DATE          NOT NULL,  -- 登録年月日
    modify_date      DATE                 ,  -- 修正年月日
    modify_user_no   VARCHAR(10)         ,  -- 修正者番号
    -- 主键
    CONSTRAINT pk_acceptance_data PRIMARY KEY (acceptance_ym, small_box_no, envelope_seq, line_no),
    -- 外键 - 关联小箱信息
    CONSTRAINT fk_acceptance_data_small_box FOREIGN KEY (small_box_no)
        REFERENCES small_box_info(small_box_no)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

-- 索引 - 提升查询性能
CREATE INDEX IF NOT EXISTS idx_acceptance_data_small_box
    ON acceptance_data(small_box_no);
CREATE INDEX IF NOT EXISTS idx_acceptance_data_acceptance_ym
    ON acceptance_data(acceptance_ym);

-- 3. 工序管理数据表 - 工程管理データ
CREATE TABLE IF NOT EXISTS process_management (
    small_box_no      VARCHAR(20)  NOT NULL,  -- 小箱番号
    process_div       VARCHAR(10)  NOT NULL,  -- 作業工程区分
    personal_code     VARCHAR(10)  NOT NULL,  -- 個人コード
    start_datetime    TIMESTAMP    NOT NULL,  -- 開始日時
    end_datetime      TIMESTAMP            ,  -- 終了日時
    work_time        INTERVAL             ,  -- 作業時間
    modify_date      DATE                 ,  -- 修正年月日
    -- 主键
    CONSTRAINT pk_process_management PRIMARY KEY (small_box_no, process_div, personal_code, start_datetime),
    -- 外键
    CONSTRAINT fk_process_management_small_box FOREIGN KEY (small_box_no)
        REFERENCES small_box_info(small_box_no)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_process_management_small_box
    ON process_management(small_box_no);

-- 4. 小箱关联表 - 小箱関連テーブル
CREATE TABLE IF NOT EXISTS small_box_relation (
    small_box_no          VARCHAR(20)  NOT NULL,  -- 小箱番号
    parent_small_box_no   VARCHAR(20)  NOT NULL,  -- 親小箱番号
    envelope_seq          INTEGER      NOT NULL,  -- 封筒SEQ
    -- 主键
    CONSTRAINT pk_small_box_relation PRIMARY KEY (small_box_no, parent_small_box_no, envelope_seq),
    -- 外键
    CONSTRAINT fk_small_box_relation_small_box FOREIGN KEY (small_box_no)
        REFERENCES small_box_info(small_box_no)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_small_box_relation_parent FOREIGN KEY (parent_small_box_no)
        REFERENCES small_box_info(small_box_no)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_small_box_relation_parent
    ON small_box_relation(parent_small_box_no);

-- 5. 箱子状态表 - 箱状態
CREATE TABLE IF NOT EXISTS box_status (
    system_div                 VARCHAR(10)  NOT NULL,  -- システム区分
    small_box_no              VARCHAR(20)  NOT NULL,  -- 小箱番号
    infox_flag                INTEGER              ,  -- INFOXフラグ (1=INFOX, 0=他センター)
    header_sheet_printed_flag  INTEGER DEFAULT 0,  -- ヘッダーシート印刷済フラグ
    scan_system_linked_flag    INTEGER DEFAULT 0,  -- スキャンシステム連携済フラグ
    small_box_status_cd       VARCHAR(10)         ,  -- 小箱ステータスコード
    small_box_div             VARCHAR(10) DEFAULT '01', -- 小箱区分
    register_date            DATE          NOT NULL,  -- 登録年月日
    modify_date              DATE                 ,  -- 修正年月日
    -- 主键
    CONSTRAINT pk_box_status PRIMARY KEY (system_div, small_box_no),
    -- 外键
    CONSTRAINT fk_box_status_small_box FOREIGN KEY (small_box_no)
        REFERENCES small_box_info(small_box_no)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_box_status_small_box
    ON box_status(small_box_no);

-- ===========================================
-- 完成
-- ===========================================
COMMENT ON TABLE small_box_info IS '小箱情報テーブル';
COMMENT ON TABLE acceptance_data IS '受付データ';
COMMENT ON TABLE process_management IS '工程管理データ';
COMMENT ON TABLE small_box_relation IS '小箱関連テーブル';
COMMENT ON TABLE box_status IS '箱状態';
