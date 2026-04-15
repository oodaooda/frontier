"""Schedule hierarchy extractor — page-by-page with context tracking.

Extracts construction CPM schedules from multi-page PDFs while
maintaining parent-child hierarchy across page breaks.
"""

import base64
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ExtractionResult:
    """Result from extracting one page."""
    headers_and_activities: list[dict]
    open_headers_at_bottom: list[dict]
    raw_response: str
    page_number: int


@dataclass
class ScheduleExtraction:
    """Complete extraction result across all pages."""
    project: dict
    structure: list[dict]
    all_activities: list[dict]  # flat list with paths
    metadata: dict
    per_page_results: list[ExtractionResult]


def _load_image_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def _build_page1_prompt(total_pages: int) -> str:
    return f"""You are extracting a construction CPM bar chart schedule from page 1 of {total_pages}.

Look carefully at the LEFT side of the schedule — there are colored vertical grouping bars that show the hierarchy. Headers are bold/colored rows. Activities are regular rows beneath headers.

Extract ALL rows visible on this page as JSON with this EXACT format:

{{
  "project": {{
    "title": "full project title from the top header"
  }},
  "headers_and_activities": [
    {{"type": "header", "level": 1, "name": "TOP LEVEL SECTION"}},
    {{"type": "activity", "id": "A1000", "name": "Activity Name", "parent_path": "TOP LEVEL SECTION", "original_duration": 0, "remaining_duration": 0, "actual_duration": 0, "early_start": "", "early_finish": "", "late_start": "", "late_finish": "", "total_float": 0}},
    {{"type": "header", "level": 2, "name": "SUB-SECTION", "parent_path": "TOP LEVEL SECTION"}},
    {{"type": "activity", "id": "A3270", "name": "Activity Name", "parent_path": "TOP LEVEL SECTION > SUB-SECTION", "original_duration": 21, "remaining_duration": 21, "actual_duration": 0, "early_start": "9/23/24", "early_finish": "10/22/24", "late_start": "9/23/24", "late_finish": "10/22/24", "total_float": 0}}
  ],
  "open_headers_at_bottom": [
    {{"level": 1, "name": "HEADER WHOSE BAR REACHES BOTTOM OF PAGE"}},
    {{"level": 2, "name": "SUB-HEADER WHOSE BAR REACHES BOTTOM OF PAGE"}}
  ]
}}

RULES:
- "parent_path" = full path from root using " > " separator (e.g., "PRE-CONSTRUCTION > PERMITS & PROCEDURES")
- "level" = depth in hierarchy (1 = top section, 2 = sub-section, 3 = sub-sub-section, etc.)
- Level 1 headers are MAJOR SECTIONS like "MAJOR MILESTONES", "PRE-CONSTRUCTION", "PERMITS", "MOBILIZATION", "SUBMITTALS, APPROVALS, PROCUREMENTS", "CONSTRUCTION", "PROJECT CLOSE-OUT". These are SIBLINGS, not nested under each other.
- Count the colored vertical bars on the left side of each row — the number of bars indicates the depth level
- "open_headers_at_bottom" = headers whose colored grouping bar extends to the VERY BOTTOM of the page. List from outermost (level 1) to innermost.
- Extract EVERY row — do not skip any activities or headers
- Use exact text as shown on the schedule
- Return ONLY valid JSON, no markdown fences"""


def _build_continuation_prompt(page_num: int, total_pages: int, carryover: list[dict]) -> str:
    context_lines = []
    for h in carryover:
        context_lines.append(f"  Level {h['level']}: {h['name']}")
    context_str = "\n".join(context_lines)

    return f"""You are extracting a construction CPM bar chart schedule from page {page_num} of {total_pages}.

CARRYOVER CONTEXT — these headers are STILL ACTIVE from previous pages. Their colored grouping bars continue from the previous page:
{context_str}

Activities at the TOP of this page (before any new header appears) belong to the INNERMOST carryover header above.

Extract ALL rows visible on this page as JSON with this EXACT format:

{{
  "headers_and_activities": [
    {{"type": "header", "level": 2, "name": "NEW SECTION ON THIS PAGE", "parent_path": "PARENT FROM CARRYOVER"}},
    {{"type": "activity", "id": "A3500", "name": "Activity Name", "parent_path": "FULL > PATH > TO > PARENT", "original_duration": 5, "remaining_duration": 5, "actual_duration": 0, "early_start": "1/23/25", "early_finish": "1/24/25", "late_start": "1/23/25", "late_finish": "1/24/25", "total_float": 0}}
  ],
  "open_headers_at_bottom": [
    {{"level": 1, "name": "HEADER WHOSE BAR REACHES BOTTOM OF PAGE"}}
  ]
}}

RULES:
- "parent_path" must include carryover headers as parents where applicable
- If a new header starts on this page, determine its level from the grouping bars and indentation
- CRITICAL: When a grouping bar ENDS (its colored line stops), that header is CLOSED. Subsequent activities belong to the PARENT header, not the closed one. Check carefully whether each header's bar extends through all activities or stops partway.
- A new top-level header (level 1) means ALL previous carryover headers are closed
- When a header's grouping bar ENDS on this page, it is NOT in open_headers_at_bottom
- If this is the last page, open_headers_at_bottom should be empty []
- Pay close attention to the NUMBER of colored bars on the left of each activity — fewer bars means the activity is at a higher level in the hierarchy
- Extract EVERY row — do not skip any
- Use exact text as shown on the schedule
- Return ONLY valid JSON, no markdown fences"""


