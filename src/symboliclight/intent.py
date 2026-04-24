from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class IntentRoute:
    method: str
    path: str


@dataclass(slots=True)
class IntentPermissions:
    web: bool | None = None
    network: bool | None = None
    filesystem_read: bool | None = None
    filesystem_write: bool | None = None
    tools: dict[str, bool] = field(default_factory=dict)


@dataclass(slots=True)
class IntentContract:
    path: Path
    routes: list[IntentRoute] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    permissions: IntentPermissions = field(default_factory=IntentPermissions)


def load_intent_contract(path: Path) -> IntentContract:
    contract = IntentContract(path=path)
    section: str | None = None
    item: dict[str, str] | None = None
    permissions_child: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if raw_line.strip().startswith("# sl:"):
            parse_sl_comment(contract, raw_line.strip()[5:].strip())
            continue
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if indent == 0 and stripped.endswith(":"):
            flush_item(contract, section, item)
            item = None
            section = stripped[:-1]
            permissions_child = None
            continue
        if section == "routes":
            if stripped.startswith("- "):
                flush_item(contract, section, item)
                item = {}
                rest = stripped[2:].strip()
                if rest:
                    assign_item_value(item, rest)
                continue
            if item is not None:
                assign_item_value(item, stripped)
            continue
        if section == "commands":
            if stripped.startswith("- "):
                flush_item(contract, section, item)
                item = {}
                rest = stripped[2:].strip()
                if ":" in rest:
                    assign_item_value(item, rest)
                elif rest:
                    contract.commands.append(unquote(rest))
                    item = None
                continue
            if item is not None:
                assign_item_value(item, stripped)
            continue
        if section == "permissions":
            if indent == 2 and stripped.endswith(":"):
                permissions_child = stripped[:-1]
                continue
            if ":" not in stripped:
                continue
            key, value = split_key_value(stripped)
            parsed = parse_bool(value)
            if indent == 2:
                permissions_child = None
            if permissions_child == "filesystem":
                if key == "read":
                    contract.permissions.filesystem_read = parsed
                elif key == "write":
                    contract.permissions.filesystem_write = parsed
            elif permissions_child == "tools":
                contract.permissions.tools[key] = parsed
            elif key == "web":
                contract.permissions.web = parsed
            elif key == "network":
                contract.permissions.network = parsed
    flush_item(contract, section, item)
    return contract


def parse_sl_comment(contract: IntentContract, text: str) -> None:
    parts = text.split()
    if not parts:
        return
    if parts[0] == "route" and len(parts) >= 3:
        contract.routes.append(IntentRoute(parts[1].upper(), parts[2]))
    elif parts[0] == "command" and len(parts) >= 2:
        contract.commands.append(parts[1])


def flush_item(contract: IntentContract, section: str | None, item: dict[str, str] | None) -> None:
    if not item:
        return
    if section == "routes":
        method = item.get("method")
        path = item.get("path")
        if method and path:
            contract.routes.append(IntentRoute(method.upper(), path))
    elif section == "commands":
        name = item.get("name")
        if name:
            contract.commands.append(name)


def assign_item_value(item: dict[str, str], text: str) -> None:
    if ":" not in text:
        return
    key, value = split_key_value(text)
    item[key] = unquote(value)


def split_key_value(text: str) -> tuple[str, str]:
    key, value = text.split(":", 1)
    return key.strip(), value.strip()


def parse_bool(value: str) -> bool | None:
    lowered = value.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    return None


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
