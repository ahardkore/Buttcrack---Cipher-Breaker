import re
import html

with open('THE_KRYPTOS_DECRYPTION_MANUSCRIPT.md', 'r') as f:
    book_raw = f.read()

# Helper to turn markdown into safe clean HTML
def md_to_html(md_text):
    lines = md_text.strip().split('\n')
    out = []
    in_code = False
    in_table = False
    table_rows = []

    for line in lines:
        if line.startswith('```'):
            if in_code:
                out.append('</code></pre>')
                in_code = False
            else:
                out.append('<pre class="code-display"><code>')
                in_code = True
            continue
        if in_code:
            out.append(html.escape(line))
            continue

        if line.startswith('|') and '|' in line[1:]:
            if not in_table:
                in_table = True
                table_rows = []
            table_rows.append(line)
            continue
        else:
            if in_table:
                out.append('<div style="overflow-x:auto; margin: 16px 0;"><table style="border-collapse: collapse; width: 100%; border: 1px solid var(--border-color); font-size: 0.85rem;">')
                for r_idx, r in enumerate(table_rows):
                    cols = [c.strip() for c in r.strip('|').split('|')]
                    if all(set(c).issubset({'-', ':', ' '}) for c in cols):
                        continue # delimiter
                    tag = 'th' if r_idx == 0 else 'td'
                    bg = 'background-color: var(--bg-dark);' if tag == 'th' else ''
                    out.append(f'<tr>' + ''.join(f'<{tag} style="border: 1px solid var(--border-color); padding: 6px 10px; {bg}">{html.escape(c)}</{tag}>' for c in cols) + '</tr>')
                out.append('</table></div>')
                in_table = False

        if line.startswith('### '):
            out.append(f'<h3 style="color: var(--copper-glow); margin-top: 1.25rem; font-size: 1.15rem;">{html.escape(line[4:])}</h3>')
        elif line.startswith('## '):
            out.append(f'<h2 style="color: var(--text-bright); margin-top: 1.75rem; border-bottom: 1px solid var(--border-color); padding-bottom: 6px;">{html.escape(line[3:])}</h2>')
        elif line.startswith('# '):
            out.append(f'<h1 style="color: var(--copper-primary); margin-top: 2rem; font-size: 1.6rem;">{html.escape(line[2:])}</h1>')
        elif line.strip() == '':
            out.append('<div style="height: 8px;"></div>')
        elif line.startswith('- ') or line.startswith('* '):
            out.append(f'<li style="margin-left: 20px; color: var(--text-main);">{html.escape(line[2:])}</li>')
        else:
            out.append(f'<p style="margin-bottom: 10px; color: var(--text-main);">{html.escape(line)}</p>')

    if in_code:
        out.append('</code></pre>')
    if in_table:
        out.append('</table></div>')

    return '\n'.join(out)

# Map chapters to section IDs
chapters_sections = [
    ("book-ch-prologue", "PROLOGUE: THE CIA SCULPTURE & THE 36-YEAR MYSTERY", "PROLOGUE: THE CIA SCULPTURE & THE 36-YEAR MYSTERY", "CHAPTER 1: THE NARRATIVE ARC"),
    ("book-ch-1", "CHAPTER 1: THE NARRATIVE ARC OF PARADIGM KRYPTOS (PK1 – PK7)", "CHAPTER 1: THE NARRATIVE ARC", "CHAPTER 2: DECOUPLING"),
    ("book-ch-2", "CHAPTER 2: DECOUPLING AND BREAKING PK8", "CHAPTER 2: DECOUPLING", "CHAPTER 3: CRACKING PK9"),
    ("book-ch-3", "CHAPTER 3: CRACKING PK9 — THE 135-CHARACTER ARTISAN TEXT", "CHAPTER 3: CRACKING PK9", "CHAPTER 4: CRACKING PK10"),
    ("book-ch-4", "CHAPTER 4: CRACKING PK10 — THE MODULAR COPPER TRIPTYCH", "CHAPTER 4: CRACKING PK10", "CHAPTER 5: THE DUAL-CIPHER"),
    ("book-ch-5", "CHAPTER 5: THE DUAL-CIPHER GPS SCULPTURE THEOREM", "CHAPTER 5: THE DUAL-CIPHER", "CHAPTER 6: GRAND CRYPTOSYSTEM"),
    ("book-ch-6", "CHAPTER 6: GRAND CRYPTOSYSTEM SYNTHESIS & UNIVERSAL INVARIANTS", "CHAPTER 6: GRAND CRYPTOSYSTEM", "CHAPTER 7: MASTER SOLUTIONS"),
    ("book-ch-7", "CHAPTER 7: MASTER SOLUTIONS DATABASE & VERIFICATION MANIFEST", "CHAPTER 7: MASTER SOLUTIONS", "EPILOGUE: COMPLETE SUITE"),
    ("book-ch-epilogue", "EPILOGUE: COMPLETE SUITE REPRODUCIBILITY ASSURANCE", "EPILOGUE: COMPLETE SUITE", "---END---")
]

