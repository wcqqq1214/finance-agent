import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./page.tsx", import.meta.url), "utf8");

test("home page lifts selected stock quote state and passes it to chart and selector", () => {
  assert.match(source, /selectedStockQuote/);
  assert.match(source, /onSelectedStockQuoteChange=\{setSelectedStockQuote\}/);
  assert.match(source, /liveQuote=\{selectedStockQuote\}/);
});
