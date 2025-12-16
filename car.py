import pymunk
from settings import CAT_GROUND, CAT_ROAD, CAT_CAR

class Car:
    def __init__(self, space, x, y, mass_val=20): 
        self.space = space
        self.bodies = []
        self.shapes = []
        self.joints = []
        self.collide_mask = CAT_GROUND | CAT_ROAD

        # --- 车身建模 ---
        hull_verts = [
            (-35, -10), 
            (35, -10),  
            (50, 5),    
            (25, 12),   
            (-25, 12),  
            (-45, 5)    
        ]
        
        mass = max(1.0, mass_val) 
        moment = pymunk.moment_for_poly(mass, hull_verts)
        self.chassis_body = pymunk.Body(mass, moment)
        self.chassis_body.position = (x, y)
        
        chassis_shape = pymunk.Poly(self.chassis_body, hull_verts)
        chassis_shape.color = (100, 200, 100, 255) 
        chassis_shape.filter = pymunk.ShapeFilter(categories=CAT_CAR, mask=self.collide_mask)
        chassis_shape.friction = 0.0 
        
        self.space.add(self.chassis_body, chassis_shape)
        self.bodies.append(self.chassis_body)
        self.shapes.append(chassis_shape)
        
        # --- 轮子参数 ---
        wheel_mass = 3.0 
        wheel_radius = 18       
        wheel_x_offset = 42     
        wheel_y_offset = 22     
        
        # 1. 先创建轮子 (create_wheel 只负责造轮子，不负责设动力)
        self.front_wheel, self.front_motor = self.create_wheel(x + wheel_x_offset, y + wheel_y_offset, wheel_mass, wheel_radius)
        self.rear_wheel, self.rear_motor = self.create_wheel(x - wheel_x_offset, y + wheel_y_offset, wheel_mass, wheel_radius)
        
        # 2. 后设定动力 (修复报错的关键：轮子都造好了，再分配力气)
        # 前轮：标准动力
        self.front_motor.max_force = 2000000
        # 后轮：减半动力 (防止翘头)
        self.rear_motor.max_force = 1000000 
        
        # --- 悬挂调教 (修复报错关键点) ---
        # 即使质量很大，弹簧硬度也不能无限大，否则物理引擎会崩溃
        # 我们用 min() 函数给它封顶，最大不超过 20000
        raw_stiffness = mass * 120
        stiffness = min(raw_stiffness, 20000) 
        
        damping = 10           
        rest_len = 0      
        
        for wheel, offset_dir in [(self.front_wheel, 1), (self.rear_wheel, -1)]:
            anchor_x = wheel_x_offset * offset_dir
            anchor_y = 8 
            
            groove_start = (anchor_x, 8)  
            groove_end = (anchor_x, 40)    
            
            spring = pymunk.DampedSpring(self.chassis_body, wheel, (anchor_x, anchor_y), (0,0), rest_len, stiffness, damping)
            groove = pymunk.GrooveJoint(self.chassis_body, wheel, groove_start, groove_end, (0,0))
            groove.error_bias = 0.1 
            
            self.space.add(spring, groove)
            self.joints.extend([spring, groove])

    def create_wheel(self, x, y, mass, radius):
        moment = pymunk.moment_for_circle(mass, 0, radius)
        body = pymunk.Body(mass, moment)
        body.position = (x, y)
        shape = pymunk.Circle(body, radius)
        shape.color = (40, 40, 40, 255)
        
        shape.friction = 6.0 
        shape.filter = pymunk.ShapeFilter(categories=CAT_CAR, mask=self.collide_mask)
        
        self.space.add(body, shape)
        self.bodies.append(body)
        self.shapes.append(shape)
        
        motor = pymunk.SimpleMotor(self.chassis_body, body, 0)
        # 注意：这里我们不再设置 max_force，而是在 __init__ 里设置
        # 默认给一个初始值，防止未设置时出错（虽然上面马上就会覆盖它）
        motor.max_force = 1000000 
        
        self.space.add(motor)
        self.joints.append(motor)
        return body, motor

    def drive(self, speed):
        self.chassis_body.activate()
        self.front_wheel.activate()
        self.rear_wheel.activate()
        
        self.front_motor.rate = -speed 
        self.rear_motor.rate = -speed 

    def destroy(self):
        for x in self.shapes + self.joints + self.bodies:
            self.space.remove(x)