import api from "@/lib/axios";
import type { AuthResp, AuthUser } from "./types";

export async function register(email: string, password: string): Promise<AuthResp> {
  const { data } = await api.post<AuthResp>("/auth/register", { email, password });
  return data;
}

export async function login(email: string, password: string): Promise<AuthResp> {
  const { data } = await api.post<AuthResp>("/auth/login", { email, password });
  return data;
}

export async function getMe(): Promise<AuthUser> {
  const { data } = await api.get<AuthUser>("/auth/me");
  return data;
}

export async function logout(): Promise<void> {
  await api.post("/auth/logout");
}
