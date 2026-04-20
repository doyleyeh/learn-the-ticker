"use client";

import { useState } from "react";
import { glossaryTerms } from "../lib/glossary";

type GlossaryPopoverProps = {
  term: keyof typeof glossaryTerms;
};

export function GlossaryPopover({ term }: GlossaryPopoverProps) {
  const [open, setOpen] = useState(false);
  const entry = glossaryTerms[term];

  return (
    <span className="glossary-wrap">
      <button
        className="glossary-trigger"
        type="button"
        aria-expanded={open}
        aria-controls={`glossary-${term.replaceAll(" ", "-")}`}
        onClick={() => setOpen((current) => !current)}
      >
        {entry.term}
      </button>
      {open ? (
        <span className="glossary-popover" id={`glossary-${term.replaceAll(" ", "-")}`} role="dialog">
          <strong>{entry.definition}</strong>
          <span>{entry.whyItMatters}</span>
          <small>{entry.beginnerMistake}</small>
        </span>
      ) : null}
    </span>
  );
}
