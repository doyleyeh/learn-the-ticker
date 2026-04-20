export type GlossaryTerm = {
  term: string;
  definition: string;
  whyItMatters: string;
  beginnerMistake: string;
};

export const glossaryTerms: Record<string, GlossaryTerm> = {
  "expense ratio": {
    term: "expense ratio",
    definition: "The yearly fund cost shown as a percentage of assets.",
    whyItMatters: "Lower costs leave more of the fund return for investors before personal taxes or fees elsewhere.",
    beginnerMistake: "Comparing only cost and ignoring what the fund owns."
  },
  "index tracking": {
    term: "index tracking",
    definition: "A fund tries to follow a published list of securities instead of picking each holding independently.",
    whyItMatters: "It explains why the fund owns what the index owns and why it may not avoid weak areas.",
    beginnerMistake: "Assuming index funds cannot lose value."
  },
  "market risk": {
    term: "market risk",
    definition: "The chance that an asset falls because the broader market or its category falls.",
    whyItMatters: "It helps separate normal price swings from asset-specific problems.",
    beginnerMistake: "Treating familiar companies or broad funds as risk-free."
  }
};
