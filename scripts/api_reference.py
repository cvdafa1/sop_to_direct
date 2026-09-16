"""Direct 平台 REST API 客户端（技能唯一调用入口）

Agent / 脚本对平台的 create / save / compile / 查询，必须经 DirectPlatformClient，
禁止在技能流程外自构 HTTP URL 或 procedure payload。

用法:
    from api_reference import DirectPlatformClient
    client = DirectPlatformClient()

    # 不含子程序（名称仅 [A-Za-z0-9_]）
    appid = client.create_program(program_name="test_proc", description="描述")
    client.save_program(appid=appid, xml_content=xml_string, description="描述", program_name="test_proc")
    # 含计时器 / 程序变量时可显式传入，或省略由 XML 自动提取
    # client.save_program(..., timers=[...], variables=[{"name":"BL","dataType":1}])
    client.compile_program(appid=appid)

    # 含子程序
    appid = client.create_program(program_name="main_proc", description="描述")
    sub_ids = [client.get_next_id(id_type=0) for _ in range(2)]
    subprograms = [
        {"id": sub_ids[0], "xml_content": sub1_xml, "name": "sub1"},
        {"id": sub_ids[1], "xml_content": sub2_xml, "name": "sub2"},
    ]
    client.save_program(appid=appid, xml_content=main_xml, description="描述",
                        program_name="main_proc", subprograms=subprograms)
    client.compile_program(appid=appid)
"""

# 标准库导入
import hashlib
import os
import re
import time
from functools import wraps

# 第三方库导入
import requests
from requests.exceptions import Timeout, ConnectionError, RequestException


# API 配置：优先环境变量；未设置或为空时用默认值（本环境默认可用，禁止因未设 env 而拒绝 create/save）
_DEFAULT_BASE_URL = "http://direct-proxy/"
_DEFAULT_AUTH_TOKEN = ""  # 经 direct-proxy 时由代理侧鉴权

BASE_URL = (os.environ.get("DIRECT_BASE_URL") or _DEFAULT_BASE_URL).rstrip("/") + "/"
AUTH_TOKEN = os.environ.get("DIRECT_AUTH_TOKEN") or _DEFAULT_AUTH_TOKEN
REQUEST_TIMEOUT = 60
HEADERS = {
    "Accept-Language": "zh-CN",
    "Authorization": AUTH_TOKEN,
    "Content-Type": "application/json",
}

# 引用程序计时器变量的元件（须在 sfc.timers.list 声明；timer:wait/clock 不需要）
TIMER_VAR_ELEMENTS = frozenset({
    "timer:start",
    "timer:stop",
    "timer:pause",
    "timer:restart",
    "timer:cond",
})


# 主程序名 / 子程序名 / 计时器名 / 程序变量名：仅字母、数字、下划线（同一规则，必须遵守）
_IDENT_NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")
_IDENT_SAFE_RE = re.compile(r"[^A-Za-z0-9_]+")


def is_valid_ident_name(name: str) -> bool:
    return bool(name) and bool(_IDENT_NAME_RE.fullmatch(name))


def validate_ident_name(name: str, kind: str = "name") -> str:
    """标识符名：仅允许 [A-Za-z0-9_]。

    适用于：主程序 program_name、子程序 name、timers[].name、variables[].name。
    """
    if not is_valid_ident_name(name):
        raise ValueError(
            f"invalid {kind} {name!r}: only letters, digits, underscore allowed "
            f"(same rule for main/sub program, timers, and variables)"
        )
    return name


def sanitize_ident_name(name: str, *, fallback_prefix: str = "n") -> str:
    """将任意字符串改写为合法标识符 [A-Za-z0-9_]。

    非法字符替换为 `_`；若结果为空、过短或无字母（常见于中文名），
    则用 ``{prefix}_{md5前8}``。
    """
    raw = (name or "").strip()
    had_illegal = bool(_IDENT_SAFE_RE.search(raw))
    cleaned = _IDENT_SAFE_RE.sub("_", raw)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    prefix = fallback_prefix if is_valid_ident_name(fallback_prefix) else "n"
    if (
        not cleaned
        or (had_illegal and (len(cleaned) < 2 or not re.search(r"[A-Za-z]", cleaned)))
    ):
        digest = hashlib.md5(raw.encode("utf-8")).hexdigest()[:8]
        cleaned = f"{prefix}_{digest}"
    return cleaned


