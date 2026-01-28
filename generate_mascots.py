"""
Gerador de Mascotes - Cria mascotes PNG simples e fofos
Execute: python generate_mascots.py
"""

from PIL import Image, ImageDraw, ImageFont
import os
import math


def create_water_drop(size=200):
    """Cria uma gotinha d'água fofa"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Cores
    light_blue = (100, 180, 255, 255)
    dark_blue = (50, 120, 200, 255)
    white = (255, 255, 255, 255)
    black = (30, 30, 30, 255)

    # Corpo da gota (elipse + triângulo no topo)
    center_x = size // 2
    body_top = size // 3
    body_bottom = size - 20

    # Desenhar corpo oval
    draw.ellipse([30, body_top, size - 30, body_bottom], fill=light_blue, outline=dark_blue, width=3)

    # Ponta superior (triângulo arredondado simulado)
    points = [
        (center_x, 15),
        (center_x - 40, body_top + 30),
        (center_x + 40, body_top + 30),
    ]
    draw.polygon(points, fill=light_blue, outline=dark_blue)

    # Brilho
    draw.ellipse([50, body_top + 20, 80, body_top + 50], fill=white)

    # Olhos
    eye_y = size // 2
    draw.ellipse([center_x - 35, eye_y - 15, center_x - 15, eye_y + 15], fill=white)
    draw.ellipse([center_x + 15, eye_y - 15, center_x + 35, eye_y + 15], fill=white)
    draw.ellipse([center_x - 30, eye_y - 8, center_x - 18, eye_y + 8], fill=black)
    draw.ellipse([center_x + 18, eye_y - 8, center_x + 30, eye_y + 8], fill=black)

    # Brilho nos olhos
    draw.ellipse([center_x - 28, eye_y - 6, center_x - 24, eye_y - 2], fill=white)
    draw.ellipse([center_x + 22, eye_y - 6, center_x + 26, eye_y - 2], fill=white)

    # Sorriso
    smile_y = eye_y + 30
    draw.arc([center_x - 25, smile_y - 10, center_x + 25, smile_y + 15], 0, 180, fill=black, width=3)

    # Bochechas rosas
    pink = (255, 150, 150, 150)
    draw.ellipse([center_x - 55, eye_y + 5, center_x - 35, eye_y + 25], fill=pink)
    draw.ellipse([center_x + 35, eye_y + 5, center_x + 55, eye_y + 25], fill=pink)

    return img


def create_frog(size=200):
    """Cria um sapo fofo"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Cores
    green = (100, 200, 100, 255)
    dark_green = (60, 140, 60, 255)
    light_green = (150, 230, 150, 255)
    white = (255, 255, 255, 255)
    black = (30, 30, 30, 255)

    center_x = size // 2

    # Corpo (oval)
    body_top = 70
    draw.ellipse([25, body_top, size - 25, size - 20], fill=green, outline=dark_green, width=3)

    # Barriga mais clara
    draw.ellipse([50, body_top + 40, size - 50, size - 30], fill=light_green)

    # Olhos (círculos no topo)
    eye_y = 50
    eye_size = 45
    # Olho esquerdo
    draw.ellipse([center_x - 60, eye_y - 20, center_x - 60 + eye_size, eye_y - 20 + eye_size],
                 fill=green, outline=dark_green, width=2)
    # Olho direito
    draw.ellipse([center_x + 15, eye_y - 20, center_x + 15 + eye_size, eye_y - 20 + eye_size],
                 fill=green, outline=dark_green, width=2)

    # Pupilas (branco + preto)
    pupil_y = eye_y - 5
    draw.ellipse([center_x - 52, pupil_y, center_x - 32, pupil_y + 25], fill=white)
    draw.ellipse([center_x + 23, pupil_y, center_x + 43, pupil_y + 25], fill=white)
    draw.ellipse([center_x - 47, pupil_y + 5, center_x - 37, pupil_y + 18], fill=black)
    draw.ellipse([center_x + 28, pupil_y + 5, center_x + 38, pupil_y + 18], fill=black)

    # Brilho nos olhos
    draw.ellipse([center_x - 45, pupil_y + 7, center_x - 42, pupil_y + 10], fill=white)
    draw.ellipse([center_x + 30, pupil_y + 7, center_x + 33, pupil_y + 10], fill=white)

    # Sorriso grande
    smile_y = 120
    draw.arc([center_x - 45, smile_y - 20, center_x + 45, smile_y + 25], 0, 180, fill=black, width=4)

    # Bochechas
    pink = (255, 180, 180, 130)
    draw.ellipse([35, 100, 60, 125], fill=pink)
    draw.ellipse([size - 60, 100, size - 35, 125], fill=pink)

    return img


