# Web Scraper for Danish Election RAG Gem

## Purpose

Build a web scraper tool that creates RAG (Retrieval-Augmented Generation) files for a Gemini Gem focused on the 2026 Danish parliamentary election.

**End Goal:** Users can chat with the Gem, describe their political stance on issues, and discover which political party's program aligns best with their viewpoint.

---

## Context & Motivation

- **Source Material:** Political party websites, manifestos, programs, policy documents
- **Output Target:** Gemini Gem (supports Markdown, PDF, Google Docs; max ~10 files per gem)
- **Challenge:** Many parties have multiple PDFs; need to merge into consolidated files per party
- **Format Decision:** Markdown is preferred over raw HTML for RAG because:
  - Better signal-to-noise ratio (cleaner content extraction)
  - Superior semantic structure for embeddings
  - More efficient use of context windows

---

## Strategy

### Overall Approach

1. **Crawl party websites** to extract content as Markdown (domain-specific, comprehensive)
2. **Consolidate PDFs** from party downloads into single merged file per party
3. **Create minimum viable Gem** with just Markdown files first, then enhance with PDFs

### Key Design Decisions

- **CLI Tool:** Python with named arguments (e.g., `--party alternativet`, `--all`, `--output-format markdown`)
- **Configuration:** YAML-based config file (parties.yaml) listing all party sites and PDF locations
- **Single entrypoint:** `scripts/crawl.py` handles all phases (crawling, PDF merging, etc.)
- **MVP-first:** Ship working functionality in phases, validate early, enhance incrementally

---

## Tech Stack

**Language:** Python 3

- Rationale: Best web scraping ecosystem (Firecrawl SDK, Playwright, BeautifulSoup, PDF tools)
- Easy dependency management in devcontainer
- Good CLI frameworks available (Click/Typer)

**Core Libraries (TBD - decision pending):**

- **Firecrawl API** (recommended approach): `firecrawl-py` — production-ready, handles JS-heavy sites, outputs clean Markdown
  - **Cost:** Free tier exists, paid for scale
  - **Benefit:** Fastest MVP path, reliable, domain-following built-in
- **Alternative (DIY):** `playwright`, `beautifulsoup4`, `trafilatura` — full control, zero cost
  - **Benefit:** No API dependency, fine-grained control
  - **Cost:** Slower development, more debugging

**PDF Handling (TBD):** `pypdf`, `pdfrw`, or `pikepdf` for merging

---

## Project Structure (Proposed)

```txt
fv2026/
├── .devcontainer/
│   └── devcontainer.json (add Python deps here)
├── .github/
│   ├── instructions/
│   │   └── web-scraper-rag-tool.instructions.md (this file)
│   └── copilot-instructions.md
├── scripts/
│   └── crawl.py (main CLI entry point)
├── src/
│   ├── crawler.py (crawling logic)
│   ├── pdf_handler.py (PDF merging)
│   ├── config.py (YAML config loader)
│   └── __init__.py
├── config/
│   └── parties.yaml (party sites, PDF locations, metadata)
├── output/
│   ├── markdown/ (crawled party markdown files)
│   └── pdfs/ (merged PDF files per party)
├── requirements.txt (Python dependencies)
└── README.md (user-facing docs)
```

---

## MVP Roadmap

### Phase 1: Single Party Markdown Crawl

- [ ] Set up devcontainer with Python deps
- [ ] Create `parties.yaml` with party sites
- [ ] Build basic `crawl.py` CLI
- [ ] Implement single-party crawl: `python scripts/crawl.py --party alternativet --output markdown`
- [ ] Output: `output/markdown/alternativet.md`
- [ ] **Validation:** Manually check that content is reasonable, Markdown is well-formatted

### Phase 2: All Parties Markdown

- [ ] Update `crawl.py` to support `--all` flag
- [ ] Run: `python scripts/crawl.py --all --output markdown`
- [ ] Output: One `.md` file per party in `output/markdown/`
- [ ] **Validation:** Create initial Gem version with just Markdown files
- **🚀 First version ships here**

### Phase 3: Single Party PDF Handling

- [ ] Add PDF discovery & download to `crawl.py`
- [ ] Implement PDF merging logic in `pdf_handler.py`
- [ ] Run: `python scripts/crawl.py --party alternativet --include-pdfs`
- [ ] Output: `alternativet.md` + `alternativet_documents.pdf`
- [ ] **Validation:** Verify merged PDF is readable, content is complete

### Phase 4: All Parties with PDFs

- [ ] Run: `python scripts/crawl.py --all --include-pdfs`
- [ ] Output: Markdown + merged PDFs for all parties
- [ ] **Validation:** Verify file count stays under gem limits

### Phase 5: Gem Enhancement

- [ ] Upload new files to Gem
- [ ] Test chat functionality with full content
- [ ] Iterate on content quality

---

## CLI Design

### Format: Named Arguments Only (No Positional)

```bash
# Single party crawl (Markdown)
python scripts/crawl.py --party alternativet --output-format markdown

# All parties (Markdown)
python scripts/crawl.py --all --output-format markdown

# Single party with PDFs
python scripts/crawl.py --party alternativet --include-pdfs --output-format markdown

# All parties with PDFs
python scripts/crawl.py --all --include-pdfs --output-format markdown

# Load from custom config
python scripts/crawl.py --config /path/to/custom-config.yaml --all --include-pdfs
```

### Config File (parties.yaml) Structure

Example:

```yaml
parties:
  - name: "Alternativet"
    website: "https://www.alternativet.dk"
    domains: ["alternativet.dk"]
    pdf_patterns: ["manifest", "program", "*.pdf"]
    
  - name: "Enhedslisten"
    website: "https://www.enhedslisten.dk"
    domains: ["enhedslisten.dk"]
    pdf_patterns: ["*.pdf"]
```

---

## Important Constraints & Notes

1. **Gemini Gem Limits:** ~10 files max per gem
   - Strategy: 1 Markdown + 1 merged PDF per party = 2 files × ~8 parties ≈ 16 files
   - **May need to create multiple gems or consolidate further**

2. **Markdown > HTML:** Don't fight against Markdown extraction; it's the right format for RAG

3. **JavaScript-Heavy Sites:** Ensure crawler handles JS-rendered content (Firecrawl does this; DIY would need Playwright)

4. **Rate Limiting:** Be respectful; add delays between requests if crawling on a schedule

5. **Content Freshness:** Consider how often to re-crawl (before elections, weekly, etc.)

---

## Pending Decisions

- [ ] Firecrawl API vs. DIY crawler approach?
- [ ] YAML or JSON for config?
- [ ] PDF merging in same script or separate utility?
- [ ] How to handle rate limiting / robots.txt?
- [ ] Storage strategy for outputs (git? object storage? local only during build?)

---

## Related Files & References

- `.devcontainer/devcontainer.json` — dependency declarations
- `config/parties.yaml` — configuration (to be created)
- `README.md` — user-facing documentation
- `requirements.txt` — Python dependencies

---

**Last Updated:** March 8, 2026
**Status:** Planning phase, ready to begin Phase 1 implementation
