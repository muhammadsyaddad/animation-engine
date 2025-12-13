


## Assistant

Now I have a comprehensive understanding of the data flow. Let me create a detailed explanation:

**Tool Call: Thinking**
Status: Completed

Now I need to synthesize everything I've learned about the animation engine's data flow:

## High-Level Architecture:
1. **Frontend (agent-ui)**: Next.js app with React components
2. **Backend (agent-api)**: FastAPI Python server with AI agents

## Data Flow Summary:

### Phase 1: User Input (Frontend)
1. User interacts with `ChatInput.tsx`
2. User can:
   - Type a message in the text area
   - Upload a CSV file using the file picker (triggers `/v1/datasets/upload`)

### Phase 2: Dataset Upload (if applicable)
- `UploadDataset.tsx` handles file uploads
- Calls `POST /v1/datasets/upload` endpoint
- Backend (`datasets.py`) processes the upload:
  - Single CSV mode: stores directly
  - Danim bundle mode (X, Y, R, Group CSVs): unifies into single long-form CSV
  - Returns `unified_rel_url` (path to the CSV)

### Phase 3: Message Submission
- User message + csv_path sent via `handleStreamResponse` hook
- Creates a FormData with message, csv_path, chart_type, etc.
- Calls `POST /v1/agents/animation_agent/runs`

### Phase 4: Backend Animation Pipeline (`agents.py`)
The `create_agent_run` function handles the full pipeline:

1. **Intent Detection**: `intent_detection.py`
   - Analyzes user message for animation keywords
   - Determines if animation is requested
   - Detects chart type hint (bubble, distribution, bar_race, etc.)

2. **Data Preprocessing**: `data_modules.py`
   - Wide→long format transformation if needed
   - Column detection (group, time, value)
   - Validation for animation suitability

3. **Chart Inference**: `chart_inference.py`
   - Analyzes data schema
   - Recommends best chart type based on data structure
   - Scores different chart types

4. **Spec Inference**: `specs.py`
   - Parses prompt for chart specifications
   - Creates data binding (columns mapping)

5. **Template Selection & Code Generation**:
   - If template matches: uses `danim_templates.py` to generate Manim code
     - `generate_bubble_code()`
     - `generate_distribution_code()`
     - `generate_bar_race_code()`
     - `generate_line_evolution_code()`
     - `generate_bento_grid_code()`
   - If no template matches: falls back to LLM code generation (`code_generation.py`)
     - Calls Claude/Anthropic API to generate Manim code

6. **Code Validation**: `validate_manim.py`
   - Validates the generated Manim code
   - Auto-fix attempts if issues found

7. **Rendering**: `video_manim.py`
   - `render_manim_stream()` function
   - Writes code to temp file
   - Runs Manim CLI to render
   - Streams progress via SSE events
   - Outputs MP4 to artifacts/videos/

### Phase 5: Response Streaming
- SSE events streamed back to frontend
- Events include: RunContent (progress), videos (final output), errors
- Frontend displays real-time progress and renders video player

## Key Files by Function:

### Frontend (agent-ui/src/):
- `components/chat/ChatArea/ChatInput/ChatInput.tsx` - User input handling
- `components/chat/ChatArea/ChatInput/UploadDataset.tsx` - File upload UI
- `hooks/useAIStreamHandler.tsx` - SSE stream processing
- `api/chat.ts` - API client functions

### Backend API (agent-api/api/):
- `routes/agents.py` - Main animation pipeline endpoint
- `routes/datasets.py` - Dataset upload handling
- `routes/chat.py` - Chat session management
- `services/data_modules.py` - Data preprocessing

### Agent Tools (agent-api/agents/tools/):
- `intent_detection.py` - Animation intent detection
- `chart_inference.py` - Smart chart type recommendation
- `data_ingestion.py` - Danim-style file unification
- `specs.py` - Chart specification inference
- `danim_templates.py` - Template-based Manim code generation
- `code_generation.py` - LLM-based Manim code generation
- `validate_manim.py` - Code validation
- `video_manim.py` - Manim rendering

### Animation Agent (agent-api/agents/):
- `animation_agent.py` - Agent configuration and instructions


## Assistant

# Animation Engine Data Flow

Here's a complete explanation of how data flows from when the user sends data until it becomes an animation:

## Overview Diagram

```/dev/null/flow.txt#L1-12
User Input (UI) 
    ↓
Dataset Upload (optional)
    ↓
Animation Pipeline (Backend)
    ├── Intent Detection
    ├── Data Preprocessing
    ├── Chart Inference
    ├── Template/Code Generation
    └── Manim Rendering
    ↓
Video Output (MP4)
```

---

## Phase 1: User Input (Frontend)

### Files Involved:
- **`agent-ui/src/components/chat/ChatArea/ChatInput/ChatInput.tsx`** - Main chat input component
- **`agent-ui/src/components/chat/ChatArea/ChatInput/UploadDataset.tsx`** - Dataset upload modal