def ensure_ident_name(name: str, kind: str = "name", *, fallback_prefix: str = "n") -> str:
    """合法则原样返回，否则 sanitize。"""
    s = (name or "").strip()
    if is_valid_ident_name(s):
        return s
    return sanitize_ident_name(s, fallback_prefix=fallback_prefix)


def validate_program_name(name: str) -> str:
    """主程序 / 子程序名称校验（与 timers/variables 同规则）。"""
    return validate_ident_name(name, kind="program name")


def strip_timer_ref(ref: str) -> str:
    """$(JSQ1) / JSQ1 → JSQ1"""
    s = (ref or "").strip()
    if s.startswith("$(") and s.endswith(")"):
        return s[2:-1].strip()
    return s


def validate_timer_name(name: str) -> str:
    return validate_ident_name(name, kind="timer name")


def unique_rename_map(
    raw_names: list[str], *, fallback_prefix: str
) -> dict[str, str]:
    """old→new；已合法的不变；冲突时追加 _2/_3…"""
    mapping: dict[str, str] = {}
    used: set[str] = set()
    for raw in raw_names:
        if raw in mapping:
            continue
        if is_valid_ident_name(raw):
            base = raw
        else:
            base = sanitize_ident_name(raw, fallback_prefix=fallback_prefix)
        cand = base
        n = 2
        while cand in used:
            cand = f"{base}_{n}"
            n += 1
        used.add(cand)
        mapping[raw] = cand
    return mapping