book_html_parts = []
for ch_id, ch_title, start_marker, end_marker in chapters_sections:
    start_pos = book_raw.find(start_marker)
    if start_pos == -1:
        chunk = f"## {ch_title}\n\nChapter content available in full manuscript."
    else:
        if end_marker == "---END---":
            chunk = book_raw[start_pos:]
        else:
            end_pos = book_raw.find(end_marker, start_pos)
            if end_pos != -1:
                chunk = book_raw[start_pos:end_pos]
            else:
                chunk = book_raw[start_pos:]
    
    html_chunk = md_to_html(chunk)
    book_html_parts.append(f'<div id="{ch_id}" class="book-chapter-block" style="margin-bottom: 40px;">\n{html_chunk}\n</div>')

book_rendered = '\n'.join(book_html_parts)

index_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Kryptos & Paradigm Kryptos — Master Cryptanalytic Suite</title>
  <link rel="stylesheet" href="styles.css">
  <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🔐</text></svg>">
</head>
<body>

  <!-- Top Navigation Bar -->
  <header>
    <div class="logo-container">
      <div class="logo-badge">KRYPTOS</div>
      <div class="logo-title">
        <h1>PARADIGM & CIA KRYPTOS RESEARCH SUITE</h1>
        <p>Comprehensive Decryption Engine, Verification Suite & Book Manuscript</p>
      </div>
    </div>
    <nav>
      <button class="nav-tab active" data-target="cipher-explorer">Ciphers (PK1–10 & K1–4)</button>
      <button class="nav-tab" data-target="sculpture-visualizer">Sculpture Architecture</button>
      <button class="nav-tab" data-target="book-reader">Manuscript Reader</button>
      <button class="nav-tab" data-target="workbench">Cryptanalytic Workbench</button>
      <button class="nav-tab" data-target="github-guide">GitHub & Deploy Guide</button>
    </nav>
  </header>

  <!-- Main Content Area -->
  <main>

    <!-- Tab 1: Cipher Explorer -->
    <div id="cipher-explorer" class="tab-pane active">
      <div class="cipher-explorer-layout">
        <!-- Sidebar -->
        <aside class="cipher-sidebar" id="cipher-sidebar-list">
          <!-- Dynamically populated via data.js -->
        </aside>

        <!-- Detail Card -->
        <section class="cipher-detail-card">
          <div class="detail-header">
            <div class="detail-title">
              <h2 id="detail-title">Loading Cipher...</h2>
              <p id="detail-subtitle">Mechanism details</p>
            </div>
            <div>
              <span id="detail-status-badge" class="cipher-badge badge-frontier">FRONTIER</span>
            </div>
          </div>

          <!-- Statistical Metrics Grid -->
          <div class="stats-grid">
            <div class="stat-box">
              <div class="stat-label">Length (N)</div>
              <div class="stat-value" id="stat-len">-</div>
            </div>
            <div class="stat-box">
              <div class="stat-label">Monogram IoC</div>
              <div class="stat-value" id="stat-ioc">-</div>
            </div>
            <div class="stat-box">
              <div class="stat-label">Shannon Entropy</div>
              <div class="stat-value" id="stat-entropy">-</div>
            </div>
            <div class="stat-box">
              <div class="stat-label">Rare Letters (JQXZ)</div>
              <div class="stat-value" id="stat-rare">-</div>
            </div>
          </div>

          <!-- Key / Mechanism Details -->
          <div class="text-section">
            <h3>Mathematical Key & Mechanism</h3>
            <div class="code-display" id="detail-key">-</div>
          </div>

          <!-- Ciphertext Display -->
          <div class="text-section">
            <h3>Ciphertext (Source Inscription)</h3>
            <pre class="code-display" id="detail-ct">-</pre>
          </div>

          <!-- Plaintext Display -->
          <div class="text-section">
            <h3>Plaintext (Verified Decryption / Frontier State)</h3>
            <pre class="code-display plaintext-highlight" id="detail-pt">-</pre>
          </div>

          <!-- Cryptanalytic Notes -->
          <div class="text-section">
            <h3>Cryptanalytic Proofs & Historical Notes</h3>
            <div class="code-display" id="detail-notes">-</div>
          </div>
        </section>
      </div>
    </div>

    <!-- Tab 2: Sculpture Visualizer -->
    <div id="sculpture-visualizer" class="tab-pane">
      <div class="sculpture-container">
        <h2>Paradigm Kryptos Sculpture & Physical Architecture Map</h2>
        <p style="color: var(--text-muted); margin-bottom: 20px;">
          Vector schematic depicting the $12 \times 42$ copper matrix panels, 3-clock harmonic gears, and CIA Langley GPS coordinate padding arithmetic.
        </p>
        <div class="sculpture-svg-wrapper">
          <img src="architecture.svg" alt="Paradigm Kryptos Architecture Map" style="max-width: 100%; height: auto; border: 1px solid var(--border-color); border-radius: 8px; background: #0b0e14;">
        </div>
      </div>
    </div>

    <!-- Tab 3: Book Reader -->
    <div id="book-reader" class="tab-pane">
      <div class="book-reader-container">
        <!-- Table of Contents -->
        <aside class="book-toc">
          <h3>Table of Contents</h3>
          <div id="book-toc-list">
            <!-- Dynamically populated via app.js -->
          </div>
        </aside>

        <!-- Book Reading View -->
        <article class="book-content" id="book-content-display">
          {book_rendered}
        </article>
      </div>
    </div>

    <!-- Tab 4: Cryptanalytic Workbench -->
    <div id="workbench" class="tab-pane">
      <div class="workbench-grid">
        <!-- Left: Decryption Engine Form -->
        <div class="workbench-card">
          <h2 style="margin-bottom: 16px; color: var(--text-bright);">Interactive Classical Cipher Engine</h2>
          <p style="color: var(--text-muted); font-size: 0.85rem; margin-bottom: 16px;">
            Test polyalphabetic and transposition hypotheses in real-time over the Kryptos alphabet (<code style="color: var(--copper-glow);">KRYPTOSABCDEFGHIJLMNQUVWXZ</code>).
          </p>

          <label style="font-size: 0.8rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">Algorithm</label>
          <select id="wb-algo-select" style="width: 100%; padding: 8px; background: var(--bg-dark); border: 1px solid var(--border-color); color: var(--text-bright); border-radius: 6px; margin: 6px 0 16px;">
            <option value="vigenere-kr">Quagmire III (Kryptos Alphabet Keystream)</option>
            <option value="vigenere-std">Standard Vigenère (A–Z Alphabet)</option>
            <option value="columnar">Columnar Transposition (Keyword Order)</option>
          </select>

          <label style="font-size: 0.8rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">Ciphertext Input</label>
          <textarea id="wb-input-ct" class="tool-input" placeholder="Paste uppercase ciphertext letters here..."></textarea>

          <label style="font-size: 0.8rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">Key / Keyword / Vector</label>
          <input type="text" id="wb-input-key" style="width: 100%; padding: 10px; background: var(--bg-dark); border: 1px solid var(--border-color); color: var(--text-bright); font-family: var(--font-mono); border-radius: 6px; margin: 6px 0 20px;" placeholder="e.g. PALIMPSEST or KCOLDYX">

          <button id="wb-btn-decrypt" class="btn-primary" style="width: 100%;">Execute Decryption Engine</button>
        </div>

        <!-- Right: Results & Real-time Metrics -->
        <div class="workbench-card">
          <h2 style="margin-bottom: 16px; color: var(--text-bright);">Live Cryptanalytic Diagnostics</h2>
          
          <div class="stats-grid" style="margin-bottom: 16px;">
            <div class="stat-box">
              <div class="stat-label">Calculated IoC</div>
              <div class="stat-value" id="wb-res-ioc">0.00000</div>
            </div>
            <div class="stat-box">
              <div class="stat-label">Entropy</div>
              <div class="stat-value" id="wb-res-ent">0.000 b</div>
            </div>
            <div class="stat-box" style="grid-column: span 2;">
              <div class="stat-label">Rare Letters (JQXZ)</div>
              <div class="stat-value" id="wb-res-rare">0</div>
            </div>
          </div>

          <label style="font-size: 0.8rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">Decrypted Plaintext Output</label>
          <pre id="wb-output-pt" class="code-display plaintext-highlight" style="min-height: 200px; margin-top: 6px; white-space: pre-wrap;">Awaiting engine execution...</pre>
        </div>
      </div>
    </div>

    <!-- Tab 5: GitHub Deployment Guide -->
    <div id="github-guide" class="tab-pane">
      <div class="github-guide-card">
        <h2>GitHub Repository & Deployment Guide</h2>
        <p style="color: var(--text-muted); margin: 8px 0 24px;">
          Deploy this full cryptanalytic suite, interactive web app, and book manuscript directly to your GitHub account and activate GitHub Pages for zero-cost static hosting.
        </p>

        <div class="github-steps">
          <div class="step-box">
            <h4>Step 1: Initialize Git Repository in Workspace</h4>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 8px;">Run these commands to configure the repository and commit all suite assets:</p>
            <pre>git init
