# kioku-agent-kit-lite

> Personal memory engine for AI agents — zero Docker, SQLite-everything.

[![PyPI](https://img.shields.io/pypi/v/kioku-agent-kit-lite)](https://pypi.org/project/kioku-agent-kit-lite/)
[![Python](https://img.shields.io/pypi/pyversions/kioku-agent-kit-lite)](https://pypi.org/project/kioku-agent-kit-lite/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**kioku-agent-kit-lite** là phiên bản nhẹ của [kioku-agent-kit](https://github.com/phuc-nt/kioku-agent-kit), thiết kế để chạy hoàn toàn local, không cần Docker, không cần server nào. Mọi thứ đều trong SQLite.

## Tính năng

- ✅ **Tri-hybrid search** — BM25 (FTS5) + Vector (sqlite-vec) + Knowledge Graph (SQLite)
- ✅ **Zero Docker** — không cần ChromaDB, FalkorDB hay Ollama server
- ✅ **FastEmbed ONNX** — embedding local, offline-capable (`intfloat/multilingual-e5-large`)
- ✅ **Agent-driven KG** — agent tự extract entities → `kg-index` (không cần built-in LLM)
- ✅ **CLI** — `kioku-lite save`, `search`, `kg-index`, `setup`, `init`
- ✅ **Python API** — import trực tiếp `KiokuLiteService` vào code
- ✅ **Multilingual** — tiếng Việt, tiếng Anh và 100+ ngôn ngữ khác
- 🔜 **MCP server** — planned (v0.2)

## Cài đặt

```bash
# CLI + core (recommended)
pip install "kioku-lite[cli]"

# Core Python API only
pip install kioku-lite

# Đầy đủ (CLI + Claude LLM extraction)
pip install "kioku-lite[full]"
```

## Quick Start

### CLI

```bash
# Lưu memory
kioku-lite save "Hôm nay họp với Hùng về dự án Kioku. Rất productive." --mood work

# Tìm kiếm
kioku-lite search "Hùng làm gì gần đây"

# Index knowledge graph (agent tự extract entities)
kioku-lite kg-index <content_hash> \
  --entities '[{"name":"Hùng","type":"PERSON"},{"name":"Kioku","type":"PROJECT"}]' \
  --relationships '[{"source":"Hùng","rel_type":"WORKS_ON","target":"Kioku"}]'
```

### Python API

```python
from kioku_lite.service import KiokuLiteService

svc = KiokuLiteService()

# Save
result = svc.save_memory("Hôm nay gặp Lan và Minh ở cà phê.", mood="happy")
print(result["content_hash"])

# Search (BM25 + Vector + KG)
results = svc.search("Lan gặp ai hôm nay", limit=5)
for r in results:
    print(r["content"], r["score"])
```

## Agent Workflow

Workflow mẫu để AI agent (Claude Code, OpenClaw,...) sử dụng kioku-lite:

```
1. Agent lưu memory:
   hash = kioku-lite save "..." --mood work

2. Agent extract entities từ context (dùng LLM riêng của agent):
   entities = [{"name": "Hùng", "type": "PERSON"}, ...]
   rels     = [{"source": "Hùng", "rel_type": "WORKS_ON", "target": "Kioku"}]

3. Agent index KG:
   kioku-lite kg-index <hash> --entities '<json>' --relationships '<json>'

4. Khi cần tìm kiếm:
   kioku-lite search "Hùng làm gì" --limit 5
```

> **Thiết kế:** kioku-lite **không tự gọi LLM** — agent chịu trách nhiệm extract entities từ context. Điều này tách biệt hoàn toàn memory store khỏi LLM dependencies.

## Cấu hình

Cấu hình qua environment variables với prefix `KIOKU_LITE_`:

| Variable | Default | Mô tả |
|---|---|---|
| `KIOKU_LITE_USER_ID` | `default` | User ID để phân tách dữ liệu |
| `KIOKU_LITE_DATA_DIR` | `~/.kioku-lite/data` | Thư mục chứa SQLite DB |
| `KIOKU_LITE_MEMORY_DIR` | `~/.kioku-lite/memory` | Thư mục chứa markdown files |
| `KIOKU_LITE_EMBED_PROVIDER` | `fastembed` | `fastembed` \| `ollama` \| `fake` |
| `KIOKU_LITE_EMBED_MODEL` | `intfloat/multilingual-e5-large` | Model name |
| `KIOKU_LITE_EMBED_DIM` | `1024` | Embedding dimensions |
| `KIOKU_LITE_OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama URL (nếu dùng Ollama) |

Hoặc dùng file `.env`:
```env
KIOKU_LITE_USER_ID=phuc
KIOKU_LITE_EMBED_PROVIDER=fastembed
KIOKU_LITE_EMBED_MODEL=intfloat/multilingual-e5-large
```

## Benchmark

Benchmark so sánh với [kioku-agent-kit](https://github.com/phuc-nt/kioku-agent-kit) (full Docker):

| Metric | kioku full | kioku-lite | |
|---|---|---|---|
| Search latency | ~2–3s | **~1.2s** | **lite nhanh hơn** |
| Precision@3 | 0.60 | **0.60** | **Ngang bằng** |
| Recall@5 | 1.04 | 0.89 | kit nhỉnh |
| Infrastructure | 3 Docker containers | Zero | **lite** |

> Với cùng embedding model (`intfloat/multilingual-e5-large`) và cùng Claude Haiku cho KG extraction, kioku-lite đạt **chất lượng search bằng** kioku full trong khi **không cần bất kỳ Docker container nào**.

Chi tiết: [docs/benchmark.md](docs/benchmark.md)

## Architecture

Xem [docs/architecture.md](docs/architecture.md) để hiểu thiết kế chi tiết.

## Development

```bash
git clone https://github.com/phuc-nt/kioku-agent-kit-lite
cd kioku-agent-kit-lite
python -m venv .venv && source .venv/bin/activate
pip install -e ".[cli,dev]"
pytest
```

## License

MIT
