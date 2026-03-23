"use client";

import React from "react";
import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { processApi } from "@/utils/api";
import { ProcessManagement } from "@/types/api";

export default function ProcessPage() {
  const [processes, setProcesses] = useState<ProcessManagement[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);
  const [smallBoxNo, setSmallBoxNo] = useState("");

  const { register, handleSubmit, reset } = useForm<{
    small_box_no: string;
    process_div: string;
    personal_code: string;
    start_datetime: string;
  }>({
    defaultValues: {
      process_div: "01",
      start_datetime: new Date().toISOString().slice(0, 16),
    },
  });

  const loadList = async (sbNo: string) => {
    if (!sbNo) {
      setProcesses([]);
      return;
    }
    setLoading(true);
    try {
      const res = await processApi.listBySmallBox(sbNo);
      setProcesses(res.data);
    } catch (err) {
      setMessage({ text: `加载失败: ${(err as Error).message}`, type: "error" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadList(smallBoxNo);
  }, [smallBoxNo]);

  const onStart = async (data: {
    small_box_no: string;
    process_div: string;
    personal_code: string;
    start_datetime: string;
  }) => {
    try {
      await processApi.start(data);
      setMessage({ text: "工序开始成功", type: "success" });
      reset({
        process_div: "01",
        start_datetime: new Date().toISOString().slice(0, 16),
      });
      loadList(data.small_box_no);
      setSmallBoxNo(data.small_box_no);
    } catch (err: any) {
      setMessage({
        text: `开始失败: ${err.response?.data?.detail || (err as Error).message}`,
        type: "error",
      });
    }
  };

  const onEnd = async (
    small_box_no: string,
    process_div: string,
    personal_code: string,
    start_datetime: string
  ) => {
    const end_datetime = new Date().toISOString().slice(0, 16);
    try {
      await processApi.end({
        small_box_no,
        process_div,
        personal_code,
        start_datetime,
        end_datetime,
      });
      setMessage({ text: "工序结束成功", type: "success" });
      loadList(small_box_no);
    } catch (err: any) {
      setMessage({
        text: `结束失败: ${err.response?.data?.detail || (err as Error).message}`,
        type: "error",
      });
    }
  };

  const handleDelete = async (
    small_box_no: string,
    process_div: string,
    personal_code: string,
    start_datetime: string
  ) => {
    if (!confirm(`确认删除这条工序记录?`)) return;
    try {
      await processApi.delete(small_box_no, process_div, personal_code, start_datetime);
      setMessage({ text: "删除成功", type: "success" });
      loadList(small_box_no);
    } catch (err: any) {
      setMessage({
        text: `删除失败: ${err.response?.data?.detail || (err as Error).message}`,
        type: "error",
      });
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">工序管理</h2>

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

      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">开始工序</h3>
        <form onSubmit={handleSubmit(onStart)} className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label htmlFor="small_box_no" className="block text-sm font-medium text-gray-700 mb-1">
              小箱编号 *
            </label>
            <input
              id="small_box_no"
              type="text"
              {...register("small_box_no", { required: true })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              onChange={(e) => setSmallBoxNo(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="process_div" className="block text-sm font-medium text-gray-700 mb-1">
              工序区分 *
            </label>
            <input
              id="process_div"
              type="text"
              {...register("process_div", { required: true })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label htmlFor="personal_code" className="block text-sm font-medium text-gray-700 mb-1">
              人员编码 *
            </label>
            <input
              id="personal_code"
              type="text"
              {...register("personal_code", { required: true })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label htmlFor="start_datetime" className="block text-sm font-medium text-gray-700 mb-1">
              开始时间 *
            </label>
            <input
              id="start_datetime"
              type="datetime-local"
              {...register("start_datetime", { required: true })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="md:col-span-4">
            <button
              type="submit"
              className="bg-yellow-500 text-white px-4 py-2 rounded-md hover:bg-yellow-600 focus:outline-none focus:ring-2 focus:ring-yellow-500"
            >
              开始工序
            </button>
          </div>
        </form>
      </div>

      {smallBoxNo && (
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">
            工序记录 - 小箱 {smallBoxNo} ({processes.length})
          </h3>
          {loading ? (
            <p className="text-gray-500">加载中...</p>
          ) : processes.length === 0 ? (
            <p className="text-gray-500">暂无工序记录</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      工序区分
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      人员编码
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      开始时间
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      结束时间
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      操作
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {processes.map((proc) => (
                    <tr key={`${proc.small_box_no}-${proc.process_div}-${proc.personal_code}-${proc.start_datetime}`}>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                        {proc.process_div}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                        {proc.personal_code}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                        {proc.start_datetime}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                        {proc.end_datetime || "-"}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                        {!proc.end_datetime && (
                          <button
                            onClick={() =>
                              onEnd(
                                proc.small_box_no,
                                proc.process_div,
                                proc.personal_code,
                                proc.start_datetime
                              )
                            }
                            className="text-green-600 hover:text-green-900 mr-3"
                          >
                            结束
                          </button>
                        )}
                        <button
                          onClick={() =>
                            handleDelete(
                              proc.small_box_no,
                              proc.process_div,
                              proc.personal_code,
                              proc.start_datetime
                            )
                          }
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
