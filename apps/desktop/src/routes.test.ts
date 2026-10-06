import { expect, it } from "vitest";
import { bundleRoute, conversationRoute, routeFromHash, sourceRoute } from "./routes";
it("makes saved evidence versions addressable without credentials", () => {
  expect(routeFromHash("#" + bundleRoute("version 1"))).toEqual({ page: "asset", bundle: "version 1", source: null, conversation: null, comparison: null });
  expect(routeFromHash("#source-123").page).toBe("library");
  expect(routeFromHash("#connections")).toEqual({ page: "connections", bundle: null, source: null, conversation: null, comparison: null });
});
it("keeps a citation tied to its exact evidence version during navigation", () => {
  expect(routeFromHash("#" + sourceRoute("older version", "source/1?&"))).toEqual({ page: "asset", bundle: "older version", source: "source/1?&", conversation: null, comparison: null });
});

it("addresses a conversation separately from its immutable cited responses", () => {
  expect(routeFromHash("#" + conversationRoute("chat/one?&"))).toEqual({ page: "conversations", bundle: null, source: null, conversation: "chat/one?&", comparison: null });
  expect(routeFromHash("#" + bundleRoute("old evidence", "chat/one?&"))).toEqual({ page: "asset", bundle: "old evidence", source: null, conversation: "chat/one?&", comparison: null });
});
