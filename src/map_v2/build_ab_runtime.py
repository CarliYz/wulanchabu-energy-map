"""Create the browser runtime contract for the A/B terminal Blender slice.

The contract is generated from the same terminal layout used by
build_ab_terminals.py.  It carries candidate-only semantics and verifies the
exported GLB contains the expected semantic roots before writing the registry.
"""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path


ROOT = Path("/path/to/wulanchabu-energy-map")
REGISTRY = ROOT / "web/map-prototype/facility-registry.json"
GLB = ROOT / "web/map-viewer/assets/ab-terminals-v1/AB_terminal_slice.glb"
OUT = ROOT / "web/map-prototype/ab-terminal-runtime.json"
ASSET_ROOT = "../map-viewer/assets/ab-terminals-v1"
REVISION = "m9-ab-terminals-v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_glb_document(path: Path) -> dict:
    data = path.read_bytes()
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or length != len(data):
        raise ValueError("GLB header/version/length mismatch")
    offset = 12
    while offset < length:
        chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        chunk = data[offset:offset + chunk_length]
        offset += chunk_length
        if chunk_type == 0x4E4F534A:
            return json.loads(chunk.decode("utf-8").rstrip(" \x00"))
    raise ValueError("GLB JSON chunk missing")


def xyz(parent_xyz: list[float], offset: tuple[float, float, float]) -> list[float]:
    return [round(parent_xyz[index] + offset[index], 6) for index in range(3)]


def make_port(entity: str, circuit: str, direction: str, role: str, medium: str) -> dict:
    return {
        "port_id": f"{entity}:{circuit}:{direction}:{role}",
        "object_id": entity,
        "circuit_id": circuit,
        "direction": direction,
        "role": role,
        "medium": medium,
        "status": "candidate_unverified",
    }


def make_connection(connection_id: str, circuit: str, from_port: dict, to_port: dict,
                    medium: str, role: str) -> dict:
    return {
        "connection_id": connection_id,
        "circuit_id": circuit,
        "medium": medium,
        "role": role,
        "from_object_id": from_port["object_id"],
        "to_object_id": to_port["object_id"],
        "from_port_id": from_port["port_id"],
        "to_port_id": to_port["port_id"],
        "status": "candidate_unverified",
    }


