'use client';

/**
 * 小箱状况列表页面
 * 自动生成由 ccs-generate
 */

import { useState, useEffect } from 'react';
import { SmallBoxInfo } from '@/types/small_box_info';
import { getSmallBoxInfoList, deleteSmallBoxInfo } from '@/api/small_box_info';

export default function SmallBoxInfoListPage() {
  const [items, setItems] = useState<SmallBoxInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const data = await getSmallBoxInfoList();
      setItems(data);
      setSelectedIds(new Set());
      setError(null);
    } catch (err) {
      setError('加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确定要删除吗？')) return;
    try {
      await deleteSmallBoxInfo(id);
      await loadData();
    } catch (err) {
      alert('删除失败');
    }
  };

  const toggleSelect = (id: number) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedIds(newSelected);
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === items.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(items.map(item => item.id)));
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto p-4">
        <div>加载中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto p-4">
        <div className="text-red-500">{error}</div>
        <button
          className="mt-4 px-4 py-2 bg-blue-500 text-white rounded"
          onClick={loadData}
        >
          重试
        </button>
      </div>
    );
  }

  // 中文标题映射
  const columnTitles = {
    id: 'ID',
    small_box_number: '小箱番号',
    new_system_flag: '操作区分',
    parent_small_box_number: '亲小箱编号',
    arrival_date: '到着日',
    created_at: '创建时间',
    updated_at: '更新时间',
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">小箱状况列表</h1>

      <div className="mb-4">
        <a
          href="/small-box-info/new"
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          新建
        </a>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full bg-white border border-gray-200">
          <thead>
            <tr className="bg-gray-50">
              <th className="px-4 py-2 border-b text-left">
                <input
                  type="checkbox"
                  checked={items.length > 0 && selectedIds.size === items.length}
                  onChange={toggleSelectAll}
                />
              </th>
              <th className="px-4 py-2 border-b text-left">No</th>
              <th className="px-4 py-2 border-b text-left">{columnTitles.small_box_number}</th>
              <th className="px-4 py-2 border-b text-left">{columnTitles.new_system_flag}</th>
              <th className="px-4 py-2 border-b text-left">{columnTitles.parent_small_box_number}</th>
              <th className="px-4 py-2 border-b text-left">{columnTitles.arrival_date}</th>
              <th className="px-4 py-2 border-b text-left">操作</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, index) => (
              <tr key={item.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 border-b">
                  <input
                    type="checkbox"
                    checked={selectedIds.has(item.id)}
                    onChange={() => toggleSelect(item.id)}
                  />
                </td>
                <td className="px-4 py-2 border-b">{index + 1}</td>
                <td className="px-4 py-2 border-b">{item.small_box_number}</td>
                <td className="px-4 py-2 border-b">{item.new_system_flag ? '新制' : '旧制'}</td>
                <td className="px-4 py-2 border-b">{item.parent_small_box_number ?? '-'}</td>
                <td className="px-4 py-2 border-b">{item.arrival_date ?? '-'}</td>
                <td className="px-4 py-2 border-b">
                  <a
                    href={`/small-box-info/${item.id}/edit`}
                    className="text-blue-500 hover:underline mr-3"
                  >
                    编辑
                  </a>
                  <button
                    onClick={() => handleDelete(item.id)}
                    className="text-red-500 hover:underline"
                  >
                    删除
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {items.length === 0 && !loading && (
        <div className="text-center py-8 text-gray-500">暂无数据</div>
      )}
    </div>
  );
}
