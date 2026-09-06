"""
Phase 10 — Testing Procedure
NOT part of the application - run manually from the backend/ folder.

Reads the 20-message Phase 9 dataset (phase9_test_dataset_v2.xlsx),
sends every message through the actual Groq LLM client at temperatures
0.3, 0.7, and 1.0, records the actual response + tier + pass/fail, and
writes three result sheets back into a new output workbook plus a
summary sheet with accuracy numbers (overall and emergency-only).

Uses a local JSON cache so re-running this script doesn't repeat API
calls for message/temperature combinations already tested.
Delete phase10_cache.json to force fresh calls.

HOW TO RUN
1. Copy this file into your backend/tests/ folder
   (next to temperature_test.py).
2. Copy phase9_test_dataset_v2.xlsx into backend/tests/ too.
3. From the backend/ folder, with your venv active:
       python tests/phase10_test_runner.py
4. Open the new file backend/tests/phase10_results.xlsx when it finishes.

EXPECTED OUTPUT
- Console progress lines as each of the 60 calls runs (or is served
  from cache).
- A final printed summary: overall accuracy and emergency-only
  accuracy, per temperature.
- phase10_results.xlsx containing one sheet per temperature (0.3, 0.7,
  1.0), each with Actual Bot Response / Actual Tier / Pass/Fail filled
  in, plus a Summary sheet with the same accuracy numbers as formulas.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from app.services.llm.client import _client
from app.services.llm.config import llm_settings
from app.services.llm.prompts import build_system_instruction
from app.services.llm.parsing import parse_urgency_tier

SOURCE_DATASET = os.path.join(os.path.dirname(__file__), "phase9_test_dataset_v2.xlsx")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "phase10_results.xlsx")
CACHE_FILE = os.path.join(os.path.dirname(__file__), "phase10_cache.json")

TEMPERATURES_TO_TEST = [0.3, 0.7, 1.0]

FONT = "Arial"


def _load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_cache(cache: dict) -> None:
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def read_dataset(path: str):
    """
    Reads rows 3..22 of the Phase 9 dataset sheet.
    Columns: ID, Test Category, Message, Expected Tier, Temperature,
    Actual Bot Response, Pass/Fail, Notes
    """
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    rows = []
    r = 3
    while ws.cell(row=r, column=3).value:
        rows.append({
            "id": ws.cell(row=r, column=1).value,
            "category": ws.cell(row=r, column=2).value,
            "message": ws.cell(row=r, column=3).value,
            "expected_tier": ws.cell(row=r, column=4).value,
        })
        r += 1
    return rows


def run_once(message: str, temperature: float) -> dict:
    system_instruction = build_system_instruction(memories=[])
    messages = [{"role": "user", "content": message}]

    response = _client.chat.completions.create(
        model=llm_settings.MODEL,
        messages=[{"role": "system", "content": system_instruction}] + messages,
        temperature=temperature,
        max_tokens=llm_settings.MAX_OUTPUT_TOKENS,
    )

    raw_text = response.choices[0].message.content
    tier, reply = parse_urgency_tier(raw_text)
    return {"tier": tier, "reply": reply}


def is_diagnosis_row(expected_tier) -> bool:
    return isinstance(expected_tier, str) and "context-dependent" in expected_tier


def score_row(expected_tier, actual_tier: str) -> str:
    """
    Diagnosis-request rows have no fixed expected tier (per the master
    prompt: tier appropriately based on symptoms, not the fact that a
    diagnosis was asked for). Those are marked for manual review
    instead of auto Pass/Fail.
    """
    if is_diagnosis_row(expected_tier):
        return "Manual review"
    return "Pass" if actual_tier == expected_tier else "Fail"


def build_output_workbook(dataset, results_by_temp):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    header_fill = PatternFill(start_color="305496", end_color="305496", fill_type="solid")
    header_font = Font(name=FONT, size=11, bold=True, color="FFFFFF")
    pass_fill = PatternFill(start_color="D9EAD3", end_color="D9EAD3", fill_type="solid")
    fail_fill = PatternFill(start_color="F4CCCC", end_color="F4CCCC", fill_type="solid")
    review_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    category_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    thin = Side(style="thin", color="B7B7B7")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    headers = ["ID", "Test Category", "Message", "Expected Tier",
               "Actual Bot Response", "Actual Tier", "Pass/Fail", "Notes"]

    for temp in TEMPERATURES_TO_TEST:
        ws = wb.create_sheet(title=f"Temp {temp}")
        for col, h in enumerate(headers, start=1):
            c = ws.cell(row=1, column=col, value=h)
            c.font = header_font
            c.fill = header_fill
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            c.border = border

        for i, row in enumerate(dataset, start=1):
            r = i + 1
            result = results_by_temp[temp][i - 1]
            verdict = score_row(row["expected_tier"], result["tier"])

            ws.cell(row=r, column=1, value=row["id"])
            cat_cell = ws.cell(row=r, column=2, value=row["category"])
            cat_cell.fill = category_fill
            ws.cell(row=r, column=3, value=row["message"]).alignment = Alignment(wrap_text=True, vertical="top")
            ws.cell(row=r, column=4, value=row["expected_tier"]).alignment = Alignment(wrap_text=True, vertical="top")
            ws.cell(row=r, column=5, value=result["reply"][:500]).alignment = Alignment(wrap_text=True, vertical="top")
            ws.cell(row=r, column=6, value=result["tier"])
            verdict_cell = ws.cell(row=r, column=7, value=verdict)
            if verdict == "Pass":
                verdict_cell.fill = pass_fill
            elif verdict == "Fail":
                verdict_cell.fill = fail_fill
            else:
                verdict_cell.fill = review_fill
            ws.cell(row=r, column=8, value="")

            for col in range(1, 9):
                ws.cell(row=r, column=col).border = border
                ws.cell(row=r, column=col).font = Font(name=FONT, size=10)

        widths = {1: 5, 2: 18, 3: 50, 4: 26, 5: 45, 6: 14, 7: 14, 8: 28}
        for col, w in widths.items():
            ws.column_dimensions[get_column_letter(col)].width = w
        ws.freeze_panes = "A2"

    # Summary sheet
    ws = wb.create_sheet(title="Summary", index=0)
    ws.cell(row=1, column=1, value="Phase 10 Summary").font = Font(name=FONT, size=13, bold=True)

    ws.cell(row=3, column=1, value="Temperature").font = header_font
    ws.cell(row=3, column=1).fill = header_fill
    ws.cell(row=3, column=2, value="Overall Accuracy").font = header_font
    ws.cell(row=3, column=2).fill = header_fill
    ws.cell(row=3, column=3, value="Emergency-only Accuracy").font = header_font
    ws.cell(row=3, column=3).fill = header_fill

    n = len(dataset)
    for i, temp in enumerate(TEMPERATURES_TO_TEST):
        r = 4 + i
        sheet_name = f"'Temp {temp}'"
        ws.cell(row=r, column=1, value=temp)
        ws.cell(row=r, column=2,
                value=f'=COUNTIF({sheet_name}!G2:G{n+1},"Pass")/COUNTIF({sheet_name}!G2:G{n+1},"<>Manual review")')
        ws.cell(row=r, column=2).number_format = "0.0%"
        ws.cell(row=r, column=3,
                value=f'=COUNTIFS({sheet_name}!B2:B{n+1},"*Emergency*",{sheet_name}!G2:G{n+1},"Pass")'
                      f'/COUNTIF({sheet_name}!B2:B{n+1},"*Emergency*")')
        ws.cell(row=r, column=3).number_format = "0.0%"

    ws.cell(row=9, column=1, value="Note: Diagnosis-request rows are excluded from accuracy").font = Font(name=FONT, size=9, italic=True)
    ws.cell(row=10, column=1, value="(marked 'Manual review' — judge those by hand per the master prompt).").font = Font(name=FONT, size=9, italic=True)

    for col, w in {1: 14, 2: 20, 3: 26}.items():
        ws.column_dimensions[get_column_letter(col)].width = w

    wb.save(OUTPUT_FILE)


def main():
    if not os.path.exists(SOURCE_DATASET):
        print(f"ERROR: could not find {SOURCE_DATASET}")
        print("Copy phase9_test_dataset_v2.xlsx into backend/tests/ first.")
        return

    dataset = read_dataset(SOURCE_DATASET)
    print(f"Loaded {len(dataset)} test messages from Phase 9 dataset.")

    cache = _load_cache()
    cache_hits = 0
    api_calls = 0
    results_by_temp = {temp: [] for temp in TEMPERATURES_TO_TEST}

    for temp in TEMPERATURES_TO_TEST:
        print(f"\n{'='*60}")
        print(f"TEMPERATURE = {temp}")
        print(f"{'='*60}")

        for row in dataset:
            cache_key = f"{row['message']}|||{temp}"

            if cache_key in cache:
                result = cache[cache_key]
                cache_hits += 1
                source = "CACHED"
            else:
                result = run_once(row["message"], temp)
                cache[cache_key] = result
                _save_cache(cache)
                api_calls += 1
                source = "LIVE"

            verdict = score_row(row["expected_tier"], result["tier"])
            print(f"[{row['id']:>2}] ({source}) [{row['category']}] -> tier: {result['tier']:<12} {verdict}")
            results_by_temp[temp].append(result)

    build_output_workbook(dataset, results_by_temp)

    print(f"\n{'='*60}")
    print(f"Done. {api_calls} live API calls made, {cache_hits} served from cache.")
    print(f"Results written to {OUTPUT_FILE}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
