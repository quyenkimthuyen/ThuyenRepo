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


DEFINE_RE = re.compile(r'{{-?\s*define\s+"([^"]+)"')
HIGHLIGHT_KEYS = {
    "replicaCount", "replicas", "enabled", "image", "tag", "pullPolicy",
    "name", "repository", "port", "targetPort", "containerPort", "servicePort",
    "resources", "limits", "requests", "cpu", "memory", "storage",
    "ingress", "host", "tls", "nodeSelector", "tolerations", "affinity",
}


def scan_templates(chart_dir: Path) -> tuple[list[dict], list[str], list[dict]]:
    templates_dir = chart_dir / "templates"
    all_resources = []
    template_files = []
    template_details = []
    if not templates_dir.is_dir():
        return all_resources, template_files, template_details
    for f in sorted(templates_dir.rglob("*")):
        if not f.is_file():
            continue
        if f.suffix not in (".yaml", ".yml", ".tpl"):
            continue
        rel = str(f.relative_to(chart_dir))
        template_files.append(rel)
        text = f.read_text(encoding="utf-8", errors="replace")
        kinds_in_file = []
        if f.suffix != ".tpl":
            kinds_in_file = list({r["kind"] for r in extract_kinds_from_file(f)})
            all_resources.extend(extract_kinds_from_file(f))
        defines = DEFINE_RE.findall(text) if f.suffix == ".tpl" else []
        template_details.append({
            "path": rel,
            "lines": text.count("\n") + 1,
            "size": len(text.encode("utf-8")),
            "kinds": kinds_in_file,
            "defines": defines,
            "isHelper": f.name.startswith("_"),
            "hasHelm": "{{" in text or "}}" in text,
        })
    return all_resources, template_files, template_details


def parse_values_tree(values_path: Path, max_depth: int = 5, max_keys: int = 80) -> list:
    if not values_path.is_file():
        return []
    tree = []
    stack = [(0, tree)]

    for line in values_path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.split("#", 1)[0].rstrip()
        if not stripped.strip() or ":" not in stripped:
            continue
        indent = len(stripped) - len(stripped.lstrip())
        depth = indent // 2
        if depth >= max_depth:
            continue
        key, _, val = stripped.strip().partition(":")
        key = key.strip().strip('"').strip("'")
        val = val.strip().strip('"').strip("'")
        if not key:
            continue

        node = {"key": key, "depth": depth}
        if val and not val.startswith("{") and val not in ("|", ">"):
            node["value"] = val[:120]
        node["children"] = []

        while stack and stack[-1][0] >= depth:
            stack.pop()
        if stack:
            parent_children = stack[-1][1]
            if len(parent_children) < max_keys:
                parent_children.append(node)
                stack.append((depth, node["children"]))
    return tree


def extract_values_highlights(values_path: Path) -> list[dict]:
    if not values_path.is_file():
        return []
    highlights = []
    path_stack = []

    for line in values_path.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = line.split("#", 1)[0].rstrip()
        if not raw.strip() or ":" not in raw:
            continue
        indent = len(raw) - len(raw.lstrip())
        depth = indent // 2
        key, _, val = raw.strip().partition(":")
        key = key.strip().strip('"').strip("'")
        val = val.strip().strip('"').strip("'")

        while len(path_stack) > depth:
            path_stack.pop()
        path_stack.append(key)
        full_key = ".".join(path_stack)

        if key in HIGHLIGHT_KEYS or any(k in full_key for k in ("image", "replica", "enabled", "port", "resources")):
            if val and val not in ("|", ">", "{", "}"):
                highlights.append({"key": full_key, "value": val[:200]})
    return highlights[:40]


def list_chart_files(chart_dir: Path) -> list[dict]:
    files = []
    for name in ("Chart.yaml", "values.yaml", "values.schema.json", "README.md", "NOTES.txt"):
        p = chart_dir / name
        if p.is_file():
            files.append({"name": name, "size": p.stat().st_size, "lines": p.read_text(encoding="utf-8", errors="replace").count("\n") + 1})
    charts_dir = chart_dir / "charts"
    if charts_dir.is_dir():
        subcharts = [d.name for d in charts_dir.iterdir() if d.is_dir() and (d / "Chart.yaml").is_file()]
        if subcharts:
            files.append({"name": "charts/", "subcharts": sorted(subcharts), "count": len(subcharts)})
    return files


