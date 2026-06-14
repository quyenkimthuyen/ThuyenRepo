#!/usr/bin/env python3
"""Scan Altiplano Helm charts and generate manifest.json for the web explorer."""

import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "manifest.json"

SKIP_DIRS = {".git", "node_modules", "helm-explorer", "__pycache__"}
KIND_RE = re.compile(r"^kind:\s*(\S+)", re.MULTILINE | re.IGNORECASE)
API_RE = re.compile(r"^apiVersion:\s*(\S+)", re.MULTILINE)
NAME_RE = re.compile(r"^name:\s*(.+)$", re.MULTILINE)
VERSION_RE = re.compile(r"^version:\s*(.+)$", re.MULTILINE)
DESC_RE = re.compile(r"^description:\s*(.+)$", re.MULTILINE)
DEP_BLOCK_RE = re.compile(
    r"^dependencies:\s*\n((?:\s+-\s+name:.*\n(?:\s+.*\n)*)*)", re.MULTILINE
)
DEP_ITEM_RE = re.compile(
    r"-\s+name:\s*(\S+)\s*\n(?:\s+repository:\s*(.+)\n)?\s+version:\s*(\S+)",
    re.MULTILINE,
)

K8S_KIND_INFO = {
    "Deployment": {"icon": "deploy", "category": "workload", "desc": "Quản lý Pod ứng dụng stateless, rolling update"},
    "StatefulSet": {"icon": "stateful", "category": "workload", "desc": "Workload có identity ổn định, persistent storage"},
    "DaemonSet": {"icon": "daemon", "category": "workload", "desc": "Chạy một Pod trên mỗi Node"},
    "Job": {"icon": "job", "category": "workload", "desc": "Task chạy một lần đến khi hoàn thành"},
    "CronJob": {"icon": "cron", "category": "workload", "desc": "Job theo lịch cron"},
    "Pod": {"icon": "pod", "category": "workload", "desc": "Đơn vị deploy nhỏ nhất trong Kubernetes"},
    "ReplicaSet": {"icon": "rs", "category": "workload", "desc": "Duy trì số lượng Pod replica"},
    "Service": {"icon": "svc", "category": "network", "desc": "Expose ứng dụng qua ClusterIP/NodePort/LoadBalancer"},
    "Ingress": {"icon": "ing", "category": "network", "desc": "HTTP/HTTPS routing từ bên ngoài cluster"},
    "NetworkPolicy": {"icon": "netpol", "category": "network", "desc": "Kiểm soát traffic giữa các Pod"},
    "ConfigMap": {"icon": "cm", "category": "config", "desc": "Cấu hình không nhạy cảm dạng key-value"},
    "Secret": {"icon": "secret", "category": "config", "desc": "Dữ liệu nhạy cảm: password, cert, token"},
    "ExternalSecret": {"icon": "es", "category": "config", "desc": "Đồng bộ secret từ vault bên ngoài (ESO)"},
    "PersistentVolumeClaim": {"icon": "pvc", "category": "storage", "desc": "Yêu cầu storage persistent"},
    "PersistentVolume": {"icon": "pv", "category": "storage", "desc": "Tài nguyên storage trong cluster"},
    "ServiceAccount": {"icon": "sa", "category": "rbac", "desc": "Identity cho Pod truy cập API server"},
    "Role": {"icon": "role", "category": "rbac", "desc": "Quyền namespace-scoped"},
    "RoleBinding": {"icon": "rb", "category": "rbac", "desc": "Gán Role cho subject trong namespace"},
    "ClusterRole": {"icon": "cr", "category": "rbac", "desc": "Quyền cluster-wide"},
    "ClusterRoleBinding": {"icon": "crb", "category": "rbac", "desc": "Gán ClusterRole cho subject"},
    "CustomResourceDefinition": {"icon": "crd", "category": "crd", "desc": "Định nghĩa Custom Resource (CRD)"},
    "HorizontalPodAutoscaler": {"icon": "hpa", "category": "autoscale", "desc": "Tự động scale Pod theo CPU/memory/custom metrics"},
    "PodDisruptionBudget": {"icon": "pdb", "category": "reliability", "desc": "Đảm bảo availability khi disruption"},
    "KongPlugin": {"icon": "kong", "category": "gateway", "desc": "Plugin mở rộng cho Kong API Gateway"},
    "KongIngress": {"icon": "kong", "category": "gateway", "desc": "Cấu hình routing Kong"},
    "HTTPRoute": {"icon": "route", "category": "gateway", "desc": "Gateway API HTTP routing"},
    "TCPIngress": {"icon": "route", "category": "gateway", "desc": "TCP routing qua ingress controller"},
}

