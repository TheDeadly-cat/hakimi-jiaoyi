"use strict";

// Keep this list identical to the mandatory jobs in research-contracts.yml.
// Unknown or missing jobs are an error: adding a domain must update the gate.
const REQUIRED_JOBS = Object.freeze([
  "python-contracts",
  "deterministic-references",
  "legacy-reference-replay",
  "mvp-contracts",
  "electron-capability-contract",
  "market-data-renderer",
  "package-install-smoke",
]);

function evaluateRequiredJobs(needs) {
  if (!needs || typeof needs !== "object" || Array.isArray(needs)) {
    return { success: false, errors: ["needs must be a job-result object"] };
  }
  const errors = [];
  for (const job of REQUIRED_JOBS) {
    if (!Object.prototype.hasOwnProperty.call(needs, job)) {
      errors.push(`${job}: missing`);
    } else if (!needs[job] || needs[job].result !== "success") {
      errors.push(`${job}: ${String(needs[job]?.result ?? "invalid")}`);
    }
  }
  for (const job of Object.keys(needs)) {
    if (!REQUIRED_JOBS.includes(job)) errors.push(`${job}: unexpected job`);
  }
  return { success: errors.length === 0, errors };
}

function main(serializedNeeds) {
  let needs;
  try {
    needs = JSON.parse(serializedNeeds);
  } catch {
    console.error("Required research checks failed: invalid needs JSON");
    return 1;
  }
  const verdict = evaluateRequiredJobs(needs);
  if (!verdict.success) {
    console.error(`Required research checks failed:\n${verdict.errors.join("\n")}`);
    return 1;
  }
  console.log(`All ${REQUIRED_JOBS.length} required research checks succeeded.`);
  return 0;
}

if (require.main === module) process.exitCode = main(process.env.RESEARCH_CI_NEEDS);
module.exports = { REQUIRED_JOBS, evaluateRequiredJobs, main };