def build_deploy_flow(resources: list[dict]) -> list[dict]:
    order = [
        ("ServiceAccount", "rbac", "Tạo identity cho Pod"),
        ("Role", "rbac", "Định nghĩa quyền namespace"),
        ("ClusterRole", "rbac", "Định nghĩa quyền cluster"),
        ("RoleBinding", "rbac", "Gán Role → ServiceAccount"),
        ("ClusterRoleBinding", "rbac", "Gán ClusterRole → subject"),
        ("ConfigMap", "config", "Inject cấu hình vào container"),
        ("Secret", "config", "Mount credentials / TLS"),
        ("ExternalSecret", "config", "Đồng bộ secret từ Vault"),
        ("PersistentVolumeClaim", "storage", "Cấp phát disk persistent"),
        ("Deployment", "workload", "Chạy container ứng dụng"),
        ("StatefulSet", "workload", "Workload có state + PVC"),
        ("DaemonSet", "workload", "Agent trên mỗi Node"),
        ("Job", "workload", "Task một lần (migration, init)"),
        ("CronJob", "workload", "Task định kỳ"),
        ("Service", "network", "ClusterIP / headless discovery"),
        ("Ingress", "network", "HTTP routing từ gateway"),
        ("HTTPRoute", "network", "Gateway API route"),
        ("TCPIngress", "network", "TCP passthrough"),
        ("KongPlugin", "gateway", "Auth, rate-limit, transform"),
        ("HorizontalPodAutoscaler", "autoscale", "Auto-scale theo metrics"),
        ("PodDisruptionBudget", "reliability", "Bảo vệ availability"),
    ]
    present = defaultdict(list)
    for r in resources:
        present[r["kind"]].append(r["file"])

    flow = []
    seen = set()
    for kind, cat, desc in order:
        if kind in present:
            flow.append({
                "kind": kind,
                "category": cat,
                "desc": desc,
                "files": list(set(present[kind])),
            })
            seen.add(kind)
    for kind, files in present.items():
        if kind not in seen:
            info = K8S_KIND_INFO.get(kind, {})
            flow.append({
                "kind": kind,
                "category": info.get("category", "other"),
                "desc": info.get("desc", ""),
                "files": list(set(files)),
            })
    return flow


# ── Helm command generation ──────────────────────────────────────────────────

NS = "<namespace>"
VALUES_FILE = "custom-values.yaml"

PLATFORM_CHARTS = {
    "altiplano-crds": {
        "order": 1,
        "desc": "Bước 1 — Cài Custom Resource Definitions (Kong, Gateway, CBUR…). Bắt buộc trước các chart khác.",
    },
    "altiplano-secrets": {
        "order": 2,
        "desc": "Bước 2 — Tạo Kubernetes Secrets: certificates, passwords, tokens.",
    },
    "altiplano-volumeclaims": {
        "order": 3,
        "desc": "Bước 3 — Provision PersistentVolumeClaims cho DB, Kafka, OpenTSDB.",
    },
    "altiplano-infra": {
        "order": 4,
        "desc": "Bước 4 — Hạ tầng: Kafka, MariaDB, Grafana, Kong Ingress, OpenTSDB, Valkey…",
    },
    "altiplano-solution": {
        "order": 5,
        "desc": "Bước 5 — Microservices nghiệp vụ Altiplano (collectors, engines, adapters, UI).",
    },
}

HELM_CMD_LINE_RE = re.compile(
    r"(?:^|[\n`])\s*\$?\s*(helm\s+(?:upgrade|install|uninstall|template|show|lint|dependency|pull|package)[^\n`]+)",
    re.IGNORECASE | re.MULTILINE,
)

_parent_enable_cache: dict[str, dict] = {}


