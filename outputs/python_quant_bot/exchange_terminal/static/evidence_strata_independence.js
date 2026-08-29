(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  if (root) {
    root.HakimiStrataIndependence = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const SCHEMA =
    "strategy-correlation-preregistered-strata-public-summary-v1";
  const FINGERPRINT =
    "20260821-preregistered-strata-independence-ledger-1";
  const GAP_LABELS = Object.freeze({
    UNKNOWN: "Evidence unavailable",
    GATE_EVIDENCE_NOT_SUPPLIED: "Gate evidence not supplied",
    BASE_COMPLETE_LINK_BLOCK_OBSERVED: "Base topology block observed",
    PARENT_STRATUM_CONCENTRATION_OBSERVED:
      "Parent-stratum concentration observed",
    INDEPENDENCE_REQUIREMENTS_OBSERVED:
      "Independence requirements observed",
  });

  function isRecord(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function countOrNull(value) {
    return Number.isInteger(value) && value >= 0 ? value : null;
  }

  function numberOrNull(value) {
    return typeof value === "number" && Number.isFinite(value) && value >= 0
      ? value
      : null;
  }

  function displayCount(value) {
    return value === null ? "Unknown" : String(value);
  }

  function presentStrataIndependence(payload) {
    const validRoot =
      isRecord(payload) &&
      payload.schema_version === SCHEMA &&
      payload.static_fingerprint === FINGERPRINT;
    const source = validRoot && isRecord(payload.source) ? payload.source : {};
    const gap = validRoot && isRecord(payload.gap) ? payload.gap : {};
    const maturity =
      validRoot && isRecord(payload.maturity) ? payload.maturity : {};
    const policy = validRoot && isRecord(payload.policy) ? payload.policy : {};

    const sourceStatus = source.status === "OBSERVED" ? "OBSERVED" : "UNKNOWN";
    const allowedGap = Object.prototype.hasOwnProperty.call(
      GAP_LABELS,
      gap.status
    )
      ? gap.status
      : "UNKNOWN";
    const maturityStatus =
      maturity.status === "CONSUMER_ONLY" ? "CONSUMER_ONLY" : "UNKNOWN";
    const clusterCount =
      sourceStatus === "OBSERVED" ? countOrNull(source.cluster_count) : null;
    const dimensionCount =
      sourceStatus === "OBSERVED" ? countOrNull(source.dimension_count) : null;
    const stratumCount =
      sourceStatus === "OBSERVED" ? countOrNull(source.stratum_count) : null;
    const blockedDimensions =
      sourceStatus === "OBSERVED"
        ? countOrNull(gap.blocked_dimension_count)
        : null;
    const maximumVotes = countOrNull(policy.maximum_votes_per_stratum);
    const minimumStrata = countOrNull(policy.minimum_independent_strata);
    const requiredFraction = numberOrNull(policy.required_strata_fraction);

    return {
      source: {
        status: sourceStatus,
        label:
          sourceStatus === "OBSERVED"
            ? "Registration observed"
            : "Source unknown",
      },
      gap: {
        status: allowedGap,
        label: GAP_LABELS[allowedGap],
      },
      maturity: {
        status: maturityStatus,
        label:
          maturityStatus === "CONSUMER_ONLY"
            ? "Consumer-only"
            : "Maturity unknown",
      },
      permission: {
        status: "RESEARCH_ONLY",
        label: "Research-only",
      },
      metrics: {
        clusters: clusterCount,
        dimensions: dimensionCount,
        strata: stratumCount,
        blockedDimensions: blockedDimensions,
      },
      policy: {
        maximumVotes,
        minimumStrata,
        requiredPercent:
          requiredFraction === null
            ? null
            : Math.round(requiredFraction * 100),
      },
    };
  }

  function markRun(count, className) {
    if (count === null) {
      return '<span class="' + className + ' is-unknown"></span>';
    }
    const visible = Math.min(count, 12);
    let html = "";
    for (let index = 0; index < visible; index += 1) {
      html += '<span class="' + className + '"></span>';
    }
    if (count > visible) {
      html +=
        '<span class="hksi-overflow">+' + String(count - visible) + "</span>";
    }
    return html;
  }

  function renderStrataIndependence(rootElement, payload) {
    if (!rootElement || typeof rootElement !== "object") {
      throw new TypeError("rootElement is required");
    }
    const view = presentStrataIndependence(payload);
    const blocked =
      view.metrics.blockedDimensions === null
        ? "Unknown"
        : String(view.metrics.blockedDimensions);
    const maximumVotes =
      view.policy.maximumVotes === null
        ? "Unknown"
        : String(view.policy.maximumVotes);
    const minimumStrata =
      view.policy.minimumStrata === null
        ? "Unknown"
        : String(view.policy.minimumStrata);
    const requiredPercent =
      view.policy.requiredPercent === null
        ? "Unknown"
        : String(view.policy.requiredPercent) + "%";

    rootElement.innerHTML =
      '<section class="hksi-ledger" tabindex="0" aria-labelledby="hksi-title">' +
      '<div class="hksi-orbit" aria-hidden="true"></div>' +
      '<header class="hksi-header">' +
      '<div>' +
      '<p class="hksi-eyebrow">Correlation governance / independence ledger</p>' +
      '<h2 id="hksi-title">Independence is counted, not assumed.</h2>' +
      '<p class="hksi-intro">Clusters collapse into preregistered parent strata before an evidence vote is counted.</p>' +
      "</div>" +
      '<div class="hksi-policy-stamp" aria-label="Fixed policy">' +
      '<span>' + maximumVotes + " vote / stratum</span>" +
      '<span>' + minimumStrata + " minimum strata</span>" +
      '<span>' + requiredPercent + " fixed fraction</span>" +
      "</div>" +
      "</header>" +
      '<div class="hksi-compression" aria-label="Vote compression">' +
      '<div class="hksi-compression-source">' +
      '<span class="hksi-compression-label">Clusters</span>' +
      '<div class="hksi-cluster-marks">' +
      markRun(view.metrics.clusters, "hksi-cluster-mark") +
      "</div>" +
      '<strong>' + displayCount(view.metrics.clusters) + "</strong>" +
      "</div>" +
      '<div class="hksi-conduit" aria-hidden="true"><span></span></div>' +
      '<div class="hksi-compression-target">' +
      '<span class="hksi-compression-label">Registered strata</span>' +
      '<div class="hksi-strata-marks">' +
      markRun(view.metrics.strata, "hksi-stratum-mark") +
      "</div>" +
      '<strong>' + displayCount(view.metrics.strata) + "</strong>" +
      "</div>" +
      "</div>" +
      '<ol class="hksi-stages" aria-label="Evidence sequence">' +
      '<li class="hksi-stage hksi-source">' +
      '<span class="hksi-stage-code">SOURCE</span>' +
      '<strong>' + view.source.label + "</strong>" +
      '<small>' + displayCount(view.metrics.dimensions) + " dimensions</small>" +
      "</li>" +
      '<li class="hksi-stage hksi-gap">' +
      '<span class="hksi-stage-code">GAP</span>' +
      '<strong>' + view.gap.label + "</strong>" +
      '<small>' + blocked + " blocked dimensions</small>" +
      "</li>" +
      '<li class="hksi-stage hksi-maturity">' +
      '<span class="hksi-stage-code">MATURITY</span>' +
      '<strong>' + view.maturity.label + "</strong>" +
      "<small>Registry and writer remain pending</small>" +
      "</li>" +
      '<li class="hksi-stage hksi-permission">' +
      '<span class="hksi-stage-code">PERMISSION</span>' +
      '<strong>' + view.permission.label + "</strong>" +
      "<small>Current disabled / paper disabled / live hard locked</small>" +
      "</li>" +
      "</ol>" +
      '<footer class="hksi-footer">' +
      "<span>Count-only public evidence</span>" +
      "<span>No identities, hashes, correlations, or rankings</span>" +
      "</footer>" +
      "</section>";
    if (typeof rootElement.setAttribute === "function") {
      rootElement.setAttribute("data-hksi-mounted", "true");
    }
    return view;
  }

  return Object.freeze({
    presentStrataIndependence,
    renderStrataIndependence,
  });
});
