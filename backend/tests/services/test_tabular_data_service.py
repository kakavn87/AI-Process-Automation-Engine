from io import BytesIO

import pytest
from openpyxl import Workbook

from app.services.tabular_data_service import TabularDataService


def test_csv_upload_profiles_columns_and_removes_duplicate_rows():
    content = (
        "Employee;Amount;City\n"
        "Alice;120,5;Berlin\n"
        "Bob;;Bochum\n"
        "Alice;120,5;Berlin\n"
    ).encode("utf-8")
    result = TabularDataService().process("finance.csv", content)

    assert result["fileType"] == "CSV"
    assert result["totalRows"] == 3
    assert result["processedRows"] == 2
    assert result["duplicateRows"] == 1
    assert result["totalColumns"] == 3
    assert result["columns"][1]["detectedType"] == "number"
    assert result["columns"][1]["numericSummary"]["mean"] == 120.5
    assert result["columns"][1]["missingCount"] == 1
    assert len(result["preview"]) == 2
    assert "not stored" in result["notice"]


def test_xlsx_upload_reads_first_worksheet_and_reports_numeric_summary():
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Orders"
    worksheet.append(["Order", "Revenue"])
    worksheet.append(["A-100", 100])
    worksheet.append(["A-101", 200])
    buffer = BytesIO()
    workbook.save(buffer)

    result = TabularDataService().process("orders.xlsx", buffer.getvalue())

    assert result["fileType"] == "XLSX"
    assert result["sheetName"] == "Orders"
    assert result["totalRows"] == 2
    assert result["columns"][1]["detectedType"] == "number"
    assert result["columns"][1]["numericSummary"] == {"min": 100.0, "max": 200.0, "mean": 150.0}


def test_upload_rejects_unsupported_file_types():
    with pytest.raises(ValueError, match="Unsupported file type"):
        TabularDataService().process("report.xls", b"some data")


def test_upload_rejects_invalid_excel_workbook():
    with pytest.raises(ValueError, match="valid .xlsx"):
        TabularDataService().process("broken.xlsx", b"not an excel workbook")


def test_upload_rejects_empty_files():
    with pytest.raises(ValueError, match="empty"):
        TabularDataService().process("empty.csv", b"")
