import pygame as pg
import sys
from random import choice, random
from os import path
from settings import *
from sprites import *
from tilemap import *

# HUD functions
def draw_player_health(surf, x, y, pct):
    '''
    This function draws the player health bar in the top left corner of the
    screen. Depending on the remaining health percentage, the bar will have
    different color (>60%: green, >30%: yellow, <30%: red).
    '''
    if pct < 0:
        pct = 0
    BAR_LENGTH = 100
    BAR_HEIGHT = 20
    fill = pct * BAR_LENGTH
    outline_rect = pg.Rect(x, y, BAR_LENGTH, BAR_HEIGHT)
    fill_rect = pg.Rect(x, y, fill, BAR_HEIGHT)
    if pct > 0.6:
        col = GREEN
    elif pct > 0.3:
        col = YELLOW
    else:
        col = RED
    pg.draw.rect(surf, col, fill_rect)
    pg.draw.rect(surf, WHITE, outline_rect, 2)

class Game:
    """
    This class contains all necessary methods for the game to run
    """
    def __init__(self):
        '''
        Setting up the game:
            Preset default mixer
            Initiallize PyGame
            Create the game screen
            Display game caption
            FPS check
            Load data
        '''
        pg.mixer.pre_init(44100, -16, 4, 2048)
        pg.init()
        self.screen = pg.display.set_mode((WIDTH, HEIGHT))
        pg.display.set_caption(TITLE)
        self.clock = pg.time.Clock()
        self.load_data()

    def draw_text(self, text, font_name, size, color, x, y, align="topleft"):
        '''
        This method is used to draw text to the screen
        '''
        font = pg.font.Font(font_name, size)
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect(**{align: (x, y)})
        self.screen.blit(text_surface, text_rect)

    def load_data(self):
        '''
        This method is used to load all necessary data (and scale, convert
        or transform them if needed) for the game to run.
        '''
        game_folder = path.dirname(__file__)
        img_folder = path.join(game_folder, 'img')
        snd_folder = path.join(game_folder, 'snd')
        music_folder = path.join(game_folder, 'music')
        self.background = pg.image.load(path.join(img_folder, BACKGROUND))
        self.map_folder = path.join(game_folder, 'maps')
        self.title_font = path.join(img_folder, 'ZOMBIE.TTF')
        self.hud_font = path.join(img_folder, 'Impacted2.0.ttf')
        self.dim_screen = pg.Surface(self.screen.get_size()).convert_alpha()
        self.dim_screen.fill((0, 0, 0, 180))
        self.player_img = pg.image.load(path.join(img_folder, PLAYER_IMG)).convert_alpha()
        self.bullet_images = {}
        self.bullet_images['lg'] = pg.image.load(path.join(img_folder, BULLET_IMG)).convert_alpha()
        self.bullet_images['sm'] = pg.transform.scale(self.bullet_images['lg'], (10, 10))
        self.mob_img = pg.image.load(path.join(img_folder, MOB_IMG)).convert_alpha()
        self.splat = pg.image.load(path.join(img_folder, SPLAT)).convert_alpha()
        self.splat = pg.transform.scale(self.splat, (64, 64))
        self.gun_flashes = []
        for img in MUZZLE_FLASHES:
            self.gun_flashes.append(pg.image.load(path.join(img_folder, img)).convert_alpha())
        self.item_images = {}
        for item in ITEM_IMAGES:
            self.item_images[item] = pg.image.load(path.join(img_folder, ITEM_IMAGES[item])).convert_alpha()

        # Lighting effect
        self.fog = pg.Surface((WIDTH, HEIGHT))
        self.fog.fill(NIGHT_COLOR)
        self.light_mask = pg.image.load(path.join(img_folder, LIGHT_MASK)).convert_alpha()
        self.light_mask = pg.transform.scale(self.light_mask, LIGHT_RADIUS)
        self.light_rect = self.light_mask.get_rect()

        # Sound loading
        pg.mixer.music.load(path.join(music_folder, BG_MUSIC))
        self.effects_sounds = {}
        for type in EFFECTS_SOUNDS:
            self.effects_sounds[type] = pg.mixer.Sound(path.join(snd_folder, EFFECTS_SOUNDS[type]))
        self.weapon_sounds = {}
        for weapon in WEAPON_SOUNDS:
            self.weapon_sounds[weapon] = []
            for snd in WEAPON_SOUNDS[weapon]:
                s = pg.mixer.Sound(path.join(snd_folder, snd))
                s.set_volume(0.3)
                self.weapon_sounds[weapon].append(s)
        self.zombie_moan_sounds = []
        for snd in ZOMBIE_MOAN_SOUNDS:
            s = pg.mixer.Sound(path.join(snd_folder, snd))
            s.set_volume(0.2)
            self.zombie_moan_sounds.append(s)
        self.player_hit_sounds = []
        for snd in PLAYER_HIT_SOUNDS:
            self.player_hit_sounds.append(pg.mixer.Sound(path.join(snd_folder, snd)))
        self.zombie_hit_sounds = []
        for snd in ZOMBIE_HIT_SOUNDS:
            self.zombie_hit_sounds.append(pg.mixer.Sound(path.join(snd_folder, snd)))

    def new(self):
        '''
        This method initializes all variables and does the setup for a new game.
        '''
        self.all_sprites = pg.sprite.LayeredUpdates()
        self.walls = pg.sprite.Group()
        self.mobs = pg.sprite.Group()
        self.bullets = pg.sprite.Group()
        self.items = pg.sprite.Group()
        self.map = TiledMap(path.join(self.map_folder, self.map_selection))
        self.map_img = self.map.make_map()
        self.map.rect = self.map_img.get_rect()
        for tile_object in self.map.tmxdata.objects:
            obj_center = vec(tile_object.x + tile_object.width / 2,
                             tile_object.y + tile_object.height / 2)
            if tile_object.name == 'player':
                self.player = Player(self, obj_center.x, obj_center.y)
            if tile_object.name == 'zombie':
                Mob(self, obj_center.x, obj_center.y)
            if tile_object.name == 'wall':
                Obstacle(self, tile_object.x, tile_object.y,
                         tile_object.width, tile_object.height)
            if tile_object.name in ['health', 'shotgun']:
                Item(self, obj_center, tile_object.name)
        self.camera = Camera(self.map.width, self.map.height)
        self.draw_debug = False
        self.paused = False
        self.night = True
        self.effects_sounds['level_start'].play()

    def run(self):
        '''
        The main game loop
        self.playing = False to end the game
        '''
        self.playing = True
        pg.mixer.music.play(loops=-1)
        while self.playing:
            self.dt = self.clock.tick(FPS) / 1000.0
            self.events()
            if not self.paused:
                self.update()
            self.draw()

    def quit(self):
        '''
        Quit the game
        '''
        pg.quit()
        sys.exit()

    def update(self):
        ''' 
        Update in the game loop
        (Sprites, camera and event)
        '''
        # Sprite and camera
        self.all_sprites.update()
        self.camera.update(self.player)

        # Win condition
        if len(self.mobs) == 0:
            self.playing = False
        
        # Get Item
        hits = pg.sprite.spritecollide(self.player, self.items, False)
        for hit in hits:
            if hit.type == 'health' and self.player.health < PLAYER_HEALTH:
                hit.kill()
                self.effects_sounds['health_up'].play()
                self.player.add_health(HEALTH_PACK_AMOUNT)
            if hit.type == 'shotgun':
                hit.kill()
                self.effects_sounds['gun_pickup'].play()
                self.player.weapon = 'shotgun'

        # Mobs hit player
        hits = pg.sprite.spritecollide(self.player, self.mobs, False, collide_hit_rect)
        for hit in hits:
            if random() < 0.7:
                choice(self.player_hit_sounds).play()
            self.player.health -= MOB_DAMAGE
            hit.vel = vec(0, 0)
            if self.player.health <= 0:
                self.playing = False
        if hits:
            self.player.hit()
            self.player.pos += vec(MOB_KNOCKBACK, 0).rotate(-hits[0].rot)
        
        # Bullets hit mobs
        hits = pg.sprite.groupcollide(self.mobs, self.bullets, False, True)
        for mob in hits:
            for bullet in hits[mob]:
                mob.health -= bullet.damage
            mob.vel = vec(0, 0)

    def draw_grid(self):
        '''
        This method is used to draw the grid for this tiled-based game
        '''
        # Column
        for x in range(0, WIDTH, TILESIZE):
            pg.draw.line(self.screen, LIGHTGREY, (x, 0), (x, HEIGHT))
        # Row
        for y in range(0, HEIGHT, TILESIZE):
            pg.draw.line(self.screen, LIGHTGREY, (0, y), (WIDTH, y))

    def render_fog(self):
        '''
        This method draws the light mask (gradient) onto fog image
        '''
        self.fog.fill(NIGHT_COLOR)
        self.light_rect.center = self.camera.apply(self.player).center
        self.fog.blit(self.light_mask, self.light_rect)
        self.screen.blit(self.fog, (0, 0), special_flags=pg.BLEND_MULT)

    def draw(self):
        '''
        This function draws everything needed for the game and flips the display
        '''
        # The line below can be used to display FPS
        # pg.display.set_caption("{:.2f}".format(self.clock.get_fps()))

        pg.display.set_caption(TITLE)
        self.screen.blit(self.map_img, self.camera.apply(self.map))
        for sprite in self.all_sprites:
            if isinstance(sprite, Mob):
                sprite.draw_health()
            self.screen.blit(sprite.image, self.camera.apply(sprite))
            if self.draw_debug:
                pg.draw.rect(self.screen, CYAN, self.camera.apply_rect(sprite.hit_rect), 1)
        if self.draw_debug:
            for wall in self.walls:
                pg.draw.rect(self.screen, CYAN, self.camera.apply_rect(wall.rect), 1)

        if self.night:
            self.render_fog()
        # HUD functions
        draw_player_health(self.screen, 10, 10, self.player.health / PLAYER_HEALTH)
        self.draw_text('Zombies: {}'.format(len(self.mobs)), self.hud_font, 30, WHITE,
                       WIDTH - 10, 10, align="topright")
        if self.paused:
            self.screen.blit(self.dim_screen, (0, 0))
            self.draw_text("Paused", self.title_font, 105, RED, WIDTH / 2, HEIGHT / 2, align="center")
        pg.display.flip()

    def events(self):
        '''
        This method is used to catch events happened in the game
        '''
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.quit()
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    self.quit()
                if event.key == pg.K_h:
                    self.draw_debug = not self.draw_debug
                if event.key == pg.K_p:
                    self.paused = not self.paused
                if event.key == pg.K_n:
                    self.night = not self.night

    def show_start_screen(self):
        '''
        This method functions as the starting screen of the game.
        (It draws, flips and wait for input)
        '''
        self.screen.fill(BLACK)
        self.background_rect = self.background.get_rect()
        self.screen.blit(self.background, self.background_rect)
        self.draw_text("Zombie Shooter", self.title_font, 120, RED,
                       WIDTH / 2, HEIGHT * 1 / 3, align="center")
        self.draw_text("A game not for the faint-hearted", self.title_font, 50, WHITE,
                       WIDTH / 2, HEIGHT * 1 / 2, align="center") 
        self.draw_text("Press any key to continue", self.title_font, 75, GREEN,
                       WIDTH / 2, HEIGHT * 2 / 3, align="center")
        self.draw_text("Created by Minh Duong for CSc 110 and further", self.title_font, 20, YELLOW,
                       WIDTH / 2, HEIGHT * 8 / 9, align="center")
        pg.display.flip()
        self.wait_for_key()

    def map_select(self):
        '''
        This method serves as the map selection portion of the game (draws, flips and
        wait for command)
        '''
        self.screen.fill(BLACK)
        self.background_rect = self.background.get_rect()
        self.screen.blit(self.background, self.background_rect)
        self.draw_text("Zombie Shooter", self.title_font, 120, RED,
                       WIDTH / 2, HEIGHT * 1 / 3, align="center")
        self.draw_text("Select a map", self.title_font, 75, WHITE,
                       WIDTH / 2, HEIGHT * 1 / 2, align="center")
        self.draw_text("Press 1 or 2", self.title_font, 75, GREEN,
                       WIDTH / 2, HEIGHT * 2 / 3, align="center")
        self.draw_text("Or just quit if you are too scared", self.title_font, 40, YELLOW,
                       WIDTH / 2, HEIGHT * 4 / 5, align="center")
        pg.display.flip()
        self.wait_for_selection()

    def wait_for_selection(self):
        '''
        This method waits for the map selection of the user and uses the right map
        for the game (in self.map_selection variable)
        '''    
        pg.event.wait()
        select_waiting = True
        while select_waiting:
            self.clock.tick(FPS)
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    select_waiting = False
                    self.quit()
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_1:
                        self.map_selection = "level1.tmx"
                        select_waiting = False
                    elif event.key == pg.K_2:
                        self.map_selection = "level2.tmx"
                        select_waiting = False

    def show_go_screen(self):
        '''
        This method draws the game over screen (for both win and lose conditions),
        flips the display and wait for user's input.
        '''
        self.screen.fill(BLACK)
        self.draw_text("GAME OVER", self.title_font, 100, RED,
                       WIDTH / 2, HEIGHT * 1 / 3, align="center")
        if len(self.mobs) != 0:
            self.draw_text("Not stronk enough for the game huh?", self.title_font, 50, YELLOW,
                        WIDTH / 2, HEIGHT * 1 / 2, align="center")
        if len(self.mobs) == 0:
            self.draw_text("Nice play man! You are stronk!", self.title_font, 50, YELLOW,
                        WIDTH / 2, HEIGHT * 1 / 2, align="center")
        self.draw_text("Press a key to return", self.title_font, 75, GREEN,
                        WIDTH / 2, HEIGHT * 2 / 3, align="center")
        self.draw_text("Zombie Shooter - created by Minh Duong", self.title_font, 30, LIGHTGREY,
                        WIDTH / 2, HEIGHT * 5 / 6, align="center")
        pg.display.flip()
        self.wait_for_key()

    def wait_for_key(self):
        '''
        This method is used to wait for the user to have any input.
        '''
        pg.event.wait()
        waiting = True
        while waiting:
            self.clock.tick(FPS)
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    waiting = False
                    self.quit()
                if event.type == pg.KEYUP:
                    waiting = False

# Run the game
g = Game()
# Game loop
while True:
    g.show_start_screen()
    g.map_select()
    g.new()
    g.run()
    g.show_go_screen()
