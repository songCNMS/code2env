from __future__ import annotations

import datetime as _datetime
import math
import tempfile
from pathlib import Path
from typing import Any


DESCRIPTOR_KEY = "__code2env_rich_fixture__"


def descriptor(kind: str, **payload: Any) -> dict[str, Any]:
    return {DESCRIPTOR_KEY: kind, **payload}


def is_descriptor(value: Any) -> bool:
    return isinstance(value, dict) and isinstance(value.get(DESCRIPTOR_KEY), str)


def dataframe_descriptor(
    records: list[dict[str, Any]],
    *,
    columns: list[str] | None = None,
    index_columns: list[str] | None = None,
    parse_dates: list[str] | None = None,
) -> dict[str, Any]:
    return descriptor(
        "pandas.DataFrame",
        records=records,
        columns=columns,
        index_columns=index_columns or [],
        parse_dates=parse_dates or [],
    )


def series_descriptor(
    data: list[Any],
    *,
    name: str | None = None,
    index: list[Any] | None = None,
    index_name: str | None = None,
) -> dict[str, Any]:
    return descriptor("pandas.Series", data=data, name=name, index=index, index_name=index_name)


def timestamp_descriptor(value: str) -> dict[str, Any]:
    return descriptor("pandas.Timestamp", value=value)


def numpy_array_descriptor(data: Any, *, dtype: str | None = None) -> dict[str, Any]:
    return descriptor("numpy.ndarray", data=data, dtype=dtype)


def torch_tensor_descriptor(data: Any, *, dtype: str | None = None) -> dict[str, Any]:
    return descriptor("torch.Tensor", data=data, dtype=dtype)


def path_descriptor(path: str = ".", *, base: str = "source_root", mkdir: bool = False) -> dict[str, Any]:
    return descriptor("pathlib.Path", path=path, base=base, mkdir=mkdir)


def hydrate_args_kwargs(
    args: list[Any],
    kwargs: dict[str, Any],
    *,
    source_root: str | Path | None = None,
) -> tuple[list[Any], dict[str, Any]]:
    return (
        [hydrate_value(value, source_root=source_root) for value in args],
        {key: hydrate_value(value, source_root=source_root) for key, value in kwargs.items()},
    )


def hydrate_value(value: Any, *, source_root: str | Path | None = None) -> Any:
    if is_descriptor(value):
        return _hydrate_descriptor(value, source_root=source_root)
    if isinstance(value, list):
        return [hydrate_value(item, source_root=source_root) for item in value]
    if isinstance(value, dict):
        return {key: hydrate_value(item, source_root=source_root) for key, item in value.items()}
    return value


def rich_fixture_audit(value: Any, *, path: str = "fixture") -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    if is_descriptor(value):
        entries.append({"path": path, "kind": str(value[DESCRIPTOR_KEY])})
    elif isinstance(value, list):
        for index, item in enumerate(value):
            entries.extend(rich_fixture_audit(item, path=f"{path}[{index}]"))
    elif isinstance(value, dict):
        for key, item in value.items():
            entries.extend(rich_fixture_audit(item, path=f"{path}.{key}"))
    return entries


def serialize_rich_value(value: Any) -> dict[str, Any] | None:
    pandas_serialized = _serialize_pandas(value)
    if pandas_serialized is not None:
        return pandas_serialized
    numpy_serialized = _serialize_numpy(value)
    if numpy_serialized is not None:
        return numpy_serialized
    torch_serialized = _serialize_torch(value)
    if torch_serialized is not None:
        return torch_serialized
    if isinstance(value, Path):
        return {"kind": "pathlib.Path", "path": str(value)}
    return None


