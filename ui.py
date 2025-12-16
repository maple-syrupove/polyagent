# ui.py
import pygame
from settings import BLACK

class Button:
    def __init__(self, x, y, w, h, text, callback, color=(220, 220, 220), text_size=14):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.callback = callback
        if len(color) == 3: color = (*color, 255)
        self.base_color = color
        self.font = pygame.font.SysFont("Arial", text_size, bold=True)
        self.active = False
        self.visible = True
        
    def draw(self, screen, mouse_pos):
        if not self.visible: return
        is_hover = self.rect.collidepoint(mouse_pos)
        if self.active:
            c = (255, 220, 100, 255)
            border_col = BLACK
            width = 2
        elif is_hover:
            c = (min(self.base_color[0]+20,255), min(self.base_color[1]+20,255), min(self.base_color[2]+20,255), 255)
            border_col = BLACK
            width = 1
        else:
            c = self.base_color
            border_col = (100, 100, 100)
            width = 1
        pygame.draw.rect(screen, c, self.rect, border_radius=4)
        pygame.draw.rect(screen, border_col, self.rect, width, border_radius=4)
        txt = self.font.render(self.text, True, BLACK)
        screen.blit(txt, txt.get_rect(center=self.rect.center))

    def handle_event(self, event):
        if not self.visible: return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.callback()
            return True
        return False

class Dropdown:
    def __init__(self, x, y, w, h, main_text, options, color=(180, 180, 200)):
        self.rect = pygame.Rect(x, y, w, h)
        self.main_btn = Button(x, y, w, h, main_text + " v", self.toggle, color)
        self.options = options 
        self.expanded = False
        offset_y = h
        for btn in self.options:
            btn.rect.x = x
            btn.rect.y = y + offset_y
            btn.rect.width = w
            btn.rect.height = h
            btn.visible = False
            offset_y += h + 2 

    def toggle(self):
        self.expanded = not self.expanded
        base_txt = self.main_btn.text[:-2]
        self.main_btn.text = base_txt + (" ^" if self.expanded else " v")
        for btn in self.options:
            btn.visible = self.expanded

    def close(self):
        self.expanded = False
        base_txt = self.main_btn.text[:-2]
        self.main_btn.text = base_txt + " v"
        for btn in self.options:
            btn.visible = False

    def draw(self, screen, mouse_pos):
        if self.expanded:
            total_h = self.rect.height + len(self.options) * (self.rect.height + 2)
            bg_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, total_h)
            pygame.draw.rect(screen, (240, 240, 240), bg_rect, border_radius=4)
            pygame.draw.rect(screen, (100, 100, 100), bg_rect, 1, border_radius=4)
            for btn in self.options:
                btn.draw(screen, mouse_pos)
        self.main_btn.draw(screen, mouse_pos)

    def handle_event(self, event):
        if self.main_btn.handle_event(event): return True
        if self.expanded:
            for btn in self.options:
                if btn.handle_event(event): return True
        return False