def parse_parent_enable_config(parent_path: str) -> dict:
    if parent_path in _parent_enable_cache:
        return _parent_enable_cache[parent_path]
    values_path = ROOT / parent_path / "values.yaml"
    config = {"tags": {}, "globalKeys": []}
    if not values_path.is_file():
        _parent_enable_cache[parent_path] = config
        return config

    text = values_path.read_text(encoding="utf-8", errors="replace")
    tags_block = re.search(r"^tags:\s*\n((?:  .+\n)*)", text, re.MULTILINE)
    if tags_block:
        for line in tags_block.group(1).splitlines():
            m = re.match(r"  ([\w.-]+):\s*(true|false)", line)
            if m:
                config["tags"][m.group(1)] = m.group(2) == "true"

    for m in re.finditer(r"^  ([a-zA-Z][\w.-]*):\s*$", text, re.MULTILINE):
        key = m.group(1)
        if key not in ("tags", "global", "localsecret", "secretstore", "externalsecret", "ingress"):
            config["globalKeys"].append(key)

    _parent_enable_cache[parent_path] = config
    return config


def find_tag_key(chart_name: str, parent_config: dict) -> str | None:
    tags = parent_config.get("tags", {})
    if chart_name in tags:
        return chart_name
    for tag in tags:
        if tag in chart_name or chart_name in tag:
            return tag
    return None


def analyze_chart_path(path: str) -> dict:
    parts = path.split("/")
    chart_indices = [i for i, p in enumerate(parts) if p == "charts"]
    if not chart_indices:
        return {
            "mode": "platform",
            "umbrella": path.split("/")[-1],
            "umbrellaPath": path,
            "depth": 0,
        }
    first_idx = chart_indices[0]
    umbrella_path = "/".join(parts[:first_idx])
    umbrella = parts[first_idx - 1] if first_idx > 0 else parts[0]
    if len(chart_indices) == 1:
        return {
            "mode": "umbrella-subchart",
            "umbrella": umbrella,
            "umbrellaPath": umbrella_path,
            "depth": 1,
        }
    parent_path = "/".join(parts[:chart_indices[-1]])
    parent_name = parts[chart_indices[-1] - 1]
    return {
        "mode": "nested-subchart",
        "umbrella": umbrella,
        "umbrellaPath": umbrella_path,
        "parentChart": parent_name,
        "parentPath": parent_path,
        "depth": len(chart_indices),
    }


def extract_readme_helm_commands(chart_dir: Path) -> list[str]:
    cmds = []
    for fname in ("README.md", "readme.md", "Readme.md"):
        readme = chart_dir / fname
        if not readme.is_file():
            continue
        text = readme.read_text(encoding="utf-8", errors="replace")
        for m in HELM_CMD_LINE_RE.finditer(text):
            cmd = re.sub(r"\s+", " ", m.group(1).strip())
            cmd = cmd.replace(" --name ", " ").replace("--name ", "")
            if 10 < len(cmd) < 300:
                cmds.append(cmd)
        break
    return list(dict.fromkeys(cmds))[:6]


def _cmd(id_: str, title: str, cmd: str, desc: str = "", category: str = "deploy") -> dict:
    return {"id": id_, "title": title, "cmd": cmd, "desc": desc, "category": category}


