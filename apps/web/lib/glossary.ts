export type GlossaryTerm = {
  term: string;
  category: string;
  definition: string;
  whyItMatters: string;
  beginnerMistake: string;
};

export type GlossaryTermGroup = {
  groupId: string;
  title: string;
  terms: GlossaryTermKey[];
};

export const glossaryTerms = {
  "expense ratio": {
    term: "expense ratio",
    category: "ETF costs",
    definition: "The yearly fund cost shown as a percentage of assets.",
    whyItMatters: "Lower costs leave more of the fund return before other account-level costs.",
    beginnerMistake: "Comparing only cost and ignoring what the fund owns."
  },
  AUM: {
    term: "AUM",
    category: "ETF size",
    definition: "Assets under management, or AUM, is the total money a fund manages for shareholders.",
    whyItMatters: "It can help show the scale of a fund, though size alone does not describe quality or risk.",
    beginnerMistake: "Assuming a larger fund is automatically better for every learning goal."
  },
  "net assets": {
    term: "net assets",
    category: "ETF size",
    definition: "Net assets are the total value managed inside a fund after accounting for its assets and liabilities.",
    whyItMatters: "They help show fund scale and are often displayed as AUM-like context on quote pages.",
    beginnerMistake: "Treating fund size as a standalone quality score."
  },
  "market cap": {
    term: "market cap",
    category: "Company size",
    definition: "Market capitalization is the market value of a company's equity based on its share price and share count.",
    whyItMatters: "It gives a rough sense of company size and how much expectations may already be reflected in the stock.",
    beginnerMistake: "Treating market cap as the same thing as sales, profit, or cash in the bank."
  },
  "P/E ratio": {
    term: "P/E ratio",
    category: "Valuation",
    definition: "The price-to-earnings ratio compares a stock price with earnings per share over a period.",
    whyItMatters: "It is one basic way to compare what investors are paying for current earnings.",
    beginnerMistake: "Reading a low or high P/E as a complete verdict without checking growth, quality, and cyclicality."
  },
  "forward P/E": {
    term: "forward P/E",
    category: "Valuation",
    definition: "Forward P/E compares a stock price with expected earnings per share for a future period.",
    whyItMatters: "It shows how valuation looks using forecasts, which can differ from recent reported earnings.",
    beginnerMistake: "Forgetting that forecasts can be wrong or change quickly."
  },
  "EV/EBITDA": {
    term: "EV/EBITDA",
    category: "Valuation",
    definition: "EV/EBITDA compares enterprise value with earnings before interest, taxes, depreciation, and amortization.",
    whyItMatters: "It can help compare companies with different debt levels or capital structures.",
    beginnerMistake: "Using it as a complete valuation answer without checking cash flow, growth, and industry context."
  },
  "dividend yield": {
    term: "dividend yield",
    category: "Income",
    definition: "Dividend yield compares annual dividends with the current share or fund price.",
    whyItMatters: "It helps explain how much cash distribution the asset has recently offered relative to price.",
    beginnerMistake: "Assuming a high yield is always safer or more attractive without checking why the yield is high."
  },
  revenue: {
    term: "revenue",
    category: "Company fundamentals",
    definition: "Revenue is the money a company brings in from selling products or services before subtracting costs.",
    whyItMatters: "It is the starting point for understanding the scale and direction of a business.",
    beginnerMistake: "Confusing revenue with profit."
  },
  "gross margin": {
    term: "gross margin",
    category: "Company profitability",
    definition: "Gross margin shows the percentage of revenue left after direct costs of making or delivering products.",
    whyItMatters: "It helps explain how much room a company has before operating costs, research, marketing, and financing costs.",
    beginnerMistake: "Comparing gross margins across very different industries as if they should be the same."
  },
  "operating margin": {
    term: "operating margin",
    category: "Company profitability",
    definition: "Operating margin shows the percentage of revenue left after regular operating costs.",
    whyItMatters: "It helps beginners see whether the core business is turning sales into operating profit.",
    beginnerMistake: "Looking at one period without checking whether margins are stable, improving, or weakening."
  },
  EPS: {
    term: "EPS",
    category: "Company profitability",
    definition: "Earnings per share, or EPS, is profit divided across a company's shares.",
    whyItMatters: "It connects company profit to each share and is often used in valuation ratios.",
    beginnerMistake: "Treating EPS growth as complete evidence without checking cash flow and one-time items."
  },
  "free cash flow": {
    term: "free cash flow",
    category: "Company cash generation",
    definition: "Free cash flow is cash from operations after subtracting capital spending needed for the business.",
    whyItMatters: "It helps show how much cash a company may have after funding its operations and investments.",
    beginnerMistake: "Assuming accounting earnings and free cash flow always move together."
  },
  debt: {
    term: "debt",
    category: "Company balance sheet",
    definition: "Debt is borrowed money a company or issuer is expected to repay under agreed terms.",
    whyItMatters: "Debt can support growth, but it can also add pressure when profits fall or rates rise.",
    beginnerMistake: "Treating all debt as bad without comparing it with cash flow, assets, and repayment timing."
  },
  benchmark: {
    term: "benchmark",
    category: "ETF structure",
    definition: "A benchmark is the index or reference point used to compare a fund's performance and exposure.",
    whyItMatters: "It helps explain what the fund is trying to resemble or measure itself against.",
    beginnerMistake: "Assuming two funds with different benchmarks are direct substitutes."
  },
  index: {
    term: "index",
    category: "ETF structure",
    definition: "An index is a published set of securities selected by rules, such as size, sector, or market.",
    whyItMatters: "For index funds, the index helps determine what the fund owns and how concentrated it can be.",
    beginnerMistake: "Assuming every index is broad or diversified just because it is rules-based."
  },
  "index tracking": {
    term: "index tracking",
    category: "ETF structure",
    definition: "A fund tries to follow a published list of securities instead of picking each holding independently.",
    whyItMatters: "It explains why the fund owns what the index owns and why it may not avoid weak areas.",
    beginnerMistake: "Assuming index funds cannot lose value."
  },
  holdings: {
    term: "holdings",
    category: "ETF exposure",
    definition: "Holdings are the securities or assets owned inside a fund.",
    whyItMatters: "They show what the investor is actually exposed to through the fund.",
    beginnerMistake: "Judging a fund only by its name instead of checking what it owns."
  },
  "top 10 concentration": {
    term: "top 10 concentration",
    category: "ETF exposure",
    definition: "Top 10 concentration is the share of a fund represented by its ten largest holdings.",
    whyItMatters: "It helps show whether a fund is spread out or heavily shaped by a small group of holdings.",
    beginnerMistake: "Assuming many holdings always means the largest positions have little influence."
  },
  "sector exposure": {
    term: "sector exposure",
    category: "ETF exposure",
    definition: "Sector exposure shows how much of a fund or company mix is tied to industries such as technology or health care.",
    whyItMatters: "It helps explain why assets may move differently when certain parts of the economy rise or fall.",
    beginnerMistake: "Assuming a fund is broad without checking whether one sector dominates."
  },
  "country exposure": {
    term: "country exposure",
    category: "ETF exposure",
    definition: "Country exposure shows how much of a fund is tied to companies or assets from each country.",
    whyItMatters: "It helps beginners see whether a fund is mostly domestic, international, or mixed.",
    beginnerMistake: "Assuming a global-sounding fund always has balanced exposure across countries."
  },
  "tracking error": {
    term: "tracking error",
    category: "ETF tracking",
    definition: "Tracking error measures how much a fund's returns vary from its benchmark over time.",
    whyItMatters: "It helps show how closely the fund has followed the index or reference point.",
    beginnerMistake: "Expecting an index fund to match its benchmark perfectly every day."
  },
  "tracking difference": {
    term: "tracking difference",
    category: "ETF tracking",
    definition: "Tracking difference is the gap between a fund's return and its benchmark's return over a period.",
    whyItMatters: "It can reflect costs, sampling, cash drag, or operational differences.",
    beginnerMistake: "Confusing a small normal gap with proof that the fund is broken."
  },
  NAV: {
    term: "NAV",
    category: "ETF pricing",
    definition: "Net asset value, or NAV, is the estimated per-share value of a fund's underlying assets.",
    whyItMatters: "It is a reference point for comparing the fund's market price with what it owns.",
    beginnerMistake: "Assuming the market price and NAV are always identical during the trading day."
  },
  "YTD return": {
    term: "YTD return",
    category: "Performance context",
    definition: "Year-to-date return shows performance from the start of the current calendar year through the stated date.",
    whyItMatters: "It gives a recent-period snapshot while staying separate from long-term evidence.",
    beginnerMistake: "Extrapolating a partial-year return as if it predicts the full year."
  },
  beta: {
    term: "beta",
    category: "Risk and volatility",
    definition: "Beta compares how much an asset has tended to move relative to a broad market benchmark.",
    whyItMatters: "It helps beginners separate market sensitivity from company or fund-specific facts.",
    beginnerMistake: "Treating beta as a guarantee of future movement."
  },
  volume: {
    term: "volume",
    category: "Trading context",
    definition: "Volume is the number of shares traded over a stated period.",
    whyItMatters: "It helps show how actively an asset is trading, which can affect execution context.",
    beginnerMistake: "Assuming high volume means the asset is safer or better."
  },
  "average volume": {
    term: "average volume",
    category: "Trading context",
    definition: "Average volume is the typical number of shares traded over a recent measurement window.",
    whyItMatters: "It gives a smoother liquidity reference than a single day's volume.",
    beginnerMistake: "Comparing today's volume without checking the usual trading level."
  },
  "day's range": {
    term: "day's range",
    category: "Trading context",
    definition: "Day's range shows the low and high market prices seen during the current trading day.",
    whyItMatters: "It provides short-term price context without explaining long-term value by itself.",
    beginnerMistake: "Reading an intraday range as a reason to trade."
  },
  "52 week range": {
    term: "52 week range",
    category: "Trading context",
    definition: "The 52 week range shows the lowest and highest prices over roughly the past year.",
    whyItMatters: "It helps place the current price in a recent historical range.",
    beginnerMistake: "Assuming a low point is automatically cheap or a high point is automatically expensive."
  },
  bid: {
    term: "bid",
    category: "Trading context",
    definition: "The bid is the price buyers are currently offering for an asset.",
    whyItMatters: "Together with the ask, it helps explain visible trading depth and spread.",
    beginnerMistake: "Confusing the bid with the last traded price."
  },
  ask: {
    term: "ask",
    category: "Trading context",
    definition: "The ask is the price sellers are currently requesting for an asset.",
    whyItMatters: "Together with the bid, it helps explain visible trading depth and spread.",
    beginnerMistake: "Confusing the ask with the price at which every order will execute."
  },
  yield: {
    term: "yield",
    category: "Income",
    definition: "Yield compares recent or expected distributions with price or net asset value.",
    whyItMatters: "It helps explain the income component of a stock or fund, separate from price changes.",
    beginnerMistake: "Assuming a higher yield is always safer or more attractive."
  },
  "premium/discount": {
    term: "premium/discount",
    category: "ETF pricing",
    definition: "A premium means a fund trades above NAV; a discount means it trades below NAV.",
    whyItMatters: "It helps show whether the market price is above or below the estimated value of the holdings.",
    beginnerMistake: "Ignoring premiums or discounts when looking at funds with less liquid holdings."
  },
  "bid-ask spread": {
    term: "bid-ask spread",
    category: "ETF trading context",
    definition: "The bid-ask spread is the gap between the price buyers offer and sellers ask in the market.",
    whyItMatters: "A wider spread can make entering or exiting a position more costly.",
    beginnerMistake: "Looking only at the expense ratio and missing trading-cost context."
  },
  liquidity: {
    term: "liquidity",
    category: "Trading context",
    definition: "Liquidity describes how easily an asset can be bought or sold without a large price impact.",
    whyItMatters: "It affects how close transaction prices may be to the visible market price.",
    beginnerMistake: "Assuming every popular ticker has the same trading depth at all times."
  },
  rebalancing: {
    term: "rebalancing",
    category: "Portfolio and index mechanics",
    definition: "Rebalancing means adjusting holdings back toward a target mix or index rule set.",
    whyItMatters: "It helps explain why a fund's holdings can change even when its goal stays the same.",
    beginnerMistake: "Assuming a fund's holdings list will stay fixed forever."
  },
  "market risk": {
    term: "market risk",
    category: "Risk",
    definition: "The chance that an asset falls because the broader market or its category falls.",
    whyItMatters: "It helps separate normal price swings from asset-specific problems.",
    beginnerMistake: "Treating familiar companies or broad funds as risk-free."
  },
  "concentration risk": {
    term: "concentration risk",
    category: "Risk",
    definition: "Concentration risk is the risk of relying heavily on one company, sector, country, or small group of holdings.",
    whyItMatters: "It helps explain why fewer dominant exposures can make results more dependent on a narrow set of drivers.",
    beginnerMistake: "Counting the number of holdings without checking how much weight the largest ones carry."
  },
  "credit risk": {
    term: "credit risk",
    category: "Risk",
    definition: "Credit risk is the risk that a borrower or bond issuer does not make promised payments.",
    whyItMatters: "It matters most for bonds, lenders, and funds that hold debt securities.",
    beginnerMistake: "Assuming all income-producing assets carry the same level of repayment risk."
  },
  "interest-rate risk": {
    term: "interest-rate risk",
    category: "Risk",
    definition: "Interest-rate risk is the risk that changes in interest rates affect asset values, especially bonds.",
    whyItMatters: "It helps explain why rate changes can move bond prices and rate-sensitive businesses.",
    beginnerMistake: "Assuming only stocks can fluctuate in value."
  }
} satisfies Record<string, GlossaryTerm>;

