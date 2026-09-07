"""BPMN 布局生成器：防重叠坐标 + 可见连线路径

使用方法：
    from layout_generator import LayoutGenerator
    gen = LayoutGenerator()
    gen.add_node("node1", "dcs", "启动泵")
    gen.add_flow("flow1", "node1", "node2", situation="yes")
    gen.layout_vertical(["node1", "node2"], center_x=500, start_y=60)

    # 并行布局
    gen.add_node("pstart", "pstart")
    gen.add_node("pend", "pend")
    gen.add_node("container", "parallel1")
    gen.layout_parallel1(
        container_id="container",
        pstart_id="pstart",
        pend_id="pend",
        branch_groups=[["dcs_a", "or_a"], ["dcs_b", "or_b"]],
        start_x=100, start_y=280
    )
    shapes = gen.get_shapes()
    edges = gen.get_edges()
"""

# 标准库导入
import json

# 第三方库导入 (无)

# 本地模块导入 (无)


class Node:
    def __init__(self, node_id, node_type, name, width, height):
        self.id = node_id
        self.type = node_type
        self.name = name
        self.w = width
        self.h = height
        self.x = 0
        self.y = 0
        self.parent_container = None  # parent container id if inside a parallel container

    @property
    def cx(self):
        return self.x + self.w // 2

    @property
    def cy(self):
        return self.y + self.h // 2

    @property
    def top(self):
        return self.y

    @property
    def bottom(self):
        return self.y + self.h

    @property
    def right(self):
        return self.x + self.w

    def bounds(self):
        return (self.x, self.y, self.x + self.w, self.y + self.h)

    def overlaps(self, other, gap=0):
        ax1, ay1, ax2, ay2 = self.bounds()
        bx1, by1, bx2, by2 = other.bounds()
        return not (ax2 + gap <= bx1 or bx2 + gap <= ax1 or
                    ay2 + gap <= by1 or by2 + gap <= ay1)


class Flow:
    def __init__(self, flow_id, source, target, situation=None, name=None):
        self.id = flow_id
        self.source = source
        self.target = target
        self.situation = situation  # None / "yes" / "no" / "0" / "1" ...
        self.name = name  # "是" / "否" / 分支描述 / None


