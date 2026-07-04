import pandas as pd

from src.skills.csv_profile import ProfileCSVSkill


def test_profile_csv_returns_columns_and_stats(tmp_path):
    csv_path = tmp_path / "sample.csv"
    pd.DataFrame({"month": ["Jan", "Feb"], "sales": [10, 20], "region": ["A", "B"]}).to_csv(csv_path, index=False)

    result = ProfileCSVSkill().run(csv_path=str(csv_path))

    assert result["success"] is True
    assert result["file_name"] == "sample.csv"
    assert result["rows"] == 2
    assert result["columns"] == 3
    assert "sales" in result["numeric_columns"]
    assert "month" in result["categorical_columns"]
    assert "missing_values" in result
    assert "numeric_summary" in result
    assert len(result["sample_rows"]) == 2
