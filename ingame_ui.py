import pygame
import sys

import ctypes
ctypes.windll.user32.SetProcessDPIAware()

class panel:
    def __init__(self, x, y, w, h, color=(40,40,40)):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = color

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect)
        pygame.draw.rect(surface, (25,25,25), self.rect, 1)

class leftbar:


    def __init__(self, x, y, w, h):
            self.rect = pygame.Rect(x, y, w, h)
            self.items = []


    def word(self, name):
        self.items.append(name)

    def draw(self, surface, font):
        mouse = pygame.mouse.get_pos()

    

        pygame.draw.rect(surface, (50, 50, 50), self.rect)
        
        for i, item in enumerate(self.items):

            if not item.strip(): 
                continue
          
            x = self.rect.x + 10
            y = self.rect.y + 60 + (i * 50)
            w = self.rect.width - 20
            h = 40

            rect = pygame.Rect(x, y, w, h)

            if 'CLEAR ALL' in item:
                if rect.collidepoint(mouse):
                 color = (0,120, 0)  
                else:
                    color = (0,220, 0)   
            elif rect.collidepoint(mouse):
                    color = (0, 200, 0)
            else:
                    color = (30, 30, 30)

            pygame.draw.rect(surface, color, rect)

            if 'CLEAR ALL' in item:
                text_color = (0, 0, 0)
            else:
                text_color = (255, 255, 255)

            text = font.render(item, True, text_color)
            surface.blit(text, (x + 10, y + 10))

            
class page:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1280, 720))
    
        self.title_font = pygame.font.SysFont('Verdana', 16,bold= True)
        self.font = pygame.font.SysFont('Verdana', 14)
    
        self.leftbar = leftbar(0, 0, 180, 700)
        self.leftbar.word('      CLEAR ALL    ')
        self.leftbar.word('')
        self.leftbar.word('NOTIFICATIONS')
        self.leftbar.word('LOGISTICS')
        self.leftbar.word('COMBAT')
        self.leftbar.word('INTEL')

        self.topbar = panel(0, 0, 1280, 50, (0,0,0))
        self.rightbar = panel(1100, 50,180, 620, (0,0,0))
        self.bottombar = panel(0, 670, 1280, 50, (0,0,0))

        self.bottom_buttons = b_buttons(self.bottombar.rect)
        self.bottom_buttons.add('RESEARCH')
        self.bottom_buttons.add('DIPLOMACY')
        self.bottom_buttons.add('TRADE')
        self.bottom_buttons.add('PRODUCTION')
        self.bottom_buttons.add('CONSTRUCTION')
        self.bottom_buttons.add('RECRUIT')

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            self.screen.fill((10,10,10))
            
           
            self.leftbar.draw(self.screen, self.font)
            self.rightbar.draw(self.screen)
            self.bottombar.draw(self.screen)
            self.topbar.draw(self.screen)
            self.bottom_buttons.draw(self.screen, self.font)
            title = self.title_font.render('OPERATIONAL COMMAND', True, (200, 170, 80))
            self.screen.blit(title, (20, 15))
            
            
            pygame.display.flip()


class b_buttons:
    def __init__(self, rect):
        self.rect = rect
        self.items = []

    def add(self, name):
        self.items.append(name)

    def draw(self, surface, font):
        mouse = pygame.mouse.get_pos()
        w = 120
        h = 30
        spacing = 10
        total_width = len(self.items) * w + (len(self.items) - 1) * spacing
        start_x = self.rect.x + (self.rect.width - total_width) // 2

        for i, item in enumerate(self.items):
            x = start_x + (i * (w + spacing))
            y = self.rect.y + 10
            rect = pygame.Rect(x, y, w, h)
            

            if rect.collidepoint(mouse):
                color = (0, 200, 0)
            else:
                color = (30, 30, 30)

            pygame.draw.rect(surface, color, rect)

            text = font.render(item, True, (255,255,255))
            text_rect = text.get_rect(center=rect.center)
            surface.blit(text, text_rect)
          
   
if __name__ == '__main__':
    page().run()

   