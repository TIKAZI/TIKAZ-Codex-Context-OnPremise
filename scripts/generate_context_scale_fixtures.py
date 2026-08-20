from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "benchmarks" / "fixtures"


def make_python_fixture() -> None:
    filler = "\n\n".join(
        f"def unrelated_{index}(value):\n    return value.upper()"
        for index in range(80)
    )
    source = f'''import json

API_URL = "https://api.example.com/v1"
RELEASE = "v8.1.0"
ERROR_CODE = "DEPLOY_ERR_81"

def deploy(client):
    """Submit the checked release and preserve the exact failure evidence."""
    response = client.post(API_URL, json={{"release": RELEASE}})
    if response.status_code != 200:
        raise RuntimeError(f"{{ERROR_CODE}}: {{response.text}}")
    return json.loads(response.text)

{filler}
'''
    (ROOT / "large-code-context.py").write_text(source, encoding="utf-8")


def make_table_fixture() -> None:
    rows = ["invoice,status,amount"]
    rows.extend(
        f"INV-{index:04d},{'approved' if index % 2 == 0 else 'pending'},10.00"
        for index in range(1, 501)
    )
    (ROOT / "large-table-context.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    make_python_fixture()
    make_table_fixture()


if __name__ == "__main__":
    main()