### What Happens:
1. User types a message in the text area (e.g., "Create an animation of life expectancy over time")
2. User can optionally upload a CSV file by clicking the "+" button
3. When a file is uploaded, it calls `POST /v1/datasets/upload`

```animation-engine/agent-ui/src/components/chat/ChatArea/ChatInput/ChatInput.tsx#L68-85
      try {
        const endpointUrl = constructEndpointUrl(selectedEndpoint)
        const url = `${endpointUrl}/v1/datasets/upload`
        const fd = new FormData()
        fd.append('file', file, file.name)

        toast.loading('Uploading dataset...')
        const resp = await fetch(url, { method: 'POST', body: fd })
```

---

## Phase 2: Dataset Upload Processing

### Files Involved:
- **`agent-api/api/routes/datasets.py`** - Upload endpoint
- **`agent-api/agents/tools/data_ingestion.py`** - Danim-style file unification

### What Happens:
The backend receives the file(s) and processes them:

**Single CSV Mode:**
- Stores the file directly in `artifacts/datasets/`
- Returns a `unified_rel_url` path

**Danim Bundle Mode (X.csv, Y.csv, R.csv, Group.csv):**
- Calls `unify_danim_files()` to merge wide-form files into long-form

```animation-engine/agent-api/agents/tools/data_ingestion.py#L174-209
def unify_danim_files(
    base_dir: str,
    x_file: str = "X.csv",
    y_file: str = "Y.csv",
    r_file: str = "R.csv",
    group_file: str = "Group_lable.csv",
    output_path: Optional[str] = None,
    entity_col_candidates: Sequence[str] = (
        "Entity", "Country", "Name", "Label", "entity", "country", "name", "label", "ID", "id"
    ),
) -> IngestionResult:
```

---

## Phase 3: Message Submission & Animation Pipeline Trigger

### Files Involved:
- **`agent-ui/src/hooks/useAIStreamHandler.tsx`** - Sends request to backend
- **`agent-api/api/routes/agents.py`** - Main animation endpoint (`create_agent_run`)

### What Happens:
When user clicks "Send":
1. Frontend builds a payload with `message`, `csv_path`, `chart_type`, etc.
2. Calls `POST /v1/agents/animation_agent/runs`
3. Backend streams SSE events back with real-time progress

---

## Phase 4: Intent Detection

### File:
- **`agent-api/agents/tools/intent_detection.py`**

### What Happens:
Analyzes the user's message using regex patterns to determine:
- Is this an animation request?
- What chart type is requested?
- Confidence level

```animation-engine/agent-api/agents/tools/intent_detection.py#L62-83
# Strong animation keywords (ID + EN)
_STRONG_ANIM_PATTERNS = [
    r"\banimasi\b",            # ID: animasi
    r"\banimasikan\b",         # ID: animasikan data
    r"\banimate\b",
    r"\banimation\b",
    r"\banimating\b",
    r"\banimated\b",
    r"\bgerakkan\b",           # ID: gerakkan data
    r"\bbergerak\b",           # ID: objek bergerak
    r"\bmanim\b",              # explicit Manim mention
    r"\bvideo\b",
    r"\bmp4\b",
    r"\bgif\b",
    r"\brender\b",
    r"\bpreview\b",
]
```

---

## Phase 5: Data Preprocessing & Schema Analysis

### Files Involved:
- **`agent-api/api/services/data_modules.py`** - Data preprocessing
- **`agent-api/agents/tools/chart_inference.py`** - Smart chart recommendation

### What Happens:
1. **Validates the dataset** for animation suitability
2. **Detects if wide-format** (country + year columns) and melts to long-format
3. **Analyzes schema** to find:
   - Time column
   - Value column(s)
   - Group column
   - Entity/name column

```animation-engine/agent-api/api/routes/agents.py#L771-794
                            preproc_info = preprocess_dataset(df_preview, filename=os.path.basename(raw_dataset_path))
                            det = preproc_info.get("detection")
                            cols = preproc_info.get("columns", {})
                            transform = preproc_info.get("transform")
                            is_wide = getattr(det, "is_wide", False)
                            applied_preview = getattr(transform, "transform_applied", False)
                            msg_pre = f"Dataset preprocessing preview: wide={is_wide}, transform_applied={applied_preview}, mapped_columns={cols}"
```

---

## Phase 6: Chart Inference & Template Selection

### Files Involved:
- **`agent-api/agents/tools/chart_inference.py`** - Recommends best chart type
- **`agent-api/agents/tools/specs.py`** - Infers chart specifications
- **`agent-api/agents/tools/danim_templates.py`** - Template code generators

