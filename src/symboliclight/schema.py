from __future__ import annotations

from symboliclight.ast import App, EnumDecl, FieldDecl, Module, TypeDecl, TypeRef


def generate_schema(app: App) -> dict[str, object]:
    type_decls = all_types(app)
    enum_decls = all_enums(app)
    definitions: dict[str, object] = {}
    enums: dict[str, object] = {}
    for name, type_decl in type_decls.items():
        definitions[name] = record_schema(type_decl, enum_names=set(enum_decls))
    for name, enum_decl in enum_decls.items():
        enums[name] = {"type": "string", "enum": list(enum_decl.variants)}
    return {
        "version": 1,
        "app": app.name,
        "definitions": definitions,
        "enums": enums,
        "routes": [
            {
                "method": route.method,
                "path": route.path,
                "body": type_schema(route.body_type, enum_names=set(enum_decls)) if route.body_type is not None else None,
                "response": type_schema(route.return_type, enum_names=set(enum_decls)),
            }
            for route in app.routes
        ],
    }


def all_types(app: App) -> dict[str, TypeDecl]:
    result = {type_decl.name: type_decl for type_decl in app.types}
    for alias, module in sorted(app.imported_modules.items()):
        for type_decl in module.types:
            result[f"{alias}.{type_decl.name}"] = qualify_type_decl(type_decl, alias, module)
        collect_nested_types(result, alias, module)
    return result


def collect_nested_types(result: dict[str, TypeDecl], prefix: str, module: Module) -> None:
    for alias, imported in sorted(module.imported_modules.items()):
        path = f"{prefix}.{alias}"
        for type_decl in imported.types:
            result[f"{path}.{type_decl.name}"] = qualify_type_decl(type_decl, path, imported)
        collect_nested_types(result, path, imported)


def qualify_type_decl(type_decl: TypeDecl, prefix: str, module: Module) -> TypeDecl:
    return TypeDecl(
        f"{prefix}.{type_decl.name}",
        [
            FieldDecl(field.name, qualify_type_ref(field.type_ref, prefix, module), field.location)
            for field in type_decl.fields
        ],
        type_decl.location,
    )


def qualify_type_ref(type_ref: TypeRef, prefix: str, module: Module) -> TypeRef:
    local_names = {item.name for item in module.types} | {item.name for item in module.enums}
    name = f"{prefix}.{type_ref.name}" if type_ref.name in local_names else type_ref.name
    return TypeRef(name, [qualify_type_ref(arg, prefix, module) for arg in type_ref.args])


def all_enums(app: App) -> dict[str, EnumDecl]:
    result = {enum_decl.name: enum_decl for enum_decl in app.enums}
    for alias, module in sorted(app.imported_modules.items()):
        for enum_decl in module.enums:
            result[f"{alias}.{enum_decl.name}"] = enum_decl
        collect_nested_enums(result, alias, module)
    return result


def collect_nested_enums(result: dict[str, EnumDecl], prefix: str, module: Module) -> None:
    for alias, imported in sorted(module.imported_modules.items()):
        path = f"{prefix}.{alias}"
        for enum_decl in imported.enums:
            result[f"{path}.{enum_decl.name}"] = enum_decl
        collect_nested_enums(result, path, imported)


def record_schema(type_decl: TypeDecl, *, enum_names: set[str]) -> dict[str, object]:
    properties = {field.name: type_schema(field.type_ref, enum_names=enum_names) for field in type_decl.fields}
    required = [
        field.name
        for field in type_decl.fields
        if field.name != "id" and field.type_ref.name != "Option"
    ]
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def type_schema(type_ref: TypeRef | None, *, enum_names: set[str]) -> dict[str, object] | None:
    if type_ref is None:
        return None
    if type_ref.name == "Bool":
        return {"type": "boolean"}
    if type_ref.name == "Int" or type_ref.name == "Id":
        return {"type": "integer"}
    if type_ref.name == "Float":
        return {"type": "number"}
    if type_ref.name == "Text":
        return {"type": "string"}
    if type_ref.name == "List" and type_ref.args:
        return {"type": "array", "items": type_schema(type_ref.args[0], enum_names=enum_names)}
    if type_ref.name == "Option" and type_ref.args:
        return {"anyOf": [type_schema(type_ref.args[0], enum_names=enum_names), {"type": "null"}]}
    if type_ref.name == "Result" and len(type_ref.args) == 2:
        return {
            "type": "object",
            "properties": {
                "ok": type_schema(type_ref.args[0], enum_names=enum_names),
                "err": type_schema(type_ref.args[1], enum_names=enum_names),
            },
            "additionalProperties": False,
        }
    if type_ref.name == "Response" and type_ref.args:
        return type_schema(type_ref.args[0], enum_names=enum_names)
    if type_ref.name in enum_names:
        return {"$ref": f"#/enums/{type_ref.render()}"}
    return {"$ref": f"#/definitions/{type_ref.render()}"}
