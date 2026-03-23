import React from "react";
import { render, screen } from "@testing-library/react";
import Home from "../page";

// Mock next/link
jest.mock("next/link", () => {
  return ({ children, href }: { children: React.ReactNode; href: string }) => {
    return <a href={href}>{children}</a>;
  };
});

describe("Home Page", () => {
  it("renders the welcome message and module cards", () => {
    render(<Home />);

    // Check welcome text
    expect(screen.getByText("欢迎使用")).toBeInTheDocument();
    expect(screen.getByText("CCS 邮政销售票据受理系统")).toBeInTheDocument();

    // Check all modules are present
    expect(screen.getByText("小箱管理")).toBeInTheDocument();
    expect(screen.getByText("受理数据")).toBeInTheDocument();
    expect(screen.getByText("工序管理")).toBeInTheDocument();
    expect(screen.getByText("箱子状态")).toBeInTheDocument();

    // Check descriptions
    expect(screen.getByText("查询、创建、更新、删除小箱信息")).toBeInTheDocument();
    expect(screen.getByText("管理销售票据受理数据")).toBeInTheDocument();
    expect(screen.getByText("记录工序开始/结束")).toBeInTheDocument();
    expect(screen.getByText("查看和更新箱子状态")).toBeInTheDocument();
  });

  it("module cards have correct links", () => {
    render(<Home />);

    const smallBoxLink = screen.getByText("小箱管理").closest("a");
    expect(smallBoxLink).toHaveAttribute("href", "/small-box");

    const acceptanceLink = screen.getByText("受理数据").closest("a");
    expect(acceptanceLink).toHaveAttribute("href", "/acceptance");

    const processLink = screen.getByText("工序管理").closest("a");
    expect(processLink).toHaveAttribute("href", "/process");

    const statusLink = screen.getByText("箱子状态").closest("a");
    expect(statusLink).toHaveAttribute("href", "/status");
  });
});
