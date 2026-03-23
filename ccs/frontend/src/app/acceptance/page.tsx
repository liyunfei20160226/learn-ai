"use client";

import React from "react";
import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { acceptanceApi } from "@/utils/api";
import { AcceptanceData } from "@/types/api";

export default function AcceptancePage() {
  const [acceptances, setAcceptances] = useState<AcceptanceData[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);
  const [searchSmallBoxNo, setSearchSmallBoxNo] = useState("");

  const { register, handleSubmit, reset } = useForm<{
    acceptance_ym: string;
    small_box_no: string;
    envelope_seq: number;
    line_no: number;
    envelope_no: string;
    registered_no: string;
    sales_start_date: string;
    sales_end_date: string;
    terminal_group_no: string;
    terminal_id_upper: string;
    terminal_id_lower: string;
    maker_no: string;
    system_div: string;
    new_system_div: string;
    sales_count: number;
    group_cd: string;
    input_date: string;
    input_user_no: string;
    envelope_type: number;
    modify_user_no: string;
    register_date: string;
  }>({
    defaultValues: {
      acceptance_ym: new Date().toISOString().slice(0, 7).replace("-", ""),
      register_date: new Date().toISOString().split("T")[0],
      envelope_seq: 1,
      line_no: 1,
      envelope_type: 1,
      sales_count: 1,
    },
  });

  const loadList = async (smallBoxNo?: string) => {
    setLoading(true);
    try {
      let res;
      if (smallBoxNo) {
        res = await acceptanceApi.listBySmallBox(smallBoxNo);
      } else {
        res = await acceptanceApi.list();
      }
      setAcceptances(res.data);
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
      await acceptanceApi.create(data);
      setMessage({ text: "创建成功", type: "success" });
      reset({
        acceptance_ym: new Date().toISOString().slice(0, 7).replace("-", ""),
        register_date: new Date().toISOString().split("T")[0],
        envelope_seq: 1,
        line_no: 1,
        envelope_type: 1,
        sales_count: 1,
      });
      loadList();
    } catch (err: any) {
      setMessage({
        text: `创建失败: ${err.response?.data?.detail || (err as Error).message}`,
        type: "error",
      });
    }
  };

  const handleSearch = () => {
    if (searchSmallBoxNo.trim()) {
      loadList(searchSmallBoxNo.trim());
    } else {
      loadList();
    }
  };

  const handleDelete = async (
    acceptanceYm: string,
    smallBoxNo: string,
    envelopeSeq: number,
    lineNo: number
  ) => {
    if (!confirm(`确认删除这条受理数据?`)) return;
    try {
      await acceptanceApi.delete(acceptanceYm, smallBoxNo, envelopeSeq, lineNo);
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
      <h2 className="text-2xl font-bold text-gray-900">受理数据管理</h2>

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
        <h3 className="text-lg font-semibold mb-4">新建受理数据</h3>
        <form onSubmit={handleSubmit(onSubmit)} className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label htmlFor="acceptance_ym" className="block text-sm font-medium text-gray-700 mb-1">
              受理年月 * (YYYYMM)
            </label>
            <input
              id="acceptance_ym"
              type="text"
              {...register("acceptance_ym", { required: true })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="202403"
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
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label htmlFor="envelope_seq" className="block text-sm font-medium text-gray-700 mb-1">
              封筒 SEQ *
            </label>
            <input
              id="envelope_seq"
              type="number"
              {...register("envelope_seq", { valueAsNumber: true, required: true })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label htmlFor="line_no" className="block text-sm font-medium text-gray-700 mb-1">
              行号 *
            </label>
            <input
              id="line_no"
              type="number"
              {...register("line_no", { valueAsNumber: true, required: true })}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label htmlFor="envelope_no" className="block text-sm font-medium text-gray-700 mb-1">
              封筒编号
            </label>
            <input
              id="envelope_no"
              type="text"
              {...register("envelope_no")}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label htmlFor="registered_no" className="block text-sm font-medium text-gray-700 mb-1">
              书留编号
            </label>
            <input
              id="registered_no"
              type="text"
              {...register("registered_no")}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="md:col-span-3">
            <button
              type="submit"
              className="bg-green-500 text-white px-4 py-2 rounded-md hover:bg-green-600 focus:outline-none focus:ring-2 focus:ring-green-500"
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
            <label className="block text-sm font-medium text-gray-700 mb-1">
              按小箱编号搜索
            </label>
            <input
              type="text"
              value={searchSmallBoxNo}
              onChange={(e) => setSearchSmallBoxNo(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="输入小箱编号"
            />
          </div>
          <button
            onClick={handleSearch}
            className="bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            搜索
          </button>
          <button
            onClick={() => {
              setSearchSmallBoxNo("");
              loadList();
            }}
            className="bg-gray-500 text-white px-4 py-2 rounded-md hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500"
          >
            全部
          </button>
        </div>
      </div>

      {/* 列表 */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">受理数据列表 ({acceptances.length})</h3>
        {loading ? (
          <p className="text-gray-500">加载中...</p>
        ) : acceptances.length === 0 ? (
          <p className="text-gray-500">暂无数据</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    受理年月
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    小箱编号
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    SEQ/行
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    销售枚数
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {acceptances.map((acc) => (
                  <tr key={`${acc.acceptance_ym}-${acc.small_box_no}-${acc.envelope_seq}-${acc.line_no}`}>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                      {acc.acceptance_ym}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                      {acc.small_box_no}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                      {acc.envelope_seq}/{acc.line_no}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                      {acc.sales_count}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                      <button
                        onClick={() =>
                          handleDelete(
                            acc.acceptance_ym,
                            acc.small_box_no,
                            acc.envelope_seq,
                            acc.line_no
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
    </div>
  );
}
