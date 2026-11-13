import csv
import json
import math
from datetime import date, datetime
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any

from openpyxl import load_workbook


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_DATA_ROWS = 20_000
PREVIEW_ROWS = 10


class TabularDataService:
    """Processes CSV/XLSX uploads in memory; files and row data are never persisted."""

    def process(self, filename: str, content: bytes) -> dict[str, Any]:
        suffix = Path(filename or "").suffix.lower()
        if suffix not in {".csv", ".xlsx"}:
            raise ValueError("Unsupported file type. Upload a .csv or .xlsx file.")
        if not content:
            raise ValueError("The uploaded file is empty.")
        if len(content) > MAX_UPLOAD_BYTES:
            raise ValueError("File is larger than the 10 MB upload limit.")

        if suffix == ".csv":
            headers, raw_rows, empty_rows_removed, truncated = self._read_csv(content)
            sheet_name = None
        else:
            headers, raw_rows, empty_rows_removed, truncated, sheet_name = self._read_xlsx(content)

        if not headers:
            raise ValueError("The file must contain a header row.")
        headers = self._unique_headers(headers, max([len(headers), *(len(row) for row in raw_rows)], default=len(headers)))
        rows = [
            {
                headers[index]: self._normalize_cell(row[index] if index < len(row) else None)
                for index in range(len(headers))
            }
            for row in raw_rows
        ]

        duplicate_rows = 0
        seen: set[str] = set()
        cleaned_rows: list[dict[str, Any]] = []
        for row in rows:
            key = json.dumps(row, sort_keys=True, ensure_ascii=False, default=str)
            if key in seen:
                duplicate_rows += 1
                continue
            seen.add(key)
            cleaned_rows.append(row)

        columns = [self._profile_column(name, [row.get(name) for row in rows]) for name in headers]
        total_rows = len(rows)
        total_cells = total_rows * len(headers)
        missing_cells = sum(column["missingCount"] for column in columns)
        completeness = 1 - (missing_cells / total_cells) if total_cells else 0
        uniqueness = 1 - (duplicate_rows / total_rows) if total_rows else 0
        quality_score = round((completeness * 0.7 + uniqueness * 0.3) * 100) if total_rows else 0

        return {
            "fileName": Path(filename).name[:180],
            "fileType": suffix.removeprefix(".").upper(),
            "sheetName": sheet_name,
            "totalRows": total_rows,
            "processedRows": len(cleaned_rows),
            "totalColumns": len(headers),
            "duplicateRows": duplicate_rows,
            "emptyRowsRemoved": empty_rows_removed,
            "truncated": truncated,
            "dataQualityScore": quality_score,
            "columns": columns,
            "preview": cleaned_rows[:PREVIEW_ROWS],
            "processingSteps": [
                "Read the uploaded file in memory.",
                "Normalized blank cells and column names.",
                "Detected column types and missing values.",
                f"Detected and removed {duplicate_rows} duplicate row(s) from the preview dataset.",
                f"Prepared a preview of up to {PREVIEW_ROWS} cleaned rows.",
            ],
            "notice": (
                f"Only the first {MAX_DATA_ROWS:,} non-empty data rows were processed."
                if truncated
                else "The uploaded file was processed in memory and was not stored."
            ),
        }

    def _read_csv(self, content: bytes) -> tuple[list[Any], list[list[Any]], int, bool]:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text = content.decode("cp1252")
            except UnicodeDecodeError as exc:
                raise ValueError("Could not decode the CSV file. Save it as UTF-8 and try again.") from exc

        try:
            try:
                dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
            except csv.Error:
                dialect = csv.excel
            reader = csv.reader(StringIO(text), dialect)
            headers = next(reader, [])
            rows: list[list[Any]] = []
            empty_rows = 0
            truncated = False
            for row in reader:
                if not any(str(value).strip() for value in row if value is not None):
                    empty_rows += 1
                    continue
                if len(rows) >= MAX_DATA_ROWS:
                    truncated = True
                    break
                rows.append(row)
            return headers, rows, empty_rows, truncated
        except csv.Error as exc:
            raise ValueError("The CSV file contains invalid rows or quoting.") from exc

    def _read_xlsx(self, content: bytes) -> tuple[list[Any], list[list[Any]], int, bool, str | None]:
        try:
            workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
        except Exception as exc:
            raise ValueError("Could not read this Excel file. Please upload a valid .xlsx workbook.") from exc

        try:
            if not workbook.worksheets:
                raise ValueError("The Excel workbook does not contain a worksheet.")
            worksheet = workbook.worksheets[0]
            iterator = worksheet.iter_rows(values_only=True)
            headers = list(next(iterator, ()) or ())
            rows: list[list[Any]] = []
            empty_rows = 0
            truncated = False
            for row in iterator:
                values = list(row)
                if not any(value is not None and str(value).strip() for value in values):
                    empty_rows += 1
                    continue
                if len(rows) >= MAX_DATA_ROWS:
                    truncated = True
                    break
                rows.append(values)
            return headers, rows, empty_rows, truncated, worksheet.title
        finally:
            workbook.close()

    @staticmethod
    def _unique_headers(headers: list[Any], width: int) -> list[str]:
        result: list[str] = []
        used: set[str] = set()
        for index in range(width):
            raw = headers[index] if index < len(headers) else None
            base = str(raw).strip() if raw is not None else ""
            base = base or f"Column {index + 1}"
            name = base
            suffix = 2
            while name in used:
                name = f"{base} ({suffix})"
                suffix += 1
            used.add(name)
            result.append(name)
        return result

    @staticmethod
    def _normalize_cell(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return value if math.isfinite(value) else None
        if isinstance(value, str):
            value = value.strip()
            return value if value else None
        return str(value).strip() or None

    @staticmethod
    def _parse_number(value: Any) -> float | None:
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, (int, float)):
            number = float(value)
            return number if math.isfinite(number) else None
        text = str(value).strip().replace(" ", "")
        if not text:
            return None
        if "," in text and "." in text:
            text = text.replace(".", "").replace(",", ".")
        elif "," in text:
            text = text.replace(",", ".")
        try:
            number = float(text)
            return number if math.isfinite(number) else None
        except ValueError:
            return None

    @classmethod
    def _profile_column(cls, name: str, values: list[Any]) -> dict[str, Any]:
        present = [value for value in values if value is not None and value != ""]
        missing = len(values) - len(present)
        unique_values = list(dict.fromkeys(
            json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
            for value in present
        ))
        numbers = [cls._parse_number(value) for value in present]
        if not present:
            detected_type = "empty"
        elif all(isinstance(value, bool) for value in present):
            detected_type = "boolean"
        elif all(number is not None for number in numbers):
            detected_type = "number"
        elif all(isinstance(value, str) for value in present):
            detected_type = "text"
        else:
            detected_type = "mixed"

        numeric_summary = None
        if detected_type == "number":
            numeric_values = [number for number in numbers if number is not None]
            numeric_summary = {
                "min": round(min(numeric_values), 3),
                "max": round(max(numeric_values), 3),
                "mean": round(sum(numeric_values) / len(numeric_values), 3),
            }

        return {
            "name": name,
            "detectedType": detected_type,
            "missingCount": missing,
            "missingPercent": round((missing / len(values)) * 100, 1) if values else 0,
            "uniqueCount": len(unique_values),
            "sampleValues": present[:3],
            "numericSummary": numeric_summary,
        }
