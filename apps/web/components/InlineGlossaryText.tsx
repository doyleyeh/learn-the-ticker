import { type AssetGlossaryContext } from "../lib/assetGlossary";
import { type GlossaryTermKey } from "../lib/glossary";
import { GlossaryPopover } from "./GlossaryPopover";

export type InlineGlossaryMatch = GlossaryTermKey | { match: string; term: GlossaryTermKey };
export type InlineGlossaryContextMap = ReadonlyMap<GlossaryTermKey, AssetGlossaryContext>;

type InlineGlossaryTextProps = {
  text: string;
  matches: readonly InlineGlossaryMatch[];
  contexts?: InlineGlossaryContextMap | null;
  sourceSection: string;
};

type InlineGlossarySegment =
  | {
      kind: "text";
      text: string;
    }
  | {
      kind: "term";
      text: string;
      term: GlossaryTermKey;
    };

export function InlineGlossaryText({ text, matches, contexts, sourceSection }: InlineGlossaryTextProps) {
  const segments = buildInlineGlossarySegments(text, matches);
  const glossaryTermCount = segments.filter((segment) => segment.kind === "term").length;

  return (
    <span
      className="glossary-inline-text"
      data-glossary-inline-region
      data-glossary-inline-source-section={sourceSection}
      data-glossary-inline-term-count={glossaryTermCount}
    >
      {segments.map((segment, index) =>
        segment.kind === "term" ? (
          <GlossaryPopover
            key={`${segment.term}-${index}`}
            term={segment.term}
            label={segment.text}
            placement="inline"
            sourceSection={sourceSection}
            assetContext={contexts?.get(segment.term)}
          />
        ) : (
          <span key={`text-${index}`}>{segment.text}</span>
        )
      )}
    </span>
  );
}

function buildInlineGlossarySegments(text: string, matches: readonly InlineGlossaryMatch[]): InlineGlossarySegment[] {
  const normalizedMatches = normalizeMatches(matches);

  if (!text || !normalizedMatches.length) {
    return [{ kind: "text", text }];
  }

  const pattern = new RegExp(normalizedMatches.map((match) => escapeRegExp(match.match)).join("|"), "gi");
  const matchByLowerCase = new Map(normalizedMatches.map((match) => [match.match.toLowerCase(), match.term]));
  const segments: InlineGlossarySegment[] = [];
  let lastIndex = 0;

  for (const match of text.matchAll(pattern)) {
    const matchedText = match[0];
    const index = match.index ?? 0;

    if (index < lastIndex || !hasTermBoundary(text, index, matchedText.length)) {
      continue;
    }

    const term = matchByLowerCase.get(matchedText.toLowerCase());
    if (!term) {
      continue;
    }

    if (index > lastIndex) {
      segments.push({ kind: "text", text: text.slice(lastIndex, index) });
    }
    segments.push({ kind: "term", text: matchedText, term });
    lastIndex = index + matchedText.length;
  }

  if (lastIndex < text.length) {
    segments.push({ kind: "text", text: text.slice(lastIndex) });
  }

  return segments.length ? segments : [{ kind: "text", text }];
}

function normalizeMatches(matches: readonly InlineGlossaryMatch[]) {
  const matchByLowerCase = new Map<string, { match: string; term: GlossaryTermKey }>();

  for (const item of matches) {
    const match = typeof item === "string" ? item : item.match;
    const term = typeof item === "string" ? item : item.term;
    const normalizedMatch = match.trim();

    if (!normalizedMatch) {
      continue;
    }

    const key = normalizedMatch.toLowerCase();
    if (!matchByLowerCase.has(key)) {
      matchByLowerCase.set(key, { match: normalizedMatch, term });
    }
  }

  return [...matchByLowerCase.values()].sort((left, right) => right.match.length - left.match.length);
}

function hasTermBoundary(text: string, index: number, length: number) {
  const before = index > 0 ? text[index - 1] : "";
  const after = index + length < text.length ? text[index + length] : "";
  return !isWordCharacter(before) && !isWordCharacter(after);
}

function isWordCharacter(value: string) {
  return /^[A-Za-z0-9]$/.test(value);
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
