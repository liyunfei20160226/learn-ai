/**
 * API 客户端
 * 自动生成由 ccs-generate
 */

import { SmallBoxInfo, SmallBoxInfoCreate, SmallBoxInfoUpdate } from '../types/small_box_info';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

/**
 * 获取列表
 */
export async function getSmallBoxInfoList(skip: number = 0, limit: number = 100): Promise<SmallBoxInfo[]> {
  const response = await fetch(`${API_BASE}/small_box_info/?skip=${skip}&limit=${limit}`);
  if (!response.ok) {
    throw new Error('Failed to fetch small_box_info list');
  }
  return response.json();
}

/**
 * 根据ID获取
 */
export async function getSmallBoxInfoById(id: number): Promise<SmallBoxInfo> {
  const response = await fetch(`${API_BASE}/small_box_info/${id}`);
  if (!response.ok) {
    throw new Error('Failed to fetch small_box_info');
  }
  return response.json();
}

/**
 * 创建
 */
export async function createSmallBoxInfo(data: SmallBoxInfoCreate): Promise<SmallBoxInfo> {
  const response = await fetch(`${API_BASE}/small_box_info/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw new Error('Failed to create small_box_info');
  }
  return response.json();
}

/**
 * 更新
 */
export async function updateSmallBoxInfo(id: number, data: SmallBoxInfoUpdate): Promise<SmallBoxInfo> {
  const response = await fetch(`${API_BASE}/small_box_info/${id}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw new Error('Failed to update small_box_info');
  }
  return response.json();
}

/**
 * 删除
 */
export async function deleteSmallBoxInfo(id: number): Promise<void> {
  const response = await fetch(`${API_BASE}/small_box_info/${id}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to delete small_box_info');
  }
}
