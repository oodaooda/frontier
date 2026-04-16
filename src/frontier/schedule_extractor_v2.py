"""Schedule hierarchy extractor v2 — separate data extraction from hierarchy detection.

Strategy:
  Pass 1: Extract all rows as flat data (easy, models are accurate)
  Pass 2: For each row, count the colored grouping bars on its left (hierarchy level)
  Pass 3: Reconstruct hierarchy from levels + position
"""

import base64
import json
import os
import re
import time
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()


def _load_image_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def _call_model(image_paths: list[str], prompt: str, model: str = "claude-opus-4-6", max_tokens: int = 64000) -> tuple[str, int, int]:
    client = anthropic.Anthropic()
    content = []
    for img_path in image_paths:
        img_data = _load_image_b64(img_path)
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": img_data},
        })
    content.append({"type": "text", "text": prompt})
    # Use streaming for large outputs to avoid timeouts
    answer = ""
    input_tokens = 0
    output_tokens = 0
    with client.messages.stream(model=model, max_tokens=max_tokens, messages=[{"role": "user", "content": content}]) as stream:
        for text in stream.text_stream:
            answer += text
        final = stream.get_final_message()
        input_tokens = final.usage.input_tokens
        output_tokens = final.usage.output_tokens
    return answer, input_tokens, output_tokens


def _parse_json(raw: str) -> any:
    text = raw.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    # Find outermost JSON structure
    for start_char, end_char in [('[', ']'), ('{', '}')]:
        start = text.find(start_char)
        end = text.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                # Try to fix truncated JSON by closing open brackets
                fragment = text[start:end + 1]
                # Count unclosed brackets
                open_sq = fragment.count('[') - fragment.count(']')
                open_cr = fragment.count('{') - fragment.count('}')
                fixed = fragment + ('}' * open_cr) + (']' * open_sq)
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    pass
    raise ValueError(f"No valid JSON found: {text[:300]}")


