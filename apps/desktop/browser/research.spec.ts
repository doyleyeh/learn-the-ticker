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
  await test.step("saved availability is separate from original source age", async () => {
    await expect(page.locator(".snapshot-status")).toContainText("Availability when saved:");
    const freshness = page.getByRole("region", { name: "Evidence freshness", exact: true });
    await expect(freshness).toContainText("from saved dates only. No new source retrieval.");
    await expect(freshness).toContainText("0 within source age limits.");
    await freshness.screenshot({ path: testInfo.outputPath("freshness-wide.png") });
    await page.setViewportSize({ width: 640, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(640);
    await freshness.screenshot({ path: testInfo.outputPath("freshness-narrow.png") });
    await page.getByRole("navigation", { name: "Ticker sections" }).getByRole("button", { name: "Sources", exact: true }).focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("region", { name: "Sources and evidence", exact: true })).toBeFocused();
    await expect(page.locator('[data-source-age="stale"]').first()).toContainText("Historical evidence remains available");
    await page.setViewportSize({ width: 1280, height: 900 });
  });
  await test.step("dashboard navigation keeps the saved version and exact statistics with honest gaps", async () => {
    const navigation = page.getByRole("navigation", { name: "Ticker sections" });
    await navigation.getByRole("button", { name: "Statistics", exact: true }).focus();
    await page.keyboard.press("Enter");
    const statistics = page.getByRole("region", { name: "Key statistics", exact: true });
    await expect(statistics).toBeFocused();
    await expect(statistics.getByText("9,007,199,254,740,992 USD", { exact: true })).toBeVisible();
    await expect(statistics.getByText(/Latest period unavailable/)).toBeVisible();
    const ratios = statistics.getByRole("region", { name: "Calculated financial statistics" });
    const aligned = ratios.locator("details").filter({ has: page.locator("summary", { hasText: "2024-01-01 through 2024-12-31" }) });
    await aligned.locator("summary").focus();
    await page.keyboard.press("Enter");
    await expect(aligned.getByText("100%", { exact: true })).toBeVisible();
    const citations = aligned.getByRole("link", { name: /Open source drawer for SEC issuer observations:/ });
    await expect(citations).toHaveCount(2);
    const ratioVersion = new URLSearchParams(new URL(original).hash.split("?")[1]).get("bundle");
    for (const citation of await citations.all()) {
      expect(new URLSearchParams((await citation.getAttribute("href"))!.split("?")[1]).get("bundle")).toBe(ratioVersion);
    }
    await expect(aligned.getByText(/Filed 2025-02-01/)).toHaveCount(2);
    const conflicted = ratios.locator("details").filter({ has: page.locator("summary", { hasText: "2025-01-01 through 2025-12-31" }) });
    await conflicted.locator("summary").click();
    await expect(conflicted.getByText("The latest filing versions contain conflicting inputs.", { exact: true })).toBeVisible();
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
    await ratios.screenshot({ path: testInfo.outputPath("financial-ratios-narrow.png") });
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
    await page.getByRole("navigation", { name: "Primary navigation" }).getByRole("link", { name: "Connections", exact: true }).click();
    const optIn = page.getByRole("checkbox", { name: "Enable experimental private Yahoo history", exact: true });
    await expect(optIn).not.toBeChecked();
    await optIn.click();
    await expect(optIn).toBeChecked();
    const review = await research(page, "Synthetic private source review");
    await review.getByRole("button", { name: "Skip these sources" }).click();
    await expect(review.getByRole("checkbox")).toHaveCount(3);
    await expect(review.locator("input:checked")).toHaveCount(0);
    await expect(review.getByText(/Numerical evidence for personal learning/)).toHaveCount(3);
    await expect(review.getByRole("checkbox", { name: /finance\.yahoo\.com\/quote\/SYN\/history/ })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(640);
    await review.screenshot({ path: testInfo.outputPath("private-review-narrow.png") });
    await review.getByRole("checkbox", { name: /finance\.yahoo\.com\/quote\/SYN\/history/ }).check();
    await review.getByRole("checkbox", { name: /finance\.yahoo\.com\/quote\/SYN\/key-statistics/ }).check();
    await review.getByRole("button", { name: "Use selected sources" }).click();
    await expect(page.getByText("Status: completed", { exact: true })).toBeVisible();
  });
  const privateVersion = page.url();
  await test.step("saved private chart, exact values and calculations keep their original evidence", async () => {
    await page.getByRole("navigation", { name: "Ticker sections" }).getByRole("button", { name: "Charts & returns", exact: true }).click();
    const market = page.locator(".market-history");
    await expect(market.getByRole("img", { name: /Retained daily closing prices/ })).toBeVisible();
    await expect(market.getByText("27.272727%", { exact: true })).toBeVisible();
    await expect(market.getByText("40%", { exact: true })).toBeVisible();
    await expect(market.getByText(/No observation at or before the required start boundary/)).toHaveCount(4);
    const quote = market.getByRole("region", { name: "Retained daily quote fields" });
    await expect(quote.getByRole("heading", { name: "Daily snapshot · 2026-01-05" })).toBeVisible();
    await expect(quote.getByText("10–15 USD", { exact: true })).toBeVisible();
    await expect(quote.getByText(/may not be the previous trading session/)).toBeVisible();
    await quote.screenshot({ path: testInfo.outputPath("daily-quote-narrow.png") });
    await quote.locator("dd").first().evaluate((node) => {
      const range = document.createRange(); range.selectNodeContents(node);
      const selection = window.getSelection()!; selection.removeAllRanges(); selection.addRange(range);
      node.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
    });
    await expect(page.locator(".term-selection-bar")).toBeVisible();
    await page.getByRole("button", { name: "Dismiss term selection" }).click();
    await market.getByRole("combobox", { name: "Chart period" }).selectOption("1m");
    await expect(market.getByText(/2 retained daily observations/)).toBeVisible();
    await market.getByText("Exact daily values (2)", { exact: true }).click();
    await expect(market.getByRole("cell", { name: "9,007,199,254,740,993", exact: true })).toBeVisible();
    await market.getByText("Retained corporate actions (2)", { exact: true }).click();
    await expect(market.getByText(/0.123456789012345678 USD/)).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(640);
    await market.screenshot({ path: testInfo.outputPath("private-history-narrow.png") });
    await page.setViewportSize({ width: 1280, height: 900 });
    await market.screenshot({ path: testInfo.outputPath("private-history-wide.png") });
    await market.locator(".market-close").evaluate((node) => {
      const range = document.createRange(); range.selectNodeContents(node);
      const selection = window.getSelection()!; selection.removeAllRanges(); selection.addRange(range);
      node.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
    });
    await expect(page.locator(".term-selection-bar")).toBeVisible();
    await page.getByRole("button", { name: "Dismiss term selection" }).click();
    await page.getByRole("heading", { name: "Basic listing information", exact: true }).evaluate((node) => {
      const range = document.createRange(); range.selectNodeContents(node);
      const selection = window.getSelection()!; selection.removeAllRanges(); selection.addRange(range);
      node.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
    });
    await expect(page.locator(".term-selection-bar")).toBeVisible();
    await page.getByRole("button", { name: "Dismiss term selection" }).click();
    await page.locator(".market-close").evaluate((node) => {
      const range = document.createRange();
      range.setStart(document.querySelector("#ticker-overview h3")!.firstChild!, 0);
      range.setEndAfter(node);
      const selection = window.getSelection()!; selection.removeAllRanges(); selection.addRange(range);
      node.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
    });
    await expect(page.locator(".term-selection-bar")).toHaveCount(0);
    await page.getByRole("textbox", { name: "Term to explain" }).fill("Daily close");
    await page.getByRole("button", { name: "Explain term", exact: true }).click();
    await expect(page.locator(".term-result").getByText("The retained daily close is 14 USD. It is a historical observation, not a live quote.")).toBeVisible();
    await page.locator(".term-result").screenshot({ path: testInfo.outputPath("yahoo-cloud-learning.png") });
    await page.locator(".term-result").getByRole("link", { name: /Open source drawer/ }).click();
    const drawer = page.locator("details.source-drawer[open]");
    await expect(drawer.getByRole("link", { name: "Inspect original source" })).toHaveAttribute("href", "https://finance.yahoo.com/quote/SYN/history/");
    await expect(drawer.getByText(/As of: 2026-01-05 · Retrieved: 2026-10-04T00:00:00Z/)).toBeVisible();
    expect(new URLSearchParams(new URL(page.url()).hash.split("?")[1]).get("bundle")).toBe(new URLSearchParams(new URL(privateVersion).hash.split("?")[1]).get("bundle"));
    await page.reload(); await connect(page);
    await expect(page.locator(".market-history").getByText("27.272727%", { exact: true })).toBeVisible();
  });
  await test.step("supplied valuations preserve original dates, gaps, cloud selection and citations", async () => {
    await page.getByRole("navigation", { name: "Ticker sections" }).getByRole("button", { name: "Statistics", exact: true }).click();
    const valuation = page.locator(".provider-valuations");
    await expect(valuation.getByText("29.5 ×As of 2026-01-05", { exact: true })).toBeVisible();
    await expect(valuation.getByRole("cell", { name: "28.123456789012345678 ×", exact: true })).toBeVisible();
    await expect(valuation.getByRole("cell", { name: "Unavailable — source value missing.", exact: true })).toBeVisible();
    await valuation.getByText("Valuation definitions and limitations", { exact: true }).focus();
    await page.keyboard.press("Enter");
    await expect(valuation.getByText(/not proven point-in-time records/)).toBeVisible();
    await valuation.getByRole("combobox", { name: "Valuation metric", exact: true }).selectOption("MarketCap");
    await valuation.getByRole("combobox", { name: "Valuation sampling", exact: true }).selectOption("annual");
    await expect(valuation.getByRole("cell", { name: "9,007,199,254,740,993 USD", exact: true })).toBeVisible();
    await valuation.screenshot({ path: testInfo.outputPath("valuations-wide.png") });
    await page.setViewportSize({ width: 640, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(640);
    await valuation.screenshot({ path: testInfo.outputPath("valuations-narrow.png") });
    await valuation.locator("td").first().evaluate((node) => {
      const range = document.createRange(); range.selectNodeContents(node);
      const selection = window.getSelection()!; selection.removeAllRanges(); selection.addRange(range);
      node.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
    });
    await expect(page.locator(".term-selection-bar")).toBeVisible();
    await page.getByRole("button", { name: "Dismiss term selection" }).click();
    await valuation.getByRole("link", { name: /Open source drawer/ }).click();
    const sourceId = new URLSearchParams(new URL(page.url()).hash.split("?")[1]).get("source");
    const drawer = page.locator(`details.source-drawer[id="source-${sourceId}"][open]`);
    await expect(drawer.getByRole("link", { name: "Inspect original source" })).toHaveAttribute("href", "https://finance.yahoo.com/quote/SYN/key-statistics/");
    expect(new URLSearchParams(new URL(page.url()).hash.split("?")[1]).get("bundle")).toBe(new URLSearchParams(new URL(privateVersion).hash.split("?")[1]).get("bundle"));
    await page.reload(); await connect(page);
    await expect(page.locator(".provider-valuations").getByText("29.5 ×As of 2026-01-05", { exact: true })).toBeVisible();
  });
  await test.step("revoking private mode stops a pending research and preserves saved history", async () => {
    await research(page, "Synthetic private opt-out");
    await page.getByRole("navigation", { name: "Primary navigation" }).getByRole("link", { name: "Connections", exact: true }).click();
    const optIn = page.getByRole("checkbox", { name: "Enable experimental private Yahoo history", exact: true });
    await expect(optIn).toBeChecked();
    await optIn.click();
    await expect(optIn).not.toBeChecked();
    await expect(page.getByText("Status: cancelled", { exact: true })).toBeVisible();
    await page.getByRole("checkbox", { name: "Allow cloud research", exact: true }).click();
    await expect(page.getByRole("checkbox", { name: "Allow cloud research", exact: true })).not.toBeChecked();
    await page.goto(privateVersion);
    await expect(page.locator(".market-history").getByText("27.272727%", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Open cached research", exact: true })).toBeVisible();
  });
  expect(generation).toHaveLength(5);
  await test.step("failed age reads keep saved evidence and citations available offline", async () => {
    await page.route("**/api/bundles/*/freshness", (route) => route.abort());
    await page.reload(); await connect(page);
    await expect(page.getByRole("region", { name: "Evidence freshness", exact: true })).toContainText("Source-age assessment unavailable. Original saved evidence remains readable.");
    await expect(page.locator(".market-history").getByText("27.272727%", { exact: true })).toBeVisible();
    await page.locator(".market-history").getByRole("link", { name: /Open source drawer/ }).click();
    await expect(page.locator("details.source-drawer[open]").getByRole("link", { name: "Inspect original source" })).toHaveAttribute("href", "https://finance.yahoo.com/quote/SYN/history/");
    expect(generation).toHaveLength(5);
  });
  expect(external).toEqual([]);
  expect(failures).toEqual([]);
});

test("fund and unresolved asset sections retain citations, risk controls and applicability states", async ({ page, context }, testInfo) => {
  const generation: string[] = [], failures: string[] = [], external: string[] = [];
  page.on("pageerror", (error) => failures.push(error.message));
  page.on("request", (request) => { if (request.method() === "POST" && new URL(request.url()).pathname === "/api/research") generation.push(request.url()); });
  await context.route("**/*", async (route) => {
    if (new URL(route.request().url()).hostname !== "127.0.0.1") { external.push(route.request().url()); await route.abort(); }
    else await route.continue();
  });
  await page.goto("/"); await connect(page);
  await page.getByRole("button", { name: /Synthetic fund parity SYN-FUND/ }).click();
  const original = page.url();
  const overview = page.getByRole("region", { name: "Ticker overview", exact: true });
  for (const name of ["Fund objective and role", "Holdings and exposures", "Fund construction", "Costs and trading context"]) {
    await expect(overview.getByRole("heading", { name, exact: true })).toBeVisible();
  }
  await expect(overview.getByText("The synthetic basket has changing exposures.", { exact: true })).toBeVisible();
  await expect(overview.getByRole("heading", { name: "Products and services", exact: true })).toHaveCount(0);
  await expect(overview.getByText("Synthetic risk delta remains uncertain.", { exact: true })).toHaveCount(0);
  await overview.getByRole("button", { name: "Show 1 more risks", exact: true }).focus();
  await page.keyboard.press("Enter");
  await expect(overview.getByText("Synthetic risk delta remains uncertain.", { exact: true })).toBeVisible();
  await overview.screenshot({ path: testInfo.outputPath("fund-overview-wide.png") });
  const news = page.getByRole("region", { name: "Ticker news and context", exact: true });
  await page.getByRole("navigation", { name: "Ticker sections" }).getByRole("button", { name: "News & context", exact: true }).click();
  await expect(news.getByText("The synthetic fund reported a portfolio-method update.", { exact: true })).toBeVisible();
  await expect(overview.getByText("The synthetic fund reported a portfolio-method update.", { exact: true })).toHaveCount(0);
  await news.getByRole("link", { name: "Open source drawer for Synthetic fund disclosure", exact: true }).focus();
  await page.keyboard.press("Enter");
  const drawer = page.locator("details.source-drawer[open]");
  await expect(drawer.getByText(/Published: Unknown · As of: Unknown/)).toBeVisible();
  expect(new URLSearchParams(new URL(page.url()).hash.split("?")[1]).get("bundle")).toBe(new URLSearchParams(new URL(original).hash.split("?")[1]).get("bundle"));
  await page.setViewportSize({ width: 640, height: 900 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(640);
  await expect(page.locator('[data-source-age="unknown"]').first()).toContainText("publication and as-of dates are missing");
  await page.getByRole("navigation", { name: "Ticker sections" }).getByRole("button", { name: "Statistics", exact: true }).click();
  await expect(page.getByText("Not applicable — individual-stock valuation metrics are not used for this asset type.", { exact: true })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("fund-applicability-narrow.png") });
  await page.getByRole("navigation", { name: "Ticker sections" }).getByRole("button", { name: "Overview", exact: true }).click();
  await overview.getByRole("button", { name: "Show fewer risks", exact: true }).click();
  await expect(overview.getByText("Synthetic risk delta remains uncertain.", { exact: true })).toHaveCount(0);
  await overview.screenshot({ path: testInfo.outputPath("fund-overview-narrow.png") });
  await page.getByRole("navigation", { name: "Primary navigation" }).getByRole("link", { name: "Library", exact: true }).click();
  await page.getByRole("button", { name: /Synthetic unknown parity SYN-UNKNOWN/ }).click();
  await expect(overview.getByText("Asset type is unconfirmed. Type-dependent sections are unavailable until identity is resolved.", { exact: true })).toBeVisible();
  await expect(overview.getByRole("heading", { name: "Holdings and exposures", exact: true })).toHaveCount(0);
  await expect(overview.getByText("The synthetic basket has changing exposures.", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Unknown applicability — confirm the asset type before using stock valuation metrics.", { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(640);
  await overview.screenshot({ path: testInfo.outputPath("unknown-overview-narrow.png") });
  expect(generation).toEqual([]); expect(external).toEqual([]); expect(failures).toEqual([]);
});