def create_robot(size=200):
    """Cria um robô fofo"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Cores
    silver = (180, 190, 200, 255)
    dark_silver = (120, 130, 140, 255)
    light_silver = (220, 230, 240, 255)
    blue = (100, 180, 255, 255)
    black = (30, 30, 30, 255)

    center_x = size // 2

    # Antena
    draw.rectangle([center_x - 3, 10, center_x + 3, 40], fill=dark_silver)
    draw.ellipse([center_x - 10, 5, center_x + 10, 25], fill=blue)

    # Cabeça (retângulo arredondado simulado)
    head_top = 45
    head_bottom = 140
    draw.rounded_rectangle([30, head_top, size - 30, head_bottom], radius=20, fill=silver, outline=dark_silver, width=3)

    # Brilho na cabeça
    draw.ellipse([40, head_top + 10, 70, head_top + 40], fill=light_silver)

    # Olhos (telas digitais)
    eye_y = 75
    eye_width = 35
    eye_height = 25
    # Olho esquerdo
    draw.rounded_rectangle([center_x - 50, eye_y, center_x - 50 + eye_width, eye_y + eye_height],
                            radius=5, fill=black)
    draw.rounded_rectangle([center_x - 48, eye_y + 2, center_x - 50 + eye_width - 2, eye_y + eye_height - 2],
                            radius=3, fill=blue)
    # Olho direito
    draw.rounded_rectangle([center_x + 15, eye_y, center_x + 15 + eye_width, eye_y + eye_height],
                            radius=5, fill=black)
    draw.rounded_rectangle([center_x + 17, eye_y + 2, center_x + 15 + eye_width - 2, eye_y + eye_height - 2],
                            radius=3, fill=blue)

    # Boca (display)
    mouth_y = 110
    draw.rounded_rectangle([center_x - 30, mouth_y, center_x + 30, mouth_y + 15],
                            radius=3, fill=black)
    # Sorriso no display
    draw.arc([center_x - 20, mouth_y - 5, center_x + 20, mouth_y + 20], 0, 180, fill=blue, width=2)

    # Corpo
    body_top = 145
    draw.rounded_rectangle([40, body_top, size - 40, size - 15], radius=15, fill=silver, outline=dark_silver, width=3)

    # Coração no corpo
    heart_x = center_x
    heart_y = body_top + 25
    draw.ellipse([heart_x - 15, heart_y - 5, heart_x + 15, heart_y + 15], fill=(255, 100, 100, 255))

    # Parafusos
    screw_color = (100, 100, 110, 255)
    draw.ellipse([45, head_top + 5, 55, head_top + 15], fill=screw_color)
    draw.ellipse([size - 55, head_top + 5, size - 45, head_top + 15], fill=screw_color)

    return img


def create_sun(size=200):
    """Cria um sol feliz"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Cores
    yellow = (255, 220, 80, 255)
    orange = (255, 180, 50, 255)
    white = (255, 255, 255, 255)
    black = (30, 30, 30, 255)

    center_x = size // 2
    center_y = size // 2

    # Raios
    ray_length = 35
    num_rays = 12
    for i in range(num_rays):
        angle = (2 * math.pi * i) / num_rays
        x1 = center_x + int(55 * math.cos(angle))
        y1 = center_y + int(55 * math.sin(angle))
        x2 = center_x + int((55 + ray_length) * math.cos(angle))
        y2 = center_y + int((55 + ray_length) * math.sin(angle))
        draw.line([x1, y1, x2, y2], fill=orange, width=8)

    # Círculo principal
    draw.ellipse([40, 40, size - 40, size - 40], fill=yellow, outline=orange, width=3)

    # Brilho
    draw.ellipse([55, 55, 85, 85], fill=white)

    # Olhos
    eye_y = center_y - 10
    draw.ellipse([center_x - 30, eye_y - 10, center_x - 15, eye_y + 10], fill=black)
    draw.ellipse([center_x + 15, eye_y - 10, center_x + 30, eye_y + 10], fill=black)
    # Brilho
    draw.ellipse([center_x - 27, eye_y - 7, center_x - 22, eye_y - 2], fill=white)
    draw.ellipse([center_x + 18, eye_y - 7, center_x + 23, eye_y - 2], fill=white)

    # Sorriso grande
    smile_y = center_y + 10
    draw.arc([center_x - 35, smile_y - 10, center_x + 35, smile_y + 25], 0, 180, fill=black, width=4)

    # Bochechas
    pink = (255, 150, 100, 150)
    draw.ellipse([50, center_y, 75, center_y + 25], fill=pink)
    draw.ellipse([size - 75, center_y, size - 50, center_y + 25], fill=pink)

    return img