### What Happens:
1. **Chart Inference** scores each chart type against the data schema:
   - `bubble` - needs x, y, r, time, entity columns
   - `distribution` - needs group, time, value columns  
   - `bar_race` - needs group, time, value columns
   - `line_evolution` - needs group, time, value columns
   - `bento_grid` - dashboard with KPIs

2. **Template Selection** based on chart type:

```animation-engine/agent-api/api/routes/agents.py#L903-916
                    from agents.tools.danim_templates import (
                        generate_bubble_code,
                        generate_distribution_code,
                        generate_bar_race_code,
                        generate_line_evolution_code,
                        generate_bento_grid_code,
                        generate_count_bar_code,
                        generate_single_numeric_code,
                    )  # type: ignore
```

---

## Phase 7: Manim Code Generation

### Files Involved:
- **`agent-api/agents/tools/danim_templates.py`** - Template-based generation
- **`agent-api/agents/tools/code_generation.py`** - LLM fallback generation

### Two Paths:

**Path A - Template Match:**
If the data fits a known template, generates deterministic Manim code:

```animation-engine/agent-api/agents/tools/danim_templates.py#L1-20
"""
Danim-style bubble chart code template generator (modern Manim).

This module generates a modern-Manim code string for a bubble chart animation
that closely resembles Danim's behavior (creation modes 1/2/3, group colors,
legend, and a time label). It avoids importing Danim directly and works with
Manim Community Edition (e.g., 0.18.x).
```

**Path B - LLM Fallback:**
If no template matches, calls Claude to generate Manim code:

```animation-engine/agent-api/agents/tools/code_generation.py#L136-162
def _call_anthropic(
    prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
    system_prompt: str,
    api_key: Optional[str],
    run_id: Optional[str] = None,
) -> str:
    """Call Anthropic API with comprehensive logging."""
```

---

## Phase 8: Manim Rendering

### File:
- **`agent-api/agents/tools/video_manim.py`**

### What Happens:
1. Writes the generated Python code to a temp file
2. Runs the Manim CLI with appropriate quality settings
3. Streams progress back via SSE (Animation 1: 50%, etc.)
4. Moves final MP4 to `artifacts/videos/`

```animation-engine/agent-api/agents/tools/video_manim.py#L104-139
def render_manim_stream(
    code: str,
    file_class: str = "GenScene",
    aspect_ratio: str = "16:9",
    project_name: str = "project",
    user_id: str = "local",
    iteration: int = 1,
    run_id: Optional[str] = None,
    quality: str = "low",
) -> Generator[dict, None, None]:
    """
    Render a Manim scene to MP4 and stream progress/results as event dicts.

    Yielded event structure suggestions (consumer can adapt as needed):
        - {"event": "RunContent", "content": "<text status>"}
        - {"event": "RunError", "content": "<error message>"}
        - {"event": "RunContent", "content": "Render completed.", "videos": [{"id": 1, "eta": 0, "url": "/static/videos/xxx.mp4"}]}
```

---

## Phase 9: Video Delivery

### What Happens:
1. Final video is saved to `artifacts/videos/video-{user}-{project}-{id}.mp4`
2. SSE event with `videos` array is sent to frontend
3. Frontend displays video player with the rendered animation

---

## Complete File Reference

| Stage | File Path | Purpose |
|-------|-----------|---------|
| **UI - Chat Input** | `agent-ui/src/components/chat/ChatArea/ChatInput/ChatInput.tsx` | User message input & file upload |
| **UI - Upload Modal** | `agent-ui/src/components/chat/ChatArea/ChatInput/UploadDataset.tsx` | Detailed upload options |
| **UI - Stream Handler** | `agent-ui/src/hooks/useAIStreamHandler.tsx` | SSE stream processing |
| **API - Main Pipeline** | `agent-api/api/routes/agents.py` | Orchestrates full animation flow |
| **API - Dataset Upload** | `agent-api/api/routes/datasets.py` | Handles file uploads |
| **Tool - Intent Detection** | `agent-api/agents/tools/intent_detection.py` | Detects animation requests |
| **Tool - Chart Inference** | `agent-api/agents/tools/chart_inference.py` | Recommends chart type |
| **Tool - Data Ingestion** | `agent-api/agents/tools/data_ingestion.py` | Unifies Danim bundle files |
| **Tool - Specs** | `agent-api/agents/tools/specs.py` | Parses chart specifications |
| **Tool - Templates** | `agent-api/agents/tools/danim_templates.py` | Template-based Manim generation |
| **Tool - Code Gen** | `agent-api/agents/tools/code_generation.py` | LLM-based Manim generation |
| **Tool - Validation** | `agent-api/agents/tools/validate_manim.py` | Validates generated code |
| **Tool - Rendering** | `agent-api/agents/tools/video_manim.py` | Runs Manim CLI & outputs MP4 |
| **Agent Config** | `agent-api/agents/animation_agent.py` | Agent behavior & instructions |
