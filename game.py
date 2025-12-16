import pygame
import pymunk
import pymunk.pygame_util
import math

# 导入我们的自定义模块
from settings import *
from ui import Button, Dropdown
from car import Car

class BridgeBuilder:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Poly Bridge: Terrain Collision & Limits")
        self.clock = pygame.time.Clock()
        
        self.space = pymunk.Space()
        self.space.gravity = (0.0, 0.0)
        self.space.iterations = 30 # 适当增加迭代次数提高碰撞稳定性
        self.space.damping = 0.99
        
        self.draw_options = pymunk.pygame_util.DrawOptions(self.screen)
        self.draw_options.flags = pymunk.pygame_util.DrawOptions.DRAW_SHAPES
        
        self.mode = "BUILD"
        self.tool = "ROAD"
        
        self.nodes = []
        self.beams = [] 
        self.joints = []
        self.saved_state = None 
        
        self.mouse_start_node = None
        self.car = None
        self.car_mass = 15.0
        
        self.input_mass_active = False
        self.input_mass_text = str(self.car_mass)
        self.input_mass_rect = pygame.Rect(480, HEIGHT-45, 120, 30)
        
        self.create_ui()
        self.reset_level()

    def create_ui(self):
        self.btn_mode_build = Button(20, HEIGHT-50, 70, 40, "BUILD", self.to_build_mode, (150, 200, 150))
        self.btn_mode_sim = Button(100, HEIGHT-50, 70, 40, "SIM", self.to_sim_mode, (200, 150, 150))
        self.btn_drive_fwd = Button(WIDTH-140, HEIGHT-50, 60, 40, "GO ->", lambda: self.drive(25), (100, 220, 100))
        self.btn_drive_bwd = Button(WIDTH-70, HEIGHT-50, 60, 40, "<- BK", lambda: self.drive(-25), (100, 220, 100))

        tool_options = [
            Button(0, 0, 0, 0, "Road", lambda: self.set_tool("ROAD"), ROAD_COLOR[:3]),
            Button(0, 0, 0, 0, "Wood", lambda: self.set_tool("WOOD"), WOOD_COLOR[:3]),
            Button(0, 0, 0, 0, "Steel", lambda: self.set_tool("STEEL"), STEEL_COLOR[:3]),
            Button(0, 0, 0, 0, "DELETE", lambda: self.set_tool("DELETE"), DELETE_COLOR[:3]),
        ]
        self.dd_tools = Dropdown(200, HEIGHT-180, 80, 30, "TOOLS", tool_options)
        self.dd_tools.rect.y = HEIGHT - 50
        self.dd_tools.main_btn.rect.y = HEIGHT - 50
        offset = 35
        for btn in tool_options:
            btn.rect.y = (HEIGHT - 50) - offset
            offset += 32

        env_options = [
            Button(0, 0, 0, 0, "Spawn Car", self.spawn_car, (100, 200, 255)),
            Button(0, 0, 0, 0, "Reset Level", self.reset_level, (200, 100, 100)),
        ]
        self.dd_env = Dropdown(300, HEIGHT-50, 90, 30, "ACTIONS", env_options)
        offset = 35
        for btn in env_options:
            btn.rect.y = (HEIGHT - 50) - offset
            offset += 32

        self.ui_elements = [self.btn_mode_build, self.btn_mode_sim, self.btn_drive_fwd, self.btn_drive_bwd, self.dd_tools, self.dd_env]
        self.update_button_states()

    def update_button_states(self):
        self.btn_mode_build.active = (self.mode == "BUILD")
        self.btn_mode_sim.active = (self.mode == "SIMULATE")
        for btn in self.dd_tools.options:
            btn.active = (btn.text.upper().replace("ROAD", "ROAD") == self.tool) or \
                         (btn.text == "Wood" and self.tool == "WOOD") or \
                         (btn.text == "Steel" and self.tool == "STEEL") or \
                         (btn.text == "DELETE" and self.tool == "DELETE")

    def set_tool(self, tool):
        self.tool = tool
        self.mouse_start_node = None
        self.dd_tools.close()
        self.update_button_states()
    
    def to_build_mode(self):
        if self.mode != "BUILD":
            self.mode = "BUILD"
            self.load_bridge_state()
            self.space.gravity = (0, 0)
            self.update_button_states()

    def to_sim_mode(self):
        if self.mode == "BUILD":
            self.save_bridge_state()
            self.mode = "SIMULATE"
            self.space.gravity = (0, 900)
            self.update_button_states()

    def save_bridge_state(self):
        saved_nodes = []
        node_map = {}
        for i, node in enumerate(self.nodes):
            is_static = (node.body_type == pymunk.Body.STATIC)
            saved_nodes.append((node.position.x, node.position.y, is_static))
            node_map[node] = i
        
        saved_beams = []
        for beam_body, beam_shape in self.beams:
            t_type = getattr(beam_shape, 'tool_type', 'WOOD')
            connected_joints = [j for j in self.joints if j.b == beam_body]
            if len(connected_joints) == 2:
                node_a = connected_joints[0].a
                node_b = connected_joints[1].a
                if node_a in node_map and node_b in node_map:
                    idx_a = node_map[node_a]
                    idx_b = node_map[node_b]
                    saved_beams.append((idx_a, idx_b, t_type))

        self.saved_state = {'nodes': saved_nodes, 'beams': saved_beams}

    def load_bridge_state(self):
        if not self.saved_state: return
        self.clear_physics_objects()
        self.create_terrain_only()
        
        new_nodes_list = []
        for (x, y, is_static) in self.saved_state['nodes']:
            new_node = self.create_node(x, y, static=is_static)
            new_nodes_list.append(new_node)
            
        old_tool = self.tool
        for (idx_a, idx_b, t_type) in self.saved_state['beams']:
            if idx_a < len(new_nodes_list) and idx_b < len(new_nodes_list):
                node_a = new_nodes_list[idx_a]
                node_b = new_nodes_list[idx_b]
                self.tool = t_type
                self.create_beam(node_a, node_b)
        self.tool = old_tool

    def clear_physics_objects(self):
        if self.car: self.car.destroy(); self.car = None
        for b in self.nodes: self.space.remove(b, *b.shapes)
        for b, s in self.beams: self.space.remove(b, s)
        for j in self.joints: self.space.remove(j)
        self.nodes.clear(); self.beams.clear(); self.joints.clear()

    # --- 新增: 检测坐标是否在实心地形内 (禁止建造区域) ---
    def is_in_terrain(self, pos):
        x, y = pos
        # 定义左岸和右岸的实心区域
        # 左岸: x < 200, y > 405 (稍微留出一点表面容差)
        if x <= 200 and y > 405: 
            return True
        # 右岸: x > 1000, y > 405
        if x >= 1000 and y > 405:
            return True
        return False

    def create_terrain_only(self):
        for s in list(self.space.shapes):
            if s.filter.categories == CAT_GROUND:
                if s.body == self.space.static_body:
                    self.space.remove(s)
                else:
                    self.space.remove(s, s.body)
                
        ground = pymunk.Segment(self.space.static_body, (0, HEIGHT), (WIDTH, HEIGHT), 5)
        ground.friction = 1.0
        # 地面也要和车、路、支撑物碰撞
        ground.filter = pymunk.ShapeFilter(categories=CAT_GROUND, mask=CAT_CAR | CAT_ROAD | CAT_SUPPORT)
        self.space.add(ground)
        self.create_platform(0, 400, 200, 200)
        self.create_platform(1000, 400, 200, 200)

    def create_default_anchors(self):
        y_pos = 405 
        self.create_node(200, y_pos, static=True)  
        self.create_node(1000, y_pos, static=True) 
        self.create_node(100, y_pos, static=True)
        self.create_node(1100, y_pos, static=True)

    def reset_level(self):
        self.mode = "BUILD"
        self.space.gravity = (0, 0)
        self.saved_state = None
        self.clear_physics_objects()
        self.create_terrain_only()
        self.create_default_anchors()
        self.update_button_states()

    def create_platform(self, x, y, w, h):
        b = pymunk.Body(body_type=pymunk.Body.STATIC)
        b.position = (x + w/2, y + h/2)
        s = pymunk.Poly.create_box(b, (w, h))
        s.color = (50, 50, 50, 255)
        s.friction = 1.0
        # --- 修改: 岸边碰撞掩码 ---
        # 以前只撞车，现在要撞 Road 和 Support (木头/钢)
        s.filter = pymunk.ShapeFilter(categories=CAT_GROUND, mask=CAT_CAR | CAT_ROAD | CAT_SUPPORT)
        self.space.add(b, s)

    def create_node(self, x, y, static=False):
        mass = 1
        radius = 5
        moment = pymunk.moment_for_circle(mass, 0, radius)
        if static: body = pymunk.Body(body_type=pymunk.Body.STATIC)
        else: body = pymunk.Body(mass, moment)
        
        body.position = (x, y)
        shape = pymunk.Circle(body, radius)
        shape.color = (0, 0, 0, 0) 
        shape.filter = pymunk.ShapeFilter(categories=CAT_NODE, mask=0) 
        self.space.add(body, shape)
        self.nodes.append(body)
        return body

    def create_beam(self, body_a, body_b):
        p1, p2 = body_a.position, body_b.position
        v = p2 - p1
        dist = v.length
        if dist < 10: return
        angle = v.angle
        mid_point = (p1 + p2) / 2

        width = 5; mass = 5; strength = 5000
        category = CAT_SUPPORT; mask = 0; color = WOOD_COLOR
        current_tool_type = self.tool 

        # --- 修改: 材料碰撞掩码 ---
        if self.tool == "ROAD":
            width = 10; mass = 10; strength = 12000; color = ROAD_COLOR
            category = CAT_ROAD
            # 路面：撞车 + 撞地
            mask = CAT_CAR | CAT_GROUND 
        elif self.tool == "WOOD":
            width = 6; mass = 5; strength = 3500; color = WOOD_COLOR
            # 木头：不撞车(mask=0的话)，但要撞地
            mask = CAT_GROUND 
        elif self.tool == "STEEL":
            width = 4; mass = 8; strength = 8000; color = STEEL_COLOR
            # 钢材：同木头
            mask = CAT_GROUND

        size = (dist, width)
        moment = pymunk.moment_for_box(mass, size)
        beam_body = pymunk.Body(mass, moment)
        beam_body.position = mid_point
        beam_body.angle = angle
        
        shape = pymunk.Poly.create_box(beam_body, size)
        shape.friction = 1.0
        shape.color = color
        shape.filter = pymunk.ShapeFilter(categories=category, mask=mask)
        shape.original_color = color 
        shape.tool_type = current_tool_type 
        
        self.space.add(beam_body, shape)
        self.beams.append((beam_body, shape))

        pivot_a = pymunk.PivotJoint(body_a, beam_body, (0, 0), (-dist/2, 0))
        pivot_b = pymunk.PivotJoint(body_b, beam_body, (0, 0), (dist/2, 0))
        pivot_a.error_bias = 0.5 
        pivot_b.error_bias = 0.5
        pivot_a.breaking_force = strength
        pivot_b.breaking_force = strength
        self.space.add(pivot_a, pivot_b)
        self.joints.extend([pivot_a, pivot_b])

    def get_nearest_node(self, pos):
        for body in self.nodes:
            if body.position.get_distance(pos) < 20: return body
        return None

    def delete_at_pos(self, pos):
        node = self.get_nearest_node(pos)
        if node:
            x, y = node.position
            is_base_anchor = (abs(y - 405) < 1) and (abs(x - 200) < 5 or abs(x - 1000) < 5)
            if is_base_anchor:
                pass
            else:
                self.remove_node_and_connected(node)
            return
        
        pq = self.space.point_query_nearest(pos, 5, pymunk.ShapeFilter())
        if pq and pq.shape:
            for beam_tuple in self.beams:
                if beam_tuple[1] == pq.shape:
                    self.remove_beam(beam_tuple)
                    break

    def remove_node_and_connected(self, node):
        bodies_to_del = set()
        for j in self.joints[:]:
            if j.a == node or j.b == node:
                other = j.b if j.a == node else j.a
                bodies_to_del.add(other)
                self.space.remove(j); self.joints.remove(j)
        for b_tpl in self.beams[:]:
            if b_tpl[0] in bodies_to_del: self.remove_beam(b_tpl)
        if node in self.nodes: self.nodes.remove(node)
        self.space.remove(node, *node.shapes)

    def remove_beam(self, tpl):
        body, shape = tpl
        self.space.remove(body, shape)
        self.beams.remove(tpl)
        for j in self.joints[:]:
            if j.a == body or j.b == body:
                self.space.remove(j); self.joints.remove(j)

    def spawn_car(self):
        if self.car: self.car.destroy()
        self.car = Car(self.space, 80, 275, self.car_mass)

    def drive(self, s):
        if self.mode == "BUILD": self.to_sim_mode()
        if self.car: self.car.drive(s)

    def check_stress(self):
        if self.mode != "SIMULATE": return
        to_del = []
        for j in self.joints:
            lim = getattr(j, 'breaking_force', float('inf'))
            if j.impulse > lim: to_del.append(j)
            else:
                beam = j.b
                target = None
                for b, s in self.beams:
                    if b == beam: target = s; break
                if target:
                    stress = min(1.0, j.impulse / lim)
                    oc = target.original_color
                    target.color = (
                        int(oc[0] + (255-oc[0])*stress),
                        int(oc[1] * (1-stress)),
                        int(oc[2] * (1-stress)),
                        255
                    )
        for j in to_del: self.space.remove(j); self.joints.remove(j)

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return False
            
            if self.input_mass_active:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        try:
                            val = float(self.input_mass_text)
                            if val > 0: self.car_mass = val
                        except:
                            self.input_mass_text = str(self.car_mass)
                        self.input_mass_active = False
                    elif event.key == pygame.K_BACKSPACE:
                        self.input_mass_text = self.input_mass_text[:-1]
                    else:
                        if event.unicode.isdigit() or event.unicode == '.':
                            self.input_mass_text += event.unicode
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if not self.input_mass_rect.collidepoint(event.pos):
                         try:
                            val = float(self.input_mass_text)
                            if val > 0: self.car_mass = val
                         except: pass
                         self.input_mass_active = False
            
            if not self.input_mass_active:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1: self.set_tool("ROAD")
                    if event.key == pygame.K_2: self.set_tool("WOOD")
                    if event.key == pygame.K_3: self.set_tool("STEEL")
                    if event.key == pygame.K_4: self.set_tool("DELETE")
                    if event.key == pygame.K_SPACE: 
                        if self.mode == "BUILD": self.to_sim_mode()
                        else: self.to_build_mode()

            ui_hit = False
            for el in reversed(self.ui_elements):
                if el.handle_event(event): ui_hit = True; break
            
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.input_mass_rect.collidepoint(event.pos):
                    self.input_mass_active = True
                    self.input_mass_text = "" 
                    ui_hit = True

            if ui_hit: continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.tool == "DELETE": 
                    self.delete_at_pos(event.pos)
                elif self.mode == "BUILD":
                    node = self.get_nearest_node(event.pos)
                    if node: 
                        self.mouse_start_node = node
                    else:
                        # --- 修改: 建造限制检查 ---
                        # 如果点击的是空地，且位于实心岸边内部，禁止开始建造
                        if self.is_in_terrain(event.pos):
                            self.mouse_start_node = None # 禁止操作
                        else:
                            # 正常锚点逻辑
                            mx, my = event.pos
                            if abs(mx - 200) < 15 and my > 405:
                                self.create_node(200, my, static=True)
                            elif abs(mx - 1000) < 15 and my > 405:
                                self.create_node(1000, my, static=True)
                            pass 

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self.mode == "BUILD" and self.tool != "DELETE":
                    if self.mouse_start_node:
                        end_node = self.get_nearest_node(event.pos)
                        start_pos = self.mouse_start_node.position
                        
                        mouse_vec = pymunk.Vec2d(*event.pos) - start_pos
                        dist = mouse_vec.length
                        
                        # 1. 连接现有节点
                        if end_node and end_node != self.mouse_start_node:
                            if dist <= MAX_BUILD_DIST:
                                self.create_beam(self.mouse_start_node, end_node)
                        
                        # 2. 点击空地 (新节点)
                        elif end_node is None:
                            target_pos = event.pos
                            
                            # 长度限制截断
                            if dist > MAX_BUILD_DIST:
                                clamped_vec = mouse_vec.normalized() * MAX_BUILD_DIST
                                target_pos = (start_pos.x + clamped_vec.x, start_pos.y + clamped_vec.y)
                            
                            # --- 修改: 建造限制检查 ---
                            # 如果目标位置在地下，禁止建造
                            if not self.is_in_terrain(target_pos):
                                
                                # 锚点吸附检查
                                mx, my = target_pos
                                is_created = False
                                if abs(mx - 200) < 15 and my > 405:
                                    new_node = self.create_node(200, my, static=True)
                                    is_created = True
                                elif abs(mx - 1000) < 15 and my > 405:
                                    new_node = self.create_node(1000, my, static=True)
                                    is_created = True
                                else:
                                    new_node = self.create_node(*target_pos)
                                    is_created = True
                                    
                                if is_created:
                                    self.create_beam(self.mouse_start_node, new_node)
                                
                        self.mouse_start_node = None
        return True

    def draw(self, screen=None):
        if screen is None: screen = self.screen
        screen.fill(WHITE)
        self.space.debug_draw(self.draw_options)
        
        mouse_pos = pygame.mouse.get_pos()
        nearest = self.get_nearest_node(mouse_pos)
        
        # 绘制节点
        for node in self.nodes:
            pos = int(node.position.x), int(node.position.y)
            is_edge = (abs(pos[0]-200) < 1 or abs(pos[0]-1000) < 1) and pos[1] >= 405
            
            if node == nearest and self.mode == "BUILD":
                pygame.draw.circle(screen, (255, 200, 50), pos, 8)
            
            if is_edge:
                pygame.draw.circle(screen, EDGE_NODE_COLOR, pos, 6)
                pygame.draw.circle(screen, BLACK, pos, 6, 2)
            elif node.body_type == pymunk.Body.STATIC:
                 pygame.draw.circle(screen, NODE_COLOR, pos, 5)
                 pygame.draw.circle(screen, NODE_BORDER, pos, 5, 2)
                 pygame.draw.circle(screen, (200, 50, 50), pos, 2)
            else:
                 pygame.draw.circle(screen, NODE_COLOR, pos, 5)
                 pygame.draw.circle(screen, NODE_BORDER, pos, 5, 2)

        if self.mode == "BUILD" and self.mouse_start_node:
            start_pos = self.mouse_start_node.position
            
            # 绘制限制圆
            pygame.draw.circle(screen, (200, 200, 200), (int(start_pos.x), int(start_pos.y)), MAX_BUILD_DIST, 1)
            
            dist_vec = pymunk.Vec2d(*mouse_pos) - start_pos
            current_dist = dist_vec.length
            
            line_color = BLACK
            if self.tool == "ROAD": line_color = ROAD_COLOR[:3]
            elif self.tool == "WOOD": line_color = WOOD_COLOR[:3]
            elif self.tool == "STEEL": line_color = STEEL_COLOR[:3]
            
            target_pos = mouse_pos
            
            # --- 修改: 可视化反馈 ---
            # 如果超长 OR 指向地下，变红
            is_too_long = (current_dist > MAX_BUILD_DIST)
            # 计算截断位置用于判断是否在地下
            clamped_vec = dist_vec
            if is_too_long: 
                clamped_vec = dist_vec.normalized() * MAX_BUILD_DIST
            check_pos = (start_pos.x + clamped_vec.x, start_pos.y + clamped_vec.y)
            is_underground = self.is_in_terrain(check_pos)
            
            if nearest and nearest != self.mouse_start_node:
                if is_too_long:
                    line_color = (255, 50, 50) 
                    target_pos = nearest.position 
            else:
                if is_too_long:
                    target_pos = start_pos + clamped_vec
                    pygame.draw.line(screen, (220, 220, 220), start_pos, mouse_pos, 1)
                
                # 如果最终落点在地下，变红
                if is_underground:
                    line_color = (255, 50, 50)

            pygame.draw.line(screen, line_color, start_pos, target_pos, 3)

        pygame.draw.rect(screen, WHITE, (0, HEIGHT-60, WIDTH, 60))
        pygame.draw.line(screen, BLACK, (0, HEIGHT-60), (WIDTH, HEIGHT-60), 2)
        for el in self.ui_elements: el.draw(screen, mouse_pos)
        
        font = pygame.font.SysFont("Arial", 16, bold=True)
        lbl = font.render("Mass:", True, BLACK)
        screen.blit(lbl, (430, HEIGHT-40))
        
        box_col = WHITE if not self.input_mass_active else (255, 255, 200)
        pygame.draw.rect(screen, box_col, self.input_mass_rect, border_radius=4)
        pygame.draw.rect(screen, BLACK, self.input_mass_rect, 2, border_radius=4)
        
        display_txt = self.input_mass_text if self.input_mass_active else str(self.car_mass)
        txt_surf = font.render(display_txt, True, BLACK)
        screen.blit(txt_surf, (self.input_mass_rect.x + 5, self.input_mass_rect.y + 5))

        info = f"Tool: {self.tool}"
        screen.blit(pygame.font.SysFont(None, 24).render(info, True, BLACK), (620, HEIGHT-40))
        
        pygame.display.flip()

    def run(self):
        while True: 
            if not self.handle_input(): break
            
            # --- 关键修改: 只有在 SIMULATE 模式下才运行物理引擎 ---
            # 这会让 BUILD 模式完全静止，节点绝对不会乱动
            if self.mode == "SIMULATE":
                steps = 5 
                dt = 1.0 / (FPS * steps) 
                for _ in range(steps):
                    self.space.step(dt)
                    self.check_stress()
            
            # 如果在 BUILD 模式，我们不运行 space.step()
            # 这样所有物体都会停留在最后的位置（或初始位置）
            
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()