def build_helm_commands(
    node: dict,
    shared_charts: dict,
    chart_registry: dict,
) -> dict:
    path = node["path"]
    chart_name = node["chart"]["name"]
    chart_dir = ROOT / path
    ctx = analyze_chart_path(path)
    readme_cmds = extract_readme_helm_commands(chart_dir)
    commands = []
    notes = []

    is_library = chart_name in shared_charts and ctx["depth"] >= 1
    is_platform = ctx["mode"] == "platform" and chart_name in PLATFORM_CHARTS

    if is_library:
        deploy_mode = "library"
        notes.append("Library chart — không deploy trực tiếp trong production Altiplano.")
        notes.append(f"Được nhúng vào {len(shared_charts[chart_name])} vị trí trong cây Helm.")
        umbrella_path = ctx.get("umbrellaPath") or path.rsplit("/charts/", 1)[0]
        commands.extend([
            _cmd(
                "dep-build",
                "Build dependencies (parent chart)",
                f"helm dependency build ./{umbrella_path}",
                "Tải/update subcharts trước khi install umbrella chart.",
                "utility",
            ),
            _cmd(
                "template-lib",
                "Render template (debug library)",
                f"helm template {chart_name} ./{path} -f {VALUES_FILE}",
                "Chỉ dùng khi debug template của library chart.",
                "debug",
            ),
        ])
    elif is_platform:
        deploy_mode = "platform"
        pinfo = PLATFORM_CHARTS[chart_name]
        notes.append(pinfo["desc"])
        notes.append(f"Thứ tự cài đặt platform: #{pinfo['order']} trong chuỗi deploy Altiplano.")
        release = chart_name
        commands.extend([
            _cmd(
                "install",
                "Install / Upgrade (production)",
                f"helm upgrade --install {release} ./{path} \\\n"
                f"  --namespace {NS} --create-namespace \\\n"
                f"  -f {VALUES_FILE} \\\n"
                f"  --wait --timeout 30m",
                "Lệnh deploy chính cho chart platform.",
            ),
            _cmd(
                "install-dry",
                "Dry-run (không apply)",
                f"helm upgrade --install {release} ./{path} \\\n"
                f"  --namespace {NS} -f {VALUES_FILE} \\\n"
                f"  --dry-run --debug",
                "Kiểm tra manifest trước khi deploy thật.",
                "debug",
            ),
            _cmd(
                "template",
                "Render manifests ra file",
                f"helm template {release} ./{path} \\\n"
                f"  --namespace {NS} -f {VALUES_FILE} \\\n"
                f"  > rendered-{chart_name}.yaml",
                "Xuất toàn bộ YAML để review.",
                "debug",
            ),
            _cmd(
                "show-values",
                "Xem values mặc định",
                f"helm show values ./{path}",
                category="utility",
            ),
            _cmd(
                "lint",
                "Lint chart",
                f"helm lint ./{path} -f {VALUES_FILE}",
                category="utility",
            ),
            _cmd(
                "history",
                "Xem lịch sử release",
                f"helm history {release} -n {NS}",
                category="utility",
            ),
            _cmd(
                "rollback",
                "Rollback phiên bản trước",
                f"helm rollback {release} -n {NS}",
                "Quay về revision trước nếu upgrade lỗi.",
                "ops",
            ),
            _cmd(
                "uninstall",
                "Gỡ cài đặt",
                f"helm uninstall {release} -n {NS}",
                "⚠ Xóa toàn bộ resources do chart quản lý.",
                "ops",
            ),
        ])
    elif ctx["mode"] == "umbrella-subchart":
        deploy_mode = "umbrella-subchart"
        umbrella = ctx["umbrella"]
        umbrella_path = ctx["umbrellaPath"]
        parent_cfg = parse_parent_enable_config(umbrella_path)
        tag_key = find_tag_key(chart_name, parent_cfg)
        global_key = chart_name if chart_name in parent_cfg.get("globalKeys", []) else chart_name

        notes.append(f"Subchart của umbrella <strong>{umbrella}</strong> — deploy qua parent chart.")
        notes.append("Trong production Nokia Altiplano, microservice KHÔNG deploy riêng lẻ.")
        if tag_key:
            notes.append(f"Enable bằng tag: <code>tags.{tag_key}: true</code>")
        notes.append(f"Hoặc trong values: <code>global.{global_key}.enabled: true</code>")

        set_flags = []
        if tag_key:
            set_flags.append(f"--set tags.{tag_key}=true")
        set_flags.append(f"--set global.{global_key}.enabled=true")
        set_line = " \\\n  ".join(set_flags)

        commands.extend([
            _cmd(
                "via-umbrella",
                "Deploy qua umbrella chart (khuyến nghị)",
                f"helm upgrade --install {umbrella} ./{umbrella_path} \\\n"
                f"  --namespace {NS} --create-namespace \\\n"
                f"  -f {VALUES_FILE} \\\n"
                f"  {set_line} \\\n"
                f"  --wait --timeout 30m",
                f"Bật {chart_name} trong lần upgrade umbrella {umbrella}.",
            ),
            _cmd(
                "enable-values",
                "Enable trong values.yaml",
                f"# Thêm vào {VALUES_FILE} (override):\n"
                f"tags:\n  {tag_key or chart_name}: true\n"
                f"global:\n  {global_key}:\n    enabled: true",
                "Cách enable ổn định — giữ cấu hình trong Git.",
                "config",
            ),
            _cmd(
                "template-umbrella",
                "Render subchart qua umbrella",
                f"helm template {umbrella} ./{umbrella_path} \\\n"
                f"  --namespace {NS} -f {VALUES_FILE} \\\n"
                f"  {set_line} | grep -A5 'kind:'",
                "Render toàn bộ umbrella rồi lọc resource của subchart.",
                "debug",
            ),
            _cmd(
                "standalone-dev",
                "Deploy riêng lẻ (dev/test)",
                f"helm upgrade --install {chart_name} ./{path} \\\n"
                f"  --namespace {NS} --create-namespace \\\n"
                f"  -f {VALUES_FILE}",
                "⚠ Thiếu global values từ parent — chỉ dùng debug chart độc lập.",
                "debug",
            ),
            _cmd(
                "template-standalone",
                "Template riêng subchart",
                f"helm template {chart_name} ./{path} -f {VALUES_FILE}",
                category="debug",
            ),
            _cmd(
                "show-values",
                "Xem values subchart",
                f"helm show values ./{path}",
                category="utility",
            ),
        ])
    elif ctx["mode"] == "nested-subchart":
        deploy_mode = "nested-subchart"
        parent_path = ctx["parentPath"]
        parent_name = ctx["parentChart"]
        umbrella = ctx["umbrella"]
        umbrella_path = ctx["umbrellaPath"]
        notes.append(f"Nested subchart — con của <strong>{parent_name}</strong> trong {umbrella}.")
        if chart_name in shared_charts:
            notes.append("Đồng thời là shared library chart.")
        commands.extend([
            _cmd(
                "via-parent",
                "Deploy qua parent chart",
                f"helm upgrade --install {parent_name} ./{parent_path} \\\n"
                f"  --namespace {NS} -f {VALUES_FILE}",
                f"Subchart {chart_name} render khi parent {parent_name} được deploy.",
            ),
            _cmd(
                "via-umbrella",
                "Deploy qua umbrella chart",
                f"helm upgrade --install {umbrella} ./{umbrella_path} \\\n"
                f"  --namespace {NS} -f {VALUES_FILE} --wait",
                f"Deploy toàn bộ {umbrella} bao gồm {parent_name} → {chart_name}.",
            ),
            _cmd(
                "template",
                "Template nested subchart",
                f"helm template {chart_name} ./{path} -f {VALUES_FILE}",
                category="debug",
            ),
        ])
    else:
        deploy_mode = "standalone"
        notes.append("Chart độc lập — có thể deploy trực tiếp.")
        commands.extend([
            _cmd(
                "install",
                "Install / Upgrade",
                f"helm upgrade --install {chart_name} ./{path} \\\n"
                f"  --namespace {NS} --create-namespace \\\n"
                f"  -f {VALUES_FILE} --wait",
            ),
            _cmd(
                "template",
                "Render manifests",
                f"helm template {chart_name} ./{path} -f {VALUES_FILE}",
                category="debug",
            ),
            _cmd(
                "show-values",
                "Show values",
                f"helm show values ./{path}",
                category="utility",
            ),
        ])

    # Dependency commands if Chart.yaml has dependencies
    deps = node["chart"].get("dependencies", [])
    if deps:
        commands.append(_cmd(
            "dep-update",
            "Cập nhật Helm dependencies",
            f"helm dependency update ./{path}\nhelm dependency list ./{path}",
            f"Dependencies: {', '.join(d['name'] for d in deps)}",
            "utility",
        ))

    return {
        "deployMode": deploy_mode,
        "context": ctx,
        "platformOrder": PLATFORM_CHARTS.get(chart_name, {}).get("order"),
        "umbrellaChart": ctx.get("umbrella"),
        "umbrellaPath": ctx.get("umbrellaPath"),
        "tagKey": find_tag_key(chart_name, parse_parent_enable_config(ctx.get("umbrellaPath", ""))) if ctx.get("umbrellaPath") else None,
        "commands": commands,
        "readmeCommands": readme_cmds,
        "notes": notes,
    }


