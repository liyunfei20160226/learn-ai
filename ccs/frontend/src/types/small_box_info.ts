/**
 * TypeScript 类型定义
 * 自动生成由 ccs-generate
 */

export interface SmallBoxInfo {
  id: number;
  small_box_number: number;
  parent_small_box_number: number | null;
  new_system_flag: boolean;
  arrival_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface SmallBoxInfoCreate {
  small_box_number: number;
  parent_small_box_number: number | null;
  new_system_flag: boolean;
  arrival_date: string | null;
}

export interface SmallBoxInfoUpdate {
  small_box_number?: number;
  parent_small_box_number?: number | null;
  new_system_flag?: boolean;
  arrival_date?: string | null;
}

export interface ListResponse<T> {
  items: T[];
  total: number;
}
