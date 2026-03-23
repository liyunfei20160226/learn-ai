"use client";

import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ProcessPage from "../page";

const mockListBySmallBox = jest.fn();
const mockStart = jest.fn();
const mockEnd = jest.fn();
const mockDelete = jest.fn();

jest.mock("@/utils/api", () => ({
  processApi: {
    listBySmallBox: (sbNo: string) => mockListBySmallBox(sbNo),
    start: (data: any) => mockStart(data),
    end: (data: any) => mockEnd(data),
    delete: (sbNo: string) => mockDelete(sbNo),
  },
}));

describe("Process Page", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders the page with title and form", () => {
    render(<ProcessPage />);

    expect(screen.getByText("工序管理")).toBeInTheDocument();
    expect(screen.getAllByText("开始工序")).toHaveLength(2);
    expect(screen.getByLabelText(/小箱编号/)).toBeInTheDocument();
    expect(screen.getByLabelText(/工序区分/)).toBeInTheDocument();
    expect(screen.getByLabelText(/人员编码/)).toBeInTheDocument();
    expect(screen.getByLabelText(/开始时间/)).toBeInTheDocument();
  });

  it("does not show list when no small box number", () => {
    render(<ProcessPage />);
    expect(screen.queryByText("工序记录")).not.toBeInTheDocument();
  });

  it("submits start process correctly", async () => {
    mockListBySmallBox.mockResolvedValue({ data: [] });
    mockStart.mockResolvedValueOnce({ data: {} });

    render(<ProcessPage />);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/小箱编号/), "TEST001");
    await user.type(screen.getByLabelText(/工序区分/), "01");
    await user.type(screen.getByLabelText(/人员编码/), "U001");

    await user.click(screen.getByRole("button", { name: /开始工序/ }));

    await waitFor(() => {
      expect(mockStart).toHaveBeenCalledWith(expect.objectContaining({
        small_box_no: "TEST001",
        process_div: "0101",
        personal_code: "U001",
      }));
      expect(screen.getByText("工序开始成功")).toBeInTheDocument();
    });
  });

  it("displays list of processes when small box is entered", async () => {
    const mockData = [
      {
        small_box_no: "TEST001",
        process_div: "01",
        personal_code: "U001",
        start_datetime: "2024-01-01T09:00",
        end_datetime: null,
      },
      {
        small_box_no: "TEST001",
        process_div: "02",
        personal_code: "U002",
        start_datetime: "2024-01-01T10:00",
        end_datetime: "2024-01-01T12:00",
      },
    ];

    render(<ProcessPage />);
    const user = userEvent.setup();

    mockListBySmallBox.mockResolvedValue({ data: mockData });
    await user.type(screen.getByLabelText(/小箱编号/), "TEST001");

    await waitFor(() => {
      expect(screen.getByText(/工序记录 - 小箱 TEST001/)).toBeInTheDocument();
      expect(screen.getByText("01")).toBeInTheDocument();
      expect(screen.getByText("U001")).toBeInTheDocument();
      expect(screen.getByText("结束")).toBeInTheDocument();
    });
  });

  it("calls end process when end button clicked", async () => {
    const mockData = [
      {
        small_box_no: "TEST001",
        process_div: "01",
        personal_code: "U001",
        start_datetime: "2024-01-01T09:00",
        end_datetime: null,
      },
    ];

    render(<ProcessPage />);
    const user = userEvent.setup();

    mockListBySmallBox.mockResolvedValue({ data: mockData });
    await user.type(screen.getByLabelText(/小箱编号/), "TEST001");

    await waitFor(() => {
      expect(screen.getByText("结束")).toBeInTheDocument();
    });

    mockEnd.mockResolvedValueOnce({ data: {} });
    mockListBySmallBox.mockResolvedValue({ data: mockData });
    await user.click(screen.getByText("结束"));

    await waitFor(() => {
      expect(mockEnd).toHaveBeenCalled();
      expect(screen.getByText("工序结束成功")).toBeInTheDocument();
    });
  });

  it("shows empty message when no processes", async () => {
    render(<ProcessPage />);
    const user = userEvent.setup();

    mockListBySmallBox.mockResolvedValue({ data: [] });
    await user.type(screen.getByLabelText(/小箱编号/), "TEST001");

    await waitFor(() => {
      expect(screen.getByText("暂无工序记录")).toBeInTheDocument();
    });
  });
});