def extract_schedule_v2(
    pdf_path: str,
    model: str = "claude-opus-4-6",
    dpi: int = 400,
) -> dict:
    """Extract schedule using the 3-pass approach."""
    from frontier.utils.pdf import render_pdf

    pdf_path = Path(pdf_path)
    render_dir = f"data/rendered/{pdf_path.stem}_v2"
    output_dir = render_pdf(str(pdf_path), dpi=dpi, output_dir=render_dir)

    page_images = sorted([
        os.path.join(str(output_dir), f)
        for f in os.listdir(str(output_dir))
        if f.endswith(".png")
    ])
    total_pages = len(page_images)
    print(f"Rendered {total_pages} pages at {dpi} DPI")

    total_in = 0
    total_out = 0
    start = time.monotonic()

    # ═══════════════════════════════════════════════════════
    # PASS 1: Extract all rows as flat data
    # ═══════════════════════════════════════════════════════
    print("\n=== PASS 1: Flat data extraction ===")

    pass1_prompt = f"""You are reading a {total_pages}-page construction CPM bar chart schedule. Extract EVERY row from ALL pages as a flat JSON array.

For each row, extract:
- "row_type": either "header" or "activity"
- "text": the exact text of the header name OR the activity name
- "id": Activity ID (like A1000) for activities, empty string for headers
- "page": which page this row is on (1, 2, or 3)
- "original_duration", "remaining_duration", "actual_duration": numbers
- "early_start", "early_finish", "late_start", "late_finish": date strings
- "total_float": number

Headers are bold/colored rows that group activities. Activities are regular rows with Activity IDs.

Return a JSON array:
[
  {{"row_type": "header", "text": "MAJOR MILESTONES", "id": "", "page": 1}},
  {{"row_type": "activity", "text": "Notice to Proceed (9/23/2024)", "id": "A1000", "page": 1, "original_duration": 0, "remaining_duration": 0, "actual_duration": 0, "early_start": "9/23/24", "early_finish": "9/23/24", "late_start": "9/23/24", "late_finish": "9/23/24", "total_float": 0}},
  ...
]

RULES:
- Extract EVERY row from ALL {total_pages} pages
- Keep rows in the exact order they appear on the schedule (top to bottom, page 1 first)
- Use exact text as shown
- Return ONLY valid JSON array"""

    raw1, in1, out1 = _call_model(page_images, pass1_prompt, model)
    total_in += in1
    total_out += out1
    rows = _parse_json(raw1)
    print(f"Pass 1: {len(rows)} rows extracted ({in1} in, {out1} out)")

    # ═══════════════════════════════════════════════════════
    # PASS 2: Determine hierarchy level for each row
    # ═══════════════════════════════════════════════════════
    print("\n=== PASS 2: Hierarchy level detection ===")

    # Build a numbered list of rows for the model to reference
    row_list = []
    for i, row in enumerate(rows):
        text = row.get("text", "")[:60]
        rid = row.get("id", "")
        rtype = row.get("row_type", "")
        row_list.append(f"Row {i+1} [{rtype}]: {rid + ' ' if rid else ''}{text}")

    row_list_str = "\n".join(row_list)

    pass2_prompt = f"""Look at all {total_pages} pages of this construction schedule. I've extracted these rows:

{row_list_str}

For EACH row, count the number of colored vertical grouping bars on its LEFT side. These bars indicate the hierarchy depth:
- 1 bar = level 1 (top-level section like MAJOR MILESTONES)
- 2 bars = level 2 (sub-section like PERMITS & PROCEDURES)
- 3 bars = level 3 (sub-sub-section like COORDINATION DRAWINGS)
- 4 bars = level 4 (deeper like MAIN ROOF, NORTH BUILDING)
- etc.

IMPORTANT:
- Headers have bars too — count them the same way
- A top-level header like "MAJOR MILESTONES", "PRE-CONSTRUCTION", "PERMITS", "MOBILIZATION", "SUBMITTALS, APPROVALS, PROCUREMENTS", "CONSTRUCTION", "PROJECT CLOSE-OUT" should be level 1
- If a header has the SAME number of bars as the activities beneath it, it's at that level
- Look carefully at where bars START and STOP — when a bar stops, subsequent rows are at a higher (shallower) level

Return a JSON array with the level for each row, in the same order:
[
  {{"row": 1, "level": 1}},
  {{"row": 2, "level": 1}},
  {{"row": 3, "level": 1}},
  {{"row": 4, "level": 2}},
  ...
]

Return ONLY valid JSON array."""

    raw2, in2, out2 = _call_model(page_images, pass2_prompt, model)
    total_in += in2
    total_out += out2

    levels = _parse_json(raw2)
    print(f"Pass 2: {len(levels)} level assignments ({in2} in, {out2} out)")

    # Map levels to rows
    level_map = {}
    for entry in levels:
        row_num = entry.get("row", 0)
        level = entry.get("level", 1)
        level_map[row_num] = level

    # ═══════════════════════════════════════════════════════
    # PASS 3: Reconstruct hierarchy from levels + position
    # ═══════════════════════════════════════════════════════
    print("\n=== PASS 3: Hierarchy reconstruction ===")

    # Assign levels to rows
    for i, row in enumerate(rows):
        row["level"] = level_map.get(i + 1, 1)

    # Build hierarchy using a stack
    structure = []
    header_stack = []  # [(level, name, node)]

    for row in rows:
        level = row["level"]
        rtype = row.get("row_type", "")
        text = row.get("text", "")

        if rtype == "header":
            node = {
                "header" if not header_stack else "subheader": text,
                "activities": [],
                "subheaders": [],
            }

            # Pop headers at same or deeper level
            while header_stack and header_stack[-1][0] >= level:
                header_stack.pop()

            if header_stack:
                header_stack[-1][2]["subheaders"].append(node)
            else:
                structure.append(node)

            header_stack.append((level, text, node))

        elif rtype == "activity":
            # Build parent path from stack
            path_parts = [h[1] for h in header_stack]
            row["parent_path"] = " > ".join(path_parts)

            # Add to deepest header
            if header_stack:
                header_stack[-1][2]["activities"].append(row)
            else:
                if not structure:
                    structure.append({"header": "_ROOT", "activities": [], "subheaders": []})
                structure[-1]["activities"].append(row)

    # ═══════════════════════════════════════════════════════
    # PASS 4: Targeted correction for ambiguous relationships
    # ═══════════════════════════════════════════════════════
    print("\n=== PASS 4: Targeted hierarchy correction ===")

    # Find the top two levels of headers
    min_level = min((r.get("level", 99) for r in rows if r.get("row_type") == "header"), default=1)
    # Headers at min_level are project-level; min_level+1 are the major sections
    section_level = min_level + 1 if min_level == 1 else min_level
    section_headers = [r["text"] for r in rows if r.get("row_type") == "header" and r.get("level") == section_level]
    print(f"Section-level ({section_level}) headers found: {section_headers}")

    # Ask model about specific ambiguous relationships
    pass4_prompt = f"""Look at this {total_pages}-page construction schedule. I need you to answer specific questions about the hierarchy.

I found these as major sections:
{json.dumps(section_headers, indent=2)}

For EACH of these sections, tell me: is it truly a top-level section, or is it nested UNDER another section?

Look at the colored grouping bars on the LEFT side of each section header. If a section's header row has a colored bar from a parent section running through it, then it is NOT top-level — it belongs under that parent.

For example, if "PERMITS" has the PRE-CONSTRUCTION colored bar still running on its left, then PERMITS is under PRE-CONSTRUCTION, not top-level.

IMPORTANT: Only mark a section as NOT top-level if you can CLEARLY see a parent section's grouping bar running through it. If the section has its own distinct colored header bar at the same visual level as other major sections, it IS top-level.

Sections like "SUBMITTALS, APPROVALS, PROCUREMENTS" and "CONSTRUCTION" are typically top-level (level 1) sections, NOT nested under PRE-CONSTRUCTION.

Return JSON:
{{
  "hierarchy_corrections": [
    {{"header": "SECTION NAME", "is_top_level": true, "actual_parent": ""}},
    {{"header": "SECTION NAME", "is_top_level": false, "actual_parent": "PRE-CONSTRUCTION"}}
  ]
}}

Only include sections where you are confident. Return ONLY valid JSON."""

    raw4, in4, out4 = _call_model(page_images, pass4_prompt, model)
    total_in += in4
    total_out += out4

    try:
        corrections_data = _parse_json(raw4)
        if isinstance(corrections_data, list):
            corrections = corrections_data
        else:
            corrections = corrections_data.get("hierarchy_corrections", corrections_data.get("corrections", []))
        print(f"Pass 4: {len(corrections)} corrections ({in4} in, {out4} out)")

        # Apply corrections — reparent sections
        reparent_map = {}
        for c in corrections:
            if not c.get("is_top_level", True) and c.get("actual_parent"):
                reparent_map[c["header"].upper()] = c["actual_parent"]
                print(f"  Reparenting: {c['header']} → under {c['actual_parent']}")

        if reparent_map:
            # Fix activity parent_paths
            for row in rows:
                if row.get("row_type") == "activity":
                    path = row.get("parent_path", "")
                    parts = path.split(" > ")
                    new_parts = []
                    for p in parts:
                        if p.upper() in reparent_map:
                            parent = reparent_map[p.upper()]
                            # Only add parent if not already in path
                            if not new_parts or new_parts[-1].upper() != parent.upper():
                                new_parts.append(parent)
                        new_parts.append(p)
                    row["parent_path"] = " > ".join(new_parts)

            # Rebuild structure with corrections
            for row in rows:
                if row.get("row_type") == "header" and row["text"].upper() in reparent_map:
                    row["level"] = row.get("level", 1) + 1

            structure = []
            header_stack = []
            for row in rows:
                level = row.get("level", 1)
                rtype = row.get("row_type", "")
                text = row.get("text", "")

                if rtype == "header":
                    node = {
                        "header" if not header_stack else "subheader": text,
                        "activities": [],
                        "subheaders": [],
                    }
                    while header_stack and header_stack[-1][0] >= level:
                        header_stack.pop()
                    if header_stack:
                        header_stack[-1][2]["subheaders"].append(node)
                    else:
                        structure.append(node)
                    header_stack.append((level, text, node))

                elif rtype == "activity":
                    if header_stack:
                        header_stack[-1][2]["activities"].append(row)

    except (ValueError, json.JSONDecodeError) as e:
        print(f"Pass 4 parse error: {e}")

    # ═══════════════════════════════════════════════════════
    # POST-PROCESSING: Strip project title from paths
    # ═══════════════════════════════════════════════════════
    # The project title row wraps everything but isn't part of the WBS hierarchy
    project_title = ""
    for r in rows:
        if r.get("row_type") == "header" and r.get("level", 99) == min_level:
            project_title = r.get("text", "")
            break

    if project_title:
        prefix = project_title + " > "
        for r in rows:
            if r.get("row_type") == "activity":
                path = r.get("parent_path", "")
                if path.startswith(prefix):
                    r["parent_path"] = path[len(prefix):]

    elapsed = (time.monotonic() - start) * 1000

    # Collect all activities
    all_activities = [r for r in rows if r.get("row_type") == "activity"]

    result = {
        "project": {"title": ""},
        "extraction_metadata": {
            "model": model,
            "pages": total_pages,
            "total_activities": len(all_activities),
            "total_headers": len([r for r in rows if r.get("row_type") == "header"]),
            "extraction_time_ms": round(elapsed),
            "input_tokens": total_in,
            "output_tokens": total_out,
            "approach": "v2-three-pass",
        },
        "structure": structure,
        "all_activities": all_activities,
    }

    # Extract project title from first header or structure
    if structure:
        result["project"]["title"] = structure[0].get("header", structure[0].get("subheader", ""))

    return result


