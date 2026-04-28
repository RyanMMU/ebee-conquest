import pygame
import sys

from engine.runtime import main

pygame.init()

def lerp(start, end, t):
    return start + (end - start) * t

WIDTH,HEIGHT = 1280,720

screen = pygame.display.set_mode((WIDTH, HEIGHT))

pygame.display.set_caption('Ebee Conquest - Main Menu') 

text= (255, 255, 255)

ease = 1
ease2= 1
ease3= 1
ease4 = 1
ease_backbutton = 1



is_fullscreen = False
ease_fullscreen = 1 

volume_drag = False


main_font = pygame.font.Font('./fonts/Inter_18pt-Medium.ttf', 18)
settings_font = pygame.font.Font('./fonts/Inter_18pt-Medium.ttf', 36)



def scale_button():
    global button_m, button_width, button_height, button_y_positions, main_font
    w, h = screen.get_size()

    
    BASE_W, BASE_H = 297, 53
    BASE_FONT = 18

    if is_fullscreen:
        scale = 1.3 
        gap = 35
    else:
        scale = 0.85 
        gap = 25
    
    button_width = int(BASE_W * scale)
    button_height = int(BASE_H * scale)
    main_font = pygame.font.Font('./fonts/Inter_18pt-Medium.ttf', int(BASE_FONT * scale))
    
    total_height = button_height * 4 + gap * 3
    start_y = (h - total_height) // 2
    button_y_positions = {
        'new_game': start_y,
        'load_game': start_y + button_height + gap,
        'settings': start_y + (button_height + gap) * 2,
        'quit': start_y + (button_height + gap) * 3
    }

    button_m = (w // 2) - (button_width // 2)



menu = 'main' 
run = True
volume = 50



bg_image = pygame.image.load('Game Menu UI Design (1).png').convert()
bg_image = pygame.transform.smoothscale(bg_image,(WIDTH, HEIGHT))

def glow(screen,x,y,w,h):
    for i in range(1,4):
        lighting = pygame.Surface((w + i*4, h + i*4), pygame.SRCALPHA)
        glow_color =(255,195,0,17)
        pygame.draw.rect(lighting, glow_color, (0, 0, w + i*4, h + i*4))
        
        screen.blit(lighting, (x - i*2, y - i*2))


def button(screen,x,y,w,h):
    button_surf = pygame.Surface((w, h),pygame.SRCALPHA)
    button_color = (15,23,43,180)  
    pygame.draw.rect(button_surf, button_color, (0,0,w,h))
    pygame.draw.rect(button_surf,(187,77,0,255),(0,0,w,h),width=2)
    screen.blit(button_surf, (x, y))


clock = pygame.time.Clock()


scale_button()
while run:
    mouse = pygame.mouse.get_pos()
    screen.blit(bg_image, (0, 0))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False




        if event.type == pygame.MOUSEBUTTONDOWN:
            if menu == 'settings':
                vol_bar_rect = pygame.Rect(button_m, 280, button_width, 30)
                if vol_bar_rect.collidepoint(mouse):
                    volume_drag = True
                    volume = int((mouse[0] - button_m) / button_width * 100)
                    volume = max(0, min(100, volume))
                    pygame.mixer.music.set_volume(volume / 100)




                if button_m < mouse[0] < button_m + button_width and 310 < mouse[1] < 363:
                    is_fullscreen = not is_fullscreen
                    if is_fullscreen:
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                    else:
                        screen = pygame.display.set_mode((WIDTH, HEIGHT))

                    scale_button()
                    w, h = screen.get_size()
                    bg_image = pygame.transform.smoothscale(pygame.image.load('Game Menu UI Design (1).png').convert(), (w, h))



                if button_m < mouse[0] < button_m + button_width and 420 < mouse[1] < 473:
                            menu = 'main'

            elif menu == 'main':
                if button_m < mouse[0] < button_m + button_width and button_y_positions['new_game'] < mouse[1] < button_y_positions['new_game'] + button_height:
                    main(is_fullscreen=is_fullscreen)
                    pygame.quit()
                    sys.exit()
                    
                elif button_m < mouse[0] < button_m+button_width and button_y_positions['settings'] < mouse[1] < button_y_positions['settings'] + button_height:
                    menu = 'settings'

                elif button_m < mouse[0] < button_m + button_width and button_y_positions['quit'] < mouse[1] < button_y_positions['quit'] + button_height:
                    run = False

                elif button_m < mouse[0] < button_m + button_width and button_y_positions['load_game'] < mouse[1] < button_y_positions['load_game'] + button_height:
                    print('loading game....')


        if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    volume_drag = False

        if event.type == pygame.MOUSEMOTION:
            if volume_drag and menu == 'settings':
                volume = int((mouse[0] - button_m) / button_width * 100)
                volume = max(0, min(100, volume))
                pygame.mixer.music.set_volume(volume / 100)






                    
    if menu == 'main':
        
        
        y_pos = button_y_positions['new_game']
        hover = button_m < mouse[0] < button_m + button_width and y_pos < mouse[1] < y_pos + button_height

        
        new_w = int(button_width * ease)
        new_x = button_m - (new_w - button_width) // 2
        
        new_h = int(button_height * ease)

       
        new_y = y_pos - (new_h - button_height) // 2

        
        if hover:
            expand = 1.15
        else:
            expand = 1 

        ease = lerp(ease, expand, 0.15)

      

        if ease > 1.01:
            glow(screen, new_x, new_y, new_w, new_h)
        button(screen, new_x, new_y, new_w, new_h)

        txt1 = main_font.render('NEW GAME',True,text)
        txt1_rect = txt1.get_rect(center=(new_x + new_w // 2, new_y + new_h // 2))
        screen.blit(txt1, txt1_rect)

            
        
        y_pos = button_y_positions['settings']
        hover = button_m < mouse[0] < button_m + button_width and y_pos < mouse[1] < y_pos + button_height

        new_w = int(button_width * ease2)
        new_x = button_m - (new_w - button_width) // 2
        
        new_h = int(button_height * ease2)

        
        new_y = y_pos - (new_h - button_height) // 2



        if hover:
            expand = 1.15
        else:
            expand = 1

        ease2 = lerp(ease2, expand, 0.15)

      

        if ease2 > 1.01:
            glow(screen, new_x, new_y, new_w, new_h)
        button(screen, new_x, new_y, new_w, new_h)

        txt2 = main_font.render('SETTINGS',True,text)
        txt2_rect = txt2.get_rect(center=(new_x + new_w // 2, new_y + new_h // 2))
        screen.blit(txt2, txt2_rect)



        y_pos = button_y_positions['quit']
        hover = button_m < mouse[0] < button_m + button_width and y_pos < mouse[1] < y_pos + button_height
        new_w = int(button_width * ease3)
        new_x = button_m - (new_w - button_width) // 2
        
        new_h = int(button_height * ease3)

       
        new_y = y_pos - (new_h - button_height) // 2


      
        if hover:
            expand = 1.15
        else:
            expand = 1

        ease3 = lerp(ease3, expand, 0.15)

      

        if ease3 > 1.01:
            glow(screen, new_x, new_y, new_w, new_h)
        button(screen, new_x, new_y, new_w, new_h)


        txt3 = main_font.render('QUIT', True, text)
        txt3_rect = txt3.get_rect(center=(new_x + new_w // 2, new_y + new_h // 2))
        screen.blit(txt3, txt3_rect)




        y_pos = button_y_positions['load_game']
        hover = button_m < mouse[0] < button_m + button_width and y_pos < mouse[1] < y_pos + button_height
        new_w = int(button_width * ease4)
        new_x = button_m - (new_w - button_width) // 2
        
        new_h = int(button_height * ease4)


        new_y = y_pos - (new_h - button_height) // 2
       

        if hover:
            expand = 1.15
        else:
            expand = 1

        ease4 = lerp(ease4, expand, 0.15)

      

        if ease4 > 1.01:
            glow(screen, new_x, new_y, new_w, new_h)
        button(screen, new_x, new_y, new_w, new_h)

        txt5 = main_font.render('LOAD GAME', True, text)
        txt5_rect = txt5.get_rect(center=(new_x + new_w // 2, new_y + new_h // 2))
        screen.blit(txt5, txt5_rect)







    if menu == 'settings':
        overlay = pygame.Surface(screen.get_size())
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        title = settings_font.render('       SETTINGS', True, text)
        screen.blit(title, (button_m, 30))

        vol_text = main_font.render('Volume: ' + str(volume) + '%', True, text)
        screen.blit(vol_text, (button_m, 250))

        pygame.draw.rect(screen, (60, 60, 60), (button_m, 290, button_width, 8))
        bar_fill = int(button_width * volume / 100)
        pygame.draw.rect(screen, (0, 255, 0), (button_m, 290, bar_fill, 8))

        knob = button_m + bar_fill
        pygame.draw.circle(screen, (255, 255, 255), (knob, 295), 8)

        
        hover_fullscreen = button_m < mouse[0] < button_m + button_width and 310 < mouse[1] < 363

        new_w = int(button_width * ease_fullscreen)
        new_x = button_m - (new_w - button_width) // 2
        new_h = int(button_height * ease_fullscreen)
        new_y = 310 - (new_h - button_height) // 2

        if hover_fullscreen:
            expand = 1.15
        else:
            expand = 1
        ease_fullscreen = lerp(ease_fullscreen, expand, 0.15)

        if ease_fullscreen > 1.01:
            glow(screen, new_x, new_y, new_w, new_h)
        button(screen, new_x, new_y, new_w, new_h)

        fs_text = 'TOGGLE FULLSCREEN: ON' if is_fullscreen else 'TOGGLE FULLSCREEN: OFF'
        fullscreen_text = main_font.render(fs_text, True, text)
        fs_box = fullscreen_text.get_rect(center=(new_x + new_w // 2, new_y + new_h // 2))
        screen.blit(fullscreen_text, fs_box)

    
        hover_back = button_m < mouse[0] < button_m + button_width and 420 < mouse[1] < 473
        new_w = int(button_width * ease_backbutton)
        new_x = button_m - (new_w - button_width) // 2
        new_h = int(button_height * ease_backbutton)
        new_y = 420 - (new_h - button_height) // 2

        if hover_back:
            expand = 1.15
        else:
            expand = 1
        ease_backbutton = lerp(ease_backbutton, expand, 0.15)

        if ease_backbutton > 1.01:
            glow(screen, new_x, new_y, new_w, new_h)
        button(screen, new_x, new_y, new_w, new_h)

        back_text = main_font.render('BACK', True, text)
        back_rect = back_text.get_rect(center=(new_x + new_w // 2, new_y + new_h // 2))
        screen.blit(back_text, back_rect)

    pygame.display.flip()

    clock.tick(240)


 
pygame.quit()           
sys.exit()