def build_zone(parent: dict, prefix: str, zone_label: str, preview_name: str,
               equipment: list[tuple[str, str, str, tuple[float, float, float]]],
               terminal_circuit: str) -> tuple[list[dict], list[dict], list[dict]]:
    parent_id = parent["object_id"]
    parent_xyz = parent["model_root_xyz"]
    heat = f"{prefix}_HEAT"
    control = f"{prefix}_CONTROL"
    objects = []
    ports = []
    connections = []
    preview = f"{ASSET_ROOT}/{preview_name}"
    descriptions = {
        "heat_exchanger": "隔离板换二次侧示意，强调两侧只传热不混水。",
        "pump": "二次侧循环泵示意；流量、扬程与选型待核。",
        "valve": "调节阀与隔离阀示意；控制策略与口径待核。",
        "header": "供回分集水器示意；支路平衡与口径待核。",
        "controller": "PLC 控制柜示意；点表、联锁和通信协议待核。",
        "sensor": "温度/流量测点示意；仪表位置与量程待核。",
        "terminal": "农业用户侧末端示意；负荷、盘管与控制参数待核。",
    }
    for object_id, name, kind, offset in equipment:
        short_name = {
            "heat_exchanger": "板换", "pump": "泵", "valve": "阀", "header": "集管",
            "controller": "PLC", "sensor": "测点", "terminal": object_id.rsplit("_", 1)[-1],
        }[kind]
        circuits = [heat] if kind != "controller" else [control]
        if kind in {"pump", "valve"}:
            circuits = [heat, control]
        objects.append({
            "object_id": object_id,
            "parent_id": parent_id,
            "name": name,
            "short_name": short_name,
            "group": parent["group"],
            "kind": kind,
            "zone_label": zone_label,
            "model_root_xyz": xyz(parent_xyz, offset),
            "model_revision": REVISION,
            "installation_status": "候选规划 · 示意补模 · 未验收投运",
            "model_status": "schematic_built",
            "design_status": "proposed",
            "planning_area": None,
            "model_footprint_m2": None,
            "description": descriptions[kind],
            "gaps": [
                "非厂家采购或施工模型",
                "无实测温度、流量、泵扬程或设备铭牌参数",
                "未完成设施级独立配准与工程水力验算",
            ],
            "preview_url": preview,
            "circuits": circuits,
        })

    def add_port(entity: str, circuit: str, direction: str, role: str, medium: str) -> dict:
        value = make_port(entity, circuit, direction, role, medium)
        ports.append(value)
        return value

    hx_out = add_port(f"{prefix}_HX", heat, "out", "flow", "water")
    hx_in = add_port(f"{prefix}_HX", heat, "in", "flow", "water")
    pump_in = add_port(f"{prefix}_PUMP", heat, "in", "flow", "water")
    pump_out = add_port(f"{prefix}_PUMP", heat, "out", "flow", "water")
    valve_in = add_port(f"{prefix}_VALVE", heat, "in", "flow", "water")
    valve_out = add_port(f"{prefix}_VALVE", heat, "out", "flow", "water")
    header_out = add_port(f"{prefix}_HEADER", heat, "out", "flow", "water")
    header_in = add_port(f"{prefix}_HEADER", heat, "in", "flow", "water")
    ctrl_out = add_port(f"{prefix}_CTRL", control, "out", "signal", "control")
    valve_ctrl = add_port(f"{prefix}_VALVE", control, "in", "signal", "control")
    pump_ctrl = add_port(f"{prefix}_PUMP", control, "in", "signal", "control")

    connections.extend([
        make_connection(f"{prefix}_HX_INTERNAL", heat, hx_out, hx_in, "water", "internal"),
        make_connection(f"{prefix}_PUMP_INTERNAL", heat, pump_in, pump_out, "water", "internal"),
        make_connection(f"{prefix}_VALVE_INTERNAL", heat, valve_in, valve_out, "water", "internal"),
        make_connection(f"{prefix}_EDGE_01", heat, hx_out, pump_in, "water", "supply"),
        make_connection(f"{prefix}_EDGE_02", heat, pump_out, valve_in, "water", "supply"),
        make_connection(f"{prefix}_EDGE_03", heat, valve_out, header_out, "water", "supply"),
        make_connection(f"{prefix}_EDGE_04", heat, header_in, hx_in, "water", "return"),
        make_connection(f"{prefix}_EDGE_05", control, ctrl_out, valve_ctrl, "signal", "control"),
        make_connection(f"{prefix}_EDGE_06", control, ctrl_out, pump_ctrl, "signal", "control"),
    ])

    terminals = [item for item in equipment if item[2] == "terminal"]
    for index, item in enumerate(terminals, start=1):
        entity = item[0]
        terminal_in = add_port(entity, terminal_circuit, "in", "flow", "water")
        terminal_out = add_port(entity, terminal_circuit, "out", "flow", "water")
        connections.append(make_connection(f"{prefix}_{entity.rsplit('_', 1)[-1]}_INTERNAL",
                                            terminal_circuit, terminal_in, terminal_out,
                                            "water", "internal"))
        connections.append(make_connection(f"{prefix}_EDGE_{10 + index}", heat, header_out,
                                            terminal_in, "water", "supply"))
        connections.append(make_connection(f"{prefix}_EDGE_{20 + index}", heat, terminal_out,
                                            header_in, "water", "return"))

    for item in ports:
        item["zone_label"] = zone_label
        item["parent_id"] = parent_id
    for item in connections:
        item["zone_label"] = zone_label
        item["parent_id"] = parent_id
    return objects, ports, connections