class LayoutGenerator:
    VERTICAL_GAP = 100
    HORIZONTAL_GAP = 300
    CONTAINER_PADDING = 40
    WAYPOINT_MARGIN = 20
    CONTAINER_EXIT_GAP = 50  # 容器边界外连线弯折间距

    NODE_SIZES = {
        "start": (54, 54),
        "end": (54, 54),
        "dcs": (200, 60),
        "var": (200, 60),
        "calc": (200, 60),
        "and": (200, 60),
        "or": (200, 60),
        "branch": (200, 60),
        "wait": (200, 60),
        "cond": (200, 60),
        "timer_start": (200, 60),
        "timer_restart": (200, 60),
        "timer_stop": (200, 60),
        "timer_pause": (200, 60),
        "timer_clock": (200, 60),
        "guide": (200, 60),
        "confirm": (200, 60),
        "alarm": (200, 60),
        "subproc": (200, 60),
        "rising_edge": (200, 60),
        "falling_edge": (200, 60),
        "concat": (200, 60),
        "file_export": (200, 60),
        "file_import": (200, 60),
        "modify_label": (200, 60),
        "modify_props": (200, 60),
        "other_main_proc": (200, 60),
        "request": (200, 60),
        "parallel1": (800, 600),
        "parallel2": (1460, 1290),
        "pstart": (800, 5),
        "pend": (800, 5),
        "text": (300, 60),
    }

    CONTAINER_TYPES = {"parallel1", "parallel2"}

    def __init__(self):
        self.nodes = {}
        self.node_order = []
        self.flows = []
        # 容器→子节点映射
        self._container_children = {}
        # 容器→pstart_id 映射
        self._container_pstart = {}
        # 容器→pend_id 映射
        self._container_pend = {}

    def add_node(self, node_id, node_type, name=""):
        w, h = self.NODE_SIZES.get(node_type, (200, 60))
        node = Node(node_id, node_type, name, w, h)
        self.nodes[node_id] = node
        self.node_order.append(node_id)
        return node

    def add_flow(self, flow_id, source, target, situation=None, name=None):
        self.flows.append(Flow(flow_id, source, target, situation, name))

    # ──────────────────────────────────────────────
    # 布局方法
    # ──────────────────────────────────────────────

    def layout_vertical(self, node_ids, center_x=500, start_y=60, gap=None):
        gap = gap or self.VERTICAL_GAP
        y = start_y
        for nid in node_ids:
            node = self.nodes[nid]
            node.x = center_x - node.w // 2
            node.y = y
            y += node.h + gap

    def layout_parallel1(self, container_id, branch_groups,
                         start_x=100, start_y=280,
                         col_gap=None, row_gap=None,
                         pstart_id=None, pend_id=None):
        """竖向并行布局（flow:parallel1）

        每个分支是一列竖向堆叠的节点，分支间水平排列。
        parallelStart 横跨容器顶部，parallelEnd 横跨容器底部。

        Args:
            container_id: 并行容器节点 id
            branch_groups: 分支组列表，每组是节点 id 列表
            start_x: 第一个分支的起始 x 坐标
            start_y: 第一个分支节点的起始 y 坐标
            col_gap: 分支间水平间距（默认 300）
            row_gap: 分支内节点间垂直间距（默认 100）
            pstart_id: parallelStart 节点 id
            pend_id: parallelEnd 节点 id
        """
        col_gap = col_gap or self.HORIZONTAL_GAP
        row_gap = row_gap or self.VERTICAL_GAP

        all_child_ids = []
        x = start_x
        for branch in branch_groups:
            y = start_y
            max_w = 0
            for nid in branch:
                node = self.nodes[nid]
                node.x = x
                node.y = y
                node.parent_container = container_id
                max_w = max(max_w, node.w)
                y += node.h + row_gap
            all_child_ids.extend(branch)
            x += max_w + col_gap

        # 注册容器-子节点关系
        self._register_container(container_id, all_child_ids, pstart_id, pend_id)

        # 计算容器边界
        self._auto_container_bounds(container_id, all_child_ids,
                                    start_x, start_y, pstart_id, pend_id)

        # 定位 parallelStart 和 parallelEnd
        self._position_pstart_pend(container_id, pstart_id, pend_id)

    def layout_parallel2(self, container_id, branch_groups,
                         start_x=100, start_y=280,
                         col_gap=None, row_gap=None,
                         pstart_id=None, pend_id=None):
        """横向并行布局（flow:parallel2）

        每个分支是一行水平排列的节点，分支间垂直堆叠。
        parallelStart 竖跨容器左侧，parallelEnd 竖跨容器右侧。

        Args:
            container_id: 并行容器节点 id
            branch_groups: 分支组列表，每组是节点 id 列表
            start_x: 第一个分支第一个节点的起始 x 坐标
            start_y: 第一个分支的起始 y 坐标
            col_gap: 分支内节点间水平间距（默认 300）
            row_gap: 分支间垂直间距（默认 100）
            pstart_id: parallelStart 节点 id
            pend_id: parallelEnd 节点 id
        """
        col_gap = col_gap or self.HORIZONTAL_GAP
        row_gap = row_gap or self.VERTICAL_GAP

        all_child_ids = []
        y = start_y
        for branch in branch_groups:
            x = start_x
            max_h = 0
            for nid in branch:
                node = self.nodes[nid]
                node.x = x
                node.y = y
                node.parent_container = container_id
                max_h = max(max_h, node.h)
                x += node.w + col_gap
            all_child_ids.extend(branch)
            y += max_h + row_gap

        # 注册容器-子节点关系
        self._register_container(container_id, all_child_ids, pstart_id, pend_id)

        # 计算容器边界
        self._auto_container_bounds(container_id, all_child_ids,
                                    start_x, start_y, pstart_id, pend_id)

        # 定位 parallelStart 和 parallelEnd（横向模式下为竖条）
        self._position_pstart_pend_horizontal(container_id, pstart_id, pend_id)

    def layout_container(self, container_id, child_ids, x=None, y=None):
        """手动计算容器边界（不自动定位 pstart/pend）"""
        container = self.nodes[container_id]
        children = [self.nodes[cid] for cid in child_ids if cid in self.nodes]
        if not children:
            return
        min_x = min(c.x for c in children)
        min_y = min(c.y for c in children)
        max_x = max(c.right for c in children)
        max_y = max(c.bottom for c in children)
        container.x = (x if x is not None else min_x) - self.CONTAINER_PADDING
        container.y = (y if y is not None else min_y) - self.CONTAINER_PADDING
        container.w = (max_x - min_x) + self.CONTAINER_PADDING * 2
        container.h = (max_y - min_y) + self.CONTAINER_PADDING * 2
        self._register_container(container_id, child_ids, None, None)

    # ──────────────────────────────────────────────
    # 容器内部方法
    # ──────────────────────────────────────────────

    def _register_container(self, container_id, child_ids, pstart_id, pend_id):
        self._container_children[container_id] = list(child_ids)
        if pstart_id:
            self._container_pstart[container_id] = pstart_id
            if pstart_id in self.nodes:
                self.nodes[pstart_id].parent_container = container_id
        if pend_id:
            self._container_pend[container_id] = pend_id
            if pend_id in self.nodes:
                self.nodes[pend_id].parent_container = container_id

    def _auto_container_bounds(self, container_id, child_ids,
                               fallback_x, fallback_y,
                               pstart_id, pend_id):
        """根据子节点位置自动计算容器边界"""
        container = self.nodes[container_id]
        children = [self.nodes[cid] for cid in child_ids if cid in self.nodes]
        if not children:
            container.x = fallback_x
            container.y = fallback_y
            return

        min_x = min(c.x for c in children)
        min_y = min(c.y for c in children)
        max_x = max(c.right for c in children)
        max_y = max(c.bottom for c in children)

        # 为 pstart/pend 预留空间
        pstart_h = self.NODE_SIZES["pstart"][1] if pstart_id else 0
        pend_h = self.NODE_SIZES["pend"][1] if pend_id else 0
        inner_padding = self.CONTAINER_PADDING + pstart_h + self.CONTAINER_PADDING
        bottom_padding = self.CONTAINER_PADDING + pend_h + self.CONTAINER_PADDING

        container.x = min_x - self.CONTAINER_PADDING
        container.y = min_y - inner_padding
        container.w = (max_x - min_x) + self.CONTAINER_PADDING * 2
        container.h = (max_y - min_y) + inner_padding + bottom_padding

    def _position_pstart_pend(self, container_id, pstart_id, pend_id):
        """竖向模式下定位 parallelStart（顶部横条）和 parallelEnd（底部横条）"""
        container = self.nodes[container_id]
        inner_w = container.w - self.CONTAINER_PADDING * 2

        if pstart_id and pstart_id in self.nodes:
            pstart = self.nodes[pstart_id]
            pstart.x = container.x + self.CONTAINER_PADDING
            pstart.y = container.y + self.CONTAINER_PADDING
            pstart.w = inner_w
            pstart.h = 5

        if pend_id and pend_id in self.nodes:
            pend = self.nodes[pend_id]
            pend.x = container.x + self.CONTAINER_PADDING
            pend.y = container.bottom - self.CONTAINER_PADDING - 5
            pend.w = inner_w
            pend.h = 5

    def _position_pstart_pend_horizontal(self, container_id, pstart_id, pend_id):
        """横向模式下定位 parallelStart（左侧竖条）和 parallelEnd（右侧竖条）"""
        container = self.nodes[container_id]
        inner_h = container.h - self.CONTAINER_PADDING * 2

        if pstart_id and pstart_id in self.nodes:
            pstart = self.nodes[pstart_id]
            pstart.x = container.x + self.CONTAINER_PADDING
            pstart.y = container.y + self.CONTAINER_PADDING
            pstart.w = 5
            pstart.h = inner_h

        if pend_id and pend_id in self.nodes:
            pend = self.nodes[pend_id]
            pend.x = container.right - self.CONTAINER_PADDING - 5
            pend.y = container.y + self.CONTAINER_PADDING
            pend.w = 5
            pend.h = inner_h

    # ──────────────────────────────────────────────
    # 连线路径计算
    # ──────────────────────────────────────────────

    def calc_waypoints(self, src_id, tgt_id):
        """通用连线路径计算，自动识别并行容器场景"""
        src = self.nodes[src_id]
        tgt = self.nodes[tgt_id]

        # 场景1: parallelStart → 分支首节点（容器内连线）
        if src.type == "pstart":
            return self._calc_pstart_to_branch(src, tgt)

        # 场景2: 分支末节点 → parallelEnd（容器内连线）
        if tgt.type == "pend":
            return self._calc_branch_to_pend(src, tgt)

        # 场景3: 容器 → 外部节点（容器 outgoing）
        if src.type in self.CONTAINER_TYPES:
            return self._calc_container_out(src, tgt)

        # 场景4: 外部节点 → 容器（容器 incoming）
        if tgt.type in self.CONTAINER_TYPES:
            return self._calc_container_in(src, tgt)

        # 场景5: 普通连线
        return self._calc_normal_waypoints(src, tgt)

    def _calc_pstart_to_branch(self, pstart, branch_node):
        """parallelStart → 分支首节点：从 pstart 底部到分支节点顶部"""
        sx = branch_node.cx  # 对齐到分支节点的 x 中心
        sy = pstart.bottom
        tx = branch_node.cx
        ty = branch_node.top
        if abs(sx - tx) < 10:
            return [(sx, sy), (tx, ty)]
        return [(sx, sy), (sx, ty), (tx, ty)]

    def _calc_branch_to_pend(self, branch_node, pend):
        """分支末节点 → parallelEnd：从分支节点底部到 pend 顶部"""
        sx = branch_node.cx
        sy = branch_node.bottom
        tx = branch_node.cx  # 对齐到分支节点的 x 中心
        ty = pend.top
        if abs(sx - tx) < 10:
            return [(sx, sy), (tx, ty)]
        return [(sx, sy), (sx, ty), (tx, ty)]

    def _calc_container_out(self, container, tgt):
        """容器 → 外部节点：从 parallelEnd 底部穿出容器边界"""
        container_id = container.id
        pend_id = self._container_pend.get(container_id)
        if pend_id and pend_id in self.nodes:
            pend = self.nodes[pend_id]
            sx = pend.cx
            sy = pend.bottom
        else:
            sx = container.cx
            sy = container.bottom

        tx = tgt.cx
        ty = tgt.top

        exit_y = container.bottom + self.CONTAINER_EXIT_GAP
        if abs(sx - tx) < 10:
            return [(sx, sy), (sx, ty)]
        return [(sx, sy), (sx, exit_y), (tx, exit_y), (tx, ty)]

    def _calc_container_in(self, src, container):
        """外部节点 → 容器：从外部节点底部到容器顶部（parallelStart 位置）"""
        container_id = container.id
        pstart_id = self._container_pstart.get(container_id)
        if pstart_id and pstart_id in self.nodes:
            pstart = self.nodes[pstart_id]
            tx = pstart.cx
            ty = pstart.top
        else:
            tx = container.cx
            ty = container.top

        sx = src.cx
        sy = src.bottom

        entry_y = container.top - self.CONTAINER_EXIT_GAP
        if abs(sx - tx) < 10:
            return [(sx, sy), (tx, ty)]
        return [(sx, sy), (sx, entry_y), (tx, entry_y), (tx, ty)]

    def _calc_normal_waypoints(self, src, tgt):
        """普通连线：直连或 L 形路径 + 避让节点"""
        sx, sy = src.cx, src.bottom
        tx, ty = tgt.cx, tgt.top
        if abs(sx - tx) < 10:
            return [(sx, sy), (tx, ty)]
        all_nodes = list(self.nodes.values())
        mid_y = (sy + ty) // 2
        for n in all_nodes:
            if n.id in (src.id, tgt.id):
                continue
            # 跳过容器节点（不会阻挡连线）
            if n.type in self.CONTAINER_TYPES:
                continue
            if n.y < mid_y < n.bottom:
                mid_y = n.bottom + self.WAYPOINT_MARGIN
                break
        return [(sx, sy), (sx, mid_y), (tx, mid_y), (tx, ty)]

    def calc_u_waypoints(self, src_id, tgt_id, side="right"):
        """U 形绕行路径（复杂场景）"""
        src = self.nodes[src_id]
        tgt = self.nodes[tgt_id]
        sx, sy = src.cx, src.bottom
        tx, ty = tgt.cx, tgt.top
        all_nodes = list(self.nodes.values())
        max_right = max(n.right for n in all_nodes) + 50
        if side == "left":
            outer_x = min(n.x for n in all_nodes) - 50
        else:
            outer_x = max_right
        mid_y1 = sy + 30
        mid_y2 = ty - 30
        return [(sx, sy), (sx, mid_y1), (outer_x, mid_y1),
                (outer_x, mid_y2), (tx, mid_y2), (tx, ty)]

    # ──────────────────────────────────────────────
    # 验证方法
    # ──────────────────────────────────────────────

    def check_overlaps(self, gap=0):
        """检查节点重叠，自动豁免容器-子节点对"""
        nodes = list(self.nodes.values())
        overlaps = []
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                a, b = nodes[i], nodes[j]
                # 豁免容器与其子节点的重叠
                if self._is_container_child_pair(a, b):
                    continue
                if a.overlaps(b, gap):
                    overlaps.append((a.id, b.id))
        return overlaps

    def _is_container_child_pair(self, a, b):
        """判断两个节点是否是容器-子节点关系"""
        # a 是 b 的父容器
        if a.id in self._container_children and b.id in self._container_children[a.id]:
            return True
        if b.id in self._container_children and a.id in self._container_children[b.id]:
            return True
        # 通过 parent_container 属性判断
        if a.parent_container == b.id or b.parent_container == a.id:
            return True
        return False

    def check_parallel_integrity(self):
        """验证并行结构完整性"""
        issues = []
        for container_id, child_ids in self._container_children.items():
            container = self.nodes.get(container_id)
            if not container:
                issues.append(f"容器 {container_id} 不存在")
                continue

            pstart_id = self._container_pstart.get(container_id)
            pend_id = self._container_pend.get(container_id)

            if not pstart_id:
                issues.append(f"容器 {container_id} 缺少 parallelStart")
            if not pend_id:
                issues.append(f"容器 {container_id} 缺少 parallelEnd")

            # 检查子节点是否在容器范围内
            for cid in child_ids:
                child = self.nodes.get(cid)
                if not child:
                    issues.append(f"子节点 {cid} 不存在")
                    continue
                if (child.x < container.x or child.right > container.right or
                        child.y < container.y or child.bottom > container.bottom):
                    issues.append(f"子节点 {cid} 超出容器 {container_id} 边界")

        return issues

    def check_id_match(self, sequence_flow_ids, node_ids):
        mismatches = []
        flow_id_set = set(f.id for f in self.flows)
        for sfid in sequence_flow_ids:
            if sfid not in flow_id_set:
                mismatches.append(('flow', sfid, 'sequenceFlow id not found in BPMNEdge'))
        node_id_set = set(self.nodes.keys())
        for nid in node_ids:
            if nid not in node_id_set:
                mismatches.append(('node', nid, 'node id not found in BPMNShape'))
        return mismatches

    # ──────────────────────────────────────────────
    # 输出方法
    # ──────────────────────────────────────────────

    def get_shapes(self):
        shapes = []
        for nid in self.node_order:
            node = self.nodes[nid]
            shapes.append({
                "id": nid,
                "x": node.x,
                "y": node.y,
                "w": node.w,
                "h": node.h,
                "type": node.type,
            })
        return shapes

    def get_edges(self):
        edges = []
        for flow in self.flows:
            waypoints = self.calc_waypoints(flow.source, flow.target)
            edges.append({
                "id": flow.id,
                "source": flow.source,
                "target": flow.target,
                "situation": flow.situation,
                "waypoints": waypoints,
            })
        return edges

    def get_shape_xml(self):
        lines = []
        for nid in self.node_order:
            n = self.nodes[nid]
            if n.type in self.CONTAINER_TYPES:
                lines.append(
                    f'    <bpmndi:BPMNShape id="{n.id}_di" bpmnElement="{n.id}" isExpanded="true">'
                )
            else:
                lines.append(
                    f'    <bpmndi:BPMNShape id="{n.id}_di" bpmnElement="{n.id}">'
                )
            lines.append(
                f'      <dc:Bounds x="{n.x}" y="{n.y}" '
                f'width="{n.w}" height="{n.h}" />'
            )
            lines.append(f'    </bpmndi:BPMNShape>')
        return "\n".join(lines)

    def get_edge_xml(self):
        lines = []
        for flow in self.flows:
            waypoints = self.calc_waypoints(flow.source, flow.target)
            lines.append(
                f'    <bpmndi:BPMNEdge id="{flow.id}_di" '
                f'bpmnElement="{flow.id}">'
            )
            for wp in waypoints:
                lines.append(f'      <di:waypoint x="{wp[0]}" y="{wp[1]}" />')
            lines.append(f'    </bpmndi:BPMNEdge>')
        return "\n".join(lines)

    def get_sequence_flow_xml(self):
        """生成 <bpmn2:sequenceFlow> 元素（流程层连线定义）

        自动根据 situation 字段选择正确的连线变体：
        - None → plain (普通连线, ext:data={"lineType":1})
        - "yes" → situation_yes (条件成立, ext:data={"situation":"yes"})
        - "no" → situation_no (条件不成立, ext:data={"situation":"no"})
        - "0"/"1"/"2"... → branch_option (择一分支, ext:data={"situation":"{索引}"})
        """
        lines = []
        for flow in self.flows:
            if flow.situation == "yes":
                lines.append(
                    f'    <bpmn2:sequenceFlow id="{flow.id}" name="条件成立" '
                    f'sourceRef="{flow.source}" targetRef="{flow.target}">\n'
                    f'      <ext:data><![CDATA[{{"situation":"yes"}}]]></ext:data>\n'
                    f'    </bpmn2:sequenceFlow>'
                )
            elif flow.situation == "no":
                lines.append(
                    f'    <bpmn2:sequenceFlow id="{flow.id}" name="条件不成立" '
                    f'sourceRef="{flow.source}" targetRef="{flow.target}">\n'
                    f'      <ext:data><![CDATA[{{"situation":"no"}}]]></ext:data>\n'
                    f'    </bpmn2:sequenceFlow>'
                )
            elif flow.situation is not None and str(flow.situation).isdigit():
                name = flow.name or f"选项{flow.situation}"
                lines.append(
                    f'    <bpmn2:sequenceFlow id="{flow.id}" name="{name}" '
                    f'sourceRef="{flow.source}" targetRef="{flow.target}">\n'
                    f'      <ext:data><![CDATA[{{"situation":"{flow.situation}"}}]]></ext:data>\n'
                    f'    </bpmn2:sequenceFlow>'
                )
            else:
                lines.append(
                    f'    <bpmn2:sequenceFlow id="{flow.id}" '
                    f'sourceRef="{flow.source}" targetRef="{flow.target}">\n'
                    f'      <ext:data><![CDATA[{{"lineType":1}}]]></ext:data>\n'
                    f'    </bpmn2:sequenceFlow>'
                )
        return "\n".join(lines)

    def get_incoming_outgoing_xml(self, node_id):
        """生成节点的 <bpmn2:incoming> 和 <bpmn2:outgoing> XML

        按流程顺序自动收集该节点的所有入边和出边 ID。
        """
        incoming_ids = []
        outgoing_ids = []
        for flow in self.flows:
            if flow.target == node_id:
                incoming_ids.append(flow.id)
            if flow.source == node_id:
                outgoing_ids.append(flow.id)

        lines = []
        for fid in incoming_ids:
            lines.append(f'  <bpmn2:incoming>{fid}</bpmn2:incoming>')
        for fid in outgoing_ids:
            lines.append(f'  <bpmn2:outgoing>{fid}</bpmn2:outgoing>')
        return "\n".join(lines)

    def check_connection_integrity(self):
        """验证连线完整性

        检查：
        1. 每条 flow 的 source 和 target 节点是否存在
        2. 起始节点必须有且只有 outgoing
        3. 结束节点必须有 incoming
        4. 中间节点必须同时有 incoming 和 outgoing
        5. 条件节点(and/or/cond)必须有 2 条 outgoing
        6. flow 的 source/target 不能是同一节点（禁止自环）
        """
        issues = []

        incoming_map = {}
        outgoing_map = {}
        for flow in self.flows:
            outgoing_map.setdefault(flow.source, []).append(flow.id)
            incoming_map.setdefault(flow.target, []).append(flow.id)

        for flow in self.flows:
            if flow.source not in self.nodes:
                issues.append(f"连线 {flow.id} 的 source 节点 {flow.source} 不存在")
            if flow.target not in self.nodes:
                issues.append(f"连线 {flow.id} 的 target 节点 {flow.target} 不存在")
            if flow.source == flow.target:
                # 豁免：条件节点(and/or/cond)的 no 分支自环是合法的等待模式
                src_node = self.nodes.get(flow.source)
                if src_node and src_node.type in ("and", "or", "cond") and flow.situation == "no":
                    pass
                else:
                    issues.append(f"连线 {flow.id} 存在自环（source 和 target 相同）")

        for nid in self.node_order:
            node = self.nodes[nid]
            inc = incoming_map.get(nid, [])
            out = outgoing_map.get(nid, [])

            if node.type == "start":
                if not out:
                    issues.append(f"起始节点 {nid} 缺少 outgoing 连线")
                if inc:
                    issues.append(f"起始节点 {nid} 不应有 incoming 连线")
            elif node.type == "end":
                if not inc:
                    issues.append(f"结束节点 {nid} 缺少 incoming 连线")
            elif node.type == "pstart":
                # parallelStart：只有 outgoing，incoming 通过容器边界隐式连接
                if not out:
                    issues.append(f"并行起始节点 {nid} 缺少 outgoing 连线")
            elif node.type == "pend":
                # parallelEnd：只有 incoming，outgoing 通过容器边界隐式连接
                if not inc:
                    issues.append(f"并行结束节点 {nid} 缺少 incoming 连线")
            elif node.type in self.CONTAINER_TYPES:
                # 容器节点：incoming/outgoing 通过内部 pstart/pend 转发
                pass
            else:
                if not inc:
                    issues.append(f"中间节点 {nid}({node.type}) 缺少 incoming 连线")
                if not out:
                    issues.append(f"中间节点 {nid}({node.type}) 缺少 outgoing 连线")

            if node.type in ("and", "or", "cond") and len(out) != 2:
                issues.append(
                    f"条件节点 {nid}({node.type}) 应有 2 条 outgoing，实际 {len(out)} 条"
                )

        return issues

    def get_diagram_xml(self, process_id="Process_1"):
        """生成完整 BPMNDiagram（先 Shape 后 Edge）。根元素无前导缩进，与 xml_template 一致。"""
        shapes = self.get_shape_xml()
        edges = self.get_edge_xml()
        return (
            f'<bpmndi:BPMNDiagram id="BPMNDiagram_1">\n'
            f'  <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="{process_id}">\n'
            f'{shapes}\n'
            f'{edges}\n'
            f'  </bpmndi:BPMNPlane>\n'
            f'</bpmndi:BPMNDiagram>'
        )

    @staticmethod
    def _strip_io_refs(node_xml: str) -> str:
        """去掉节点内已有的 incoming/outgoing，避免与 layout 结果不一致。"""
        import re
        node_xml = re.sub(
            r"\s*<bpmn2:incoming>[^<]*</bpmn2:incoming>\s*",
            "\n",
            node_xml,
        )
        node_xml = re.sub(
            r"\s*<bpmn2:outgoing>[^<]*</bpmn2:outgoing>\s*",
            "\n",
            node_xml,
        )
        return node_xml

    def _inject_io_refs(self, node_xml: str, node_id: str) -> str:
        """在节点结束标签前插入 incoming/outgoing（来自 self.flows）。"""
        import re
        io_xml = self.get_incoming_outgoing_xml(node_id)
        if not io_xml:
            return node_xml.strip()
        # 匹配最后一个结束标签
        m = re.search(r"(</[^>]+>)\s*$", node_xml.strip())
        if not m:
            raise ValueError(f"节点 XML 缺少结束标签: {node_id}")
        body = node_xml.strip()[: m.start()].rstrip()
        return f"{body}\n{io_xml}\n{m.group(1)}"

    def assemble_full_xml(self, node_xml_by_id: dict, process_id="Process_1") -> str:
        """组装可保存的完整 XML（process + diagram）。

        这是防止「节点有、连线不显示」的推荐入口：
        - sequenceFlow 与 BPMNEdge 使用同一套 flow id
        - Shape 在前、Edge 在后
        - 每条 plain 连线带 ext:data lineType
        - 节点 incoming/outgoing 与 flow 一致

        Args:
            node_xml_by_id: {node_id: 节点完整 XML}。可含或不含 incoming/outgoing，
                            本方法会剥离后按 flows 重写。
            process_id: process 元素 id，默认 Process_1
        """
        missing = [nid for nid in self.node_order if nid not in node_xml_by_id]
        if missing:
            raise ValueError(f"缺少节点 XML: {missing}")

        issues = self.check_connection_integrity()
        if issues:
            raise ValueError("连线完整性失败: " + "; ".join(issues))
        overlaps = self.check_overlaps()
        if overlaps:
            raise ValueError(f"节点重叠: {overlaps}")

        # 未布局（仍在 0,0）会导致 Edge 叠在一起，平台上看起来像没连线
        unset = [
            nid for nid in self.node_order
            if self.nodes[nid].x == 0 and self.nodes[nid].y == 0
            and self.nodes[nid].type not in ("pstart", "pend")
        ]
        if len(unset) == len(self.node_order):
            raise ValueError("尚未调用 layout_vertical/layout_parallel*，禁止组装")

        lines = [f'<bpmn2:process id="{process_id}" isExecutable="true">']
        for nid in self.node_order:
            cleaned = self._strip_io_refs(node_xml_by_id[nid])
            lines.append(self._inject_io_refs(cleaned, nid))
        lines.append(self.get_sequence_flow_xml())
        lines.append("</bpmn2:process>")
        lines.append(self.get_diagram_xml(process_id=process_id))
        return "\n".join(lines)
