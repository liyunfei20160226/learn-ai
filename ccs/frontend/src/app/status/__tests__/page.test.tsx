"use client";

import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import BoxStatusPage from "../page";

const mockGetBySmallBox = jest.fn();
const mockCreate = jest.fn();
const mockDelete = jest.fn();

jest.mock("@/utils/api", () => ({
  boxStatusApi: {
    getBySmallBox: (sbNo: string) => mockGetBySmallBox(sbNo),
    create: (data: any) => mockCreate(data),
    delete: (systemDiv: string, sbNo: string) => mockDelete(systemDiv, sbNo),
  },
}));

describe("Box Status Page", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders the page with title and form", () => {
    render(<BoxStatusPage />);

    expect(screen.getByText("箱子状态管理")).toBeInTheDocument();
    expect(screen.getByText("新建箱子状态")).toBeInTheDocument();
    expect(screen.getByText("按小箱编号查询状态")).toBeInTheDocument();
    expect(screen.getByLabelText(/系统区分/)).toBeInTheDocument();
    expect(screen.getAllByLabelText(/小箱编号/)).toHaveLength(2);
    expect(screen.getByLabelText(/INFOX 标志/)).toBeInTheDocument();
    expect(screen.getByLabelText(/登记日期/)).toBeInTheDocument();
  });

  it("does not show list when no small box number", () => {
    render(<BoxStatusPage />);
    expect(screen.queryByText("箱子状态列表")).not.toBeInTheDocument();
  });

  it("submits create form correctly", async () => {
    mockCreate.mockResolvedValueOnce({ data: {} });
    mockGetBySmallBox.mockResolvedValueOnce({ data: [] });

    render(<BoxStatusPage />);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/系统区分/), "01");
    await user.type(screen.getAllByLabelText(/小箱编号/)[0], "TEST001");

    await user.click(screen.getByRole("button", { name: /创建/ }));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(expect.objectContaining({
        system_div: "0101",
        small_box_no: "TEST001",
        infox_flag: 1,
        register_date: expect.any(String),
      }));
      expect(screen.getByText("创建成功")).toBeInTheDocument();
    });
  });

  it("displays list of statuses when queried", async () => {
    const mockData = [
      {
        system_div: "01",
        small_box_no: "TEST001",
        infox_flag: 1,
        small_box_status_cd: "ACTIVE",
        register_date: "2024-01-01",
      },
      {
        system_div: "02",
        small_box_no: "TEST001",
        infox_flag: 0,
        register_date: "2024-01-02",
      },
    ];

    render(<BoxStatusPage />);
    const user = userEvent.setup();

    mockGetBySmallBox.mockResolvedValueOnce({ data: mockData });
    await user.type(screen.getByLabelText(/按小箱编号查询状态/), "TEST001");
    await user.click(screen.getByRole("button", { name: /查询/ }));

    await waitFor(() => {
      expect(mockGetBySmallBox).toHaveBeenCalledWith("TEST001");
      expect(screen.getByText(/箱子状态列表 - TEST001/)).toBeInTheDocument();
      expect(screen.getByText("01")).toBeInTheDocument();
      expect(screen.getByText("ACTIVE")).toBeInTheDocument();
      expect(screen.getByText("1")).toBeInTheDocument();
    });
  });

  it("shows empty message when no statuses", async () => {
    render(<BoxStatusPage />);
    const user = userEvent.setup();

    mockGetBySmallBox.mockResolvedValueOnce({ data: [] });
    await user.type(screen.getByLabelText(/按小箱编号查询状态/), "TEST001");
    await user.click(screen.getByRole("button", { name: /查询/ }));

    await waitFor(() => {
      expect(screen.getByText("暂无状态记录")).toBeInTheDocument();
    });
  });

  it("shows loading state when fetching", async () => {
    render(<BoxStatusPage />);
    const user = userEvent.setup();

    mockGetBySmallBox.mockImplementation(() => new Promise(resolve => setTimeout(() => resolve({ data: [] }), 100)));
    await user.type(screen.getByLabelText(/按小箱编号查询状态/), "TEST001");
    await user.click(screen.getByRole("button", { name: /查询/ }));

    expect(await screen.findByText("加载中...")).toBeInTheDocument();
  });
});