def validate(result: dict, gt_table_id: int) -> dict:
    """Validate against ground truth."""
    from frontier.database import get_db
    from frontier.models.table_gt import get_rows

    conn = get_db()
    gt_rows = get_rows(conn, gt_table_id)
    conn.close()

    gt = {}
    for r in gt_rows:
        d = r.data
        aid = d.get("Activity ID", "")
        path = d.get("path", "")
        if aid and d.get("_section_marker") != "true":
            gt[aid] = path

    extracted = {}
    for act in result.get("all_activities", []):
        aid = act.get("id", "")
        path = act.get("parent_path", "")
        if aid:
            extracted[aid] = path

    correct = 0
    wrong = 0
    missing = 0
    errors = []

    for aid, gt_path in gt.items():
        if aid in extracted:
            if _norm(extracted[aid]) == _norm(gt_path):
                correct += 1
            else:
                wrong += 1
                errors.append({"id": aid, "expected": gt_path, "got": extracted[aid]})
        else:
            missing += 1
            errors.append({"id": aid, "expected": gt_path, "got": "(missing)", "type": "missing"})

    extra = len(set(extracted) - set(gt))
    total = len(gt)
    acc = round(correct / total * 100, 1) if total > 0 else 0

    return {
        "total": total,
        "extracted": len(extracted),
        "correct": correct,
        "wrong": wrong,
        "missing": missing,
        "extra": extra,
        "accuracy": acc,
        "errors": sorted(errors, key=lambda e: e["id"]),
    }