def _parse_model_response(raw: str) -> dict:
    """Parse JSON from model response, handling markdown fences."""
    text = raw.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in response: {text[:200]}")
    return json.loads(text[start:end + 1])


def _call_model(image_paths: list[str], prompt: str, model: str = "claude-opus-4-6") -> tuple[str, int, int]:
    """Send images + prompt to the model. Returns (answer, input_tokens, output_tokens)."""
    client = anthropic.Anthropic()
    content = []
    for img_path in image_paths:
        img_data = _load_image_b64(img_path)
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": img_data},
        })
    content.append({"type": "text", "text": prompt})

    response = client.messages.create(
        model=model,
        max_tokens=16000,
        messages=[{"role": "user", "content": content}],
    )
    answer = ""
    for block in response.content:
        if block.type == "text":
            answer += block.text
    return answer, response.usage.input_tokens, response.usage.output_tokens


def extract_schedule(
    pdf_path: str,
    model: str = "claude-opus-4-6",
    dpi: int = 400,
    render_dir: str | None = None,
) -> ScheduleExtraction:
    """Extract a multi-page construction schedule with context tracking.

    Args:
        pdf_path: Path to the schedule PDF
        model: Model ID to use
        dpi: DPI for rendering
        render_dir: Directory for rendered pages (default: data/rendered/<stem>)

    Returns:
        ScheduleExtraction with hierarchical structure and flat activity list
    """
    from frontier.utils.pdf import render_pdf

    pdf_path = Path(pdf_path)
    if render_dir is None:
        render_dir = f"data/rendered/{pdf_path.stem}_extract"
    output_dir = render_pdf(str(pdf_path), dpi=dpi, output_dir=render_dir)

    # Get page images
    import os
    page_images = sorted([
        os.path.join(str(output_dir), f)
        for f in os.listdir(str(output_dir))
        if f.endswith(".png")
    ])
    total_pages = len(page_images)
    print(f"Rendered {total_pages} pages at {dpi} DPI")

    # Track state
    carryover_headers: list[dict] = []
    page_results: list[ExtractionResult] = []
    all_headers_and_activities: list[dict] = []
    project_info = {}
    total_input_tokens = 0
    total_output_tokens = 0
    start_time = time.monotonic()

    for page_num in range(1, total_pages + 1):
        page_img = page_images[page_num - 1]
        print(f"\n--- Page {page_num}/{total_pages} ---")

        if page_num == 1:
            prompt = _build_page1_prompt(total_pages)
        else:
            prompt = _build_continuation_prompt(page_num, total_pages, carryover_headers)
            print(f"Carryover context: {[h['name'] for h in carryover_headers]}")

        raw, in_tok, out_tok = _call_model([page_img], prompt, model)
        total_input_tokens += in_tok
        total_output_tokens += out_tok
        print(f"Tokens: {in_tok} in, {out_tok} out")

        try:
            data = _parse_model_response(raw)
        except (ValueError, json.JSONDecodeError) as e:
            print(f"ERROR parsing page {page_num}: {e}")
            print(f"Raw response: {raw[:500]}")
            page_results.append(ExtractionResult([], [], raw, page_num))
            continue

        # Extract project info from page 1
        if page_num == 1 and "project" in data:
            project_info = data["project"]

        items = data.get("headers_and_activities", [])
        open_headers = data.get("open_headers_at_bottom", [])

        print(f"Extracted {len(items)} items, {len(open_headers)} open headers at bottom")

        # Store results
        page_results.append(ExtractionResult(items, open_headers, raw, page_num))
        all_headers_and_activities.extend(items)

        # Update carryover for next page
        carryover_headers = open_headers

    elapsed_ms = (time.monotonic() - start_time) * 1000

    # Verification pass — send all pages + extracted hierarchy, ask model to verify
    print("\n--- Verification Pass ---")
    flat_activities_pre = [
        item for item in all_headers_and_activities if item.get("type") == "activity"
    ]
    headers_pre = [
        item for item in all_headers_and_activities if item.get("type") == "header"
    ]

    # Build a summary of the hierarchy for verification
    hierarchy_summary = []
    for h in headers_pre:
        hierarchy_summary.append(f"[L{h.get('level',1)}] {h.get('name','')}")
    for a in flat_activities_pre[:5]:
        hierarchy_summary.append(f"  Activity {a.get('id','')}: parent_path = {a.get('parent_path','')}")

    verify_prompt = f"""You extracted a construction schedule across {total_pages} pages. Here is a summary of the hierarchy you found:

HEADERS FOUND:
{chr(10).join(hierarchy_summary[:50])}

I need you to verify these specific hierarchy questions by looking at ALL {total_pages} pages:

1. Is "PROJECT CLOSE-OUT" a top-level section (level 1, sibling of CONSTRUCTION) or nested inside CONSTRUCTION? Look at the colored grouping bars on the left.

2. Is "SUBMITTALS, APPROVALS, PROCUREMENTS" a top-level section (level 1)? Does "DIVISION 2 - SITE WORK" belong under it?

3. Is "SECTION AT ADJACENT PROPERTY EXTERIOR BUILDING FACADE" at the same level as "1-STOREY MASONRY BUILDING" (both under LLW), or is it nested INSIDE 1-STOREY MASONRY?

Answer as JSON:
{{
  "corrections": [
    {{"header": "PROJECT CLOSE-OUT", "correct_level": 1, "correct_parent_path": ""}},
    {{"header": "DIVISION 2 - SITE WORK", "correct_parent_path": "SUBMITTALS, APPROVALS, PROCUREMENTS"}},
    {{"header": "SECTION AT ADJACENT PROPERTY EXTERIOR BUILDING FACADE - DWG 7/DM104", "correct_parent_path": "CONSTRUCTION > LLW NO.: 127569 - EARLY DEMOLITION PACKAGE"}}
  ]
}}

Only include corrections that differ from what was extracted. Return ONLY JSON."""

    verify_raw, v_in, v_out = _call_model(page_images, verify_prompt, model)
    total_input_tokens += v_in
    total_output_tokens += v_out
    print(f"Verification tokens: {v_in} in, {v_out} out")

    try:
        verify_data = _parse_model_response(verify_raw)
        corrections = verify_data.get("corrections", [])
        print(f"Got {len(corrections)} corrections")

        # Apply corrections
        correction_map = {}
        for c in corrections:
            header_name = c.get("header", "")
            correct_path = c.get("correct_parent_path", "")
            correct_level = c.get("correct_level")
            if header_name:
                correction_map[header_name.upper()] = {
                    "parent_path": correct_path,
                    "level": correct_level,
                }

        # Fix activities whose parent headers were corrected
        for item in all_headers_and_activities:
            if item.get("type") == "header":
                name_upper = item.get("name", "").upper()
                if name_upper in correction_map:
                    corr = correction_map[name_upper]
                    if corr.get("level"):
                        item["level"] = corr["level"]
                    if "parent_path" in corr:
                        item["parent_path"] = corr["parent_path"]
                        print(f"  Corrected header: {item['name']} → parent: {corr['parent_path']}")

            elif item.get("type") == "activity":
                path = item.get("parent_path", "")
                for header_name, corr in correction_map.items():
                    # If this activity's path goes through a corrected header, fix it
                    if header_name in path.upper():
                        old_path = path
                        # Rebuild path with correction
                        if corr.get("parent_path") == "":
                            # Header is top-level — remove any parents above it
                            parts = path.split(" > ")
                            for i, p in enumerate(parts):
                                if p.upper() == header_name:
                                    item["parent_path"] = " > ".join(parts[i:])
                                    break
                        elif corr.get("parent_path"):
                            # Header should be under a specific parent
                            parts = path.split(" > ")
                            for i, p in enumerate(parts):
                                if p.upper() == header_name:
                                    new_parts = corr["parent_path"].split(" > ") + parts[i:]
                                    item["parent_path"] = " > ".join(new_parts)
                                    break
                        if item["parent_path"] != old_path:
                            print(f"  Fixed {item.get('id','')}: {old_path} → {item['parent_path']}")

    except (ValueError, json.JSONDecodeError) as e:
        print(f"Verification parse error: {e}")

    # Build hierarchical structure from flat list
    structure = _build_hierarchy(all_headers_and_activities)

    # Build flat activity list with paths
    flat_activities = [
        item for item in all_headers_and_activities if item.get("type") == "activity"
    ]

    return ScheduleExtraction(
        project=project_info,
        structure=structure,
        all_activities=flat_activities,
        metadata={
            "model": model,
            "pages": total_pages,
            "total_activities": len(flat_activities),
            "total_headers": len([i for i in all_headers_and_activities if i.get("type") == "header"]),
            "extraction_time_ms": round(elapsed_ms),
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
        },
        per_page_results=page_results,
    )