git config user.name "Your Name"
git config user.email "your-email@users.noreply.github.com"
git add .
git commit -m "Initialize Kryptos & Paradigm Kryptos Master Suite"</pre>
          </div>

          <div class="step-box">
            <h4>Step 2: Create a New GitHub Repository</h4>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 8px;">Go to <code style="color: var(--copper-glow);">https://github.com/new</code> and create a repository (e.g. <code>kryptos-suite</code> or <code>paradigm-kryptos</code>).</p>
          </div>

          <div class="step-box">
            <h4>Step 3: Connect Remote & Push</h4>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 8px;">Add your remote repository URL and push the main branch:</p>
            <pre>git branch -M main
git remote add origin https://github.com/&lt;USERNAME&gt;/&lt;REPO-NAME&gt;.git
git push -u origin main</pre>
          </div>

          <div class="step-box">
            <h4>Step 4: Enable Free GitHub Pages Web Hosting</h4>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 8px;">In your GitHub repository settings:</p>
            <ul style="font-size: 0.85rem; color: var(--text-main); margin-left: 20px;">
              <li>Navigate to <strong>Settings</strong> &gt; <strong>Pages</strong>.</li>
              <li>Under <strong>Build and deployment</strong> &gt; <strong>Source</strong>, select <strong>Deploy from a branch</strong>.</li>
              <li>Under <strong>Branch</strong>, select <code>main</code> and folder <code>/kryptos-app</code> (or deploy via GitHub Actions).</li>
              <li>Your app is immediately live at <code>https://&lt;USERNAME&gt;.github.io/&lt;REPO-NAME&gt;/</code>!</li>
            </ul>
          </div>
        </div>
      </div>
    </div>

  </main>

  <!-- Global Footer -->
  <footer>
    <p>Kryptos & Paradigm Kryptos Master Cryptanalytic Suite &copy; 2026. Cryptanalytic research, proofs, and verified solution catalog.</p>
  </footer>

  <script src="data.js"></script>
  <script src="app.js"></script>
</body>
</html>
'''

with open('kryptos-app/index.html', 'w') as f:
    f.write(index_html)

print("kryptos-app/index.html successfully created! Size:", len(index_html))
