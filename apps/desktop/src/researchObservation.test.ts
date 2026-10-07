import { afterEach, describe, expect, it, vi } from "vitest";
import { observeResearch } from "./researchObservation";
import { api, watchJob } from "./client";

vi.mock("./client", () => ({ api: vi.fn(), watchJob: vi.fn() }));
afterEach(() => { vi.clearAllMocks(); vi.useRealTimers(); });

describe("existing research observation", () => {
  it("continues read-only polling after socket loss and transient API failure", async () => {
    vi.useFakeTimers();
    const close = vi.fn(), jobs = vi.fn(), errors = vi.fn();
    let disconnect = () => {};
    vi.mocked(watchJob).mockImplementation((_id, _event, onClose) => { disconnect = onClose; return close; });
    vi.mocked(api).mockResolvedValueOnce({ status: "running" }).mockRejectedValueOnce(new Error("disconnected"))
      .mockResolvedValueOnce({ status: "completed", result: { id: "original-version" } });
    const stop = observeResearch("existing/id", jobs, vi.fn(), errors);
    await vi.advanceTimersByTimeAsync(0);
    disconnect();
    await vi.advanceTimersByTimeAsync(2000);
    expect(errors).toHaveBeenCalledTimes(1);
    expect(jobs.mock.calls.at(-1)?.[0].result.id).toBe("original-version");
    await vi.advanceTimersByTimeAsync(10000);
    expect(api).toHaveBeenCalledTimes(3);
    for (const [path, init] of vi.mocked(api).mock.calls) {
      expect(path).toBe("/api/jobs/existing%2Fid");
      expect(init?.method).toBeUndefined();
      expect(init?.body).toBeUndefined();
    }
    stop(); expect(close).toHaveBeenCalledOnce();
  });
  it("never overlaps reads or applies a late result after cleanup", async () => {
    vi.useFakeTimers();
    let resolve: (value: { status: string }) => void = () => {};
    let disconnect = () => {};
    vi.mocked(watchJob).mockImplementation((_id, _event, onClose) => { disconnect = onClose; return vi.fn(); });
    vi.mocked(api).mockReturnValue(new Promise((done) => { resolve = done; }));
    const jobs = vi.fn(), stop = observeResearch("existing", jobs, vi.fn(), vi.fn());
    disconnect(); disconnect();
    await vi.advanceTimersByTimeAsync(10000);
    expect(api).toHaveBeenCalledTimes(1);
    const signal = vi.mocked(api).mock.calls[0][1]?.signal;
    stop(); expect(signal?.aborted).toBe(true);
    resolve({ status: "completed" });
    await vi.advanceTimersByTimeAsync(10000);
    expect(jobs).not.toHaveBeenCalled(); expect(api).toHaveBeenCalledTimes(1);
  });
});
