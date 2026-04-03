import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const markdownRendererSource = readFileSync(
  new URL("./MarkdownRenderer.tsx", import.meta.url),
  "utf8",
);
const packageJsonSource = readFileSync(
  new URL("../../../package.json", import.meta.url),
  "utf8",
);

test("markdown renderer uses react-markdown with github-flavored markdown support", () => {
  assert.match(markdownRendererSource, /from "react-markdown"/);
  assert.match(markdownRendererSource, /from "remark-gfm"/);
  assert.match(markdownRendererSource, /remarkPlugins=\{\[remarkGfm\]\}/);
  assert.match(markdownRendererSource, /skipHtml/);
});

test("markdown renderer no longer injects handwritten html", () => {
  assert.doesNotMatch(markdownRendererSource, /dangerouslySetInnerHTML/);
  assert.doesNotMatch(markdownRendererSource, /const renderMarkdown =/);
});

test("frontend depends on stable markdown rendering libraries", () => {
  assert.match(packageJsonSource, /"react-markdown"\s*:/);
  assert.match(packageJsonSource, /"remark-gfm"\s*:/);
});
