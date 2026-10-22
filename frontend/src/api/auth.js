import { get, post } from "./client";

export const authApi = {
  me: () => get("/auth/me"),
  login: (username, password) => post("/auth/login", { username, password }),
  register: (payload) => post("/auth/register", payload),
  logout: () => post("/auth/logout"),
  users: () => get("/users"),
};