def enrich_helm_commands(node: dict, shared_charts: dict, chart_registry: dict) -> None:
    if node.get("type") == "chart":
        node["helmCommands"] = build_helm_commands(node, shared_charts, chart_registry)
    for child in node.get("children", []):
        enrich_helm_commands(child, shared_charts, chart_registry)


def count_values_keys(values_path: Path, max_depth: int = 2) -> int:
    if not values_path.is_file():
        return 0
    count = 0
    for line in values_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if re.match(r"^[^\s#]", line) and ":" in line:
            count += 1
    return count


def group_resources_by_category(resources: list[dict]) -> dict:
    grouped = defaultdict(lambda: {"kinds": defaultdict(int), "total": 0})
    for r in resources:
        cat = r.get("category") or K8S_KIND_INFO.get(r["kind"], {}).get("category", "other")
        grouped[cat]["kinds"][r["kind"]] += 1
        grouped[cat]["total"] += 1
    return {k: {"kinds": dict(v["kinds"]), "total": v["total"]} for k, v in grouped.items()}


def build_directory_tree(base: Path, rel: str = "") -> dict:
    node_id = rel or base.name
    children = []
    chart_meta = None
    is_chart = False
    chart_path = base / "Chart.yaml"
    if chart_path.is_file():
        is_chart = True
        chart_meta = parse_chart_yaml(chart_path)
        resources, templates, template_details = scan_templates(base)
        values_path = base / "values.yaml"
        values_count = count_values_keys(values_path)
        kind_summary = defaultdict(int)
        for r in resources:
            kind_summary[r["kind"]] += 1
        helpers = [t for t in template_details if t.get("defines")]
        all_defines = []
        for t in template_details:
            all_defines.extend(t["defines"])
        node_data = {
            "id": node_id,
            "name": base.name,
            "path": rel or base.name,
            "type": "chart",
            "chart": chart_meta,
            "resources": resources,
            "resourceSummary": dict(kind_summary),
            "resourcesByCategory": group_resources_by_category(resources),
            "templateFiles": templates,
            "templateDetails": template_details,
            "templateCount": len(templates),
            "valuesKeyCount": values_count,
            "hasValues": values_path.is_file(),
            "valuesTree": parse_values_tree(values_path),
            "valuesHighlights": extract_values_highlights(values_path),
            "chartFiles": list_chart_files(base),
            "helmDefines": sorted(set(all_defines)),
            "deployFlow": build_deploy_flow(resources),
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

    # Post-process: helm commands per chart
    enrich_helm_commands(root_node, shared_charts, chart_registry)
    flatten_nodes(root_node, flat)

    platform_install_sequence = [
        {
            "order": v["order"],
            "chart": k,
            "path": k,
            "desc": v["desc"],
            "command": (
                f"helm upgrade --install {k} ./{k} "
                f"--namespace {NS} --create-namespace -f {VALUES_FILE} --wait --timeout 30m"
            ),
        }
        for k, v in sorted(PLATFORM_CHARTS.items(), key=lambda x: x[1]["order"])
    ]

    manifest = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "rootPath": str(ROOT),
        "version": "26.9.0-MAIN_23607",
        "product": "Nokia Altiplano",
        "stats": stats,
        "k8sKindInfo": K8S_KIND_INFO,
        "topLevelMeta": TOP_LEVEL_META,
        "platformInstallSequence": platform_install_sequence,
        "sharedCharts": shared_charts,
        "tree": root_node,
        "flatIndex": {k: {
            "id": v["id"],
            "name": v["name"],
            "path": v["path"],
            "type": v.get("type"),
            "chart": v.get("chart"),
            "resourceSummary": v.get("resourceSummary"),
            "resourcesByCategory": v.get("resourcesByCategory"),
            "templateCount": v.get("templateCount"),
            "valuesHighlights": v.get("valuesHighlights"),
            "helmCommands": v.get("helmCommands"),
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
