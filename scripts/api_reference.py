"""Direct 平台 REST API 客户端参考实现

用法:
    from api_reference import DirectPlatformClient
    client = DirectPlatformClient()

    # 不含子程序
    appid = client.create_program(program_name="测试程序", description="描述")
    client.save_program(appid=appid, xml_content=xml_string, description="描述", program_name="测试程序")
    client.compile_program(appid=appid)

    # 含子程序
    appid = client.create_program(program_name="主程序", description="描述")
    sub_ids = [client.get_next_id(id_type=0) for _ in range(2)]
    subprograms = [
        {"id": sub_ids[0], "xml_content": sub1_xml, "description": "子程序1", "name": "sub1"},
        {"id": sub_ids[1], "xml_content": sub2_xml, "description": "子程序2", "name": "sub2"},
    ]
    client.save_program(appid=appid, xml_content=main_xml, description="描述",
                        program_name="主程序", subprograms=subprograms)
    client.compile_program(appid=appid)
"""

# 标准库导入
import time
from functools import wraps

# 第三方库导入
import requests
from requests.exceptions import Timeout, ConnectionError, RequestException


# 集中配置
BASE_URL = "http://direct-proxy/"
AUTH_TOKEN = ""
REQUEST_TIMEOUT = 60
HEADERS = {
    "Accept-Language": "zh-CN",
    "Authorization": AUTH_TOKEN,
    "Content-Type": "application/json",
}


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


def _check_response_code(response: dict, action_name: str):
    if response.get("code") is not None and response.get("code") != 0:
        raise RuntimeError(f"{action_name}失败: {response.get('message', '未知错误')}")


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
        url = BASE_URL + f"/vxdirect/nextId?idType={id_type}"
        response = make_request("GET", url)
        _check_response_code(response, "获取下一个ID")
        return response.get("result", {}).get("data", {}).get("nextId", "")

    # 查询程序分组列表
    def get_data_groups(self) -> list:
        """查询程序分组列表，返回 [{groupId, groupName}, ...]"""
        url = BASE_URL + "/vxdirect/auth/dataGroups?"
        response = make_request("GET", url)
        _check_response_code(response, "查询程序分组")
        return response.get("result", {}).get("data", {}).get("dataGroups", [])

    # 查询位号信息列表
    def get_tags(self, current_page: int = 1, page_size: int = 10,
                 tag_data_types: str = "") -> dict:
        """查询位号信息列表，返回 {list: [{name, type, remark}, ...], pagination: {...}}

        tag_data_types: 按类型过滤，type 1=浮点 2=整型 3=字符串
        """
        url = BASE_URL + f"/vxdirect/tag?currentPage={current_page}&pageSize={page_size}&tagDataTypes={tag_data_types}"
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
                     subprograms: list = None) -> dict:
        """保存主程序，可选同时保存子程序。

        :param appid: 主程序ID
        :param xml_content: 主程序XML（含 flow:subproc 引用）
        :param description: 程序描述
        :param program_name: 程序名称
        :param subprograms: 子程序列表，每项为 dict：
            {
                "id": "子程序预生成ID",
                "xml_content": "<子程序XML>",
                "name": "子程序名称"
            }
        """
        def _make_main(appid, xml_content, description, name):
            return {
                "sfc": {
                    "params": {"list": []},
                    "refServerVariables": {"list": []},
                    "variables": {"list": []},
                    "timers": {"list": []},
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

        def _make_sub(sub_id, sub_xml, sub_name, parent_id, root_id):
            return {
                "sfc": {
                    "params": {"list": []},
                    "refServerVariables": {},
                    "variables": {"list": []},
                    "timers": {"list": []},
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
                "customOrder": 1
            }

        update_list = [_make_main(appid, xml_content, description, program_name)]
        if subprograms:
            for sub in subprograms:
                update_list.append(_make_sub(
                    sub["id"], sub["xml_content"], sub["name"], appid, appid
                ))

        payload = {
            "addProcedures": [],
            "updateProcedures": update_list,
            "deleteProcedureIds": "",
            "rootId": appid
        }
        url = BASE_URL + "/vxdirect/procedure/all"
        response = make_request("POST", url, json=payload)
        _check_response_code(response, "主程序保存")
        return response

    # 编译主程序
    def compile_program(self, appid: str) -> dict:
        payload = {"ids": appid, "cmd": 1}
        url = BASE_URL + "/vxdirect/procedureHead/cmd"
        response = make_request("POST", url, json=payload)
        _check_response_code(response, "主程序编译")
        return response

    # 获取主程序列表
    def get_program_info(self) -> dict:
        url = BASE_URL + "/vxdirect/procedureHead?currentPage=1&pageSize=20"
        response = make_request("GET", url)
        _check_response_code(response, "获取主程序信息")
        return response

    # 一键创建并部署完整流程（支持子程序）
    def deploy_program(self, program_name: str, xml_content: str,
                       description: str = "", version: str = "v1.0",
                       subprograms: list = None) -> dict:
        results = {}
        appid = self.create_program(
            program_name=program_name,
            version=version,
            description=description
        )
        results["appid"] = appid
        results["create"] = "success"

        self.save_program(
            appid=appid,
            xml_content=xml_content,
            description=description,
            program_name=program_name,
            subprograms=subprograms
        )
        results["save"] = "success"

        self.compile_program(appid=appid)
        results["compile"] = "success"

        return results
