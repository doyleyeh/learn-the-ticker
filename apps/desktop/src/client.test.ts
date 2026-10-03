import { describe, expect, it, vi, afterEach } from "vitest";
import { api, connect } from "./client";

afterEach(() => vi.unstubAllGlobals());
describe("local transport", () => {
  it("rejects remote or credential-bearing endpoints", () => {
    for (const endpoint of ["https://evil.example", "http://localhost:1", "http://127.0.0.1:1/?token=x", "http://user@127.0.0.1:1/"]) {
      expect(() => connect({ endpoint, token: "x".repeat(40) })).toThrow();
    }
  });
  it("uses a memory credential header and refuses redirects", async () => {
    const fetcher = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: "ready" }) });
    vi.stubGlobal("fetch", fetcher);
    connect({ endpoint: "http://127.0.0.1:1234", token: "x".repeat(40) });
    await api("/api/health");
    expect(fetcher.mock.calls[0][0]).toBe("http://127.0.0.1:1234/api/health");
    expect(fetcher.mock.calls[0][1].headers.Authorization).toBe("Bearer " + "x".repeat(40));
    expect(fetcher.mock.calls[0][1].redirect).toBe("error");
  });
});
