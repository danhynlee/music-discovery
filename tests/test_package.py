import discover


def test_package_imports_with_version() -> None:
    assert discover.__version__ == "0.1.0"
