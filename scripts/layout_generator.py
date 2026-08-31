"""BPMN 布局生成器：防重叠坐标 + 可见连线路径

使用方法：
    from layout_generator import LayoutGenerator
    gen = LayoutGenerator()
    gen.add_node("node1", "dcs", "启动泵", 200, 60)
    gen.add_flow("flow1", "node1", "node2", situation="yes")
    gen.layout_vertical(center_x=500, start_y=60, gap=100)
    gen.layout_parallel(center_x=500, start_y=300, gap=300)
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
        "guide": (200, 60),
        "confirm": (200, 60),
        "subproc": (200, 60),
        "parallel1": (800, 600),
        "parallel2": (1460, 1290),
        "pstart": (800, 5),
        "pend": (800, 5),
        "text": (300, 60),
    }

    def __init__(self):
        self.nodes = {}
        self.node_order = []
        self.flows = []

    def add_node(self, node_id, node_type, name=""):
        w, h = self.NODE_SIZES.get(node_type, (200, 60))
        node = Node(node_id, node_type, name, w, h)
        self.nodes[node_id] = node
        self.node_order.append(node_id)
        return node

    def add_flow(self, flow_id, source, target, situation=None, name=None):
        self.flows.append(Flow(flow_id, source, target, situation, name))

    def layout_vertical(self, node_ids, center_x=500, start_y=60, gap=None):
        gap = gap or self.VERTICAL_GAP
        y = start_y
        for nid in node_ids:
            node = self.nodes[nid]
            node.x = center_x - node.w // 2
            node.y = y
            y += node.h + gap

    def layout_parallel(self, branch_groups, start_x=100, start_y=280,
                        col_gap=None, row_gap=None):
        col_gap = col_gap or self.HORIZONTAL_GAP
        row_gap = row_gap or self.VERTICAL_GAP
        x = start_x
        for branch in branch_groups:
            y = start_y
            for nid in branch:
                node = self.nodes[nid]
                node.x = x
                node.y = y
                y += node.h + row_gap
            x += 200 + col_gap

    def layout_container(self, container_id, child_ids, x=None, y=None):
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

    def calc_waypoints(self, src_id, tgt_id):
        src = self.nodes[src_id]
        tgt = self.nodes[tgt_id]
        sx, sy = src.cx, src.bottom
        tx, ty = tgt.cx, tgt.top
        if abs(sx - tx) < 10:
            return [(sx, sy), (tx, ty)]
        all_nodes = list(self.nodes.values())
        mid_y = (sy + ty) // 2
        for n in all_nodes:
            if n.id in (src_id, tgt_id):
                continue
            if n.y < mid_y < n.bottom:
                mid_y = n.bottom + self.WAYPOINT_MARGIN
                break
        return [(sx, sy), (sx, mid_y), (tx, mid_y), (tx, ty)]

    def calc_u_waypoints(self, src_id, tgt_id, side="right"):
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

    def check_overlaps(self, gap=0):
        nodes = list(self.nodes.values())
        overlaps = []
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                if nodes[i].overlaps(nodes[j], gap):
                    overlaps.append((nodes[i].id, nodes[j].id))
        return overlaps

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

    def get_diagram_xml(self):
        shapes = self.get_shape_xml()
        edges = self.get_edge_xml()
        return f'  <bpmndi:BPMNDiagram id="BPMNDiagram_1">\n    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1">\n{shapes}\n{edges}\n    </bpmndi:BPMNPlane>\n  </bpmndi:BPMNDiagram>'
