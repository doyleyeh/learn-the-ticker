from __future__ import annotations

from dataclasses import dataclass
from inspect import signature
from typing import Any, Callable, get_type_hints
from urllib.parse import parse_qsl, urlsplit

from pydantic import BaseModel, ValidationError


@dataclass(frozen=True)
class _Route:
    method: str
    path: str
    endpoint: Callable[..., Any]


class Response:
    def __init__(self, status_code: int, payload: Any):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        return self._payload


class FastAPI:
    """Small local fallback used only when the FastAPI package is unavailable."""

    def __init__(self, **_: Any):
        self.routes: list[_Route] = []

    def get(self, path: str, **_: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._register("GET", path)

    def post(self, path: str, **_: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._register("POST", path)

    def _register(self, method: str, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(endpoint: Callable[..., Any]) -> Callable[..., Any]:
            self.routes.append(_Route(method=method, path=path, endpoint=endpoint))
            return endpoint

        return decorator

    def handle(self, method: str, path: str, *, params: dict[str, Any] | None = None, json: dict[str, Any] | None = None) -> Response:
        for route in self.routes:
            if route.method != method:
                continue
            path_params = _match_path(route.path, path)
            if path_params is None:
                continue
            try:
                payload = route.endpoint(**_build_kwargs(route.endpoint, path_params, params or {}, json or {}))
            except ValidationError as exc:
                return Response(422, {"detail": exc.errors()})
            return Response(200, _to_jsonable(payload))
        return Response(404, {"detail": "Not Found"})


class TestClient:
    def __init__(self, app: FastAPI):
        self.app = app

    def get(self, path: str, params: dict[str, Any] | None = None) -> Response:
        clean_path, query_params = _split_url(path)
        query_params.update(params or {})
        return self.app.handle("GET", clean_path, params=query_params)

    def post(self, path: str, json: dict[str, Any] | None = None) -> Response:
        clean_path, _ = _split_url(path)
        return self.app.handle("POST", clean_path, json=json)


def _split_url(path: str) -> tuple[str, dict[str, str]]:
    parsed = urlsplit(path)
    return parsed.path, dict(parse_qsl(parsed.query))


def _match_path(template: str, path: str) -> dict[str, str] | None:
    template_parts = template.strip("/").split("/")
    path_parts = path.strip("/").split("/")
    if len(template_parts) != len(path_parts):
        return None

    params: dict[str, str] = {}
    for expected, actual in zip(template_parts, path_parts, strict=True):
        if expected.startswith("{") and expected.endswith("}"):
            params[expected[1:-1]] = actual
        elif expected != actual:
            return None
    return params


def _build_kwargs(
    endpoint: Callable[..., Any],
    path_params: dict[str, str],
    query_params: dict[str, Any],
    body: dict[str, Any],
) -> dict[str, Any]:
    kwargs: dict[str, Any] = dict(path_params)
    hints = get_type_hints(endpoint)

    for name, parameter in signature(endpoint).parameters.items():
        if name in kwargs:
            continue
        annotation = hints.get(name)
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            kwargs[name] = annotation(**body)
        elif name in query_params:
            kwargs[name] = query_params[name]
        elif parameter.default is not parameter.empty:
            kwargs[name] = parameter.default

    return kwargs


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value
