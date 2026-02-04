from pathlib import Path

def project_root() -> Path:
    # Works locally + on Streamlit Cloud
    return Path(__file__).resolve().parents[1]

def abs_path(*parts) -> Path:
    return project_root().joinpath(*parts)
