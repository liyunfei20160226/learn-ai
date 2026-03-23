# CCS 数据库设计

## 汇总所有数据库表

从 5 份设计书的 DB 项目编辑仕様中，汇总得到以下表结构：

---

### 1. `small_box_info` - 小箱情報テーブル

| 字段名 | 日文名称 | 说明 | 类型 | 可空 |
|--------|----------|------|------|------|
| `small_box_no` | 小箱番号 | 小箱编号 | VARCHAR(20) | NO |
| `system_div` | システム区分 | 系统区分 | VARCHAR(10) | YES |
| `small_box_type` | 小箱種別 | 小箱类型 | VARCHAR(10) | YES |
| `arrival_date` | 到着日 | 到达日期 | DATE | YES |
| `envelope_count` | 封筒数 | 信封数量 | INTEGER | YES |
| `terminal_count` | 端末数 | 终端数量 | INTEGER | YES |
| `remark` | 備考 | 备注 | VARCHAR(500) | YES |
| `small_box_remark` | 小箱備考 | 小箱备注（更新用） | VARCHAR(500) | YES |
| `register_date` | 登録年月日 | 登记日期 | DATE | NO |
| `modify_date` | 修正年月日 | 修改日期 | DATE | YES |

**主键**: `small_box_no`

---

### 2. `acceptance_data` - 受付データ

| 字段名 | 日文名称 | 说明 | 类型 | 可空 |
|--------|----------|------|------|------|
| `acceptance_ym` | 受付年月 | 受理年月 (YYYYMM) | VARCHAR(6) | NO |
| `small_box_no` | 小箱番号 | 小箱编号 | VARCHAR(20) | NO |
| `envelope_seq` | 封筒SEQ | 信封序号 | INTEGER | NO |
| `line_no` | 行番号 | 行号 | INTEGER | NO |
| `envelope_no` | 封筒番号 | 信封编号 | VARCHAR(20) | YES |
| `registered_no` | 書留番号 | 挂号编号 | VARCHAR(20) | YES |
| `sales_start_date` | 売上開始日 | 销售开始日 | DATE | YES |
| `sales_end_date` | 売上終了日 | 销售结束日 | DATE | YES |
| `terminal_group_no` | 端末グループ番号 | 终端组编号 | VARCHAR(20) | YES |
| `terminal_id_upper` | 端末識別番号(上桁) | 终端识别号（上部分） | VARCHAR(10) | YES |
| `terminal_id_lower` | 端末識別番号(下桁) | 终端识别号（下部分） | VARCHAR(10) | YES |
| `maker_no` | メーカー番号 | 厂商编号 | VARCHAR(10) | YES |
| `system_div` | システム区分 | 系统区分 | VARCHAR(10) | YES |
| `new_system_div` | 新システム区分 | 新系统区分 | VARCHAR(10) | YES |
| `sales_count` | 売上枚数 | 销售票数 | INTEGER | YES |
| `group_cd` | グループ | 分组代码 | VARCHAR(10) | YES |
| `input_date` | 入力年月日 | 输入日期 | DATE | YES |
| `input_user_no` | 入力者番号 | 输入者编号 | VARCHAR(10) | YES |
| `envelope_type` | 封筒種別 | 信封类型 (0=旧信封, 1=新信封) | INTEGER | YES |
| `register_date` | 登録年月日 | 登记日期 | DATE | NO |
| `modify_date` | 修正年月日 | 修改日期 | DATE | YES |
| `modify_user_no` | 修正者番号 | 修改者编号 | VARCHAR(10) | YES |

**主键**: `acceptance_ym` + `small_box_no` + `envelope_seq` + `line_no`

---

### 3. `process_management` - 工程管理データ

| 字段名 | 日文名称 | 说明 | 类型 | 可空 |
|--------|----------|------|------|------|
| `small_box_no` | 小箱番号 | 小箱编号 | VARCHAR(20) | NO |
| `process_div` | 作業工程区分 | 作业工程区分 | VARCHAR(10) | NO |
| `personal_code` | 個人コード | 个人代码 | VARCHAR(10) | NO |
| `start_datetime` | 開始日時 | 开始时间 | TIMESTAMP | NO |
| `end_datetime` | 終了日時 | 结束时间 | TIMESTAMP | YES |
| `work_time` | 作業時間 | 作业时间 | INTERVAL | YES |
| `modify_date` | 修正年月日 | 修改日期 | DATE | YES |

**主键**: `small_box_no` + `process_div` + `personal_code` + `start_datetime`

---

### 4. `small_box_relation` - 小箱関連テーブル

| 字段名 | 日文名称 | 说明 | 类型 | 可空 |
|--------|----------|------|------|------|
| `small_box_no` | 小箱番号 | 小箱编号 | VARCHAR(20) | NO |
| `parent_small_box_no` | 親小箱番号 | 父小箱编号 | VARCHAR(20) | NO |
| `envelope_seq` | 封筒SEQ | 信封序号 | INTEGER | NO |

**主键**: `small_box_no` + `parent_small_box_no` + `envelope_seq`

---

### 5. `box_status` - 箱状態

| 字段名 | 日文名称 | 说明 | 类型 | 可空 |
|--------|----------|------|------|------|
| `system_div` | システム区分 | 系统区分 | VARCHAR(10) | NO |
| `small_box_no` | 小箱番号 | 小箱编号 | VARCHAR(20) | NO |
| `infox_flag` | INFOXフラグ | INFOX标志 (1=INFOX, 0=其他中心) | INTEGER | YES |
| `header_sheet_printed_flag` | ヘッダーシート印刷済フラグ | 头表已打印标志 | INTEGER | DEFAULT 0 |
| `scan_system_linked_flag` | スキャンシステム連携済フラグ | 扫描系统已关联标志 | INTEGER | DEFAULT 0 |
| `small_box_status_cd` | 小箱ステータスコード | 小箱状态代码 | VARCHAR(10) | YES |
| `small_box_div` | 小箱区分 | 小箱区分 | VARCHAR(10) | DEFAULT '01' |
| `register_date` | 登録年月日 | 登记日期 | DATE | NO |
| `modify_date` | 修正年月日 | 修改日期 | DATE | YES |

**主键**: `system_div` + `small_box_no`

---

## 表关系图

```
small_box_info (1) ──┐
                      ├─→ acceptance_data (N)
                      ├─→ process_management (N)
                      ├─→ small_box_relation (N)
                      └─→ box_status (1)
```

- `small_box_info.small_box_no` → `acceptance_data.small_box_no`
- `small_box_info.small_box_no` → `process_management.small_box_no`
- `small_box_info.small_box_no` → `small_box_relation.small_box_no`
- `small_box_info.small_box_no` → `box_status.small_box_no`