def make_json_compatible(value: Any) -> Any:
    rich = serialize_rich_value(value)
    if rich is not None:
        return rich
    if isinstance(value, dict):
        return {str(key): make_json_compatible(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [make_json_compatible(item) for item in value]
    if isinstance(value, (_datetime.datetime, _datetime.date, _datetime.time)):
        return value.isoformat()
    if isinstance(value, float):
        if math.isnan(value):
            return {"kind": "float", "value": "NaN"}
        if math.isinf(value):
            return {"kind": "float", "value": "Infinity" if value > 0 else "-Infinity"}
    return value


def _hydrate_descriptor(value: dict[str, Any], *, source_root: str | Path | None) -> Any:
    kind = value[DESCRIPTOR_KEY]
    if kind == "pandas.DataFrame":
        import pandas as pd

        records = [
            {key: hydrate_value(item, source_root=source_root) for key, item in record.items()}
            for record in value.get("records", [])
        ]
        df = pd.DataFrame(records)
        columns = value.get("columns")
        if isinstance(columns, list) and columns:
            for column in columns:
                if column not in df.columns:
                    df[column] = None
            df = df[columns]
        parse_dates = {item for item in value.get("parse_dates", []) if isinstance(item, str)}
        for column in parse_dates:
            if column in df.columns:
                df[column] = pd.to_datetime(df[column])
        index_columns = value.get("index_columns", [])
        if isinstance(index_columns, list) and index_columns:
            df = df.set_index(index_columns)
        return df
    if kind == "pandas.Series":
        import pandas as pd

        data = [hydrate_value(item, source_root=source_root) for item in value.get("data", [])]
        index = value.get("index")
        if isinstance(index, list):
            index = [hydrate_value(item, source_root=source_root) for item in index]
        return pd.Series(data, index=index, name=value.get("name")).rename_axis(value.get("index_name"))
    if kind == "pandas.Timestamp":
        import pandas as pd

        return pd.Timestamp(value.get("value"))
    if kind == "numpy.ndarray":
        import numpy as np

        dtype = value.get("dtype")
        return np.array(value.get("data", []), dtype=dtype if isinstance(dtype, str) else None)
    if kind == "numpy.scalar":
        import numpy as np

        dtype = value.get("dtype")
        if isinstance(dtype, str):
            return np.array(value.get("value"), dtype=dtype).item()
        return np.array(value.get("value")).item()
    if kind == "torch.Tensor":
        try:
            import torch
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError("torch is required to hydrate torch.Tensor fixture") from exc

        dtype = value.get("dtype")
        torch_dtype = getattr(torch, dtype, None) if isinstance(dtype, str) else None
        return torch.tensor(value.get("data", []), dtype=torch_dtype)
    if kind == "pathlib.Path":
        return _hydrate_path(value, source_root=source_root)
    raise ValueError(f"unknown rich fixture descriptor: {kind}")


def _hydrate_path(value: dict[str, Any], *, source_root: str | Path | None) -> Path:
    base = value.get("base", "source_root")
    raw_path = str(value.get("path", "."))
    if base == "source_root":
        root = Path(source_root).resolve() if source_root is not None else Path.cwd()
        if Path(raw_path).is_absolute():
            raise ValueError("source_root path fixture must be relative")
        path = (root / raw_path).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError("source_root path fixture escapes source root") from exc
    elif base == "tmpdir":
        path = Path(tempfile.mkdtemp(prefix="code2env-fixture-"))
        if raw_path not in {"", "."}:
            path = path / raw_path
    else:
        path = Path(raw_path).expanduser().resolve()
    if value.get("mkdir"):
        path.mkdir(parents=True, exist_ok=True)
    return path


def _serialize_pandas(value: Any) -> dict[str, Any] | None:
    try:
        import pandas as pd
    except ModuleNotFoundError:
        return None
    if isinstance(value, pd.DataFrame):
        return {
            "kind": "pandas.DataFrame",
            "columns": [make_json_compatible(column) for column in value.columns.tolist()],
            "index": [make_json_compatible(index) for index in value.index.tolist()],
            "index_names": [str(name) if name is not None else None for name in value.index.names],
            "dtypes": {str(column): str(dtype) for column, dtype in value.dtypes.items()},
            "data": [
                [make_json_compatible(item) for item in row]
                for row in value.itertuples(index=False, name=None)
            ],
        }
    if isinstance(value, pd.Series):
        return {
            "kind": "pandas.Series",
            "name": str(value.name) if value.name is not None else None,
            "index": [make_json_compatible(index) for index in value.index.tolist()],
            "index_names": [str(name) if name is not None else None for name in value.index.names],
            "dtype": str(value.dtype),
            "data": [make_json_compatible(item) for item in value.tolist()],
        }
    if isinstance(value, pd.Timestamp):
        return {"kind": "pandas.Timestamp", "value": value.isoformat()}
    if value is pd.NaT:
        return {"kind": "pandas.NaT"}
    return None


def _serialize_numpy(value: Any) -> dict[str, Any] | None:
    try:
        import numpy as np
    except ModuleNotFoundError:
        return None
    if isinstance(value, np.ndarray):
        return {
            "kind": "numpy.ndarray",
            "shape": list(value.shape),
            "dtype": str(value.dtype),
            "data": make_json_compatible(value.tolist()),
        }
    if isinstance(value, np.generic):
        return {
            "kind": "numpy.scalar",
            "dtype": str(value.dtype),
            "value": make_json_compatible(value.item()),
        }
    return None


def _serialize_torch(value: Any) -> dict[str, Any] | None:
    try:
        import torch
    except ModuleNotFoundError:
        return None
    if isinstance(value, torch.Tensor):
        detached = value.detach().cpu()
        return {
            "kind": "torch.Tensor",
            "shape": list(detached.shape),
            "dtype": str(detached.dtype).removeprefix("torch."),
            "data": make_json_compatible(detached.tolist()),
        }
    return None
