import React from "react";
import Link from "next/link";

export default function Home() {
  const modules = [
    {
      name: "小箱管理",
      description: "查询、创建、更新、删除小箱信息",
      href: "/small-box",
      color: "bg-blue-500 hover:bg-blue-600",
    },
    {
      name: "受理数据",
      description: "管理销售票据受理数据",
      href: "/acceptance",
      color: "bg-green-500 hover:bg-green-600",
    },
    {
      name: "工序管理",
      description: "记录工序开始/结束",
      href: "/process",
      color: "bg-yellow-500 hover:bg-yellow-600",
    },
    {
      name: "箱子状态",
      description: "查看和更新箱子状态",
      href: "/status",
      color: "bg-purple-500 hover:bg-purple-600",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-3xl font-bold text-gray-900">欢迎使用</h2>
        <p className="mt-2 text-lg text-gray-600">
          CCS 邮政销售票据受理系统
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4 mt-8">
        {modules.map((module) => (
          <Link
            key={module.href}
            href={module.href}
            className={`relative rounded-lg shadow-md p-6 text-white ${module.color} transition-all hover:shadow-lg`}
          >
            <h3 className="text-xl font-semibold mb-2">{module.name}</h3>
            <p className="text-sm opacity-90">{module.description}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
