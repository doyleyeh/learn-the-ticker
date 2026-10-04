import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { ResearchJobList, ResearchJobs } from "./ResearchJobs";

describe("research recovery presentation", () => {
  it("discloses read-only recovery and bounded history", () => {
    const html = renderToStaticMarkup(<ResearchJobs onOpen={async () => {}}/>);
    expect(html).toContain("Opening a job never starts it again");
    expect(html).toContain("Up to 50 jobs"); expect(html).toContain("Refresh job list");
  });
  it("keeps request text escaped and shows status, language, level and scope", () => {
    const html = renderToStaticMarkup(<ResearchJobList disabled={false} currentId="old" onOpen={() => {}} jobs={[{
      id: "old", status: "interrupted", created_at: "2026-10-04T00:00:00Z",
      request: { query: "<script>Example 公司</script>", asset_id: "TEST:ONE", provider: "codex", language: "zh-TW", level: "intermediate" },
    }]}/>);
    expect(html).toContain("interrupted"); expect(html).toContain("zh-TW"); expect(html).toContain("intermediate");
    expect(html).toContain("TEST:ONE"); expect(html).toContain('aria-pressed="true"');
    expect(html).not.toContain("<script>");
  });
});
