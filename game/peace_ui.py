import pygame
import sys
import ctypes

WIDTH, HEIGHT = 1280, 720
STATUS_BAR_HEIGHT = 60 
LEFTBAR_WIDTH = 230
RIGHTBAR_WIDTH = 250
BOTTOMBAR_HEIGHT = 70

ctypes.windll.user32.SetProcessDPIAware()


class PeaceTreatyScreen:
    
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.title_font = pygame.font.SysFont("bahnschrift", 20, bold=True)  
        self.mini_font= pygame.font.SysFont("bahnschrift", 12)  
        self.small_font = pygame.font.SysFont("bahnschrift", 15)
        
        self.running = True
        
        self.exit_btn_rect = pygame.Rect(20, HEIGHT - BOTTOMBAR_HEIGHT + 15, 180, 40)
        self.clear_btn_rect = pygame.Rect(WIDTH - RIGHTBAR_WIDTH + (RIGHTBAR_WIDTH - 140) // 2, HEIGHT - BOTTOMBAR_HEIGHT - 52, 140, 32)
        self.chat_btn_rect = pygame.Rect((WIDTH // 2) - 210, HEIGHT - BOTTOMBAR_HEIGHT + 15, 200, 40)
        self.history_btn_rect = pygame.Rect((WIDTH // 2) + 10, HEIGHT - BOTTOMBAR_HEIGHT + 15, 200, 40)
        self.submit_btn_rect = pygame.Rect(WIDTH - 200, HEIGHT - BOTTOMBAR_HEIGHT + 15, 180, 40)

        self.demands = ["CEASEFIRE", "STATE TRANSFER", "PUPPET STATE", "MILITARY ACCESS", "REGIME CHANGE"]
        self.demand_rects = []
        for i in range(len(self.demands)):
            rect = pygame.Rect(WIDTH - RIGHTBAR_WIDTH + 14, STATUS_BAR_HEIGHT + 60 + (i * 66), RIGHTBAR_WIDTH - 28, 52)
            self.demand_rects.append(rect)
        
        self.countries = ["Malaysia", "Thailand", "Vietnam", "Indonesia", "Philippines", "Laos"]
        self.country_rects = []
        for i in range(len(self.countries)):
            rect = pygame.Rect(14, STATUS_BAR_HEIGHT + 60 + (i * 66), LEFTBAR_WIDTH - 28, 52)
            self.country_rects.append(rect)

        self.chat_open = False
        self.chat_input_text = ""
        self.chat_history = [
            ("LEADER", "Welcome to the Peace Conference."),
        ]
        
        self.chat_panel_rect = pygame.Rect(LEFTBAR_WIDTH + 40, STATUS_BAR_HEIGHT + 40, 
                                           WIDTH - LEFTBAR_WIDTH - RIGHTBAR_WIDTH - 80, 
                                           HEIGHT - STATUS_BAR_HEIGHT - BOTTOMBAR_HEIGHT - 80)
        self.chat_input_rect = pygame.Rect(self.chat_panel_rect.x + 20, self.chat_panel_rect.bottom - 60, 
                                           self.chat_panel_rect.width - 40, 40)
        
        self.selected_demand = ""
        self.popup_rect = pygame.Rect((WIDTH // 2) - 200, (HEIGHT // 2) - 100, 400, 200)
        self.popup_close_btn = pygame.Rect(self.popup_rect.centerx - 50, self.popup_rect.bottom - 50, 100, 35)
        self.selected_demands_set = set()
        self.selected_country = None
        self.active_popup = None
        self.popup_confirm_btn = pygame.Rect(self.popup_rect.centerx - 120, self.popup_rect.bottom - 50, 100, 35)
        self.popup_cancel_btn = pygame.Rect(self.popup_rect.centerx + 20, self.popup_rect.bottom - 50, 100, 35)
        self._hover_glow = {}

    def draw_status_bar(self):
        status_rect = pygame.Rect(0, 0, WIDTH, STATUS_BAR_HEIGHT)
        pygame.draw.rect(self.screen, (12, 18, 29), status_rect)
        pygame.draw.line(self.screen, (76, 64, 38), (0, STATUS_BAR_HEIGHT - 2), (WIDTH, STATUS_BAR_HEIGHT - 2), 1)
        pygame.draw.line(self.screen, (240, 198, 116), (0, STATUS_BAR_HEIGHT - 1), (WIDTH, STATUS_BAR_HEIGHT - 1), 1)
        
        ebee_surf = self.title_font.render("EBEE COMMAND", True, (240, 198, 116))
        ebee_rect = ebee_surf.get_rect(midleft=(16, STATUS_BAR_HEIGHT // 2))
        self.screen.blit(ebee_surf, ebee_rect)
        
        title_surf = self.title_font.render("PEACE CONFERENCE", True, (255, 255,255))
        title_rect = title_surf.get_rect(center=(WIDTH // 2, STATUS_BAR_HEIGHT // 2))
        self.screen.blit(title_surf, title_rect)



        points_surf = self.mini_font.render("CONFERENCE POINTS:", True, (255,255,255))
        points_rect = points_surf.get_rect(midright=(WIDTH - 16, STATUS_BAR_HEIGHT // 2))
        self.screen.blit(points_surf, points_rect)

    def draw_left_bar(self):
        leftbar_rect = pygame.Rect(0, STATUS_BAR_HEIGHT, LEFTBAR_WIDTH, HEIGHT - STATUS_BAR_HEIGHT - BOTTOMBAR_HEIGHT)
        pygame.draw.rect(self.screen, (12, 18, 29), leftbar_rect)
        pygame.draw.rect(self.screen, (28, 38, 52), leftbar_rect, 1)
        pygame.draw.line(self.screen, (76, 64, 38), leftbar_rect.topright, leftbar_rect.bottomright, 1)
        
        left_title = self.small_font.render("PARTICIPANTS", True, (240, 198, 116))
        left_rect = left_title.get_rect(centerx=leftbar_rect.centerx, y=leftbar_rect.y + 16)
        self.screen.blit(left_title, left_rect)

        mouse_pos = pygame.mouse.get_pos()
        motion_time = pygame.time.get_ticks() / 1000.0

        for i, rect in enumerate(self.country_rects):
            country_name = self.countries[i]
            hovered = rect.collidepoint(mouse_pos)
            is_selected = (self.selected_country == country_name)

            glow = self._hover_glow.get(f"c_{country_name}", 0.0)
            if hovered:
                glow = min(1.0, glow + 0.16)
            else:
                glow = max(0.0, glow - 0.10)
            self._hover_glow[f"c_{country_name}"] = glow

            self.draw_interactive_panel(self.screen, rect, hovered, is_selected, glow, motion_time)

            text_x = rect.x + 18 + int(glow * 4)
            text_color = (239, 224, 185) if is_selected else ((224, 228, 231) if hovered else (202, 207, 211))
            
            country_text = self.small_font.render(country_name.upper(), True, text_color)
            self.screen.blit(country_text, (text_x, rect.y + (rect.height - country_text.get_height()) // 2))
    

    def draw_right_bar(self):
        rightbar_rect = pygame.Rect(WIDTH - RIGHTBAR_WIDTH, STATUS_BAR_HEIGHT, RIGHTBAR_WIDTH, HEIGHT - STATUS_BAR_HEIGHT - BOTTOMBAR_HEIGHT)
        pygame.draw.rect(self.screen, (12, 18, 29), rightbar_rect)
        pygame.draw.rect(self.screen, (28, 38, 52), rightbar_rect, 1)
        pygame.draw.line(self.screen, (76, 64, 38), rightbar_rect.topleft, rightbar_rect.bottomleft, 1)
        
         
        right_title = self.small_font.render("                 DEMANDS", True, (240, 198, 116))
        right_rect = right_title.get_rect(left=rightbar_rect.left + 20, y=rightbar_rect.y + 16)
        self.screen.blit(right_title, right_rect)

        mouse_pos = pygame.mouse.get_pos()
        motion_time = pygame.time.get_ticks() / 1000.0

        for i, rect in enumerate(self.demand_rects):
            demand_name = self.demands[i]
            hovered = rect.collidepoint(mouse_pos)
            is_selected = (demand_name in self.selected_demands_set)

            glow = self._hover_glow.get(f"d_{demand_name}", 0.0)
            if hovered:
                glow = min(1.0, glow + 0.16)
            else:
                glow = max(0.0, glow - 0.10)
            self._hover_glow[f"d_{demand_name}"] = glow

            self.draw_interactive_panel(self.screen, rect, hovered, is_selected, glow, motion_time)

            text_x = rect.x + 18 + int(glow * 4)
            text_color = (239, 224, 185) if is_selected else ((224, 228, 231) if hovered else (202, 207, 211))
            
            txt_surf = self.small_font.render(demand_name, True, text_color)
            self.screen.blit(txt_surf, (text_x, rect.y + (rect.height - txt_surf.get_height()) // 2))

        count_val = len(self.selected_demands_set)
        count_str = f"{count_val} DEMAND SELECTED" if count_val == 1 else f"{count_val} DEMANDS SELECTED"
        count_surf = self.small_font.render(count_str, True, (240, 198, 116))
        count_rect = count_surf.get_rect(centerx=rightbar_rect.centerx, bottom=self.clear_btn_rect.top - 12)
        self.screen.blit(count_surf, count_rect)

       
        clear_hovered = self.clear_btn_rect.collidepoint(mouse_pos)
        clear_glow = self._hover_glow.get("b_clear", 0.0)
        clear_glow = min(1.0, clear_glow + 0.16) if clear_hovered else max(0.0, clear_glow - 0.10)
        self._hover_glow["b_clear"] = clear_glow

        self.draw_interactive_panel(self.screen, self.clear_btn_rect, clear_hovered, False, clear_glow, motion_time)

        clear_text_color = (239, 224, 185) if clear_hovered else (202, 207, 211)
        clear_surf = self.small_font.render("CLEAR ALL", True, clear_text_color)
        self.screen.blit(clear_surf, clear_surf.get_rect(center=self.clear_btn_rect.center))


    def draw_bottom_bar(self):
        bottombar_rect = pygame.Rect(0, HEIGHT - BOTTOMBAR_HEIGHT, WIDTH, BOTTOMBAR_HEIGHT)
        pygame.draw.rect(self.screen, (5, 10, 17), bottombar_rect)
        pygame.draw.line(self.screen, (240, 198, 116), bottombar_rect.topleft, bottombar_rect.topright, 1)
        
        mouse_pos = pygame.mouse.get_pos()
        motion_time = pygame.time.get_ticks() / 1000.0
        for btn_name in ["exit", "chat", "history", "submit"]:
            if f"b_{btn_name}" not in self._hover_glow:
                self._hover_glow[f"b_{btn_name}"] = 0.0

        exit_hovered = self.exit_btn_rect.collidepoint(mouse_pos)
        exit_glow = self._hover_glow["b_exit"]
        exit_glow = min(1.0, exit_glow + 0.16) if exit_hovered else max(0.0, exit_glow - 0.10)
        self._hover_glow["b_exit"] = exit_glow
        
        if exit_hovered:
            exit_colors = ((80, 15, 15, 150), (255, 50, 50, 255))
            exit_text_color = (255, 180, 180)
        else:
            exit_colors = ((45, 10, 10, 100), (200, 30, 30, 200))
            exit_text_color = (220, 120, 120)
            
        self.draw_interactive_panel(self.screen, self.exit_btn_rect, exit_hovered, False, exit_glow, motion_time, custom_colors=exit_colors)
        
        btn_text = self.small_font.render("EXIT CONFERENCE", True, exit_text_color)
        self.screen.blit(btn_text, btn_text.get_rect(center=self.exit_btn_rect.center))

        chat_hovered = self.chat_btn_rect.collidepoint(mouse_pos)
        chat_glow = self._hover_glow["b_chat"]
        chat_glow = min(1.0, chat_glow + 0.16) if chat_hovered else max(0.0, chat_glow - 0.10)
        self._hover_glow["b_chat"] = chat_glow
        self.draw_interactive_panel(self.screen, self.chat_btn_rect, chat_hovered, self.chat_open, chat_glow, motion_time)
        chat_text_color = (239, 224, 185) if self.chat_open or chat_hovered else (202, 207, 211)
        chat_text = self.small_font.render("CHAT WITH LEADERS", True, chat_text_color)
        self.screen.blit(chat_text, chat_text.get_rect(center=self.chat_btn_rect.center))

        history_hovered = self.history_btn_rect.collidepoint(mouse_pos)
        history_glow = self._hover_glow["b_history"]
        history_glow = min(1.0, history_glow + 0.16) if history_hovered else max(0.0, history_glow - 0.10)
        self._hover_glow["b_history"] = history_glow
        self.draw_interactive_panel(self.screen, self.history_btn_rect, history_hovered, False, history_glow, motion_time)
        history_text_color = (239, 224, 185) if history_hovered else (202, 207, 211)
        history_text = self.small_font.render("PROPOSAL HISTORY", True, history_text_color)
        self.screen.blit(history_text, history_text.get_rect(center=self.history_btn_rect.center))

        submit_hovered = self.submit_btn_rect.collidepoint(mouse_pos)
        submit_glow = self._hover_glow["b_submit"]
        submit_glow = min(1.0, submit_glow + 0.16) if submit_hovered else max(0.0, submit_glow - 0.10)
        self._hover_glow["b_submit"] = submit_glow
        submit_colors = ((10, 50, 15), (0, 255, 0)) if submit_hovered else ((5, 35, 10), (0, 200, 0))
        self.draw_interactive_panel(self.screen, self.submit_btn_rect, submit_hovered, False, submit_glow, motion_time, custom_colors=submit_colors)
        submit_text_color = (150, 255, 150) if submit_hovered else (0, 220, 0)
        submit_text = self.small_font.render("SUBMIT DEMANDS", True, submit_text_color)
        self.screen.blit(submit_text, submit_text.get_rect(center=self.submit_btn_rect.center))

    def draw_chat_window(self):
        if not self.chat_open:
            return
            
        pygame.draw.rect(self.screen, (16, 24, 38), self.chat_panel_rect)
        pygame.draw.rect(self.screen, (240, 198, 116), self.chat_panel_rect, 2)
        
        header_surf = self.title_font.render("NEGOTIATE PLACE", True, (240, 198, 116))
        self.screen.blit(header_surf, (self.chat_panel_rect.x + 20, self.chat_panel_rect.y + 15))
        pygame.draw.line(self.screen, (40, 52, 72), 
                         (self.chat_panel_rect.x, self.chat_panel_rect.y + 50), 
                         (self.chat_panel_rect.right, self.chat_panel_rect.y + 50), 2)
        
        start_y = self.chat_panel_rect.y + 70
        for sender, msg in self.chat_history[-8:]:
            color = (150, 200, 255) if sender == "You" else (240, 198, 116)
            display_line = f"{sender}: {msg}"
            msg_surf = self.small_font.render(display_line, True, color)
            self.screen.blit(msg_surf, (self.chat_panel_rect.x + 20, start_y))
            start_y += 30

        pygame.draw.rect(self.screen, (24, 33, 46), self.chat_input_rect)
        pygame.draw.rect(self.screen, (76, 64, 38), self.chat_input_rect, 1)
        
        text_to_render = self.chat_input_text + ("|" if pygame.time.get_ticks() % 1000 < 500 else "")
        input_surf = self.small_font.render(text_to_render, True, (255, 255, 255))
        self.screen.blit(input_surf, (self.chat_input_rect.x + 10, self.chat_input_rect.y + 10))

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                
                if self.chat_open and not self.active_popup:
                    if event.key == pygame.K_RETURN:
                        if self.chat_input_text.strip():
                            user_msg = self.chat_input_text
                            self.chat_history.append(("You", user_msg))
                            reply = f"....AI to be implemented...."
                            self.chat_history.append(("LEADER", reply))
                            self.chat_input_text = ""
                    elif event.key == pygame.K_BACKSPACE:
                        self.chat_input_text = self.chat_input_text[:-1]
                    else:
                        if event.unicode.isprintable():
                            self.chat_input_text += event.unicode

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if self.active_popup in ["demand", "history"]:
                        if self.popup_close_btn.collidepoint(event.pos):
                            self.active_popup = None
                        return
                    elif self.active_popup == "submit":
                        if self.popup_confirm_btn.collidepoint(event.pos):
                            print("Demands Submitted!")
                            self.active_popup = None
                        elif self.popup_cancel_btn.collidepoint(event.pos):
                            self.active_popup = None
                        return

                    if self.chat_btn_rect.collidepoint(event.pos):
                        self.chat_open = not self.chat_open
                    if self.exit_btn_rect.collidepoint(event.pos):
                        self.running = False

                    if self.history_btn_rect.collidepoint(event.pos):
                        self.active_popup = "history"
                    if self.submit_btn_rect.collidepoint(event.pos):
                        self.active_popup = "submit"
                    if self.clear_btn_rect.collidepoint(event.pos):
                        self.selected_demands_set.clear()

                    for i, rect in enumerate(self.country_rects):
                        if rect.collidepoint(event.pos):
                            self.selected_country = self.countries[i]

                    for i, rect in enumerate(self.demand_rects):
                        if rect.collidepoint(event.pos):
                            label = self.demands[i]
                            self.selected_demand = label
                            if label in self.selected_demands_set:
                                self.selected_demands_set.remove(label)
                            else:
                                self.selected_demands_set.add(label)
                            self.active_popup = "demand"
                    

    def draw_interactive_panel(self, surface, rect, is_hovered, is_selected, glow_strength, motion_time, radius=6, custom_colors=None):
        if custom_colors:
            base_color, border_color = custom_colors
            base_color = base_color if len(base_color) == 4 else (*base_color, 255)
            border_color = border_color if len(border_color) == 4 else (*border_color, 255)
        elif is_selected:
            base_color = (37, 35, 28, 255) if not is_hovered else (50, 44, 30, 255)
            border_color = (212, 169, 77, 255)
        else:
            base_color = (28, 39, 59, 255) if is_hovered else (14, 22, 33, 255)
            border_color = (42, 55, 72, 255) if not is_hovered else (88, 101, 118, 255)

        shadow = pygame.Surface((rect.width + 8, rect.height + 8), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 75), shadow.get_rect(), border_radius=radius + 2)
        surface.blit(shadow, (rect.x - 3, rect.y - 1))

        top_color = base_color
        bottom_color = (int(top_color[0] * 0.4), int(top_color[1] * 0.4), int(top_color[2] * 0.4), top_color[3])
        
        gradient_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        for y_offset in range(rect.height):
            t = y_offset / max(1, rect.height - 1)
            blended_rgba = tuple(int(top_color[i] + (bottom_color[i] - top_color[i]) * t) for i in range(4))
            pygame.draw.line(gradient_surf, blended_rgba, (0, y_offset), (rect.width, y_offset))
        
        mask = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
        gradient_surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(gradient_surf, rect.topleft)

        border_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(border_surf, border_color, border_surf.get_rect(), 1, border_radius=radius)
        surface.blit(border_surf, rect.topleft)

        if glow_strength > 0.01:
            glow_color = border_color[:3]
            glow_surf = pygame.Surface((rect.width + 20, rect.height + 20), pygame.SRCALPHA)
            
            for ring in range(4):
                alpha = int(glow_strength * (36 - ring * 7))
                if alpha <= 0:
                    continue
                offset = ring * 2 + 2
                pygame.draw.rect(
                    glow_surf,
                    (*glow_color, alpha),
                    (10 - offset, 10 - offset, rect.width + offset * 2, rect.height + offset * 2),
                    border_radius=radius + offset,
                    width=2,
                )
            surface.blit(glow_surf, (rect.x - 10, rect.y - 10))

        if is_selected:
            pygame.draw.rect(surface, (212, 169, 77), pygame.Rect(rect.x, rect.y + 8, 3, rect.height - 16), border_radius=2)

    def draw_popup(self):
        if not self.active_popup:
            return
        
        surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 150))
        self.screen.blit(surf, (0, 0))

        pygame.draw.rect(self.screen, (16, 24, 38), self.popup_rect)
        pygame.draw.rect(self.screen, (240, 198, 116), self.popup_rect, 2)
        mouse_pos = pygame.mouse.get_pos()

        if self.active_popup == "demand":
            p_title = self.title_font.render("DEMAND SELECTED", True, (240, 198, 116))
            self.screen.blit(p_title, p_title.get_rect(centerx=self.popup_rect.centerx, y=self.popup_rect.y + 25))

            p_msg = self.small_font.render(f"You chose: {self.selected_demand}", True, (255, 255, 255))
            self.screen.blit(p_msg, p_msg.get_rect(centerx=self.popup_rect.centerx, y=self.popup_rect.y + 75))

            b_color = (40, 52, 72) if self.popup_close_btn.collidepoint(mouse_pos) else (24, 33, 46)
            pygame.draw.rect(self.screen, b_color, self.popup_close_btn)
            pygame.draw.rect(self.screen, (240, 198, 116), self.popup_close_btn, 1)
            
            btn_txt = self.small_font.render("CLOSE", True, (240, 198, 116))
            self.screen.blit(btn_txt, btn_txt.get_rect(center=self.popup_close_btn.center))

        elif self.active_popup == "submit":
            p_title = self.title_font.render("CONFIRM SUBMISSION", True, (240, 198, 116))
            self.screen.blit(p_title, p_title.get_rect(centerx=self.popup_rect.centerx, y=self.popup_rect.y + 25))

            count_val = len(self.selected_demands_set)
            p_msg = self.small_font.render(f"You selected {count_val} demands, do you want to submit?", True, (255, 255, 255))
            self.screen.blit(p_msg, p_msg.get_rect(centerx=self.popup_rect.centerx, y=self.popup_rect.y + 75))

            confirm_color = (40, 120, 40) if self.popup_confirm_btn.collidepoint(mouse_pos) else (30, 90, 30)
            pygame.draw.rect(self.screen, confirm_color, self.popup_confirm_btn)
            pygame.draw.rect(self.screen, (255, 255, 255), self.popup_confirm_btn, 1)
            confirm_txt = self.small_font.render("SUBMIT", True, (255, 255, 255))
            self.screen.blit(confirm_txt, confirm_txt.get_rect(center=self.popup_confirm_btn.center))

            cancel_color = (120, 40, 40) if self.popup_cancel_btn.collidepoint(mouse_pos) else (90, 30, 30)
            pygame.draw.rect(self.screen, cancel_color, self.popup_cancel_btn)
            pygame.draw.rect(self.screen, (255, 255, 255), self.popup_cancel_btn, 1)
            cancel_txt = self.small_font.render("CANCEL", True, (255, 255, 255))
            self.screen.blit(cancel_txt, cancel_txt.get_rect(center=self.popup_cancel_btn.center))


        elif self.active_popup == "history":
            p_title = self.title_font.render("PROPOSAL HISTORY", True, (240, 198, 116))
            self.screen.blit(p_title, p_title.get_rect(centerx=self.popup_rect.centerx, y=self.popup_rect.y + 25))

            p_msg1 = self.small_font.render("No previous proposals found.", True, (170, 180, 190))
            self.screen.blit(p_msg1, p_msg1.get_rect(centerx=self.popup_rect.centerx, y=self.popup_rect.y + 75))
            
            

            b_color = (40, 52, 72) if self.popup_close_btn.collidepoint(mouse_pos) else (24, 33, 46)
            pygame.draw.rect(self.screen, b_color, self.popup_close_btn)
            pygame.draw.rect(self.screen, (240, 198, 116), self.popup_close_btn, 1)
            
            btn_txt = self.small_font.render("CLOSE", True, (240, 198, 116))
            self.screen.blit(btn_txt, btn_txt.get_rect(center=self.popup_close_btn.center))
            
    def draw(self):
        self.screen.fill((11, 18, 32))
        self.draw_status_bar()
        self.draw_left_bar()
        self.draw_right_bar()
        self.draw_bottom_bar()
        self.draw_chat_window()
        
        self.draw_popup()
        
        pygame.display.flip()

    def run(self):
        while self.running:
            self.handle_events()
            self.draw()
            self.clock.tick(60)
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    app = PeaceTreatyScreen()
    app.run()