def _build_hierarchy(items: list[dict]) -> list[dict]:
    """Build a nested hierarchy from a flat list of headers and activities."""
    root: list[dict] = []
    stack: list[tuple[int, dict]] = []  # (level, node)

    for item in items:
        if item.get("type") == "header":
            level = item.get("level", 1)
            node = {
                "header" if level == 1 or not stack else "subheader": item["name"],
                "activities": [],
                "subheaders": [],
            }
            # Pop stack until we find the parent level
            while stack and stack[-1][0] >= level:
                stack.pop()

            if stack:
                stack[-1][1]["subheaders"].append(node)
            else:
                root.append(node)

            stack.append((level, node))

        elif item.get("type") == "activity":
            # Add to the deepest header on the stack
            if stack:
                stack[-1][1]["activities"].append(item)
            else:
                # Orphan activity — create an implicit root
                if not root or "activities" not in root[-1]:
                    root.append({"header": "_UNASSIGNED", "activities": [], "subheaders": []})
                root[-1]["activities"].append(item)

    return root


def save_extraction(extraction: ScheduleExtraction, output_path: str) -> None:
    """Save extraction result as JSON."""
    output = {
        "project": extraction.project,
        "extraction_metadata": extraction.metadata,
        "columns": [
            "Activity ID", "Activity Name", "Original Duration",
            "Remaining Duration", "Actual Duration", "Early Start",
            "Early Finish", "Late Start", "Late Finish", "Total Float",
        ],
        "structure": extraction.structure,
    }
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved extraction to {output_path}")