def collect_xml_ident_names(xml_content: str) -> dict[str, list[str]]:
    """从 XML 收集子程序 / 计时器 / 程序变量裸名（可能含非法名）。

    返回 {"subproc": [...], "timer": [...], "variable": [...]}（去重保序）。
    """
    if not xml_content:
        return {"subproc": [], "timer": [], "variable": []}

    def _uniq(seq: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for x in seq:
            if x in seen:
                continue
            seen.add(x)
            out.append(x)
        return out

    subprocs = [r["name"] for r in extract_subproc_refs(xml_content)]
    timers: list[str] = []
    for m in re.finditer(r'"timer"\s*:\s*"(\$\([^"]+\)|[^"]+)"', xml_content):
        timers.append(strip_timer_ref(m.group(1)))

    timer_set = set(timers)
    variables: list[str] = []
    for m in re.finditer(r"\$\(([^)]+)\)", xml_content):
        name = m.group(1).strip()
        if not name or name in timer_set:
            continue
        variables.append(name)

    return {
        "subproc": _uniq(subprocs),
        "timer": _uniq(timers),
        "variable": _uniq(variables),
    }


def extract_subproc_refs(xml_content: str) -> list[dict]:
    """主程序 XML 中的 flow:subproc 引用：[{name, subId}, ...]（文档顺序）。"""
    if not xml_content:
        return []
    refs: list[dict] = []
    for m in re.finditer(r"<flow:subproc\b([^>]*)>", xml_content):
        attrs = m.group(1)
        nm = re.search(r'\bname="([^"]*)"', attrs)
        sid = re.search(r'\bsubId="([^"]*)"', attrs)
        refs.append({
            "name": (nm.group(1).strip() if nm else ""),
            "subId": (sid.group(1).strip() if sid else ""),
        })
    return refs


def check_split_bundle(main_xml: str, subprograms: list | None) -> list[str]:
    """拆分保存一致性：主 XML 必须引用全部子程序，且每个子程序有非空 XML。

    返回错误列表（空=通过）。
    """
    errors: list[str] = []
    refs = extract_subproc_refs(main_xml or "")
    subs = list(subprograms or [])

    if not refs and not subs:
        return errors

    if refs and not subs:
        errors.append(
            "main XML has flow:subproc but subprograms is empty; "
            "split mode requires main XML + each sub XML"
        )
        return errors

    if subs and not refs:
        errors.append(
            "subprograms provided but main XML has no flow:subproc; "
            "main must reference every subprocess"
        )
        return errors

    if len(refs) != len(subs):
        errors.append(
            f"flow:subproc count ({len(refs)}) != subprograms count ({len(subs)})"
        )

    by_id: dict[str, dict] = {}
    for i, sub in enumerate(subs):
        sid = str(sub.get("id") or "").strip()
        sname = str(sub.get("name") or "").strip()
        sxml = sub.get("xml_content") or ""
        if not sid:
            errors.append(f"subprograms[{i}] missing id")
            continue
        if not sname:
            errors.append(f"subprograms[{i}] missing name")
        if not str(sxml).strip():
            errors.append(f"subprograms[{i}] ({sname or sid}) missing xml_content")
        if sid in by_id:
            errors.append(f"duplicate subprograms id {sid!r}")
        by_id[sid] = sub

    seen_ids: set[str] = set()
    for i, ref in enumerate(refs):
        name, sid = ref["name"], ref["subId"]
        if not name:
            errors.append(f"flow:subproc[{i}] missing name")
        if not sid:
            errors.append(f"flow:subproc[{i}] missing subId")
            continue
        if sid in seen_ids:
            errors.append(f"duplicate flow:subproc subId {sid!r}")
        seen_ids.add(sid)
        sub = by_id.get(sid)
        if not sub:
            errors.append(
                f"flow:subproc name={name!r} subId={sid!r} has no matching "
                f"subprograms[].id"
            )
            continue
        sub_name = ensure_ident_name(
            str(sub.get("name") or ""), fallback_prefix="sub"
        )
        ref_name = ensure_ident_name(name, fallback_prefix="sub") if name else ""
        if name and sub_name != ref_name:
            errors.append(
                f"flow:subproc name={name!r} != subprograms name="
                f"{sub.get('name')!r} (subId={sid})"
            )

    for sid, sub in by_id.items():
        if sid not in seen_ids:
            errors.append(
                f"subprograms id={sid!r} name={sub.get('name')!r} "
                f"not referenced by any flow:subproc in main XML"
            )

    return errors


def find_invalid_xml_idents(xml_content: str) -> list[tuple[str, str]]:
    """返回 [(kind, raw_name), ...]，kind 为 subproc|timer|variable。"""
    issues: list[tuple[str, str]] = []
    collected = collect_xml_ident_names(xml_content)
    for kind, names in collected.items():
        for name in names:
            if not is_valid_ident_name(name):
                issues.append((kind, name))
    return issues


def sanitize_xml_ident_names(xml_content: str) -> tuple[str, list[tuple[str, str, str]]]:
    """改写 XML 内非法的子程序/计时器/变量名。

    返回 (new_xml, [(kind, old, new), ...])；无改动时 renames 为空。
    """
    if not xml_content:
        return xml_content, []

    collected = collect_xml_ident_names(xml_content)
    renames: list[tuple[str, str, str]] = []
    text = xml_content

    sub_map = unique_rename_map(collected["subproc"], fallback_prefix="sub")
    for old, new in sub_map.items():
        if old == new:
            continue
        renames.append(("subproc", old, new))

        def _sub_repl(m: re.Match, _old=old, _new=new) -> str:
            attrs = m.group(1)
            attrs2 = re.sub(
                rf'(\bname=")({re.escape(_old)})(")',
                rf"\g<1>{_new}\3",
                attrs,
                count=1,
            )
            return f"<flow:subproc{attrs2}>"

        text = re.sub(r"<flow:subproc\b([^>]*)>", _sub_repl, text)

    # 计时器与变量共用 $() 改写；先合并映射再统一替换
    tm_map = unique_rename_map(collected["timer"], fallback_prefix="tm")
    # 变量改写时避开已占用的计时器新名
    used_after_tm = set(tm_map.values())
    var_map: dict[str, str] = {}
    for raw in collected["variable"]:
        if raw in var_map:
            continue
        if is_valid_ident_name(raw) and raw not in used_after_tm:
            var_map[raw] = raw
            used_after_tm.add(raw)
            continue
        base = (
            raw
            if is_valid_ident_name(raw)
            else sanitize_ident_name(raw, fallback_prefix="var")
        )
        cand = base
        n = 2
        while cand in used_after_tm:
            cand = f"{base}_{n}"
            n += 1
        var_map[raw] = cand
        used_after_tm.add(cand)

    dollar_map: dict[str, str] = {}
    for old, new in tm_map.items():
        if old != new:
            renames.append(("timer", old, new))
            dollar_map[old] = new
    for old, new in var_map.items():
        if old != new:
            renames.append(("variable", old, new))
            dollar_map[old] = new

    if dollar_map:
        # 长名优先，避免前缀误伤
        ordered = sorted(dollar_map.keys(), key=len, reverse=True)

        def _dollar_repl(m: re.Match) -> str:
            inner = m.group(1)
            new = dollar_map.get(inner)
            return f"$({new})" if new else m.group(0)

        # 一次性替换所有 $()；仅映射表内的会变
        pattern = re.compile(
            r"\$\((" + "|".join(re.escape(k) for k in ordered) + r")\)"
        )
        text = pattern.sub(_dollar_repl, text)

        # "timer": "裸名" 无 $() 的写法
        def _timer_field_repl(m: re.Match) -> str:
            raw = m.group(1)
            bare = strip_timer_ref(raw)
            new = dollar_map.get(bare)
            if not new:
                return m.group(0)
            if raw.startswith("$("):
                return f'"timer": "$({new})"'
            return f'"timer": "{new}"'

        text = re.sub(
            r'"timer"\s*:\s*"(\$\([^"]+\)|[^"]+)"',
            _timer_field_repl,
            text,
        )

    return text, renames


def normalize_timers(timers) -> list:
    """规范为 save payload 的 timers.list 项。

    入参可为:
      - ["JSQ1", "$(JSQ_001)"]
      - [{"name": "JSQ1", "dataType": 3, "defaultValue": "00:00:00"}, ...]
    返回去重后的 list[{name, dataType, defaultValue}]。
    name 规则与程序变量相同：仅 [A-Za-z0-9_]；非法名自动 sanitize。
    """
    if not timers:
        return []
    seen = set()
    out = []
    for item in timers:
        if isinstance(item, str):
            name = ensure_ident_name(
                strip_timer_ref(item), kind="timer name", fallback_prefix="tm"
            )
            entry = {"name": name, "dataType": 3, "defaultValue": "00:00:00"}
        elif isinstance(item, dict):
            name = ensure_ident_name(
                strip_timer_ref(str(item.get("name", ""))),
                kind="timer name",
                fallback_prefix="tm",
            )
            entry = {
                "name": name,
                "dataType": int(item.get("dataType", 3)),
                "defaultValue": item.get("defaultValue") or "00:00:00",
            }
        else:
            raise TypeError(f"invalid timer entry: {item!r}")
        if name in seen:
            continue
        seen.add(name)
        out.append(entry)
    return out


def extract_timers_from_xml(xml_content: str) -> list:
    """从 XML 中收集 timer:start/stop/pause/restart/cond 的 ext.timer 引用。"""
    if not xml_content:
        return []
    names = []
    # 在含 timer 字段的 CDATA JSON 中匹配 "timer":"$(...)" / "timer": "..."
    for m in re.finditer(
        r'"timer"\s*:\s*"(\$\([^"]+\)|[^"]+)"',
        xml_content,
    ):
        names.append(m.group(1))
    return normalize_timers(names)


def resolve_timers(timers, xml_content: str) -> list:
    """显式 timers 优先；否则从 XML 自动提取。"""
    if timers is not None:
        return normalize_timers(timers)
    return extract_timers_from_xml(xml_content)


# 程序变量 dataType：1=浮点 2=字符串 3=整型
_VAR_DEFAULTS = {
    1: {"unit": "", "isEnum": False, "defaultValue": "0.000"},
    2: {"unit": "", "isEnum": False, "defaultValue": ""},
    3: {"unit": "", "isEnum": False, "defaultValue": "0"},
}


def strip_var_ref(ref: str) -> str:
    """$(BL) / $$$(x) / BL → 裸名（不处理 #() 位号）"""
    s = (ref or "").strip()
    if s.startswith("$$$(") and s.endswith(")"):
        return s[4:-1].strip()
    if s.startswith("$(") and s.endswith(")"):
        return s[2:-1].strip()
    return s


def validate_var_name(name: str) -> str:
    """程序变量名与计时器名规则一致：仅 [A-Za-z0-9_]。"""
    return validate_ident_name(name, kind="variable name")


def normalize_variables(variables) -> list:
    """规范为 save payload 的 variables.list 项。

    入参可为:
      - ["BL", "$(x)"]  → dataType 默认 1（浮点）
      - [{"name":"BL","dataType":1,"unit":"","isEnum":false,"defaultValue":"0.000"}, ...]
    dataType: 1=浮点 2=字符串 3=整型。
    name 规则与计时器相同：仅 [A-Za-z0-9_]；非法名自动 sanitize。
    """
    if not variables:
        return []
    seen = set()
    out = []
    for item in variables:
        if isinstance(item, str):
            name = ensure_ident_name(
                strip_var_ref(item), kind="variable name", fallback_prefix="var"
            )
            dt = 1
            base = dict(_VAR_DEFAULTS[dt])
            entry = {"name": name, "dataType": dt, **base}
        elif isinstance(item, dict):
            name = ensure_ident_name(
                strip_var_ref(str(item.get("name", ""))),
                kind="variable name",
                fallback_prefix="var",
            )
            dt = int(item.get("dataType", 1))
            if dt not in _VAR_DEFAULTS:
                raise ValueError(f"invalid variable dataType {dt}: must be 1, 2, or 3")
            base = dict(_VAR_DEFAULTS[dt])
            entry = {
                "name": name,
                "dataType": dt,
                "unit": item["unit"] if "unit" in item else base["unit"],
                "isEnum": bool(item["isEnum"]) if "isEnum" in item else base["isEnum"],
                "defaultValue": (
                    item["defaultValue"]
                    if "defaultValue" in item and item["defaultValue"] is not None
                    else base["defaultValue"]
                ),
            }
        else:
            raise TypeError(f"invalid variable entry: {item!r}")
        if name in seen:
            continue
        seen.add(name)
        out.append(entry)
    return out


def extract_variables_from_xml(xml_content: str, timer_names: set | None = None) -> list:
    """从 XML 收集 $(name) 程序变量；排除 #() 位号与已在 timers 中的名。

    自动提取时 dataType 默认 1；精确类型请显式传 variables / IR.variables。
    """
    if not xml_content:
        return []
    timer_names = timer_names or {
        t["name"] for t in extract_timers_from_xml(xml_content)
    }
    names = []
    for m in re.finditer(r"\$\(([^)]+)\)", xml_content):
        name = m.group(1).strip()
        if not name or name in timer_names:
            continue
        names.append(name)
    return normalize_variables(names)


def resolve_variables(variables, xml_content: str, timers_list: list | None = None) -> list:
    """显式 variables 优先；否则从 XML 自动提取（dataType 默认浮点）。"""
    if variables is not None:
        return normalize_variables(variables)
    timer_names = {t["name"] for t in (timers_list or [])}
    return extract_variables_from_xml(xml_content, timer_names=timer_names)


def _handle_api_errors(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Timeout:
            raise RuntimeError(f"请求超时（{REQUEST_TIMEOUT}秒）")
        except ConnectionError:
            raise RuntimeError(f"连接失败：无法连接到 {BASE_URL}")
        except RequestException as e:
            raise RuntimeError(f"请求失败：{str(e)}")
    return wrapper


def _response_msg(response: dict) -> str:
    """平台响应文案：优先 msg，兼容 message 等字段。"""
    for key in ("msg", "message", "errorMsg", "errorMessage"):
        val = response.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return "未知错误"


def _is_success_code(code) -> bool:
    return code == 0 or code == "0"


def _check_response_code(response: dict, action_name: str, *, require_code: bool = False):
    """按 code / msg 判定成败。

    require_code=True（如 save）：响应必须带 code，且为 0 / \"0\" 才算成功。
    """
    if not isinstance(response, dict):
        raise RuntimeError(f"{action_name}失败: 响应非对象；msg=未知错误")
    code = response.get("code")
    msg = _response_msg(response)
    if require_code and code is None:
        raise RuntimeError(f"{action_name}失败: 响应缺少 code；msg={msg}")
    if code is not None and not _is_success_code(code):
        raise RuntimeError(f"{action_name}失败: code={code}；msg={msg}")


@_handle_api_errors
def make_request(method: str, url: str, **kwargs):
    kwargs.setdefault('timeout', REQUEST_TIMEOUT)
    kwargs.setdefault('headers', HEADERS)
    response = requests.request(method, url, **kwargs)
    if response.ok:
        return response.json()
    try:
        return response.json()
    except ValueError:
        response.raise_for_status()


class DirectPlatformClient:
    """Direct 平台 API 客户端"""

    # 获取下一个ID
    def get_next_id(self, id_type: int = 0) -> str:
        """获取下一个ID，返回 nextId 字符串

        id_type: ID类型，0=默认
        """
        url = BASE_URL + f"vxdirect/nextId?idType={id_type}"
        response = make_request("GET", url)
        _check_response_code(response, "获取下一个ID")
        return response.get("result", {}).get("data", {}).get("nextId", "")

    # 查询程序分组列表
    def get_data_groups(self) -> list:
        """查询程序分组列表，返回 [{groupId, groupName}, ...]"""
        url = BASE_URL + "vxdirect/auth/dataGroups?"
        response = make_request("GET", url)
        _check_response_code(response, "查询程序分组")
        return response.get("result", {}).get("data", {}).get("dataGroups", [])

    # 查询位号信息列表
    def get_tags(self, current_page: int = 1, page_size: int = 10,
                 tag_data_types: str = "") -> dict:
        """查询位号信息列表，返回 {list: [{name, type, remark}, ...], pagination: {...}}

        tag_data_types: 按类型过滤，type 1=浮点 2=整型 3=字符串
        """
        url = BASE_URL + f"vxdirect/tag?currentPage={current_page}&pageSize={page_size}&tagDataTypes={tag_data_types}"
        response = make_request("GET", url)
        _check_response_code(response, "查询位号信息")
        return response.get("result", {}).get("data", {})

    # 按名称关键词搜索位号
    def search_tags_by_name(self, keyword: str, max_pages: int = 100) -> list:
        """按关键词搜索位号名称（遍历分页，返回所有匹配项）"""
        results = []
        for page in range(1, max_pages + 1):
            data = self.get_tags(current_page=page, page_size=100)
            tag_list = data.get("list", [])
            if not tag_list:
                break
            for tag in tag_list:
                if keyword.upper() in tag.get("name", "").upper():
                    results.append(tag)
            pagination = data.get("pagination", {})
            if not pagination.get("hasMore", False):
                break
        return results

    # 新增主程序
    def create_program(self, program_name: str = "", version: str = "v1.0",
                       description: str = "", group_id: str = "1001",
                       label_id: str = "0", product_id: str = "0",
                       created_by: str = "admin") -> str:
        program_name = ensure_ident_name(
            program_name, kind="program name", fallback_prefix="proc"
        )
        payload = {
            "procedureHead": {
                "name": program_name,
                "version": version,
                "versionRemark": version,
                "description": description,
                "groupId": group_id,
                "labelId": label_id,
                "status": 1,
                "createdBy": created_by,
                "updatedBy": "",
                "product": {
                    "id": product_id,
                    "unit": "kg",
                    "maxSize": 10000.0,
                    "minSize": 0.0,
                    "normalSize": 100.0
                },
                "createdTime": int(time.time() * 1000),
                "updatedTime": int(time.time() * 1000)
            }
        }
        url = BASE_URL + "vxdirect/procedureHead"
        response = make_request("POST", url, json=payload)
        _check_response_code(response, "新增主程序")
        appid = response.get('result', {}).get("data", {}).get("procedureHeadId", "")
        return appid

    # 保存主程序（XML内容）—— 支持子程序
    def save_program(self, appid: str, xml_content: str,
                     description: str = "", program_name: str = "",
                     subprograms: list = None, timers: list = None,
                     variables: list = None) -> dict:
        """保存主程序，可选同时保存子程序。

        :param appid: 主程序ID
        :param xml_content: 主程序XML；拆分时必须含全部 flow:subproc 引用
        :param description: 程序描述
        :param program_name: 程序名称（仅 [A-Za-z0-9_]，与子程序/timers/variables 同规则）
        :param subprograms: 拆分时必填；与主 XML 中 flow:subproc 一一对应（id=subId、name 一致、xml_content 非空）
            {
                "id": "子程序预生成ID",
                "xml_content": "<子程序XML>",
                "name": "子程序名称",  # 同 program_name 命名规则
                "timers": [...],     # 可选；省略则从该子 XML 自动提取
                "variables": [...]   # 可选；省略则从该子 XML 自动提取
            }
        :param timers: 主程序计时器列表；省略则从主 XML 自动提取。
            timer:start/stop/pause/restart/cond → sfc.timers（见 normalize_timers）。
        :param variables: 主程序变量列表；省略则从主 XML 的 $(name) 提取。
            io:var / io:calc 等使用程序变量时 → sfc.variables（见 normalize_variables）。
            dataType: 1=浮点 2=字符串 3=整型。
        """
        program_name = ensure_ident_name(
            program_name, kind="program name", fallback_prefix="proc"
        )

        def _make_main(appid, xml_content, description, name, timers_list, variables_list):
            return {
                "sfc": {
                    "params": {"list": []},
                    "refServerVariables": {"list": []},
                    "variables": {"list": variables_list},
                    "timers": {"list": timers_list},
                    "aliases": {"list": []},
                    "sfcRunning": {"value": xml_content},
                    "sfcPausing": {"value": ""},
                    "sfcResuming": {"value": ""},
                    "sfcStopping": {"value": ""}
                },
                "description": {"value": description},
                "id": appid,
                "deviceId": "0",
                "parentId": "0",
                "rootId": appid,
                "name": name,
                "resourceGroupId": "0",
                "customOrder": 1,
                "schedulePeriod": 1000,
                "signPathId": "0",
                "branchSignPathId": "0",
                "formulaGroupId": "0"
            }

        def _make_sub(sub_id, sub_xml, sub_name, parent_id, root_id, order,
                      timers_list, variables_list):
            return {
                "sfc": {
                    "params": {"list": []},
                    "refServerVariables": {},
                    "variables": {"list": variables_list},
                    "timers": {"list": timers_list},
                    "aliases": {"list": []},
                    "sfcRunning": {"value": sub_xml},
                    "sfcPausing": {"value": ""},
                    "sfcResuming": {"value": ""},
                    "sfcStopping": {"value": ""}
                },
                "id": sub_id,
                "parentId": parent_id,
                "rootId": root_id,
                "name": sub_name,
                "customOrder": order
            }

        # 保存前：XML 内子程序/计时器/变量名必须 [A-Za-z0-9_]；非法则改写
        xml_content, _ = sanitize_xml_ident_names(xml_content)

        # 拆分：主 XML 必须含 flow:subproc，且与 subprograms 一一对应
        if subprograms:
            fixed_subs = []
            for sub in subprograms:
                sub = dict(sub)
                if sub.get("xml_content"):
                    sub["xml_content"], _ = sanitize_xml_ident_names(sub["xml_content"])
                fixed_subs.append(sub)
            subprograms = fixed_subs

        split_errs = check_split_bundle(xml_content, subprograms)
        if split_errs:
            raise ValueError(
                "split save rejected:\n  - " + "\n  - ".join(split_errs)
            )

        main_timers = resolve_timers(timers, xml_content)
        main_vars = resolve_variables(variables, xml_content, main_timers)
        update_list = [_make_main(
            appid, xml_content, description, program_name, main_timers, main_vars
        )]
        add_list = []
        if subprograms:
            for idx, sub in enumerate(subprograms, start=1):
                sub_xml = sub["xml_content"]
                sub_name = ensure_ident_name(
                    sub["name"], kind="program name", fallback_prefix="sub"
                )
                sub_timers = resolve_timers(sub.get("timers"), sub_xml)
                sub_vars = resolve_variables(sub.get("variables"), sub_xml, sub_timers)
                add_list.append(_make_sub(
                    sub["id"], sub_xml, sub_name, appid, appid, idx,
                    sub_timers, sub_vars
                ))

        payload = {
            "addProcedures": add_list,
            "updateProcedures": update_list,
            "deleteProcedureIds": "",
            "rootId": appid
        }
        url = BASE_URL + "vxdirect/procedure/all"
        response = make_request("POST", url, json=payload)
        # 自动保存门禁：必须 code 成功才返回；失败抛错含 code + msg
        _check_response_code(response, "主程序保存", require_code=True)
        return response

    # 编译主程序
    def compile_program(self, appid: str) -> dict:
        payload = {"ids": appid, "cmd": 1}
        url = BASE_URL + "vxdirect/procedureHead/cmd"
        response = make_request("POST", url, json=payload)
        _check_response_code(response, "主程序编译", require_code=True)
        return response

    # 获取主程序列表
    def get_program_info(self) -> dict:
        url = BASE_URL + "vxdirect/procedureHead?currentPage=1&pageSize=20"
        response = make_request("GET", url)
        _check_response_code(response, "获取主程序信息")
        return response

    # 已禁用：会跳过用户确认并自动编译，与 skill 门禁冲突
    def deploy_program(self, *args, **kwargs) -> dict:
        raise RuntimeError(
            "deploy_program 已禁用。请按 skill 流程分步调用："
            "create_program → save_program（code=0 成功）→（用户确认后）compile_program"
        )
