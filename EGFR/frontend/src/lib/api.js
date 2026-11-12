import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
  headers: { "Content-Type": "application/json" },
  timeout: 15000,
});

export async function analyzeMolecule(smiles) {
  const { data } = await api.post("/analyze", { smiles });
  return data;
}

export async function getApiStatus() {
  const { data } = await api.get("/health");
  return data;
}

export function getApiErrorMessage(error) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
    if (error.code === "ECONNABORTED") {
      return "The analysis service took too long to respond. Please try again.";
    }
    if (!error.response) {
      return "Could not reach the analysis service. Check that the backend is running and configured.";
    }
    return `The analysis service returned an unexpected response (${error.response.status}).`;
  }
  return "An unexpected error occurred while analyzing this molecule.";
}