def main() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    parents = {item["object_id"]: item for item in registry["objects"]}
    glb = read_glb_document(GLB)
    semantic_roots = {}
    for index, node in enumerate(glb.get("nodes", [])):
        extras = node.get("extras") or {}
        object_id = extras.get("object_id")
        if object_id and extras.get("parent_id") in {"AGRI_014", "AGRI_015"}:
            kind = extras.get("kind")
            if kind in {"heat_exchanger", "pump", "valve", "header", "controller", "sensor", "terminal"}:
                semantic_roots[object_id] = index

    definitions = {
        "AGRI_014": {
            "zone_label": "A区种薯 / 温室",
            "preview": "AGRI_014_A区末端验收.png",
            "equipment": [
                ("AGRI_014_HX", "隔离板换：仅传热不混水", "heat_exchanger", (-8, -112, 2)),
                ("AGRI_014_PUMP", "二次侧循环泵", "pump", (-8, -122, 2)),
                ("AGRI_014_VALVE", "调节阀与隔离阀", "valve", (-8, -132, 2)),
                ("AGRI_014_HEADER", "供回分集水器", "header", (-8, -141, 2)),
                ("AGRI_014_CTRL", "PLC 控制柜", "controller", (34, -132, 2)),
                ("AGRI_014_SENSOR", "温度/流量测点", "sensor", (20, -132, 2)),
                ("AGRI_014_GH1", "种薯温室 GH1", "terminal", (-52, -142, 2)),
                ("AGRI_014_GH2", "种薯温室 GH2", "terminal", (36, -142, 2)),
            ],
            "terminal_circuit": "AGRI_014_HEAT",
        },
        "AGRI_015": {
            "zone_label": "B区番茄 / 草莓",
            "preview": "AGRI_015_B区末端验收.png",
            "equipment": [
                ("AGRI_015_HX", "隔离板换：仅传热不混水", "heat_exchanger", (-8, -72, 2)),
                ("AGRI_015_PUMP", "二次侧循环泵", "pump", (-8, -82, 2)),
                ("AGRI_015_VALVE", "调节阀与隔离阀", "valve", (-8, -92, 2)),
                ("AGRI_015_HEADER", "供回分集水器", "header", (-8, -101, 2)),
                ("AGRI_015_CTRL", "PLC 控制柜", "controller", (34, -92, 2)),
                ("AGRI_015_SENSOR", "温度/流量测点", "sensor", (20, -92, 2)),
                ("AGRI_015_AHU1", "番茄温室 AHU1", "terminal", (-42, -102, 2)),
                ("AGRI_015_AHU2", "草莓温室 AHU2", "terminal", (30, -102, 2)),
            ],
            "terminal_circuit": "AGRI_015_HEAT",
        },
    }
    all_objects, all_ports, all_connections = [], [], []
    zone_records = []
    for parent_id, definition in definitions.items():
        parent = parents[parent_id]
        objects, ports, connections = build_zone(parent, parent_id, definition["zone_label"],
                                                  definition["preview"], definition["equipment"],
                                                  definition["terminal_circuit"])
        all_objects.extend(objects)
        all_ports.extend(ports)
        all_connections.extend(connections)
        zone_records.append({
            "parent_id": parent_id,
            "zone_label": definition["zone_label"],
            "preview_url": f"{ASSET_ROOT}/{definition['preview']}",
            "preview_sha256": sha256(GLB.parent / definition["preview"]),
            "object_ids": [item["object_id"] for item in objects],
            "semantic_root_nodes": {item["object_id"]: semantic_roots.get(item["object_id"]) for item in objects},
        })

    expected_objects = {item["object_id"] for item in all_objects}
    missing_roots = sorted(expected_objects - set(semantic_roots))
    if missing_roots:
        raise ValueError(f"semantic roots missing from GLB: {missing_roots}")
    if len(all_objects) != 16 or len(all_ports) != 30 or len(all_connections) != 30:
        raise ValueError(f"unexpected counts: {len(all_objects)}/{len(all_ports)}/{len(all_connections)}")

    payload = {
        "schema_version": 1,
        "revision": REVISION,
        "requirement_revision": "ui-design-v2+c-zone-completeness-v1+m9-ab-terminals-v1",
        "asset_url": f"{ASSET_ROOT}/AB_terminal_slice.glb",
        "asset_sha256": sha256(GLB),
        "asset_format": "glTF Binary v2",
        "blender_source": "outputs/m9-ab-terminals-v1/乌兰察布_AB末端补模_v1.blend",
        "blender_scene": "05 | 水培育苗",
        "candidate_status": "候选规划 · 示意补模 · 未施工、未投运、未完成水力验算",
        "parent_facilities": [
            {"object_id": "AGRI_014", "name": parents["AGRI_014"]["name"], "zone": "A区"},
            {"object_id": "AGRI_015", "name": parents["AGRI_015"]["name"], "zone": "B区"},
        ],
        "objects": all_objects,
        "ports": all_ports,
        "connections": all_connections,
        "zones": zone_records,
        "rendered_previews": [
            {"path": f"{ASSET_ROOT}/AGRI_014_A区末端验收.png", "sha256": sha256(GLB.parent / "AGRI_014_A区末端验收.png")},
            {"path": f"{ASSET_ROOT}/AGRI_015_B区末端验收.png", "sha256": sha256(GLB.parent / "AGRI_015_B区末端验收.png")},
        ],
        "external_status": "A/B 末端回路仅作为父设施内的候选示意关系展示；未接入城市干线，也未证明现场连通。",
        "hydraulic_validation": "not_run",
        "engineering_gaps": [
            "设施级独立地理配准与控制点未完成",
            "道路、铁路、水域穿越与路网贴合未完成",
            "末端流量、泵扬程、阀门口径和热负荷未完成工程计算",
            "条件电锅炉、PTES 放热及全区剩余设施仍在后续批次",
        ],
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUT), "objects": len(all_objects), "ports": len(all_ports),
                      "connections": len(all_connections), "asset_sha256": payload["asset_sha256"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
