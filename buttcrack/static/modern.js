/* Explicit local crypto labs. No localStorage, remote requests or key persistence. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const definitions = {
    rsa: {
      description: "Tests shared prime factors, close factors (bounded Fermat search), small private exponents (Wiener), and unpadded low-exponent messages/broadcasts. This does not break secure RSA or decode OAEP padding. Supply decimal integers as strings or 0x-prefixed hex strings, not JavaScript numbers for large keys.",
      fields: [
        ["keys", "Public keys and optional raw ciphertexts (JSON array of {n, e, c})", "json"],
        ["fermat_steps", "Maximum Fermat candidates per modulus (0–20000)", "number", 1000],
        ["budget", "Search budget (0.1–5 seconds)", "number", 3],
      ],
      example: { keys: [{ n: "3233", e: "17", c: "2790" }, { n: "2867", e: "17" }], fermat_steps: 1000, budget: 3 },
    },
    keystream: {
      description: "For messages aligned to the same reused stream/keystream. Pairwise XOR is a relationship, not evidence that reuse occurred. A crib is a hypothesis: it produces corresponding fragments in the other messages, not authenticated plaintext. Offsets count bytes, not characters.",
      fields: [
        ["ciphertexts", "Aligned ciphertexts (JSON array of hex strings)", "json"],
        ["crib", "Known/guessed plaintext fragment (UTF-8)", "text"],
        ["message_index", "Which ciphertext contains the crib? (zero-based)", "number", 0],
        ["offset", "Crib starting byte offset", "number", 0],
      ],
      example: { ciphertexts: ["50766705162d", "556775011b22"], crib: "ATTACK", message_index: 0, offset: 0 },
    },
    aes: {
      description: "Block analysis needs no provider or key. Encrypt/decrypt requires a supplied AES key and the maintained cryptography provider (bundled on Windows). GCM requires a separate 16-byte tag for decryption, a 12-byte nonce and matching AAD. CTR uses a 16-byte initial counter block. CBC uses a 16-byte IV. Never reuse a nonce/counter with the same key. Non-GCM output is unauthenticated.",
      fields: [
        ["operation", "Operation", ["analyze", "decrypt", "encrypt"], "analyze"],
        ["data", "Input bytes (hex)", "hex"],
        ["mode", "AES mode (for known-key operations)", ["GCM", "CBC", "CTR", "ECB"], "GCM"],
        ["key", "Supplied key (16, 24 or 32 bytes, hex)", "secret"],
        ["iv", "IV / nonce / initial counter block (hex)", "hex"],
        ["tag", "GCM authentication tag (hex; decrypt only)", "hex"],
        ["aad", "GCM additional authenticated data (hex)", "hex"],
        ["padding", "PKCS#7 padding (ECB/CBC only)", "boolean", false],
      ],
      example: { operation: "decrypt", data: "0388dace60b6a392f328c2b971b2fe78", mode: "GCM", key: "00000000000000000000000000000000", iv: "000000000000000000000000", tag: "ab6e47d42cec13bdf53a67b21257bddf", aad: "", padding: false },
    },
    enigma: {
      description: "Historical Enigma I (not modern cryptography), including pre-keypress stepping and double stepping. Rotor order is left to right. Rings and positions are three letters (A=01). Search varies initial positions only; you must supply rotor order, rings, reflector and plugboard. Crib search is bounded and may finish without examining all 17,576 positions.",
      fields: [
        ["operation", "Operation", ["transform", "search"], "transform"],
        ["text", "Plaintext/ciphertext (A–Z and spaces only)", "text"],
        ["rotors", "Rotor order (JSON array, left to right)", "json", ["I", "II", "III"]],
        ["rings", "Ring settings (A–Z)", "text", "AAA"],
        ["positions", "Initial positions (transform only)", "text", "AAA"],
        ["reflector", "Reflector", ["B", "C"], "B"],
        ["plugboard", "Plugboard pairs, e.g. AB CD (up to ten)", "text"],
        ["crib", "Search crib (at least eight A–Z letters)", "text"],
        ["offset", "Crib letter offset after removing spaces", "number", 0],
        ["budget", "Search budget (0.1–5 seconds)", "number", 3],
      ],
      example: { operation: "transform", text: "HELLOWORLD", rotors: ["I", "II", "III"], rings: "AAA", positions: "AAA", reflector: "B", plugboard: "", crib: "", offset: 0, budget: 3 },
    },
  };
  let fields = {};
  function render(values = {}) {
    const definition = definitions[$("modern-lab").value];
    $("modern-description").textContent = definition.description;
    $("modern-fields").replaceChildren();
    $("modern-result").textContent = "";
    $("modern-status").textContent = "Ready. Results include the prerequisites and evidence limitations.";
    fields = {};
    for (const [name, caption, type, initial] of definition.fields) {
      const label = document.createElement("label");
      label.textContent = caption;
      let input;
      if (Array.isArray(type)) {
        input = document.createElement("select");
        for (const choice of type) {
          const option = document.createElement("option");
          option.value = choice;
          option.textContent = choice;
          input.append(option);
        }
      } else if (type === "boolean") {
        input = document.createElement("input");
        input.type = "checkbox";
      } else if (type === "number" || type === "secret") {
        input = document.createElement("input");
        input.type = type === "secret" ? "password" : "number";
        if (type === "number") input.step = "any";
      } else {
        input = document.createElement("textarea");
        input.rows = type === "json" ? 5 : 2;
      }
      input.id = `modern-${name}`;
      input.autocomplete = "off";
      input.spellcheck = false;
      const value = Object.hasOwn(values, name) ? values[name] : (initial ?? (type === "json" ? [] : ""));
      if (type === "boolean") input.checked = value;
      else input.value = type === "json" ? JSON.stringify(value, null, 2) : String(value);
      label.htmlFor = input.id;
      label.append(input);
      $("modern-fields").append(label);
      fields[name] = {input, type};
    }
  }
  $("modern-lab").addEventListener("change", () => render());
  $("modern-example").addEventListener("click", () => render(definitions[$("modern-lab").value].example));
  $("modern-clear").addEventListener("click", () => render());
  $("modern-run").addEventListener("click", async () => {
    const buttons = ["modern-run", "modern-lab", "modern-example", "modern-clear"];
    try {
      const options = {};
      for (const [name, {input, type}] of Object.entries(fields)) {
        if (type === "json") options[name] = JSON.parse(input.value);
        else if (type === "boolean") options[name] = input.checked;
        else if (type === "number") {
          if (!input.value.trim()) throw new Error(`${name} requires a number`);
          options[name] = Number(input.value);
          if (!Number.isFinite(options[name])) throw new Error(`${name} must be finite`);
        } else options[name] = input.value;
      }
      if ($("modern-lab").value === "rsa" && Array.isArray(options.keys)) {
        for (const record of options.keys) {
          for (const name of ["n", "e", "c"]) {
            if (record && typeof record[name] === "number" && !Number.isSafeInteger(record[name])) {
              throw new Error(`RSA ${name} is too large for a JSON number; quote it as a decimal or hex string`);
            }
          }
        }
      }
      for (const id of buttons) $(id).disabled = true;
      $("modern-status").textContent = "Running locally…";
      $("modern-result").textContent = "";
      const response = await fetch("/api/modern", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({lab: $("modern-lab").value, options}),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Lab failed");
      $("modern-status").textContent = result.status;
      $("modern-result").textContent = JSON.stringify(result, null, 2);
    } catch (error) {
      $("modern-status").textContent = error.message;
    } finally {
      for (const id of buttons) $(id).disabled = false;
    }
  });
  render();
  function openHash() {
    if (window.location.hash === "#modern") document.querySelector('[data-tab="modern"]').click();
  }
  window.addEventListener("hashchange", openHash);
  document.addEventListener("DOMContentLoaded", openHash);
})();
