"use client";

import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SmallBoxPage from "../page";

const mockGet = jest.fn();
const mockPost = jest.fn();
const mockPut = jest.fn();
const mockDelete = jest.fn();

jest.mock("@/utils/api", () => ({
  smallBoxApi: {
    list: () => mockGet(),
    create: (data: any) => mockPost(data),
  },
}));

describe("SmallBox Page", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders the page with title and form", () => {
    mockGet.mockResolvedValueOnce({ data: [] });
    render(<SmallBoxPage />);

    expect(screen.getByText("小箱管理")).toBeInTheDocument();
    expect(screen.getByText("创建新小箱")).toBeInTheDocument();
    expect(screen.getByText(/小箱列表/)).toBeInTheDocument();
    expect(screen.getByLabelText(/小箱编号/)).toBeInTheDocument();
    expect(screen.getByLabelText(/登记日期/)).toBeInTheDocument();
  });

  it("loads list on mount", async () => {
    mockGet.mockResolvedValueOnce({ data: [] });
    render(<SmallBoxPage />);
    await waitFor(() => {
      expect(mockGet).toHaveBeenCalled();
    });
  });

  it("submits create form correctly", async () => {
    mockGet.mockResolvedValueOnce({ data: [] });
    mockPost.mockResolvedValueOnce({ data: {} });
    mockGet.mockResolvedValueOnce({ data: [] });

    render(<SmallBoxPage />);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/小箱编号/), "TEST001");
    await user.type(screen.getByLabelText(/系统区分/), "01");
    await user.type(screen.getByLabelText(/封筒数/), "10");

    await user.click(screen.getByRole("button", { name: /创建/ }));

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith(expect.objectContaining({
        small_box_no: "TEST001",
        system_div: "01",
        envelope_count: 10,
      }));
    });
  });

  it("displays list of small boxes", async () => {
    const mockData = [
      {
        small_box_no: "TEST001",
        system_div: "01",
        envelope_count: 10,
        register_date: "2024-01-01",
      },
      {
        small_box_no: "TEST002",
        system_div: "02",
        envelope_count: 20,
        register_date: "2024-01-02",
      },
    ];
    mockGet.mockResolvedValueOnce({ data: mockData });

    render(<SmallBoxPage />);
    await waitFor(() => {
      expect(screen.getByText("TEST001")).toBeInTheDocument();
      expect(screen.getByText("TEST002")).toBeInTheDocument();
    });
  });
});
