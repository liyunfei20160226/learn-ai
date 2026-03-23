"use client";

import React from "react";
import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { smallBoxApi } from "@/utils/api";
import { SmallBoxInfo } from "@/types/api";

export default function SmallBoxPage() {
  const [smallBoxes, setSmallBoxes] = useState<SmallBoxInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);

  const { register, handleSubmit, reset } = useForm<{
    small_box_no: string;
    system_div: string;
    small_box_type: string;
    arrival_date: string;
    envelope_count: number;
    terminal_count: number;
    remark: string;
    small_box_remark: string;
    register_date: string;
  }>({
    defaultValues: {
      register_date: new Date().toISOString().split("T")[0],
    },
  });

  const loadList = async () => {
    setLoading(true);
    try {
      const res = await smallBoxApi.list();
      setSmallBoxes(res.data);
    } catch (err) {
      setMessage({ text: `加载失败: ${(err as Error).message}`, type: "error" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadList();
  }, []);

  const onSubmit = async (data: any) => {
    try {
      await smallBoxApi.create(data);
      setMessage({ text: "创建成功", type: "success" });
      reset({});
      loadList();
    } catch (err: any) {
      setMessage({
        text: `创建失败: ${err.response?.data?.detail || (err as Error).message}`,
        type: "error",
      });
    }
  };

  const handleDelete = async (smallBoxNo: string) => {
    if (!confirm(`确认删除小箱 ${smallBoxNo}?`)) return;
    try {
      await smallBoxApi.delete(smallBoxNo);
      setMessage({ text: "删除成功", type: "success" });
      loadList();
    } catch (err: any) {
      setMessage({
        text: `删除失败: ${err.response?.data?.detail || (err as Error).message}`,
        type: "error",
      });
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">小箱管理</h2>

      {message && (
        <div
          className={`p-4 rounded-md ${
            message.type === "success"
              ? "bg-green-50 text-green-700"
              : "bg-red-50 text-red-700"
          }`}
        >
          {message.text}
        </div>
      )}

      {/* 创建表单 */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">创建新小箱</h3>
        <form onSubmit={handleSubmit(onSubmit)} className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="small_box_no" className="block text-sm font-medium text-gray-700 mb-1">
              小箱编号 *
            </label>
            <input
              id="small_box_no"
              type="text"
              {...register("small_box_no", { required: true })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="例如: TEST001"
            />
          </div>
          <div>
            <label htmlFor="system_div" className="block text-sm font-medium text-gray-700 mb-1">
              系统区分
            </label>
            <input
              id="system_div"
              type="text"
              {...register("system_div")}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="例如: 01"
            />
          </div>
          <div>
            <label htmlFor="small_box_type" className="block text-sm font-medium text-gray-700 mb-1">
              小箱类型
            </label>
            <input
              id="small_box_type"
              type="text"
              {...register("small_box_type")}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label htmlFor="arrival_date" className="block text-sm font-medium text-gray-700 mb-1">
              到达日期
            </label>
            <input
              id="arrival_date"
              type="date"
              {...register("arrival_date")}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label htmlFor="envelope_count" className="block text-sm font-medium text-gray-700 mb-1">
              封筒数
            </label>
            <input
              id="envelope_count"
              type="number"
              {...register("envelope_count", { valueAsNumber: true })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label htmlFor="terminal_count" className="block text-sm font-medium text-gray-700 mb-1">
              端末数
            </label>
            <input
              id="terminal_count"
              type="number"
              {...register("terminal_count", { valueAsNumber: true })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label htmlFor="remark" className="block text-sm font-medium text-gray-700 mb-1">
              备注
            </label>
            <input
              id="remark"
              type="text"
              {...register("remark")}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label htmlFor="small_box_remark" className="block text-sm font-medium text-gray-700 mb-1">
              小箱备注
            </label>
            <input
              id="small_box_remark"
              type="text"
              {...register("small_box_remark")}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label htmlFor="register_date" className="block text-sm font-medium text-gray-700 mb-1">
              登记日期 *
            </label>
            <input
              id="register_date"
              type="date"
              {...register("register_date", { required: true })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="md:col-span-2">
            <button
              type="submit"
              className="bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              创建
            </button>
          </div>
        </form>
      </div>

      {/* 列表 */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">小箱列表 ({smallBoxes.length})</h3>
        {loading ? (
          <p className="text-gray-500">加载中...</p>
        ) : smallBoxes.length === 0 ? (
          <p className="text-gray-500">暂无数据</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    小箱编号
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    系统区分
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    封筒数
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    登记日期
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {smallBoxes.map((box) => (
                  <tr key={box.small_box_no}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {box.small_box_no}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {box.system_div || "-"}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {box.envelope_count || "-"}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {box.register_date}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <button
                        onClick={() => handleDelete(box.small_box_no)}
                        className="text-red-600 hover:text-red-900"
                      >
                        删除
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
