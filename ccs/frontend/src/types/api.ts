// 小箱信息
export interface SmallBoxInfo {
  small_box_no: string;
  system_div?: string;
  small_box_type?: string;
  arrival_date?: string;
  envelope_count?: number;
  terminal_count?: number;
  remark?: string;
  small_box_remark?: string;
  register_date: string;
  modify_date?: string;
}

export interface SmallBoxInfoCreate {
  small_box_no: string;
  system_div?: string;
  small_box_type?: string;
  arrival_date?: string;
  envelope_count?: number;
  terminal_count?: number;
  remark?: string;
  small_box_remark?: string;
  register_date: string;
}

export interface SmallBoxInfoUpdate extends Partial<SmallBoxInfoCreate> {}

// 受理数据
export interface AcceptanceData {
  acceptance_ym: string;
  small_box_no: string;
  envelope_seq: number;
  line_no: number;
  envelope_no?: string;
  registered_no?: string;
  sales_start_date?: string;
  sales_end_date?: string;
  terminal_group_no?: string;
  terminal_id_upper?: string;
  terminal_id_lower?: string;
  maker_no?: string;
  system_div?: string;
  new_system_div?: string;
  sales_count?: number;
  group_cd?: string;
  input_date?: string;
  input_user_no?: string;
  envelope_type?: number;
  modify_user_no?: string;
  register_date: string;
  modify_date?: string;
}

export interface AcceptanceDataCreate {
  acceptance_ym: string;
  small_box_no: string;
  envelope_seq: number;
  line_no: int;
  envelope_no?: string;
  registered_no?: string;
  sales_start_date?: string;
  sales_end_date?: string;
  terminal_group_no?: string;
  terminal_id_upper?: string;
  terminal_id_lower?: string;
  maker_no?: string;
  system_div?: string;
  new_system_div?: string;
  sales_count?: number;
  group_cd?: string;
  input_date?: string;
  input_user_no?: string;
  envelope_type?: number;
  modify_user_no?: string;
  register_date: string;
}

// 工序管理
export interface ProcessManagement {
  small_box_no: string;
  process_div: string;
  personal_code: string;
  start_datetime: string;
  end_datetime?: string;
  work_time?: string;
  modify_date?: string;
}

export interface ProcessManagementCreate {
  small_box_no: string;
  process_div: string;
  personal_code: string;
  start_datetime: string;
  end_datetime?: string;
  work_time?: string;
  modify_date?: string;
}

// 箱子状态
export interface BoxStatus {
  system_div: string;
  small_box_no: string;
  infox_flag?: number;
  header_sheet_printed_flag?: number;
  scan_system_linked_flag?: number;
  small_box_status_cd?: string;
  small_box_div?: string;
  register_date: string;
  modify_date?: string;
}

export interface BoxStatusCreate {
  system_div: string;
  small_box_no: string;
  infox_flag?: number;
  header_sheet_printed_flag?: number;
  scan_system_linked_flag?: number;
  small_box_status_cd?: string;
  small_box_div?: string;
  register_date: string;
}

export interface MessageResponse {
  message: string;
}