def create_cloud(size=200):
    """Cria uma nuvem fofa"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Cores
    white = (250, 252, 255, 255)
    light_gray = (220, 225, 235, 255)
    black = (30, 30, 30, 255)

    center_x = size // 2
    center_y = size // 2 + 10

    # Nuvem (vários círculos sobrepostos)
    circles = [
        (center_x - 50, center_y, 50),
        (center_x, center_y - 20, 55),
        (center_x + 45, center_y, 45),
        (center_x - 25, center_y + 15, 40),
        (center_x + 20, center_y + 15, 42),
    ]

    # Desenhar sombra primeiro
    for cx, cy, r in circles:
        draw.ellipse([cx - r + 3, cy - r + 3, cx + r + 3, cy + r + 3], fill=light_gray)

    # Desenhar nuvem
    for cx, cy, r in circles:
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=white)

    # Olhos
    eye_y = center_y - 5
    draw.ellipse([center_x - 25, eye_y - 8, center_x - 12, eye_y + 8], fill=black)
    draw.ellipse([center_x + 12, eye_y - 8, center_x + 25, eye_y + 8], fill=black)
    # Brilho
    draw.ellipse([center_x - 23, eye_y - 5, center_x - 19, eye_y - 1], fill=white)
    draw.ellipse([center_x + 14, eye_y - 5, center_x + 18, eye_y - 1], fill=white)

    # Sorriso
    smile_y = center_y + 15
    draw.arc([center_x - 20, smile_y - 5, center_x + 20, smile_y + 12], 0, 180, fill=black, width=3)

    # Bochechas
    pink = (255, 200, 200, 130)
    draw.ellipse([center_x - 45, eye_y + 5, center_x - 30, eye_y + 20], fill=pink)
    draw.ellipse([center_x + 30, eye_y + 5, center_x + 45, eye_y + 20], fill=pink)

    return img


def create_cactus(size=200):
    """Cria um cacto fofo"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Cores
    green = (120, 180, 100, 255)
    dark_green = (80, 130, 60, 255)
    light_green = (160, 210, 140, 255)
    white = (255, 255, 255, 255)
    black = (30, 30, 30, 255)

    center_x = size // 2

    # Corpo principal
    body_width = 60
    draw.rounded_rectangle([center_x - body_width//2, 60, center_x + body_width//2, size - 20],
                            radius=25, fill=green, outline=dark_green, width=3)

    # Braço esquerdo
    draw.rounded_rectangle([20, 100, 50, 150], radius=12, fill=green, outline=dark_green, width=2)
    draw.rounded_rectangle([35, 80, 65, 155], radius=12, fill=green, outline=dark_green, width=2)

    # Braço direito
    draw.rounded_rectangle([size - 50, 90, size - 20, 145], radius=12, fill=green, outline=dark_green, width=2)
    draw.rounded_rectangle([size - 65, 70, size - 35, 150], radius=12, fill=green, outline=dark_green, width=2)

    # Listras verticais (linhas de cacto)
    for x_offset in [-15, 0, 15]:
        draw.line([center_x + x_offset, 80, center_x + x_offset, size - 40], fill=dark_green, width=1)

    # Flor no topo
    flower_y = 45
    pink = (255, 150, 180, 255)
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        px = center_x + int(15 * math.cos(rad))
        py = flower_y + int(15 * math.sin(rad))
        draw.ellipse([px - 8, py - 8, px + 8, py + 8], fill=pink)
    draw.ellipse([center_x - 8, flower_y - 8, center_x + 8, flower_y + 8], fill=(255, 220, 100, 255))

    # Olhos
    eye_y = 110
    draw.ellipse([center_x - 18, eye_y - 8, center_x - 5, eye_y + 8], fill=black)
    draw.ellipse([center_x + 5, eye_y - 8, center_x + 18, eye_y + 8], fill=black)
    draw.ellipse([center_x - 16, eye_y - 5, center_x - 12, eye_y - 1], fill=white)
    draw.ellipse([center_x + 8, eye_y - 5, center_x + 12, eye_y - 1], fill=white)

    # Sorriso
    smile_y = eye_y + 20
    draw.arc([center_x - 15, smile_y - 5, center_x + 15, smile_y + 10], 0, 180, fill=black, width=2)

    # Bochechas
    blush = (255, 180, 180, 120)
    draw.ellipse([center_x - 30, eye_y + 5, center_x - 18, eye_y + 17], fill=blush)
    draw.ellipse([center_x + 18, eye_y + 5, center_x + 30, eye_y + 17], fill=blush)

    return img


def main():
    """Gera todos os mascotes"""
    print("=" * 50)
    print("GERADOR DE MASCOTES")
    print("=" * 50)

    # Criar diretório se não existir
    os.makedirs("mascots", exist_ok=True)

    mascots = [
        ("gotinha", create_water_drop, "Gotinha d'água"),
        ("sapo", create_frog, "Sapo fofo"),
        ("robo", create_robot, "Robô simpático"),
        ("sol", create_sun, "Sol feliz"),
        ("nuvem", create_cloud, "Nuvem fofa"),
        ("cacto", create_cactus, "Cacto com flor"),
    ]

    for filename, create_func, description in mascots:
        filepath = f"mascots/{filename}.png"
        print(f"  Criando {description}... ", end="")

        try:
            img = create_func(200)
            img.save(filepath, "PNG")
            print(f"OK -> {filepath}")
        except Exception as e:
            print(f"ERRO: {e}")

    print("\n" + "=" * 50)
    print("Mascotes criados com sucesso!")
    print("Vá em Settings > Mascote & IA para escolher")
    print("=" * 50)


if __name__ == "__main__":
    main()