TOP_LEVEL_META = {
    "altiplano-solution": {
        "title": "Altiplano Solution",
        "role": "Microservices ứng dụng",
        "desc": "Tập hợp các microservice nghiệp vụ Altiplano: collectors, mediators, engines, adapters và UI.",
        "color": "#00a0e3",
    },
    "altiplano-infra": {
        "title": "Altiplano Infrastructure",
        "role": "Hạ tầng nền tảng",
        "desc": "Kafka, OpenTSDB, Grafana, Kong Ingress, OAuth2, backup/restore, monitoring và các thành phần platform.",
        "color": "#7b68ee",
    },
    "altiplano-crds": {
        "title": "Custom Resource Definitions",
        "role": "CRD & API extensions",
        "desc": "Định nghĩa Custom Resource cho Kong, Gateway, CBUR và các operator.",
        "color": "#ff6b35",
    },
    "altiplano-secrets": {
        "title": "Secrets Management",
        "role": "Quản lý bí mật",
        "desc": "Helm charts tạo và quản lý Kubernetes Secrets cho app và infra.",
        "color": "#e63946",
    },
    "altiplano-certificates": {
        "title": "Certificate Management",
        "role": "PKI & TLS",
        "desc": "CA, client/server certificates, migration secrets cho MariaDB, Kafka và microservices.",
        "color": "#2a9d8f",
    },
    "altiplano-volumeclaims": {
        "title": "Persistent Volume Claims",
        "role": "Storage provisioning",
        "desc": "PVC templates cho databases, Kafka, OpenTSDB và persistent data.",
        "color": "#f4a261",
    },
}


