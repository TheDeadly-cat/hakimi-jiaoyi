"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
const css = fs.readFileSync(
  path.join(__dirname, "strategy_correlation_cluster_ticket_policy_v1.css"),
  "utf8"
);

function policyMarkup() {
  const start = policyStartIndex();
  const end = html.indexOf("</details>", start);
  assert.notEqual(end, -1);
  return html.slice(start, end + "</details>".length);
}

function policyStartIndex() {
  const match = /<details\b[^>]*\bid="strategyClusterTicketPolicyV1"[^>]*>/.exec(html);
  assert.ok(match);
  return match.index;
}

test("policy drawer is linked once and nested in the existing correlation ledger", () => {
  const link = "strategy_correlation_cluster_ticket_policy_v1.css?v=20260825-cluster-ticket-policy-a11y-2";
  assert.equal(html.split(link).length - 1, 1);
  const ledgerStart = html.indexOf('<section class="strategy-correlation-ledger"');
  const ledgerEnd = html.indexOf("</section>", ledgerStart);
  const policyStart = policyStartIndex();
  assert.ok(ledgerStart >= 0 && policyStart > ledgerStart && policyStart < ledgerEnd);
  assert.match(policyMarkup(), /^<details[^>]* open>/);
});

test("native disclosure and diagram expose stable accessible relationships", () => {
  const markup = policyMarkup();
  assert.match(markup, /<details id="strategyClusterTicketPolicyV1"/);
  assert.match(
    markup,
    /<summary[^>]*aria-controls="strategyClusterTicketPolicyBodyV1"[^>]*aria-describedby="strategyClusterTicketPolicyBoundaryV1"/
  );
  assert.match(markup, /<div id="strategyClusterTicketPolicyBodyV1"/);
  assert.match(
    markup,
    /class="strategy-cluster-ticket-policy-v1__diagram" role="img" aria-label="同一相关簇内两个标的折叠为一张结构票"/
  );
  assert.match(markup, /<p id="strategyClusterTicketPolicyBoundaryV1">/);
  assert.doesNotMatch(markup, /aria-expanded=/);
});

test("governance stages preserve SOURCE GAP MATURITY PERMISSION order", () => {
  const markup = policyMarkup();
  const stages = ["SOURCE", "GAP", "MATURITY", "PERMISSION"];
  const positions = stages.map((stage) => markup.indexOf(`>${stage}<`));
  assert.equal(positions.every((position) => position >= 0), true);
  assert.equal(
    positions.every((position, index) => index === 0 || position > positions[index - 1]),
    true
  );
  assert.match(markup, /fresh 投影证据未完成/);
  assert.match(markup, /<strong>未授权<\/strong>/);
  assert.doesNotMatch(markup, /\bREADY\b/i);
});

test("ticket diagram teaches cluster collapse without presenting a live result", () => {
  const markup = policyMarkup();
  assert.match(markup, /同簇多标的只计 1 张结构票/);
  assert.match(markup, /标的甲/);
  assert.match(markup, /标的乙/);
  assert.match(markup, /STRUCTURAL TICKET/);
  assert.match(markup, /策略规则说明 · 非实时结果/);
  assert.match(markup, /不产生预算、仓位、信号、订单或盈利结论/);
});

test("isolated CSS carries the rail palette, ticket signature, and keyboard focus", () => {
  assert.match(css, /\.strategy-cluster-ticket-policy-v1\s*\{/);
  assert.match(css, /--ticket-tide:\s*#0d6670/);
  assert.match(css, /--ticket-rust:\s*#b34e34/);
  assert.match(css, /__ticket/);
  assert.match(css, /clip-path:\s*polygon/);
  assert.match(css, /summary:focus-visible/);
  assert.doesNotMatch(css, /(^|\n)\s*(?:body|html|:root)\s*\{/);
});

test("policy microcopy uses a readable utility scale and forced-color fallback", () => {
  assert.match(
    css,
    /summary small\s*\{[\s\S]*?font:\s*600 11px\/1\.35/
  );
  assert.match(css, /__ticket small\s*\{[\s\S]*?font-size:\s*10px/);
  assert.match(css, /__stages strong\s*\{[\s\S]*?font-size:\s*11px/);
  assert.match(css, /__body > p\s*\{[\s\S]*?font:\s*600 12px\/1\.6/);
  assert.match(css, /forced-colors:\s*active/);
  assert.match(css, /clip-path:\s*none/);
});

test("responsive and reduced-motion contracts are explicit", () => {
  assert.match(css, /prefers-reduced-motion:\s*reduce/);
  assert.match(css, /max-width:\s*720px/);
  assert.match(css, /max-width:\s*430px/);
  assert.match(css, /grid-template-columns:\s*1fr/);
});

test("protected production scripts retain their original load identities", () => {
  assert.match(
    html,
    /evidence_presentation\.js\?v=20260821-correlation-multiplicity-ledger-1/
  );
  assert.match(html, /app\.js\?v=20260821-correlation-multiplicity-ledger-1/);
  assert.doesNotMatch(policyMarkup(), /<script\b/i);
});
