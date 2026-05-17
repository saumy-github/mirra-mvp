# Research & External Knowledge Base

This folder stores useful information, research findings, and external documentation discovered during development. Think of it as a knowledge base for tools, APIs, and technologies used in the Mirra project.

---

## Purpose

Whenever Claude (or other AI) finds useful information from the web or external sources, it should be documented here:
- CLO 3D SDK documentation and findings
- REST API specifications and examples
- MongoDB queries and best practices
- Python library documentation excerpts
- Integration patterns and solutions
- Performance optimization tips
- Troubleshooting solutions found online

---

## Folder Organization

```
research/
├── README.md                    (this file)
├── clo3d/                       (CLO 3D SDK, API, plugin info)
│   ├── clo-rest-api.md          (CLO REST API endpoints)
│   ├── clo-avatar-formats.md    (Avatar file format specs)
│   ├── clo-physics-params.md    (Physics simulation parameters)
│   └── [other CLO topics]
├── mongodb/                     (MongoDB queries, schemas, tips)
│   ├── measurement-schema.md    (Measurement collection structure)
│   ├── queries.md               (Common MongoDB queries)
│   └── [other MongoDB topics]
├── python/                      (Python libraries, patterns)
│   ├── opencv-tips.md           (OpenCV usage patterns)
│   ├── pydantic-schemas.md      (Pydantic data validation)
│   └── [other Python topics]
├── performance/                 (Performance optimization, profiling)
│   ├── optimization-tips.md     (General optimization patterns)
│   └── [specific bottleneck solutions]
├── integrations/                (Third-party integrations)
│   ├── clip-zero-shot.md        (CLIP model usage)
│   ├── rmbg-segmentation.md     (RMBG-1.4 background removal)
│   └── [other integrations]
└── troubleshooting/             (Solutions found online)
    ├── common-issues.md         (Common problems & solutions)
    └── [issue-specific files]
```

---

## How to Add Information

When you discover useful information:

1. **Identify the category** (clo3d, mongodb, python, performance, integrations, troubleshooting)
2. **Create or update a file** in the appropriate subfolder
3. **Use clear headers and examples** (markdown format)
4. **Link to source** if available (URL, documentation page)
5. **Tag for searching** - use headers to make info findable

### Example Entry

```markdown
# CLO REST API - Pattern Import

**Source**: CLO SDK Documentation, December 2025

## Endpoint: /import-pattern

**Method**: POST  
**Purpose**: Import a DXF or SVG pattern into active CLO project

**Request**:
```json
{
  "file_path": "/path/to/pattern.dxf",
  "pattern_id": "front_panel",
  "scale": 1.0
}
```

**Response**:
```json
{
  "success": true,
  "pattern_id": "front_panel",
  "vertices_count": 124,
  "edges_count": 32
}
```

**Notes**:
- DXF units must be in centimeters
- Patterns should be 2D (z=0)
- Max file size: 50MB

**Used by**: Step 3 (virtual try-on) - `step_04_import_patterns.py`
```

---

## Usage Tips

**Finding Information Quickly**:
- Search by category (e.g., `research/clo3d/`)
- Use markdown headers for easy scanning
- Link related documents

**Keeping It Current**:
- Update with new findings
- Add dates/versions when relevant
- Remove outdated information
- Note when information may expire (API versions, etc.)

**Connecting to Code**:
- Reference code files that use this knowledge
- Example: "Used by: `avatar_runtime/client.py`, line 45"
- This helps future developers find relevant code

---

## Categories Explained

| Category | Purpose | Examples |
|----------|---------|----------|
| **clo3d/** | CLO 3D SDK, API, plugin specs | REST endpoints, avatar formats, physics params |
| **mongodb/** | Database queries, schemas | Measurement collection, query patterns |
| **python/** | Libraries, patterns, tips | OpenCV, Pydantic, asyncio, image processing |
| **performance/** | Optimization, profiling, bottlenecks | Caching, algorithm optimization, memory |
| **integrations/** | Third-party tools & APIs | CLIP, RMBG, segmentation models |
| **troubleshooting/** | Solutions, workarounds | Common errors, fixes, debugging tips |

---

## When to Add Information

✅ **Add if**:
- You discover new CLO API behavior
- You find useful MongoDB query patterns
- You optimize a slow algorithm
- You solve a tricky integration issue
- You find good documentation online
- You learn something about the tech stack

❌ **Don't add**:
- General programming tutorials (too broad)
- Information already in code comments
- Outdated or deprecated content
- Marketing/sales information
- Information already in `.claude/` docs

---

## Integration with Code

When adding research, consider:
1. **Is this actionable?** (Can developers use it?)
2. **Is it discoverable?** (Can future developers find it?)
3. **Does it reference code?** (Link to where it's used)

Example:
```markdown
# CLIP Zero-Shot Image Classification

**Source**: OpenAI CLIP Documentation, v2.0

Used by: `product_ingestion/view_selection.py` - classifies garment images as front/back/side

## Basic Usage
...
```

---

## Notes

- Files are markdown format (`.md`) for easy reading/editing
- Organize by topic, not by date
- Use clear headers for scanability
- Include source/URL when available
- Reference related code files
- Update when information becomes outdated

---

*Last updated: 2026-05-16*
