# Leviathan Cloud OS — Macro Background Tasks
# These are persistent architecture tasks that should be worked on during ANY idle time.
# If all active tasks are complete, DEFAULT to building these. Never report "everything is done."

## MACRO-001: 3D Interactive Knowledge Graph Dashboard
**Priority:** HIGH — Core visualization infrastructure
**Status:** DESIGNED (not started)
**Estimated Scope:** Multi-session build

### Description
A fully interactive Google Earth-style 3D dashboard that renders the entire Leviathan knowledge graph with all entity connections, workflow paths, and system relationships. Users can explore the knowledge graph visually and deploy Leviathan agents on anything they see.

### Core Requirements

#### 3D Rendering Engine
- Three.js or Babylon.js for WebGL 3D rendering
- Force-directed graph layout in 3D space (d3-force-3d or custom)
- Smooth camera controls: orbit, zoom, pan (like Google Earth)
- Node clustering by category (agents, systems, bugs, workflows, channels)
- Edge rendering with directional arrows showing relationships
- Real-time data from memory.db SQLite (entities + relations tables)

#### Semantic Layer Segmentation (CRITICAL)
The knowledge graph MUST support layer-based visualization:

1. **Tier 1 — Hot Memory Layer**: Currently active context tokens, LRU cache entries, precomputed context windows. Rendered as bright, high-opacity nodes close to center.

2. **Tier 2 — Semantic Context Layer**: Warm storage entities — full documents, API responses, cached reasoning. Rendered as medium-opacity nodes in middle ring. Shows semantic relationships between concepts.

3. **Tier 3 — Deep Knowledge Layer**: Cold archive — git history, archived memories, long-term knowledge. Rendered as low-opacity nodes in outer ring. Shows historical connections.

#### Layer Controls
- Toggle switches for each layer (Tier 1 / Tier 2 / Tier 3)
- Individual layer view: show only one tier at a time
- Overlay mode: see all tiers overlaid with depth/opacity differentiation
- Tier 1 = innermost sphere (bright cyan glow)
- Tier 2 = middle sphere (warm orange)
- Tier 3 = outer sphere (cool blue/gray)
- Transitions animate smoothly when toggling layers

#### Workflow Visualization
- All 13 Tier 4 workflows (7 Auditor + 6 Debugger) rendered as flowchart paths through the graph
- Workflow nodes highlighted when selected
- Can trace a workflow path through the knowledge graph to see which entities it touches
- Click any workflow node to see its definition and trigger conditions

#### Interaction Model
- Click any node: expand details panel (entity type, connections, last accessed, tier, confidence)
- Right-click any node: "Deploy Leviathan" context menu → send task to CTO/Cloud/Brain
- Search bar: find entities by name, type, or relationship
- Filter by: entity type, tier, confidence threshold, last-accessed date
- Minimap in corner showing full graph overview

#### Data Pipeline
- Read from memory.db: entities table, relations table, memories table
- Read from agent manifests: agent definitions, capabilities, model chains
- Read from git log: commit history, file changes
- Real-time refresh: poll memory_manager.py health endpoint for updates
- Export: screenshot, data dump, filtered subgraph

#### Technology Stack (Proposed)
- Frontend: React + Three.js (react-three-fiber) or standalone Three.js
- Graph layout: 3d-force-graph library (MIT license, built on Three.js)
- Data: REST API from memory_manager.py or direct SQLite read
- Deploy: Static files served from Railway or standalone
- Fallback: 2D mode using D3.js force-directed graph for low-end devices

### Implementation Phases

**Phase 1 — Data Pipeline** (1-2 sessions)
- SQLite reader for entities/relations/memories tables
- REST API endpoint in memory_manager.py for graph data
- JSON schema for graph nodes and edges

**Phase 2 — Basic 3D Graph** (2-3 sessions)
- Three.js scene with force-directed layout
- Node rendering by entity type
- Edge rendering with labels
- Camera controls (orbit/zoom/pan)

**Phase 3 — Layer System** (1-2 sessions)
- Tier 1/2/3 layer separation
- Toggle controls with smooth transitions
- Opacity and position differentiation by tier
- Overlay mode

**Phase 4 — Workflow Overlay** (1-2 sessions)
- Render 13 workflows as paths through graph
- Workflow selection panel
- Path highlighting and tracing

**Phase 5 — Interaction + Deploy** (2-3 sessions)
- Click/right-click handlers
- Detail panels
- "Deploy Leviathan" integration
- Search and filter

### Dependencies
- memory_manager.py must expose REST API for graph data
- Knowledge Harvesting must be populating entities/relations tables
- Agent manifests must be current (no stale data)

---

## MACRO-002: Build from Source in Dockerfile
**Priority:** MEDIUM — Enables Rust code changes to deploy
**Status:** DESIGNED
**Estimated Scope:** 1-2 sessions

### Description
Current Dockerfile downloads pre-built OpenFang v0.2.3 binary. Our Rust code changes to the fork don't deploy until we build from source. Switch Dockerfile to multi-stage build: cargo build in builder stage, copy binary to runtime stage.

### Blockers
- Need to verify all our Rust changes compile cleanly
- Build time may be long (Rust compilation)
- Railway build timeout limits

---

## MACRO-003: Leviathan Vision — Token Mapping Microsystem
**Priority:** MEDIUM — Last unimplemented Phase 5 system
**Status:** DESIGNED ONLY
**Estimated Scope:** 1 session

### Description
O(n) semantic compression: single-pass scan with per-agent keyword matching, TF-IDF weighting, narrative summary generation. Compresses 3000-token documents to 150-200 token semantic tokens.

### Target
- Python companion daemon or integration into memory_manager.py
- Per-agent keyword profiles
- Compression ratio: 90%+ with 95% information retention

---

## MACRO-004: Voice-to-Text Pipeline
**Priority:** LOW — Communication enhancement
**Status:** DESIGNED (from v2.6 changelog)
**Estimated Scope:** 2-3 sessions

### Description
Dedicated Whisper API pipeline with domain-specific vocabulary for Leviathan terminology. Replaces manual typing for Owner -> Leviathan communication.

---

*Last updated: 2026-03-01 by External CTO (Claude Opus 4.6)*
*This file is canonical. If idle, build from this list.*
