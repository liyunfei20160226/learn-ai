"use client";

import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AcceptancePage from "../page";

const mockList = jest.fn();
const mockCreate = jest.fn();

jest.mock("@/utils/api", () => ({
  acceptanceApi: {
    list: () => mockList(),
    listBySmallBox: (sbNo: string) => mockList(sbNo),
    create: (data: any) => mockCreate(data),
  },
}));

describe("Acceptance Page", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders the page with title and form", () => {
    mockList.mockResolvedValueOnce({ data: [] });
    render(<AcceptancePage />);

    expect(screen.getByText("受理数据管理")).toBeInTheDocument();
    expect(screen.getByText("新建受理数据")).toBeInTheDocument();
    expect(screen.getByText(/受理数据列表/)).toBeInTheDocument();
    expect(screen.getByLabelText(/受理年月/)).toBeInTheDocument();
    expect(screen.getByLabelText(/小箱编号/)).toBeInTheDocument();
    expect(screen.getByLabelText(/封筒 SEQ/)).toBeInTheDocument();
    expect(screen.getByLabelText(/行号/)).toBeInTheDocument();
  });

  it("loads list on mount", async () => {
    mockList.mockResolvedValueOnce({ data: [] });
    render(<AcceptancePage />);

    await waitFor(() => {
      expect(mockList).toHaveBeenCalled();
      expect(screen.getByText("暂无数据")).toBeInTheDocument();
    });
  });

  it("submits create form correctly", async () => {
    mockList.mockResolvedValueOnce({ data: [] });
    mockCreate.mockResolvedValueOnce({ data: {} });
    mockList.mockResolvedValueOnce({ data: [] });

    render(<AcceptancePage />);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/受理年月/), "202403");
    await user.type(screen.getByLabelText(/小箱编号/), "TEST001");
    await user.type(screen.getByLabelText(/封筒 SEQ/), "1");
    await user.type(screen.getByLabelText(/行号/), "1");

    await user.click(screen.getByRole("button", { name: /创建/ }));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(expect.objectContaining({
        acceptance_ym: expect.stringContaining("202403"),
        small_box_no: "TEST001",
        envelope_seq: 11,
        line_no: 11,
      }));
    });
  });

  it("displays list of acceptance data", async () => {
    const mockData = [
      {
        acceptance_ym: "202403",
        small_box_no: "TEST001",
        envelope_seq: 1,
        line_no: 1,
        sales_count: 10,
      },
      {
        acceptance_ym: "202403",
        small_box_no: "TEST002",
        envelope_seq: 2,
        line_no: 1,
        sales_count: 20,
      },
    ];
    mockList.mockResolvedValueOnce({ data: mockData });

    render(<AcceptancePage />);
    await waitFor(() => {
      expect(screen.getByText("TEST001")).toBeInTheDocument();
      expect(screen.getByText("TEST002")).toBeInTheDocument();
      expect(screen.getByText("10")).toBeInTheDocument();
    });
  });

  it("searches by small box number", async () => {
    mockList.mockResolvedValueOnce({ data: [] });
    const mockData = [{
      acceptance_ym: "202403",
      small_box_no: "TEST001",
      envelope_seq: 1,
      line_no: 1,
      sales_count: 10,
    }];

    render(<AcceptancePage />);
    const user = userEvent.setup();

    mockList.mockResolvedValueOnce({ data: mockData });
    await user.type(screen.getByPlaceholderText("输入小箱编号"), "TEST001");
    await user.click(screen.getByRole("button", { name: /搜索/ }));

    await waitFor(() => {
      expect(mockList).toHaveBeenCalledWith("TEST001");
      expect(screen.getByText("TEST001")).toBeInTheDocument();
    });
  });

  it("clears search and shows all", async () => {
    mockList.mockResolvedValueOnce({ data: [] });
    render(<AcceptancePage />);
    const user = userEvent.setup();

    await user.type(screen.getByPlaceholderText("输入小箱编号"), "TEST001");
    mockList.mockResolvedValueOnce({ data: [] });
    await user.click(screen.getByRole("button", { name: /全部/ }));

    await waitFor(() => {
      expect(mockList).toHaveBeenCalled();
    });
  });
});
