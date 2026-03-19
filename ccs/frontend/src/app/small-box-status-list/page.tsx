'use client';

/**
 * 小箱状况一览 页面
 * 自动生成由 ccs-generate
 */

import { useState, useEffect } from 'react';
import { SmallBoxStatusList } from '@/types/small_box_status_list';
import { getSmallBoxStatusListList, deleteSmallBoxStatusList } from '@/api/small_box_status_list';

export default function SmallBoxStatusListPage() {
  const [items, setItems] = useState<SmallBoxStatusList[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const data = await getSmallBoxStatusListList();
      setItems(data);
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
      await deleteSmallBoxStatusList(id);
      await loadData();
    } catch (err) {
      alert('删除失败');
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

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">小箱状况一览</h1>

      <div className="mb-4">
        <a
          href="/small-box-status-list/new"
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          新建
        </a>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full bg-white border border-gray-200">
          <thead>
            <tr className="bg-gray-50">
              <th className="px-4 py-2 border-b text-left">ID</th>
              <th className="px-4 py-2 border-b text-left">小箱编号</th>
              <th className="px-4 py-2 border-b text-left">父小箱编号</th>
              <th className="px-4 py-2 border-b text-left">新系统区分</th>
              <th className="px-4 py-2 border-b text-left">到达日期</th>
              <th className="px-4 py-2 border-b text-left">操作</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 border-b">{item.id}</td>
                <td className="px-4 py-2 border-b">{item.small_box_number}</td>
                <td className="px-4 py-2 border-b">{item.parent_small_box_number}</td>
                <td className="px-4 py-2 border-b">{item.new_system_flag ? '是' : '否'}</td>
                <td className="px-4 py-2 border-b">{item.arrival_date}</td>
                <td className="px-4 py-2 border-b">
                  <a
                    href={`/small-box-status-list/${item.id}/edit`}
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
