/* Counts geometry only; it does not identify an outlier or decode a cipher. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  let revision = 0;
  function invalidate() {
    revision++;
    $("strip-results").hidden = true;
    $("strip-rows").replaceChildren();
    $("strip-status").textContent = "Input or guide changed; count again.";
  }
  $("input").addEventListener("input", invalidate);
  $("strip-column").addEventListener("input", invalidate);
  $("strip-run").addEventListener("click", async () => {
    const current = ++revision;
    $("strip-results").hidden = true;
    $("strip-rows").replaceChildren();
    const field = $("strip-column").value;
    if (!field || !Number.isInteger(Number(field))) {
      $("strip-status").textContent = "Guide column must be a whole number.";
      return;
    }
    $("strip-status").textContent = "Counting on the local server…";
    try {
      const response = await fetch("/api/strip-analysis", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({text: $("input").value, column: Number(field)}),
      });
      const data = await response.json();
      if (current !== revision) return;
      if (!response.ok) throw new Error(data.error || "Count failed.");
      const fragment = document.createDocumentFragment();
      for (const row of data.rows) {
        const tr = document.createElement("tr");
        for (const value of [row.line, row.letters, row.before, row.on, row.after]) {
          const td = document.createElement("td");
          td.textContent = String(value);
          tr.appendChild(td);
        }
        fragment.appendChild(tr);
      }
      $("strip-rows").replaceChildren(fragment);
      $("strip-results").hidden = false;
      $("strip-status").textContent = `${data.rows.length} rows counted at column ${data.guide_column}. No outlier or solution is inferred.`;
    } catch (error) {
      if (current === revision) $("strip-status").textContent = error.message;
    }
  });
})();
