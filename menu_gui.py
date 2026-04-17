import pygame
import sys

from engine.runtime import main

pygame.init()

def lerp(start, end, t):
    return start + (end - start) * t

WIDTH,HEIGHT = 1280,720

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE | pygame.SCALED)

pygame.display.set_caption('game menu') 

text= (255, 255, 255)

ease = 1
ease2= 1
ease3= 1
ease4 = 1
ease5 = 1
target_ease = 1


main_font = pygame.font.Font('./fonts/Inter_18pt-Medium.ttf', 18)
big_font = pygame.font.Font('./fonts/Inter_18pt-Medium.ttf', 18)

menu = 'main' 
run = True


button_width = 297
button_height = 53
button_m=(WIDTH // 2) - (button_width // 2)


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

while run:
    mouse = pygame.mouse.get_pos()
    screen.blit(bg_image, (0, 0))
    
    for event in pygame.event.get():

        
        if event.type == pygame.QUIT:
            run = False


        if event.type == pygame.MOUSEBUTTONDOWN:

            if menu== 'main':
            
                
                if button_m < mouse[0] < button_m + button_width and 170 < mouse[1] < 223:
                        main()
               
                elif button_m < mouse[0] < button_m+button_width and 345 < mouse[1] < 390:
                        menu = 'settings'
                
                elif button_m < mouse[0] < button_m + button_width and 430 < mouse[1] < 490:
                            run = False

                elif button_m < mouse[0] < button_m + button_width and 255 < mouse[1] < 345:
                        print('loading game....')
            
            elif menu == 'settings':

                
                
       
                if button_m < mouse[0] < button_m + button_width and 430 < mouse[1] < 490:
                    menu = 'main'
                    
    if menu == 'main':
        
        hover = button_m < mouse[0] < button_m + button_width and 170 < mouse[1] < 223
        
        new_w = int(button_width * ease)
        new_x = button_m - (new_w - button_width) // 2
        
        new_h = int(button_height * ease)

        new_y = 170 - (new_h - button_height) // 2

        txt1 = main_font.render('NEW GAME',True,text)
        txt1_rect = txt1.get_rect(center=(new_x + new_w // 2, new_y + new_h // 2))
        screen.blit(txt1, txt1_rect)

        
        if hover:
            target_ease = 1.15
        else:
            target_ease = 1

        ease = lerp(ease, target_ease, 0.15)

      

        if ease > 1.01:
            glow(screen, new_x, new_y, new_w, new_h)
        button(screen, new_x, new_y, new_w, new_h)

            
    
        hover = button_m < mouse[0] < button_m + button_width and 345 < mouse[1] < 390

        new_w = int(button_width * ease2)
        new_x = button_m - (new_w - button_width) // 2
        
        new_h = int(button_height * ease2)

        new_y = 345 - (new_h - button_height) // 2

        txt2 = main_font.render('SETTINGS',True,text)
        txt2_rect = txt2.get_rect(center=(button_m + button_width // 2, 345 + button_height // 2))
        screen.blit(txt2, txt2_rect)


        if hover:
            target_ease = 1.15
        else:
            target_ease = 1

        ease2 = lerp(ease2, target_ease, 0.15)

      

        if ease2 > 1.01:
            glow(screen, new_x, new_y, new_w, new_h)
        button(screen, new_x, new_y, new_w, new_h)



            
        
        
        hover = button_m < mouse[0] < button_m + button_width and 430 < mouse[1] < 490
        new_w = int(button_width * ease3)
        new_x = button_m - (new_w - button_width) // 2
        
        new_h = int(button_height * ease3)

        new_y = 430 - (new_h - button_height) // 2


        txt3 = main_font.render('QUIT', True, text)
        txt3_rect = txt3.get_rect(center=(button_m + button_width // 2, 430 + button_height // 2))
        screen.blit(txt3, txt3_rect)

        if hover:
            target_ease = 1.15
        else:
            target_ease = 1

        ease3 = lerp(ease3, target_ease, 0.15)

      

        if ease3 > 1.01:
            glow(screen, new_x, new_y, new_w, new_h)
        button(screen, new_x, new_y, new_w, new_h)




        hover = button_m < mouse[0] < button_m + button_width and 255 < mouse[1] < 345
        new_w = int(button_width * ease4)
        new_x = button_m - (new_w - button_width) // 2
        
        new_h = int(button_height * ease4)

        new_y = 255 - (new_h - button_height) // 2

        txt5 = main_font.render('LOAD GAME', True, text)
        txt5_rect = txt5.get_rect(center=(button_m + button_width // 2, 255 + button_height // 2))
        screen.blit(txt5, txt5_rect)

        if hover:
            target_ease = 1.15
        else:
            target_ease = 1

        ease4 = lerp(ease4, target_ease, 0.15)

      

        if ease4 > 1.01:
            glow(screen, new_x, new_y, new_w, new_h)
        button(screen, new_x, new_y, new_w, new_h)



    elif menu == 'settings':
        t2 = big_font.render('SETTINGS',True,text)
        title_x2 = (WIDTH // 2) - (t2.get_width() // 2)
        screen.blit(t2, (title_x2,50))




        hover = button_m < mouse[0] < button_m + button_width and 430 < mouse[1] < 490
        new_w = int(button_width * ease5)
        new_x = button_m - (new_w - button_width) // 2
        
        new_h = int(button_height * ease5)

        new_y = 430 - (new_h - button_height) // 2
        txt4 = main_font.render('BACK',True,text)
        txt4_rect = txt4.get_rect(center=(button_m + button_width // 2, 430 + button_height // 2))
        screen.blit(txt4,txt4_rect)

        if hover:
            target_ease = 1.15
        else:
            target_ease = 1

        ease5 = lerp(ease5, target_ease, 0.15)

      

        if ease5 > 1.01:
            glow(screen, new_x, new_y, new_w, new_h)
        button(screen, new_x, new_y, new_w, new_h)



    pygame.display.flip()

    clock.tick(500)


    
    
pygame.quit()           
sys.exit()