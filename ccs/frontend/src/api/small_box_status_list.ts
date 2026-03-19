/**
 * API 客户端
 * 自动生成由 ccs-generate
 */

import { SmallBoxStatusList, SmallBoxStatusListCreate, SmallBoxStatusListUpdate } from '../types/small_box_status_list';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

/**
 * 获取列表
 */
export async function getSmallBoxStatusListList(skip: number = 0, limit: number = 100): Promise<SmallBoxStatusList[]> {
  const response = await fetch(`${API_BASE}/small_box_info/?skip=${skip}&limit=${limit}`);
  if (!response.ok) {
    throw new Error('Failed to fetch 小箱状况一览 list');
  }
  return response.json();
}

/**
 * 根据ID获取
 */
export async function getSmallBoxStatusListById(id: number): Promise<SmallBoxStatusList> {
  const response = await fetch(`${API_BASE}/small_box_info/${id}`);
  if (!response.ok) {
    throw new Error('Failed to fetch 小箱状况一览');
  }
  return response.json();
}

/**
 * 创建
 */
export async function createSmallBoxStatusList(data: SmallBoxStatusListCreate): Promise<SmallBoxStatusList> {
  const response = await fetch(`${API_BASE}/small_box_info/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw new Error('Failed to create 小箱状况一览');
  }
  return response.json();
}

/**
 * 更新
 */
export async function updateSmallBoxStatusList(id: number, data: SmallBoxStatusListUpdate): Promise<SmallBoxStatusList> {
  const response = await fetch(`${API_BASE}/small_box_info/${id}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw new Error('Failed to update 小箱状况一览');
  }
  return response.json();
}

/**
 * 删除
 */
export async function deleteSmallBoxStatusList(id: number): Promise<void> {
  const response = await fetch(`${API_BASE}/small_box_info/${id}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to delete 小箱状况一览');
  }
}