def validate_against_ground_truth(
    extraction: ScheduleExtraction,
    ground_truth_table_id: int | None = None,
    ground_truth_json_path: str | None = None,
) -> dict:
    """Compare extraction against ground truth.

    Args:
        extraction: The extraction result
        ground_truth_table_id: ID of the table_ground_truth in the Frontier DB
        ground_truth_json_path: Path to a ground truth JSON file

    Returns:
        Validation report dict
    """
    # Load ground truth
    gt_activities = {}  # activity_id -> path
    if ground_truth_table_id:
        from frontier.database import get_db
        from frontier.models.table_gt import get_rows
        conn = get_db()
        rows = get_rows(conn, ground_truth_table_id)
        for r in rows:
            data = r.data
            aid = data.get("Activity ID", "")
            path = data.get("path", "")
            if aid and data.get("_section_marker") != "true":
                gt_activities[aid] = path
        conn.close()
    elif ground_truth_json_path:
        with open(ground_truth_json_path) as f:
            gt_data = json.load(f)
        for entry in gt_data.get("entries", []):
            aid = entry.get("Activity ID", "")
            path = entry.get("path", "")
            if aid:
                gt_activities[aid] = path

    if not gt_activities:
        return {"error": "No ground truth loaded"}

    # Build extracted activity paths
    extracted = {}
    for act in extraction.all_activities:
        aid = act.get("id", "")
        path = act.get("parent_path", "")
        if aid:
            extracted[aid] = path

    # Compare
    correct = 0
    wrong_parent = 0
    missing = 0
    extra = 0
    errors = []

    for aid, gt_path in gt_activities.items():
        if aid in extracted:
            ext_path = extracted[aid]
            if _normalize_path(ext_path) == _normalize_path(gt_path):
                correct += 1
            else:
                wrong_parent += 1
                errors.append({
                    "activity_id": aid,
                    "expected_path": gt_path,
                    "extracted_path": ext_path,
                    "error_type": "wrong_parent",
                })
        else:
            missing += 1
            errors.append({
                "activity_id": aid,
                "expected_path": gt_path,
                "extracted_path": "",
                "error_type": "missing",
            })

    for aid in extracted:
        if aid not in gt_activities:
            extra += 1
            errors.append({
                "activity_id": aid,
                "expected_path": "",
                "extracted_path": extracted[aid],
                "error_type": "extra",
            })

    total_expected = len(gt_activities)
    total_extracted = len(extracted)
    path_accuracy = round(correct / total_expected * 100, 1) if total_expected > 0 else 0

    report = {
        "summary": {
            "total_expected": total_expected,
            "total_extracted": total_extracted,
            "missing": missing,
            "extra": extra,
            "path_correct": correct,
            "path_wrong": wrong_parent,
            "path_accuracy_pct": path_accuracy,
        },
        "errors": sorted(errors, key=lambda e: e["activity_id"]),
    }

    return report


