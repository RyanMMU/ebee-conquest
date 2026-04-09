import pygame
import sys

pygame.init()

WIDTH,HEIGHT = 1280,720

screen = pygame.display.set_mode((WIDTH, HEIGHT))

pygame.display.set_caption('game menu') 

black = (10,10,10)
dark_blue = (15,25,45)
h_blue = (30,45,70)
text= (255, 215, 0)

hover_color = h_blue

text_color = dark_blue
main_font = pygame.font.SysFont('georgia', 30)
big_font = pygame.font.SysFont('georgia', 50)

menu = 'main' 
run = True

button_width = 400
button_height = 80
button_m=(WIDTH // 2) - (button_width // 2)

bg_image = pygame.image.load('Group 1.png').convert()
bg_image = pygame.transform.scale(bg_image,(WIDTH, HEIGHT))

while run:
    mouse = pygame.mouse.get_pos()
    screen.blit(bg_image, (0, 0))
    
    for event in pygame.event.get():
         
        if event.type == pygame.QUIT:
            run = False


        if event.type == pygame.MOUSEBUTTONDOWN:

            if menu== 'main':
            
                
                if button_m < mouse[0] < button_m + button_width and 150 < mouse[1] < 210:
                        print('starting the game....')
               
                elif button_m < mouse[0] < button_m+button_width and 250 < mouse[1] < 310:
                        menu = 'settings'
                
                elif button_m < mouse[0] < button_m + button_width and 350 < mouse[1] < 410:
                            run = False
            
            elif menu == 'settings':

                
                
       
                if button_m < mouse[0] < button_m + button_width and 450 < mouse[1] < 510:
                    menu = 'main'
                    
    if menu == 'main':
        
        color = dark_blue if button_m < mouse[0] < button_m + button_width and 150 < mouse[1] < 210 else h_blue

       
        pygame.draw.rect(screen, color, (button_m ,150,button_width,button_height))
   
        
        txt1 = main_font.render('START', True, text)
        screen.blit(txt1, (button_m+50,165))

      
        color = dark_blue if button_m < mouse[0] < button_m + button_width and 250 < mouse[1] < 310 else h_blue

 
        pygame.draw.rect(screen, color,(button_m ,250,button_width,button_height) )
        txt2 = main_font.render('SETTINGS', True, text)
        screen.blit(txt2,(button_m + 35, 265))

   
       
        color = dark_blue if button_m < mouse[0] < button_m + button_width and 350 < mouse[1] < 410 else h_blue
        pygame.draw.rect(screen, color,(button_m,350,button_width,button_height))
        txt3 = main_font.render('QUIT', True, text)
        screen.blit(txt3,(button_m + 65,365))


    elif menu == 'settings':
        t2 = big_font.render('SETTINGS', True, text)
        title_x2 = (WIDTH // 2) - (t2.get_width() // 2)
        screen.blit(t2,(title_x2,50))
        
       
        color = dark_blue if button_m < mouse[0] < button_m + button_width and 450 < mouse[1] < 510 else h_blue
        pygame.draw.rect(screen, color, (button_m, 450, button_width, button_height))
        txt4 = main_font.render('BACK', True, text)
        screen.blit(txt4, (button_m + 65, 475))



    pygame.display.flip()


    
    
pygame.quit()           
sys.exit()