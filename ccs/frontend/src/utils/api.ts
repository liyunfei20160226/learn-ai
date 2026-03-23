import axios from "axios";

const api = axios.create({
  baseURL: "",
  timeout: 10000,
});

// 小箱相关 API
export const smallBoxApi = {
  list: () => api.get("/api/small-box/"),
  get: (smallBoxNo: string) => api.get(`/api/small-box/${smallBoxNo}`),
  create: (data: any) => api.post("/api/small-box/", data),
  update: (smallBoxNo: string, data: any) => api.put(`/api/small-box/${smallBoxNo}`, data),
  delete: (smallBoxNo: string) => api.delete(`/api/small-box/${smallBoxNo}`),
  getStatus: (smallBoxNo: string) => api.get(`/api/small-box/${smallBoxNo}/status`),
  getAcceptance: (smallBoxNo: string) => api.get(`/api/small-box/${smallBoxNo}/acceptance`),
  getProcess: (smallBoxNo: string) => api.get(`/api/small-box/${smallBoxNo}/process`),
};

// 受理数据 API
export const acceptanceApi = {
  list: (skip: number = 0, limit: number = 100) =>
    api.get("/api/acceptance/", { params: { skip, limit } }),
  get: (acceptanceYm: string, smallBoxNo: string, envelopeSeq: number, lineNo: number) =>
    api.get(`/api/acceptance/${acceptanceYm}/${smallBoxNo}/${envelopeSeq}/${lineNo}`),
  create: (data: any) => api.post("/api/acceptance/", data),
  createBatch: (data: any[]) => api.post("/api/acceptance/batch", data),
  update: (acceptanceYm: string, smallBoxNo: string, envelopeSeq: number, lineNo: number, data: any) =>
    api.put(`/api/acceptance/${acceptanceYm}/${smallBoxNo}/${envelopeSeq}/${lineNo}`, data),
  delete: (acceptanceYm: string, smallBoxNo: string, envelopeSeq: number, lineNo: number) =>
    api.delete(`/api/acceptance/${acceptanceYm}/${smallBoxNo}/${envelopeSeq}/${lineNo}`),
  listBySmallBox: (smallBoxNo: string) =>
    api.get(`/api/acceptance/by-small-box/${smallBoxNo}`),
};

// 工序管理 API
export const processApi = {
  start: (data: any) => api.post("/api/process/start", data),
  end: (data: any) => api.put("/api/process/end", data),
  listBySmallBox: (smallBoxNo: string) =>
    api.get(`/api/process/by-small-box/${smallBoxNo}`),
  delete: (smallBoxNo: string, processDiv: string, personalCode: string, startDatetime: string) =>
    api.delete(`/api/process/${smallBoxNo}/${processDiv}/${personalCode}/${startDatetime}`),
};

// 箱子状态 API
export const boxStatusApi = {
  get: (systemDiv: string, smallBoxNo: string) =>
    api.get(`/api/status/${systemDiv}/${smallBoxNo}`),
  getBySmallBox: (smallBoxNo: string) =>
    api.get(`/api/status/by-small-box/${smallBoxNo}`),
  create: (data: any) => api.post("/api/status/", data),
  update: (systemDiv: string, smallBoxNo: string, data: any) =>
    api.put(`/api/status/${systemDiv}/${smallBoxNo}`, data),
  delete: (systemDiv: string, smallBoxNo: string) =>
    api.delete(`/api/status/${systemDiv}/${smallBoxNo}`),
};

export default api;
