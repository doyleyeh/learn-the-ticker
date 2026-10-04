import { expect, test, type Page } from "@playwright/test";

async function connect(page: Page) {
  await page.getByText("Developer browser connection", { exact: true }).click();
  await page.getByRole("textbox", { name: "Local endpoint", exact: true }).fill("http://127.0.0.1:18764");
  await page.getByRole("textbox", { name: "Temporary session credential" }).fill("synthetic-preview-credential-not-for-production");
  await page.getByRole("button", { name: "Connect locally" }).click();
  await expect(page.getByRole("textbox", { name: "Understand an asset" })).toBeVisible();
}

async function research(page: Page, query: string) {
  await page.getByRole("textbox", { name: "Understand an asset" }).fill(query);
  await page.getByRole("button", { name: "Research", exact: true }).click();
  const review = page.getByRole("region", { name: "Source review", exact: true });
  await expect(review).toBeVisible();
  await expect(review.getByRole("checkbox")).toHaveCount(9);
  await expect(review.locator("input:checked")).toHaveCount(0);
  await expect(review.getByRole("button", { name: "Use selected sources" })).toBeDisabled();
  return review;
}

test("admitted versions, source review and reconnect preserve evidence at normal and narrow widths", async ({ page, context }, testInfo) => {
  const failures: string[] = [], external: string[] = [], generation: string[] = [], termLookups: { bundle_id: string }[] = [];
  page.on("pageerror", (error) => failures.push(error.message));
  page.on("response", (response) => { if (response.url().includes("/api/") && response.status() >= 400) failures.push(`${response.status()} ${new URL(response.url()).pathname}`); });
  page.on("request", (request) => { if (request.method() === "POST" && new URL(request.url()).pathname === "/api/research") generation.push(request.url()); });
  page.on("request", (request) => { if (new URL(request.url()).pathname === "/api/terms/lookup") termLookups.push(request.postDataJSON()); });
  await context.route("**/*", async (route) => {
    if (new URL(route.request().url()).hostname !== "127.0.0.1") {
      external.push(route.request().url());
      await route.abort();
    } else await route.continue();
  });
  await page.goto("/");
  await connect(page);
  const history = page.getByRole("region", { name: "Financial history", exact: true });

  await test.step("original exact decimals, five-year issuer history and immutable bookmark", async () => {
    await page.getByRole("button", { name: /SYNTHETIC COMPANY SYN/ }).click();
    await page.getByText("Revenue · USD · Annual periods · 5 retained periods", { exact: true }).click();
    await expect(history.getByText("9,007,199,254,740,992 USD", { exact: true })).toBeVisible();
    await expect(page.getByText("Five-year daily price history: unavailable in this snapshot.", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Bookmark this version" }).click();
    await expect(page.getByText("Research version bookmarked.", { exact: true })).toBeVisible();
  });
  const original = page.url();
  await test.step("dashboard navigation keeps the saved version and exact statistics with honest gaps", async () => {
    const navigation = page.getByRole("navigation", { name: "Ticker sections" });
    await navigation.getByRole("button", { name: "Statistics", exact: true }).focus();
    await page.keyboard.press("Enter");
    const statistics = page.getByRole("region", { name: "Key statistics", exact: true });
    await expect(statistics).toBeFocused();
    await expect(statistics.getByText("9,007,199,254,740,992 USD", { exact: true })).toBeVisible();
    await expect(statistics.getByText(/Latest period unavailable/)).toBeVisible();
    await statistics.screenshot({ path: testInfo.outputPath("dashboard-statistics-wide.png") });
    await navigation.getByRole("button", { name: "Overview", exact: true }).click();
    await page.screenshot({ path: testInfo.outputPath("dashboard-overview-wide.png") });
    await navigation.getByRole("button", { name: "Financials", exact: true }).click();
    await history.getByRole("combobox", { name: "Reporting periods" }).selectOption("quarter");
    await expect(history.getByText("Unavailable — no admitted observations for these reporting periods.", { exact: true })).toBeVisible();
    await expect(history.getByRole("img")).toHaveCount(0);
    await history.getByRole("combobox", { name: "Reporting periods" }).selectOption("annual");
    await history.getByText("Revenue · USD · Annual periods · 5 retained periods", { exact: true }).click();
    await expect(history.getByRole("img")).not.toHaveCount(0);
    await navigation.getByRole("button", { name: "Learn about this ticker", exact: true }).click();
    await expect(page.getByRole("region", { name: "Understand a term", exact: true })).toBeFocused();
    await page.getByRole("button", { name: "revenue", exact: true }).focus();
    await expect.poll(() => termLookups.length).toBeGreaterThan(0);
    expect(termLookups.at(-1)?.bundle_id).toBe(new URLSearchParams(new URL(original).hash.split("?")[1]).get("bundle"));
    expect(generation).toHaveLength(0);
    await expect(page).toHaveURL(original);
    await page.setViewportSize({ width: 640, height: 900 });
    await navigation.getByRole("button", { name: "Statistics", exact: true }).click();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(640);
    await statistics.screenshot({ path: testInfo.outputPath("dashboard-statistics-narrow.png") });
    await navigation.getByRole("button", { name: "Analyst insights", exact: true }).click();
    await expect(page.getByText(/no qualified analyst estimates or outlooks/)).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("dashboard-analysts-narrow.png") });
    await page.setViewportSize({ width: 1280, height: 900 });
  });
  await test.step("selected revenue appears while other evidence still awaits review", async () => {
    const review = await research(page, "Synthetic reviewed research");
    await expect(review.getByText(/publication and as-of dates remain unknown/)).toBeVisible();
    await review.screenshot({ path: testInfo.outputPath("review-wide.png") });
    await review.getByRole("checkbox", { name: /\/Revenues\.json$/ }).check();
    await review.getByRole("button", { name: "Use selected sources" }).click();
    await expect(review.getByRole("checkbox", { name: /\/submissions\/CIK0000000001\.json$/ })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Incomplete research — checked sections", exact: true })).toBeVisible();
    await expect(history.getByText("100 USD", { exact: true })).toBeVisible();
    expect(page.url()).not.toBe(original);
    await page.setViewportSize({ width: 640, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(640);
    await review.scrollIntoViewIfNeeded();
    await page.screenshot({ path: testInfo.outputPath("review-narrow.png") });
    const index = review.getByRole("checkbox");
    await index.focus();
    await page.keyboard.press("Space");
    await expect(index).toBeChecked();
    await review.getByRole("button", { name: "Use selected sources" }).click();
    await expect(review.getByRole("checkbox", { name: /\/event\.htm$/ })).toBeVisible();
    await review.getByRole("checkbox").check();
    await review.getByRole("button", { name: "Use selected sources" }).click();
    await expect(page.getByText("Status: completed", { exact: true })).toBeVisible();
    await expect(review).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Incomplete research — checked sections", exact: true })).toHaveCount(0);
  });
  const completed = page.url();
  await test.step("final source drawer keeps original publication, as-of and retrieval dates", async () => {
    await page.getByRole("link", { name: "Open source drawer for 8-K filing", exact: true }).click();
    await expect(page.getByRole("link", { name: "Inspect original source", exact: true })).toHaveAttribute("href", "https://www.sec.gov/Archives/edgar/data/1/000000999926000003/event.htm");
    const drawer = page.locator("details.source-drawer[open]");
    await expect(drawer.getByText("Published: 2026-09-17 · As of: 2026-09-15 · Retrieved: 2026-10-04T00:00:00Z", { exact: true })).toBeVisible();
    await expect(drawer.getByText("Source-use policy: full_text_allowed · Provenance: verified_retrieval", { exact: true })).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("original-citation-narrow.png") });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(640);
    await page.getByRole("link", { name: "Saved research", exact: true }).click();
    const saved = page.getByRole("button", { name: "SYNTHETIC COMPANY", exact: true });
    await saved.focus();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(original);
    await page.getByText("Revenue · USD · Annual periods · 5 retained periods", { exact: true }).click();
    await expect(history.getByText("9,007,199,254,740,992 USD", { exact: true })).toBeVisible();
    expect(original).not.toBe(completed);
  });
  await test.step("skipping sources exposes missing data without inventing evidence", async () => {
    const review = await research(page, "Synthetic skipped research");
    await review.getByRole("button", { name: "Skip these sources" }).click();
    await expect(page.getByText("Status: completed", { exact: true })).toBeVisible();
    await expect(page.getByText("Financial history awaits source review; no financial sources were selected.", { exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "Open source drawer for 8-K filing", exact: true })).toHaveCount(0);
  });
  await test.step("reload observes and cancels the same pending job without replay", async () => {
    const review = await research(page, "Synthetic reconnect research");
    const scope = await review.getByText(/^Asset: /).innerText();
    await page.reload();
    await connect(page);
    await expect(review.getByText(scope, { exact: true })).toBeVisible();
    await expect(review.locator("input:checked")).toHaveCount(0);
    await review.getByRole("button", { name: "Cancel this research" }).click();
    await expect(page.getByText("Status: cancelled", { exact: true })).toBeVisible();
    await expect(review).toHaveCount(0);
    await expect(page.getByText(/This job has stopped. Earlier saved research is unchanged/)).toBeVisible();
  });
  await test.step("private numerical review discloses scope and remains unchecked at narrow width", async () => {
    const headers = { Authorization: "Bearer synthetic-preview-credential-not-for-production" };
    const settings = await (await page.request.get("http://127.0.0.1:18764/api/settings", { headers })).json();
    const saved = await page.request.put("http://127.0.0.1:18764/api/settings", { headers, data: { ...settings, experimental_yahoo_enabled: true } });
    expect(saved.ok()).toBe(true);
    const review = await research(page, "Synthetic private source review");
    await review.getByRole("button", { name: "Skip these sources" }).click();
    await expect(review.getByRole("checkbox")).toHaveCount(2);
    await expect(review.locator("input:checked")).toHaveCount(0);
    await expect(review.getByText(/Private numerical retrieval only/)).toHaveCount(2);
    await expect(review.getByRole("checkbox", { name: /finance\.yahoo\.com\/quote\/SYN\/history/ })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(640);
    await review.screenshot({ path: testInfo.outputPath("private-review-narrow.png") });
    await review.getByRole("button", { name: "Cancel this research" }).click();
    await expect(page.getByText("Status: cancelled", { exact: true })).toBeVisible();
  });
  expect(generation).toHaveLength(4);
  expect(external).toEqual([]);
  expect(failures).toEqual([]);
});
