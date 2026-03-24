import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

base_image_path = r"C:\Users\lucas\.gemini\antigravity\brain\41ab8e80-e847-4cd5-99c4-9064e62ec2e8\rpa_base_gear_1773951669562.png"
output_dir = r"C:\Users\lucas\OneDrive\Desktop\PROJETOS\ESTAGIO\rpa-reajuste-tabelas-vigencia\rpa-icons"
os.makedirs(output_dir, exist_ok=True)

print("Carregando imagem base e aplicando recorte matematico (Módulo Numpy-Livre)...")
img_orig = Image.open(base_image_path).convert("RGB")
width, height = img_orig.size
pixels = img_orig.load()

# Encontrar o menor valor do canal Red (cor mais sólida do azul)
min_red = 255
for y in range(height):
    for x in range(width):
        r, g, b = pixels[x, y]
        if r < min_red:
            min_red = r

# Buscar a cor base para aplicar o anti-aliasing matematico puramente no python
base_colors = []
for y in range(height):
    for x in range(width):
        r, g, b = pixels[x, y]
        if r <= min_red + 5:
            base_colors.append((r, g, b))

if len(base_colors) > 0:
    base_color = (
        int(sum(c[0] for c in base_colors) / len(base_colors)),
        int(sum(c[1] for c in base_colors) / len(base_colors)),
        int(sum(c[2] for c in base_colors) / len(base_colors))
    )
else:
    base_color = (0, 0, 255) # fallback

print(f"Cor base azul detectada: {base_color}")

# Recriar a imagem pixel a pixel com extrema perfeicao sem fundo branco
img_base = Image.new("RGBA", (width, height))
base_pixels = img_base.load()

denominator = float(max(1, 255 - base_color[0]))

for y in range(height):
    for x in range(width):
        r, g, b = pixels[x, y]
        # Recuperando o alpha matematicamente
        alpha_val = (255.0 - float(r)) / denominator
        # Travando entre 0 e 1
        alpha_val = max(0.0, min(1.0, alpha_val))
        
        # Pixels agora recebem apenas a cor base + Transparencia (mata o branco total)
        base_pixels[x, y] = (base_color[0], base_color[1], base_color[2], int(alpha_val * 255))

print("Aplicando a borda preta suave para contorno absoluto...")
# Criar borda preta suave para fechar o contorno perfeitamente (Stroke)
alpha_mask = img_base.split()[-1]
# Expande a mascara pra criar o volume pra fora
mask_dilated = alpha_mask.filter(ImageFilter.MaxFilter(3))
# Esfuma a mascara (anti-aliasing contra qualquer fundo)
mask_blurred = mask_dilated.filter(ImageFilter.GaussianBlur(1.5))

# Camada de sombra 100% preta
shadow = Image.new("RGBA", img_base.size, (20, 20, 20, 255))
shadow.putalpha(mask_blurred)

# Juntando o azul perfeito encima da sombra perfeita
final_base = Image.alpha_composite(shadow, img_base)

font_path = "arialbd.ttf"
try:
    font = ImageFont.truetype(font_path, 130)
except IOError:
    font = ImageFont.load_default()

print("Gerando os 30 icones numerados...")
for i in range(1, 31):
    img = final_base.copy()
    
    badge_radius = int(min(width, height) * 0.12)
    center_x = width - badge_radius - int(width * 0.08)
    center_y = height - badge_radius - int(height * 0.08)
    
    draw = ImageDraw.Draw(img)
    
    outline_radius = int(badge_radius * 1.08)
    draw.ellipse(
        [(center_x - outline_radius, center_y - outline_radius),
         (center_x + outline_radius, center_y + outline_radius)],
        fill=(20, 20, 20, 255) # Borda do badge seguindo o tema preto escutro da sombra
    )
    
    draw.ellipse(
        [(center_x - badge_radius, center_y - badge_radius),
         (center_x + badge_radius, center_y + badge_radius)],
        fill=(255, 59, 48, 255)
    )
    
    text = str(i)
    try:
        font_size = int(badge_radius * 1.3)
        loop_font = ImageFont.truetype(font_path, font_size)
    except IOError:
        loop_font = font
        
    try:
        draw.text((center_x, center_y), text, fill="white", font=loop_font, anchor="mm")
    except Exception as e:
        bbox = draw.textbbox((0, 0), text, font=loop_font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        draw.text((center_x - text_w/2, center_y - text_h/2 - text_h*0.1), text, fill="white", font=loop_font)
    
    out_path = os.path.join(output_dir, f"rpa_icon_{i}.png")
    img.save(out_path, "PNG")

print(f"Sucesso Total! 30 icones idênticos sem depender de Numpy.")
