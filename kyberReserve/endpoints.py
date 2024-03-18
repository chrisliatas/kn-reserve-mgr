import json
from dataclasses import dataclass
from typing import Any


@dataclass
class EndpointItem:
    path: str
    base: str
    url: str
    methods: list[str]
    options: dict[str, str]
    params: dict[str, str]
    description: str

    def full_path(self, options: dict[str, Any] | None = None) -> str:
        path = f"{self.base}/{self.path}"
        if options:
            path += "?" + "&".join([f"{k}={v}" for k, v in options.items()])
        return path

    def full_url(self, options: dict[str, Any] | None = None) -> str:
        path = self.full_path(options)
        return f"{self.url}/{path}"

    @property
    def host_base(self) -> str:
        return f"{self.url}/{self.base}"

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "base": self.base,
            "url": self.url,
            "methods": self.methods,
            "options": self.options,
            "params": self.params,
            "description": self.description,
        }

    def __repr__(self) -> str:
        return (
            f"EndpointItem({self.base}/{self.path}, {self.url}, {self.methods}, "
            f"{self.options}, {self.params}, {self.description})"
        )


def load_endpoints(endpoints_json: str) -> dict[str, EndpointItem]:
    endpoints = {}
    with open(endpoints_json, "r") as f:
        data = json.load(f)
    if data:
        for i in data:
            base = i["base"]
            url = i.get("url", "")
            for j in i["endpoints"]:
                path = j["path"]
                methods = j["methods"]
                options = j.get("options", {})
                params = j.get("params", {})
                description = j["description"]
                item = EndpointItem(
                    path, base, url, methods, options, params, description
                )
                endpoints[f"{base}_{path}"] = item
    return endpoints


class ReserveEndpoints:
    def __init__(self, endpoints_json: str) -> None:
        self.endpoints: dict[str, EndpointItem] = load_endpoints(endpoints_json)