def parse_chart_yaml(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    meta = {
        "name": (NAME_RE.search(text) or [None, path.parent.name])[1].strip().strip('"'),
        "version": (VERSION_RE.search(text) or [None, ""])[1].strip().strip('"'),
        "description": (DESC_RE.search(text) or [None, ""])[1].strip().strip('"'),
        "dependencies": [],
    }
    for m in DEP_ITEM_RE.finditer(text):
        meta["dependencies"].append(
            {"name": m.group(1), "repository": (m.group(2) or "").strip(), "version": m.group(3)}
        )
    return meta


def extract_kinds_from_file(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    resources = []
    # Multi-document YAML separated by ---
    docs = re.split(r"\n---\n", text)
    for doc in docs:
        kind_m = KIND_RE.search(doc)
        if not kind_m:
            continue
        kind = kind_m.group(1).strip().strip('"').strip("'")
        if kind in ("List", "Template", "Helm"):
            continue
        api_m = API_RE.search(doc)
        api_version = api_m.group(1).strip() if api_m else ""
        resources.append(
            {
                "kind": kind,
                "apiVersion": api_version,
                "file": path.name,
                "category": K8S_KIND_INFO.get(kind, {}).get("category", "other"),
            }
        )
    return resources


def scan_templates(chart_dir: Path) -> tuple[list[dict], list[str]]:
    templates_dir = chart_dir / "templates"
    all_resources = []
    template_files = []
    if not templates_dir.is_dir():
        return all_resources, template_files
    for f in sorted(templates_dir.rglob("*")):
        if not f.is_file():
            continue
        if f.suffix not in (".yaml", ".yml", ".tpl"):
            continue
        rel = str(f.relative_to(chart_dir))
        template_files.append(rel)
        if f.suffix == ".tpl":
            continue
        all_resources.extend(extract_kinds_from_file(f))
    return all_resources, template_files


def count_values_keys(values_path: Path, max_depth: int = 2) -> int:
    if not values_path.is_file():
        return 0
    count = 0
    for line in values_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if re.match(r"^[^\s#]", line) and ":" in line:
            count += 1
    return count


def build_directory_tree(base: Path, rel: str = "") -> dict:
    node_id = rel or base.name
    children = []
    chart_meta = None
    is_chart = False
    chart_path = base / "Chart.yaml"
    if chart_path.is_file():
        is_chart = True
        chart_meta = parse_chart_yaml(chart_path)
        resources, templates = scan_templates(base)
        values_count = count_values_keys(base / "values.yaml")
        kind_summary = defaultdict(int)
        for r in resources:
            kind_summary[r["kind"]] += 1
        node_data = {
            "id": node_id,
            "name": base.name,
            "path": rel or base.name,
            "type": "chart",
            "chart": chart_meta,
            "resources": resources,
            "resourceSummary": dict(kind_summary),
            "templateFiles": templates,
            "templateCount": len(templates),
            "valuesKeyCount": values_count,
            "hasValues": (base / "values.yaml").is_file(),
            "children": [],
        }
    else:
        top_meta = TOP_LEVEL_META.get(base.name, {})
        node_data = {
            "id": node_id,
            "name": base.name,
            "path": rel or base.name,
            "type": "folder",
            "meta": top_meta,
            "children": [],
        }

    try:
        entries = sorted(
            [e for e in base.iterdir() if e.is_dir() and e.name not in SKIP_DIRS],
            key=lambda p: p.name.lower(),
        )
    except PermissionError:
        entries = []

    for entry in entries:
        child_rel = f"{rel}/{entry.name}" if rel else entry.name
        # Skip charts/ subfolder handling: still traverse
        child = build_directory_tree(entry, child_rel)
        node_data["children"].append(child)

    # If folder contains charts/ subfolder, mark it
    charts_sub = base / "charts"
    if charts_sub.is_dir() and not is_chart:
        subchart_count = sum(1 for c in charts_sub.iterdir() if (c / "Chart.yaml").is_file())
        node_data["subchartCount"] = subchart_count

    return node_data


def collect_charts_by_name(node: dict, registry: dict) -> None:
    if node.get("type") == "chart" and node.get("chart"):
        name = node["chart"]["name"]
        registry[name].append(
            {"id": node["id"], "path": node["path"], "version": node["chart"]["version"]}
        )
    for child in node.get("children", []):
        collect_charts_by_name(child, registry)


def collect_dependencies(node: dict, links: list) -> None:
    if node.get("type") == "chart" and node.get("chart"):
        for dep in node["chart"].get("dependencies", []):
            links.append(
                {
                    "source": node["id"],
                    "target": dep["name"],
                    "targetName": dep["name"],
                    "type": "dependency",
                    "version": dep["version"],
                }
            )
    for child in node.get("children", []):
        collect_dependencies(child, links)


def flatten_nodes(node: dict, flat: dict) -> None:
    flat[node["id"]] = node
    for child in node.get("children", []):
        flatten_nodes(child, flat)


def compute_stats(flat: dict) -> dict:
    charts = [n for n in flat.values() if n.get("type") == "chart"]
    all_kinds = defaultdict(int)
    total_templates = 0
    for c in charts:
        total_templates += c.get("templateCount", 0)
        for k, v in c.get("resourceSummary", {}).items():
            all_kinds[k] += v
    return {
        "totalCharts": len(charts),
        "totalFolders": len([n for n in flat.values() if n.get("type") == "folder"]),
        "totalTemplates": total_templates,
        "resourceKinds": dict(sorted(all_kinds.items(), key=lambda x: -x[1])),
        "topLevelCharts": len([n for n in flat.values() if n.get("type") == "chart" and "/" not in n["path"]]),
    }


def main():
    print(f"Scanning {ROOT} ...")
    tree_children = []
    for entry in sorted(ROOT.iterdir(), key=lambda p: p.name.lower()):
        if not entry.is_dir() or entry.name in SKIP_DIRS:
            continue
        tree_children.append(build_directory_tree(entry, entry.name))

    root_node = {
        "id": "root",
        "name": ROOT.name,
        "path": "",
        "type": "root",
        "children": tree_children,
    }

    flat = {}
    flatten_nodes(root_node, flat)

    chart_registry = defaultdict(list)
    for child in tree_children:
        collect_charts_by_name(child, chart_registry)

    # Shared charts: same name appears in multiple paths
    shared_charts = {
        name: instances
        for name, instances in chart_registry.items()
        if len(instances) > 1
    }

    dep_links = []
    for child in tree_children:
        collect_dependencies(child, dep_links)

    # Resolve dependency links to actual node IDs where possible
    name_to_ids = chart_registry
    resolved_links = []
    for link in dep_links:
        targets = name_to_ids.get(link["targetName"], [])
        if targets:
            for t in targets:
                resolved_links.append(
                    {
                        **link,
                        "targetId": t["id"],
                        "targetPath": t["path"],
                        "shared": len(targets) > 1,
                    }
                )
        else:
            resolved_links.append({**link, "targetId": None, "targetPath": None, "shared": False})

    stats = compute_stats(flat)

    manifest = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "rootPath": str(ROOT),
        "version": "26.9.0-MAIN_23607",
        "product": "Nokia Altiplano",
        "stats": stats,
        "k8sKindInfo": K8S_KIND_INFO,
        "topLevelMeta": TOP_LEVEL_META,
        "sharedCharts": shared_charts,
        "tree": root_node,
        "flatIndex": {k: {
            "id": v["id"],
            "name": v["name"],
            "path": v["path"],
            "type": v.get("type"),
            "chart": v.get("chart"),
            "resourceSummary": v.get("resourceSummary"),
            "templateCount": v.get("templateCount"),
            "meta": v.get("meta"),
        } for k, v in flat.items()},
        "dependencyLinks": resolved_links,
    }

    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Written {OUT} ({OUT.stat().st_size // 1024} KB)")
    print(f"  Charts: {stats['totalCharts']}, Templates: {stats['totalTemplates']}")
    print(f"  Shared chart names: {len(shared_charts)}")


if __name__ == "__main__":
    main()
