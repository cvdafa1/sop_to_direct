"""BPMN 布局生成器：槽位布局 + 正交走廊走线 + 重叠/穿线/交叉校验

使用方法：
    from layout_generator import LayoutGenerator
    gen = LayoutGenerator()
    gen.add_node("node1", "dcs", "启动泵")
    gen.add_flow("flow1", "node1", "node2", situation="yes")
    gen.layout_vertical(["node1", "node2"], center_x=500, start_y=60)
    # 是/否分叉：
    # gen.layout_branch_columns(decision_id, yes_ids, no_ids, merge_id=...)

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
    xml = gen.assemble_full_xml(node_xml_by_id)  # 含几何自动修复与硬门禁
"""

# 标准库导入
import json
import math

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
        self.waypoints = None  # list[(x,y)]，由布局/路由填充


class LayoutGenerator:
    VERTICAL_GAP = 100
    HORIZONTAL_GAP = 300
    CONTAINER_PADDING = 40
    WAYPOINT_MARGIN = 20
    CONTAINER_EXIT_GAP = 50  # 容器边界外连线弯折间距
    LANE_SPACING = 18  # 同层水平走线错层间距
    EDGE_NODE_PAD = 4  # 连线与节点矩形的最小间隙
    LABEL_OFFSET_X = 60  # BPMNLabel 相对首个 waypoint 向左
    LABEL_OFFSET_Y = 15  # BPMNLabel 相对首个 waypoint 向上
    COORD_MIN = 45  # 节点、拐点、标签的 x/y 均不得小于该值

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
        # 水平走廊 lane 占用：mid_y → count
        self._lane_bucket = {}

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
        """主链单列垂直槽位布局。"""
        gap = gap or self.VERTICAL_GAP
        y = start_y
        for nid in node_ids:
            node = self.nodes[nid]
            node.x = center_x - node.w // 2
            node.y = y
            y += node.h + gap

    def layout_branch_columns(self, decision_id, yes_ids, no_ids=None,
                              merge_id=None, center_x=500, col_gap=None,
                              row_gap=None):
        """条件分叉槽位：是→左列，否→右列；可选汇合点在下方居中。

        decision 保持在 center_x；yes_ids/no_ids 为决策点之后各自分支上的节点（不含 decision）。
        """
        col_gap = col_gap or self.HORIZONTAL_GAP
        row_gap = row_gap or self.VERTICAL_GAP
        no_ids = no_ids or []
        decision = self.nodes[decision_id]
        decision.x = center_x - decision.w // 2

        yes_x = center_x - col_gap - 100
        no_x = center_x + col_gap - 100
        start_y = decision.bottom + row_gap

        y = start_y
        for nid in yes_ids:
            n = self.nodes[nid]
            n.x = yes_x - n.w // 2
            n.y = y
            y += n.h + row_gap
        yes_bottom = y

        y = start_y
        for nid in no_ids:
            n = self.nodes[nid]
            n.x = no_x - n.w // 2
            n.y = y
            y += n.h + row_gap
        no_bottom = y

        if merge_id:
            merge = self.nodes[merge_id]
            merge.x = center_x - merge.w // 2
            merge.y = max(yes_bottom, no_bottom, start_y)

    def layout_multi_columns(self, decision_id, branch_groups,
                             merge_id=None, center_x=500, col_gap=None,
                             row_gap=None):
        """多路择一（flow:branch）槽位：每路一列，可选汇合点居中下方。

        branch_groups: 列表，每项为该路节点 id 列表（不含 decision / merge）。
        列从左到右排列，整体以 center_x 为中心。
        """
        col_gap = col_gap or self.HORIZONTAL_GAP
        row_gap = row_gap or self.VERTICAL_GAP
        branch_groups = [list(g) for g in (branch_groups or []) if g is not None]
        if not branch_groups:
            raise ValueError("layout_multi_columns requires branch_groups")

        decision = self.nodes[decision_id]
        decision.x = center_x - decision.w // 2
        # decision.y 由调用方先设好（或保持原值）
        start_y = decision.bottom + row_gap

        n = len(branch_groups)
        # 以 center_x 为中心均分列
        total_span = (n - 1) * col_gap
        left_center = center_x - total_span / 2.0

        bottoms = []
        for i, group in enumerate(branch_groups):
            col_cx = left_center + i * col_gap
            y = start_y
            for nid in group:
                node = self.nodes[nid]
                node.x = int(col_cx - node.w // 2)
                node.y = int(y)
                y += node.h + row_gap
            bottoms.append(y)

        if merge_id:
            merge = self.nodes[merge_id]
            merge.x = center_x - merge.w // 2
            merge.y = max(bottoms) if bottoms else start_y

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
        """普通连线：直连或正交折线；水平段走行间走廊并错层。"""
        sx, sy = src.cx, src.bottom
        tx, ty = tgt.cx, tgt.top
        if abs(sx - tx) < 10:
            return [(sx, sy), (tx, ty)]

        # 目标在源上方或侧向汇合：外侧 U 形，减少交叉
        if ty + 10 < sy:
            return self.calc_u_waypoints(src.id, tgt.id, side="right")

        mid_y = (sy + ty) // 2
        mid_y = self._avoid_nodes_on_band(mid_y, src.id, tgt.id)
        mid_y = self._alloc_lane_y(mid_y)
        return [(sx, sy), (sx, mid_y), (tx, mid_y), (tx, ty)]

    def _avoid_nodes_on_band(self, mid_y, src_id, tgt_id):
        """若 mid_y 落在某节点带内，推到该节点下方走廊。"""
        changed = True
        guard = 0
        while changed and guard < 20:
            changed = False
            guard += 1
            for n in self.nodes.values():
                if n.id in (src_id, tgt_id):
                    continue
                if n.type in self.CONTAINER_TYPES:
                    continue
                if n.y - self.EDGE_NODE_PAD < mid_y < n.bottom + self.EDGE_NODE_PAD:
                    mid_y = n.bottom + self.WAYPOINT_MARGIN
                    changed = True
        return mid_y

    def _alloc_lane_y(self, mid_y):
        """同层水平线错开 lane，避免粘连。"""
        key = int(round(mid_y / max(self.LANE_SPACING, 1)))
        count = self._lane_bucket.get(key, 0)
        self._lane_bucket[key] = count + 1
        if count == 0:
            return mid_y
        # 奇偶上下交替
        offset = ((count + 1) // 2) * self.LANE_SPACING
        return mid_y + offset if count % 2 else mid_y - offset

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

    def calc_bus_waypoints(self, src_id, tgt_id, bus_y: int):
        """高扇入汇合：水平段分 lane，避免多条边共线重叠。"""
        src = self.nodes[src_id]
        tgt = self.nodes[tgt_id]
        sx, sy = src.cx, src.bottom
        tx, ty = tgt.cx, tgt.top
        by = int(bus_y)
        if by <= sy:
            by = sy + 40
        if by >= ty:
            by = max(sy + 20, ty - 40)
        by = self._alloc_lane_y(by)
        if abs(sx - tx) < 10:
            return [(sx, sy), (tx, ty)]
        return [(sx, sy), (sx, by), (tx, by), (tx, ty)]

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

    @staticmethod
    def _segments(waypoints):
        segs = []
        for i in range(len(waypoints) - 1):
            x1, y1 = waypoints[i]
            x2, y2 = waypoints[i + 1]
            segs.append((x1, y1, x2, y2))
        return segs

    @staticmethod
    def _seg_hits_rect(x1, y1, x2, y2, rx1, ry1, rx2, ry2, pad=0):
        """正交线段是否穿过矩形内部（端点贴边不算）。"""
        rx1 -= pad
        ry1 -= pad
        rx2 += pad
        ry2 += pad
        eps = 0.5
        if abs(x1 - x2) < 1e-6:  # vertical
            x = x1
            ymin, ymax = sorted([y1, y2])
            if x <= rx1 + eps or x >= rx2 - eps:
                return False
            return ymax > ry1 + eps and ymin < ry2 - eps
        if abs(y1 - y2) < 1e-6:  # horizontal
            y = y1
            xmin, xmax = sorted([x1, x2])
            if y <= ry1 + eps or y >= ry2 - eps:
                return False
            return xmax > rx1 + eps and xmin < rx2 - eps
        return False

    @staticmethod
    def _hv_proper_cross(ax1, ay1, ax2, ay2, bx1, by1, bx2, by2):
        """两条正交线段是否内部交叉（端点相接不算）。"""
        a_vert = abs(ax1 - ax2) < 1e-6
        b_vert = abs(bx1 - bx2) < 1e-6
        if a_vert == b_vert:
            return False  # 平行不记交叉
        if a_vert:
            vx, ymin, ymax = ax1, *sorted([ay1, ay2])
            hy, xmin, xmax = by1, *sorted([bx1, bx2])
        else:
            hy, xmin, xmax = ay1, *sorted([ax1, ax2])
            vx, ymin, ymax = bx1, *sorted([by1, by2])
        return xmin < vx < xmax and ymin < hy < ymax

    @staticmethod
    def _hv_collinear_overlap(ax1, ay1, ax2, ay2, bx1, by1, bx2, by2, min_len=1.0):
        """两条正交线段是否共线且有正长度重叠（不允许叠线）。"""
        a_vert = abs(ax1 - ax2) < 1e-6
        a_horz = abs(ay1 - ay2) < 1e-6
        b_vert = abs(bx1 - bx2) < 1e-6
        b_horz = abs(by1 - by2) < 1e-6
        if a_vert and b_vert:
            if abs(ax1 - bx1) > 1e-6:
                return False
            a0, a1 = sorted([ay1, ay2])
            b0, b1 = sorted([by1, by2])
            return min(a1, b1) - max(a0, b0) > min_len
        if a_horz and b_horz:
            if abs(ay1 - by1) > 1e-6:
                return False
            a0, a1 = sorted([ax1, ax2])
            b0, b1 = sorted([bx1, bx2])
            return min(a1, b1) - max(a0, b0) > min_len
        return False

    @staticmethod
    def _point_near(x, y, px, py, tol=2.0) -> bool:
        return abs(x - px) <= tol and abs(y - py) <= tol

    def _seg_touches_node_port(self, seg, node_id, port: str) -> bool:
        """线段端点是否落在节点顶/底中心端口（汇合/分叉豁免用）。"""
        n = self.nodes.get(node_id)
        if not n:
            return False
        x1, y1, x2, y2 = seg
        if port == "top":
            px, py = n.cx, n.top
        else:
            px, py = n.cx, n.bottom
        return self._point_near(x1, y1, px, py) or self._point_near(x2, y2, px, py)

    def check_edges_through_nodes(self):
        """连线段不得穿过非端点节点矩形。"""
        issues = []
        for flow in self.flows:
            wps = flow.waypoints
            if not wps or len(wps) < 2:
                continue
            for n in self.nodes.values():
                if n.id in (flow.source, flow.target):
                    continue
                if n.type in self.CONTAINER_TYPES or n.type in ("pstart", "pend"):
                    continue
                rx1, ry1, rx2, ry2 = n.bounds()
                for x1, y1, x2, y2 in self._segments(wps):
                    if self._seg_hits_rect(
                        x1, y1, x2, y2, rx1, ry1, rx2, ry2, pad=self.EDGE_NODE_PAD
                    ):
                        issues.append(f"edge_through:{flow.id}→{n.id}")
                        break
        return issues

    def check_edge_crossings(self):
        """正交折线之间不得内部交叉。"""
        issues = []
        prepared = []
        for flow in self.flows:
            if flow.waypoints and len(flow.waypoints) >= 2:
                prepared.append((flow.id, self._segments(flow.waypoints)))
        for i in range(len(prepared)):
            id_a, segs_a = prepared[i]
            for j in range(i + 1, len(prepared)):
                id_b, segs_b = prepared[j]
                crossed = False
                for sa in segs_a:
                    for sb in segs_b:
                        if self._hv_proper_cross(*sa, *sb):
                            crossed = True
                            break
                    if crossed:
                        break
                if crossed:
                    issues.append(f"edge_cross:{id_a}×{id_b}")
        return issues

    # 共线重叠：短于该长度视为数值噪声；同源扇出/同宿汇合总线整段豁免
    EDGE_OVERLAP_MIN_LEN = 12.0

    def check_edge_overlaps(self):
        """无关连线不得长距离共线重叠。

        豁免：同源扇出、同宿汇合总线、端口短重合、以及短于 EDGE_OVERLAP_MIN_LEN 的重叠。
        """
        issues = []
        prepared = []
        for flow in self.flows:
            if flow.waypoints and len(flow.waypoints) >= 2:
                prepared.append((flow, self._segments(flow.waypoints)))
        for i in range(len(prepared)):
            fa, segs_a = prepared[i]
            for j in range(i + 1, len(prepared)):
                fb, segs_b = prepared[j]
                share_src = fa.source == fb.source
                share_tgt = fa.target == fb.target
                overlapped = False
                for sa in segs_a:
                    for sb in segs_b:
                        if not self._hv_collinear_overlap(
                            *sa, *sb, min_len=self.EDGE_OVERLAP_MIN_LEN
                        ):
                            continue
                        # 同宿汇合总线 / 同源扇出：允许共线
                        if share_tgt or share_src:
                            continue
                        overlapped = True
                        break
                    if overlapped:
                        break
                if overlapped:
                    issues.append(f"edge_overlap:{fa.id}×{fb.id}")
        return issues

    def recompute_waypoints(self, force_u_for=None):
        """按当前坐标重算全部边的 waypoints。"""
        force_u_for = force_u_for or set()
        self._lane_bucket = {}
        fan_in: dict = {}
        for flow in self.flows:
            fan_in.setdefault(flow.target, []).append(flow)
        bus_y_by_tgt = {}
        for tgt, fins in fan_in.items():
            if len(fins) < 3 or tgt not in self.nodes:
                continue
            bottoms = [
                self.nodes[f.source].bottom
                for f in fins
                if f.source in self.nodes
            ]
            if not bottoms:
                continue
            top = self.nodes[tgt].top
            bus_y_by_tgt[tgt] = (max(bottoms) + top) // 2
        for flow in self.flows:
            if flow.id in force_u_for:
                flow.waypoints = self.calc_u_waypoints(flow.source, flow.target)
            elif flow.target in bus_y_by_tgt:
                flow.waypoints = self.calc_bus_waypoints(
                    flow.source, flow.target, bus_y_by_tgt[flow.target]
                )
            else:
                flow.waypoints = self.calc_waypoints(flow.source, flow.target)

    def expand_spacing(self, extra_v=40, extra_h=40):
        """加大列间距与同行垂直间距，并刷新并行容器边界。"""
        skip = self.CONTAINER_TYPES | {"pstart", "pend"}
        nodes = [n for n in self.nodes.values() if n.type not in skip]
        if not nodes:
            return

        cols = {}
        for n in nodes:
            key = int(round(n.cx / 50.0) * 50)
            cols.setdefault(key, []).append(n)
        sorted_keys = sorted(cols.keys())
        if len(sorted_keys) >= 2:
            shifts = {}
            running_right = max(n.right for n in cols[sorted_keys[0]])
            shifts[sorted_keys[0]] = 0
            for i in range(1, len(sorted_keys)):
                cur_key = sorted_keys[i]
                cur_min_x = min(n.x for n in cols[cur_key])
                dx = max(0, running_right + self.HORIZONTAL_GAP + extra_h - cur_min_x)
                shifts[cur_key] = dx
                running_right = max(n.right for n in cols[cur_key]) + dx
            for key, ns in cols.items():
                dx = shifts.get(key, 0)
                if dx:
                    for n in ns:
                        n.x += dx

        for ns in cols.values():
            ns.sort(key=lambda n: n.y)
            for i in range(1, len(ns)):
                min_y = ns[i - 1].bottom + self.VERTICAL_GAP + extra_v
                if ns[i].y < min_y:
                    delta = min_y - ns[i].y
                    for j in range(i, len(ns)):
                        ns[j].y += delta

        for cid, children in self._container_children.items():
            if cid not in self.nodes:
                continue
            pstart = self._container_pstart.get(cid)
            pend = self._container_pend.get(cid)
            c = self.nodes[cid]
            self._auto_container_bounds(cid, children, c.x, c.y, pstart, pend)
            self._position_pstart_pend(cid, pstart, pend)

    def fix_layout_issues(self, max_attempts=6):
        """重叠/穿线/交叉/叠线：扩距 + 重路由（必要时 U 形），仍失败则返回问题列表。"""
        force_u = set()
        remaining = []
        for attempt in range(max_attempts):
            self.recompute_waypoints(force_u_for=force_u)
            overlaps = self.check_overlaps()
            through = self.check_edges_through_nodes()
            crosses = self.check_edge_crossings()
            edge_olaps = self.check_edge_overlaps()
            remaining = [f"overlap:{a}/{b}" for a, b in overlaps]
            remaining.extend(through)
            remaining.extend(crosses)
            remaining.extend(edge_olaps)
            if not remaining:
                self.shift_to_non_negative()
                return []
            for msg in crosses + edge_olaps:
                if msg.startswith("edge_cross:") or msg.startswith("edge_overlap:"):
                    force_u.update(msg.split(":", 1)[1].split("×"))
            for msg in through:
                if msg.startswith("edge_through:"):
                    force_u.add(msg.split(":", 1)[1].split("→")[0])
            self.expand_spacing(
                extra_v=35 + attempt * 30,
                extra_h=50 + attempt * 55,
            )
        self.shift_to_non_negative()
        return remaining

    def shift_to_non_negative(self):
        """若 x/y 小于 COORD_MIN（45），整图向右、向下平移，使最小坐标为 45。

        不把单个节点钳回边界（那会重叠）。左侧超出时图向右变宽。
        含节点、拐点，以及条件边标签（相对首个拐点向左/向上的偏移）。
        """
        if any(f.waypoints is None for f in self.flows):
            self.recompute_waypoints()

        xs = []
        ys = []
        for n in self.nodes.values():
            xs.append(n.x)
            ys.append(n.y)
        for f in self.flows:
            wps = f.waypoints or []
            for x, y in wps:
                xs.append(x)
                ys.append(y)
            if wps and (f.situation is not None or f.name):
                xs.append(wps[0][0] - self.LABEL_OFFSET_X)
                ys.append(wps[0][1] - self.LABEL_OFFSET_Y)
        if not xs:
            return

        min_x = min(xs)
        min_y = min(ys)
        floor = self.COORD_MIN
        dx = math.ceil(floor - min_x) if min_x < floor else 0
        dy = math.ceil(floor - min_y) if min_y < floor else 0
        if dx == 0 and dy == 0:
            return

        for n in self.nodes.values():
            n.x += dx
            n.y += dy
        for f in self.flows:
            if not f.waypoints:
                continue
            f.waypoints = [(x + dx, y + dy) for x, y in f.waypoints]

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
        if any(f.waypoints is None for f in self.flows):
            self.recompute_waypoints()
        edges = []
        for flow in self.flows:
            edges.append({
                "id": flow.id,
                "source": flow.source,
                "target": flow.target,
                "situation": flow.situation,
                "waypoints": list(flow.waypoints or []),
            })
        return edges

    def get_shape_xml(self):
        self.shift_to_non_negative()
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
        if any(f.waypoints is None for f in self.flows):
            self.recompute_waypoints()
        self.shift_to_non_negative()
        lines = []
        for flow in self.flows:
            waypoints = flow.waypoints or self.calc_waypoints(flow.source, flow.target)
            lines.append(
                f'    <bpmndi:BPMNEdge id="{flow.id}_di" '
                f'bpmnElement="{flow.id}">'
            )
            for wp in waypoints:
                lines.append(f'      <di:waypoint x="{wp[0]}" y="{wp[1]}" />')
            # 带 name 的条件/分支连线：含 BPMNLabel
            if flow.situation is not None or flow.name:
                label_name = flow.name
                if not label_name:
                    if flow.situation == "yes":
                        label_name = "是"
                    elif flow.situation == "no":
                        label_name = "否"
                    else:
                        label_name = str(flow.situation)
                # Label 放在首个 waypoint 附近
                lx = waypoints[0][0] - self.LABEL_OFFSET_X if waypoints else 0
                ly = waypoints[0][1] - self.LABEL_OFFSET_Y if waypoints else 0
                lines.append("      <bpmndi:BPMNLabel>")
                lines.append(
                    f'        <dc:Bounds x="{lx}" y="{ly}" width="120" height="12" />'
                )
                lines.append("      </bpmndi:BPMNLabel>")
            lines.append("    </bpmndi:BPMNEdge>")
        return "\n".join(lines)

    def get_sequence_flow_xml(self):
        """生成 <bpmn2:sequenceFlow>（见 golden_xml_rules）

        - plain：自闭合，无 ext:data
        - yes/no：name=\"是\"/\"否\"，ext:data 仅 situation
        - 分支索引：name 可自定义，situation 为数字字符串
        """
        lines = []
        for flow in self.flows:
            if flow.situation == "yes":
                lines.append(
                    f'  <bpmn2:sequenceFlow id="{flow.id}" name="是" '
                    f'sourceRef="{flow.source}" targetRef="{flow.target}">\n'
                    f'    <ext:data><![CDATA[{{"situation":"yes"}}]]></ext:data>\n'
                    f'  </bpmn2:sequenceFlow>'
                )
            elif flow.situation == "no":
                lines.append(
                    f'  <bpmn2:sequenceFlow id="{flow.id}" name="否" '
                    f'sourceRef="{flow.source}" targetRef="{flow.target}">\n'
                    f'    <ext:data><![CDATA[{{"situation":"no"}}]]></ext:data>\n'
                    f'  </bpmn2:sequenceFlow>'
                )
            elif flow.situation is not None and str(flow.situation).isdigit():
                name = flow.name or f"选项{flow.situation}"
                lines.append(
                    f'  <bpmn2:sequenceFlow id="{flow.id}" name="{name}" '
                    f'sourceRef="{flow.source}" targetRef="{flow.target}">\n'
                    f'    <ext:data><![CDATA[{{"situation":"{flow.situation}"}}]]></ext:data>\n'
                    f'  </bpmn2:sequenceFlow>'
                )
            else:
                # 普通连线：自闭合、无 ext:data
                lines.append(
                    f'  <bpmn2:sequenceFlow id="{flow.id}" '
                    f'sourceRef="{flow.source}" targetRef="{flow.target}" />'
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
        5. 条件节点(and/or/cond) outgoing 为 1（仅是）或 2（是+否）；仅明确需要否时才为 2
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

            if node.type in ("and", "or", "cond"):
                if len(out) not in (1, 2):
                    issues.append(
                        f"条件节点 {nid}({node.type}) outgoing 应为 1（仅是）或 2（是+否），实际 {len(out)} 条"
                    )
                else:
                    situations = []
                    for fid in out:
                        for flow in self.flows:
                            if flow.id == fid:
                                situations.append(flow.situation)
                    if "yes" not in situations:
                        issues.append(
                            f"条件节点 {nid}({node.type}) 必须包含 situation=yes 的 outgoing"
                        )
                    if len(out) == 2 and "no" not in situations:
                        issues.append(
                            f"条件节点 {nid}({node.type}) 两条 outgoing 时应含 situation=no"
                        )

        return issues

    def get_diagram_xml(self, process_id="Process_1"):
        """生成完整 BPMNDiagram。

        Plane 内先全部 BPMNEdge，再全部 BPMNShape。
        """
        edges = self.get_edge_xml()
        shapes = self.get_shape_xml()
        return (
            f'<bpmndi:BPMNDiagram id="BPMNDiagram_1">\n'
            f'  <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="{process_id}">\n'
            f'{edges}\n'
            f'{shapes}\n'
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

        - sequenceFlow 与 BPMNEdge 同一套 flow id
        - Diagram 内先 Edge 后 Shape
        - plain 连线自闭合无 ext:data；条件边 name=是/否
        - 节点 incoming/outgoing 与 flow 一致
        """
        missing = [nid for nid in self.node_order if nid not in node_xml_by_id]
        if missing:
            raise ValueError(f"缺少节点 XML: {missing}")

        issues = self.check_connection_integrity()
        if issues:
            raise ValueError("连线完整性失败: " + "; ".join(issues))
        parallel_issues = self.check_parallel_integrity()
        if parallel_issues:
            raise ValueError("并行结构失败: " + "; ".join(parallel_issues))
        layout_issues = self.fix_layout_issues()
        if layout_issues:
            raise ValueError("布局校验失败（重叠/穿线/交叉/叠线）: " + "; ".join(layout_issues))

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
