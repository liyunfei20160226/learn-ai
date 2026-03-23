"use client";

import React from "react";
import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { boxStatusApi } from "@/utils/api";
import { BoxStatus } from "@/types/api";

export default function BoxStatusPage() {
  const [statuses, setStatuses] = useState<BoxStatus[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);
  const [smallBoxNo, setSmallBoxNo] = useState("");

  const { register, handleSubmit, reset } = useForm<{
    system_div: string;
    small_box_no: string;
    infox_flag: number;
    header_sheet_printed_flag: number;
    scan_system_linked_flag: number;
    small_box_status_cd: string;
    small_box_div: string;
    register_date: string;
  }>({
    defaultValues: {
      system_div: "01",
      infox_flag: 1,
      header_sheet_printed_flag: 0,
      scan_system_linked_flag: 0,
      small_box_div: "01",
      register_date: new Date().toISOString().split("T")[0],
    },
  });

  const loadList = async (sbNo: string) => {
    if (!sbNo) {
      setStatuses([]);
      return;
    }
    setLoading(true);
    try {
      const res = await boxStatusApi.getBySmallBox(sbNo);
      setStatuses(res.data);
    } catch (err) {
      setMessage({ text: `加载失败: ${(err as Error).message}`, type: "error" });
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = async (data: any) => {
    try {
      await boxStatusApi.create(data);
      setMessage({ text: "创建成功", type: "success" });
      reset({
        system_div: "01",
        infox_flag: 1,
        header_sheet_printed_flag: 0,
        scan_system_linked_flag: 0,
        small_box_div: "01",
        register_date: new Date().toISOString().split("T")[0],
      });
      loadList(data.small_box_no);
      setSmallBoxNo(data.small_box_no);
    } catch (err: any) {
      setMessage({
        text: `创建失败: ${err.response?.data?.detail || (err as Error).message}`,
        type: "error",
      });
    }
  };

  const handleDelete = async (systemDiv: string, smallBoxNo: string) => {
    if (!confirm(`确认删除箱子状态?`)) return;
    try {
      await boxStatusApi.delete(systemDiv, smallBoxNo);
      setMessage({ text: "删除成功", type: "success" });
      loadList(smallBoxNo);
    } catch (err: any) {
      setMessage({
        text: `删除失败: ${err.response?.data?.detail || (err as Error).message}`,
        type: "error",
      });
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">箱子状态管理</h2>

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
        <h3 className="text-lg font-semibold mb-4">新建箱子状态</h3>
        <form onSubmit={handleSubmit(onSubmit)} className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label htmlFor="system_div" className="block text-sm font-medium text-gray-700 mb-1">
              系统区分 *
            </label>
            <input
              id="system_div"
              type="text"
              {...register("system_div", { required: true })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>
          <div>
            <label htmlFor="small_box_no" className="block text-sm font-medium text-gray-700 mb-1">
              小箱编号 *
            </label>
            <input
              id="small_box_no"
              type="text"
              {...register("small_box_no", { required: true })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
              onChange={(e) => setSmallBoxNo(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="infox_flag" className="block text-sm font-medium text-gray-700 mb-1">
              INFOX 标志 (0/1)
            </label>
            <input
              id="infox_flag"
              type="number"
              {...register("infox_flag", { valueAsNumber: true })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
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
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>
          <div className="md:col-span-3">
            <button
              type="submit"
              className="bg-purple-500 text-white px-4 py-2 rounded-md hover:bg-purple-600 focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              创建
            </button>
          </div>
        </form>
      </div>

      {/* 搜索 */}
      <div className="bg-white shadow rounded-lg p-6">
        <div className="flex gap-4 items-end">
          <div className="flex-1">
            <label htmlFor="search_small_box_no" className="block text-sm font-medium text-gray-700 mb-1">
              按小箱编号查询状态
            </label>
            <input
              id="search_small_box_no"
              type="text"
              value={smallBoxNo}
              onChange={(e) => setSmallBoxNo(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
              placeholder="输入小箱编号"
            />
          </div>
          <button
            onClick={() => loadList(smallBoxNo)}
            className="bg-purple-500 text-white px-4 py-2 rounded-md hover:bg-purple-600 focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            查询
          </button>
        </div>
      </div>

      {/* 列表 */}
      {smallBoxNo && (
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">
            箱子状态列表 - {smallBoxNo} ({statuses.length})
          </h3>
          {loading ? (
            <p className="text-gray-500">加载中...</p>
          ) : statuses.length === 0 ? (
            <p className="text-gray-500">暂无状态记录</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      系统区分
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      INFOX
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      状态码
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      登记日期
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      操作
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {statuses.map((status) => (
                    <tr key={`${status.system_div}-${status.small_box_no}`}>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                        {status.system_div}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                        {status.infox_flag}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                        {status.small_box_status_cd || "-"}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                        {status.register_date}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                        <button
                          onClick={() => handleDelete(status.system_div, status.small_box_no)}
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
      )}
    </div>
  );
}