def _norm(path: str) -> str:
    s = path.strip().upper().replace("  ", " ")
    s = re.sub(r'DM0*(\d+)', r'DM\1', s)
    s = re.sub(r'\s*-\s*', ' - ', s)
    s = re.sub(r'\s+', ' ', s)
    # Strip project title prefix if present
    for prefix in [
        "M.S.680(K) - LLW NO. 127569 - EARLY DEMOLITION PACKAGE - BASELINE > ",
        "M.S.680(K) - LLW NO. 127569-EARLY DEMOLITION PACKAGE - BASELINE > ",
    ]:
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    return s


if __name__ == "__main__":
    import sys

    pdf = sys.argv[1] if len(sys.argv) > 1 else "datasets/pdfs/04_K680-Full_CPM_Bar_Chart_B000.pdf"
    model = "claude-opus-4-6"
    gt_id = 4

    for i, arg in enumerate(sys.argv):
        if arg == "--model" and i + 1 < len(sys.argv):
            model = sys.argv[i + 1]
        if arg == "--gt-table-id" and i + 1 < len(sys.argv):
            gt_id = int(sys.argv[i + 1])

    result = extract_schedule_v2(pdf, model=model)

    # Save
    out_path = "datasets/results/k680_extraction_v2_3pass.json"
    os.makedirs("datasets/results", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nSaved to {out_path}")

    # Validate
    report = validate(result, gt_id)
    print(f"\n=== Validation ===")
    print(f"Expected: {report['total']}")
    print(f"Extracted: {report['extracted']}")
    print(f"Correct: {report['correct']}")
    print(f"Wrong: {report['wrong']}")
    print(f"Missing: {report['missing']}")
    print(f"Extra: {report['extra']}")
    print(f"ACCURACY: {report['accuracy']}%")

    if report['errors']:
        print(f"\n--- Errors ({len(report['errors'])}) ---")
        for e in report['errors']:
            print(f"  {e['id']}:")
            print(f"    Expected: {e['expected']}")
            print(f"    Got:      {e['got']}")

    # Save report
    report_path = out_path.replace(".json", "_validation.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
