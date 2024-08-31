import json
from dataclasses import dataclass
from typing import Any


@dataclass
class EndpointItem:
    path: str
    base: str
    sub_base: str
    url: str
    methods: list[str]
    secured: bool
    options: dict[str, str]
    params: dict[str, str]
    description: str

    def full_path(self, options: dict[str, Any] | None = None) -> str:
        if self.sub_base:
            path = f"{self.base}/{self.sub_base}/{self.path}"
        else:
            path = f"{self.base}/{self.path}"
        if options:
            path += "?" + "&".join([f"{k}={v}" for k, v in options.items()])
        if path.startswith("/"):
            path = path[1:]
        return path

    def full_url(self, options: dict[str, Any] | None = None) -> str:
        path = self.full_path(options)
        return f"{self.url}/{path}"

    @property
    def host_base(self) -> str:
        if self.url and self.base:
            if self.sub_base:
                return f"{self.url}/{self.base}/{self.sub_base}"
            return f"{self.url}/{self.base}"
        if self.url:
            return self.url
        return ""

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "base": self.base,
            "sub_base": self.sub_base,
            "url": self.url,
            "methods": self.methods,
            "secured": self.secured,
            "options": self.options,
            "params": self.params,
            "description": self.description,
        }

    def __repr__(self) -> str:
        if self.base:
            if self.sub_base:
                base_path = f"{self.base}/{self.sub_base}/{self.path}"
            else:
                base_path = f"{self.base}/{self.path}"
        else:
            base_path = self.path
        return (
            f"EndpointItem({base_path}, {self.url}, {self.methods}, "
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
                sub_base = j.get("sub_base", "")
                methods = j["methods"]
                secured = j.get("secured", False)
                options = j.get("options", {})
                params = j.get("params", {})
                description = j["description"]
                item = EndpointItem(
                    path,
                    base,
                    sub_base,
                    url,
                    methods,
                    secured,
                    options,
                    params,
                    description,
                )
                if base:
                    ep_key = (
                        f"{base}_{sub_base}_{path}" if sub_base else f"{base}_{path}"
                    )
                else:
                    ep_key = path
                endpoints[ep_key] = item
    return endpoints


class ReserveEndpoints:
    def __init__(self, endpoints_json: str) -> None:
        self.endpoints: dict[str, EndpointItem] = load_endpoints(endpoints_json)