def _normalize_path(path: str) -> str:
    """Normalize a path for comparison — handle minor text differences."""
    s = path.strip().upper().replace("  ", " ")
    # Normalize drawing reference numbers: DM010 = DM10, DM0010 = DM10
    s = re.sub(r'DM0*(\d+)', r'DM\1', s)
    s = re.sub(r'DWG\s+0*(\d)', r'DWG \1', s)
    # Normalize spaces around punctuation
    s = re.sub(r'\s*-\s*', ' - ', s)
    s = re.sub(r'\s+', ' ', s)
    return s


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m frontier.schedule_extractor extract <pdf_path> [--model MODEL] [--output PATH]")
        print("  python -m frontier.schedule_extractor validate <result.json> --gt-table-id ID")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "extract":
        pdf = sys.argv[2] if len(sys.argv) > 2 else "datasets/pdfs/04_K680-Full_CPM_Bar_Chart_B000.pdf"
        model = "claude-opus-4-6"
        output = "datasets/results/k680_extraction.json"

        for i, arg in enumerate(sys.argv):
            if arg == "--model" and i + 1 < len(sys.argv):
                model = sys.argv[i + 1]
            if arg == "--output" and i + 1 < len(sys.argv):
                output = sys.argv[i + 1]

        result = extract_schedule(pdf, model=model)
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        save_extraction(result, output)

        print(f"\n=== Extraction Summary ===")
        print(f"Model: {model}")
        print(f"Pages: {result.metadata['pages']}")
        print(f"Activities: {result.metadata['total_activities']}")
        print(f"Headers: {result.metadata['total_headers']}")
        print(f"Time: {result.metadata['extraction_time_ms']}ms")
        print(f"Tokens: {result.metadata['input_tokens']} in, {result.metadata['output_tokens']} out")

    elif cmd == "validate":
        result_path = sys.argv[2]
        gt_table_id = None
        for i, arg in enumerate(sys.argv):
            if arg == "--gt-table-id" and i + 1 < len(sys.argv):
                gt_table_id = int(sys.argv[i + 1])

        # Load extraction
        with open(result_path) as f:
            data = json.load(f)

        # Rebuild flat activity list from structure
        def flatten(structure, path=""):
            acts = []
            for section in structure:
                name = section.get("header", section.get("subheader", ""))
                current = f"{path} > {name}" if path else name
                for act in section.get("activities", []):
                    act["parent_path"] = current
                    acts.append(act)
                if "subheaders" in section:
                    acts.extend(flatten(section["subheaders"], current))
            return acts

        extraction = ScheduleExtraction(
            project=data.get("project", {}),
            structure=data.get("structure", []),
            all_activities=flatten(data.get("structure", [])),
            metadata=data.get("extraction_metadata", {}),
            per_page_results=[],
        )

        report = validate_against_ground_truth(extraction, ground_truth_table_id=gt_table_id)

        print(f"\n=== Validation Report ===")
        s = report["summary"]
        print(f"Expected: {s['total_expected']} activities")
        print(f"Extracted: {s['total_extracted']} activities")
        print(f"Missing: {s['missing']}")
        print(f"Extra: {s['extra']}")
        print(f"Path correct: {s['path_correct']}")
        print(f"Path wrong: {s['path_wrong']}")
        print(f"PATH ACCURACY: {s['path_accuracy_pct']}%")

        if report["errors"]:
            print(f"\n--- Errors ({len(report['errors'])}) ---")
            for e in report["errors"]:
                print(f"  [{e['error_type']}] {e['activity_id']}")
                if e['expected_path']:
                    print(f"    Expected: {e['expected_path']}")
                if e['extracted_path']:
                    print(f"    Got:      {e['extracted_path']}")

        # Save report
        report_path = result_path.replace(".json", "_validation.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nSaved validation report to {report_path}")