export type GlossaryTermKey = keyof typeof glossaryTerms;

export const beginnerGlossaryGroupsByAssetType = {
  stock: [
    {
      groupId: "stock-business-metrics",
      title: "Business and financial metrics",
      terms: ["market cap", "revenue", "operating margin", "EPS", "free cash flow", "debt", "volume", "average volume"]
    },
    {
      groupId: "stock-valuation-risk",
      title: "Valuation and risk",
      terms: ["P/E ratio", "forward P/E", "EV/EBITDA", "beta", "yield", "day's range", "52 week range", "bid", "ask", "market risk", "concentration risk"]
    }
  ],
  etf: [
    {
      groupId: "etf-fund-basics",
      title: "Fund basics",
      terms: ["expense ratio", "AUM", "benchmark", "index", "holdings", "net assets", "yield", "YTD return"]
    },
    {
      groupId: "etf-exposure-risk",
      title: "Exposure and risk",
      terms: ["top 10 concentration", "sector exposure", "country exposure", "concentration risk"]
    },
    {
      groupId: "etf-trading-tracking",
      title: "Trading and tracking",
      terms: ["bid-ask spread", "premium/discount", "NAV", "liquidity", "tracking error", "tracking difference", "bid", "ask", "volume", "average volume", "day's range", "52 week range", "beta"]
    }
  ]
} satisfies Record<"stock" | "etf", GlossaryTermGroup[]>;

export function getGlossaryTerm(term: string): GlossaryTerm | undefined {
  return glossaryTerms[term as GlossaryTermKey];
}
