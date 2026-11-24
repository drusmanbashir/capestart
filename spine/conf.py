from pathlib import Path


def path(key):  #AI
    """Read a path from the spine-local config."""
    conf_path = Path(__file__).resolve().parent / ".agent.conf"
    values = {}
    if conf_path.exists():
        for raw_line in conf_path.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            name = name.strip()
            if name:
                values[name] = value.strip().strip("'\"")
    if key not in values:
        raise KeyError(f"{key} is absent from {conf_path}")
    result = Path(values[key])
    return result
