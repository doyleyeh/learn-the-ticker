import { expect, it } from "vitest";
import { bundleRoute, routeFromHash, sourceRoute } from "./routes";
it("makes saved evidence versions addressable without credentials", () => {
  expect(routeFromHash("#" + bundleRoute("version 1"))).toEqual({ page: "asset", bundle: "version 1", source: null });
  expect(routeFromHash("#source-123").page).toBe("library");
  expect(routeFromHash("#connections")).toEqual({ page: "connections", bundle: null, source: null });
});
it("keeps a citation tied to its exact evidence version during navigation", () => {
  expect(routeFromHash("#" + sourceRoute("older version", "source/1?&"))).toEqual({ page: "asset", bundle: "older version", source: "source/1?&" });
});
