"use client";

import { useId, useState } from "react";
import { getGlossaryTerm } from "../lib/glossary";

type GlossaryPopoverProps = {
  term: string;
};

export function GlossaryPopover({ term }: GlossaryPopoverProps) {
  const [open, setOpen] = useState(false);
  const entry = getGlossaryTerm(term);
  const componentId = useId().replace(/[^a-z0-9]+/gi, "-");
  const termId = term.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "") || "unavailable";
  const safeId = `glossary-${termId}-${componentId}`;

  return (
    <span className="glossary-wrap" data-glossary-term={term} data-glossary-available={entry ? "true" : "false"}>
      <button
        className="glossary-trigger"
        type="button"
        aria-expanded={open}
        aria-controls={safeId}
        aria-label={`Open glossary definition for ${entry?.term ?? term}`}
        onClick={() => setOpen((current) => !current)}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            setOpen(false);
          }
        }}
      >
        {entry?.term ?? term}
      </button>
      {open ? (
        <span
          className="glossary-popover"
          id={safeId}
          role="dialog"
          aria-label={`Glossary card for ${entry?.term ?? term}`}
          data-glossary-term={entry?.term ?? term}
          data-glossary-category={entry?.category ?? "unavailable"}
        >
          {entry ? (
            <>
              <span className="glossary-category" data-glossary-category={entry.category}>
                {entry.category}
              </span>
              <strong data-glossary-definition>{entry.definition}</strong>
              <span data-glossary-why-it-matters>{entry.whyItMatters}</span>
              <small data-glossary-beginner-mistake>{entry.beginnerMistake}</small>
            </>
          ) : (
            <>
              <span className="glossary-category" data-glossary-category="unavailable">
                Unavailable
              </span>
              <strong data-glossary-definition>Definition unavailable for this glossary term.</strong>
              <span data-glossary-why-it-matters>No local glossary entry is available.</span>
              <small data-glossary-beginner-mistake>No beginner mistake is shown without a curated entry.</small>
            </>
          )}
        </span>
      ) : null}
    </span>
  );
}
