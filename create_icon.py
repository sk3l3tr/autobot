#!/usr/bin/env python3
from PIL import Image
import os

def create_multi_resolution_ico():
    # Ruta del PNG original
    png_path = os.path.join(os.path.dirname(__file__), "resources", "icon.png")
    ico_path = os.path.join(os.path.dirname(__file__), "resources", "icon_highres.ico")

    # Abrir la imagen original
    img = Image.open(png_path)

    # Crear versiones en diferentes tamaños
    sizes = [16, 32, 48, 64, 96, 128, 256]
    icons = []

    for size in sizes:
        # Redimensionar manteniendo la relación de aspecto
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        icons.append(resized)

    # Crear versión de alta resolución (256x256)
    high_res = img.resize((256, 256), Image.Resampling.LANCZOS)
    
    # Guardar como ICO
    high_res.save(ico_path, format='ICO')
    
    # También reemplazar el icon.ico original con la versión de alta resolución
    original_ico_path = os.path.join(os.path.dirname(__file__), "resources", "icon.ico")
    high_res.save(original_ico_path, format='ICO')

    print(f"Icono de alta resolución creado: {ico_path}")
    print(f"Tamaño del archivo: {os.path.getsize(ico_path)} bytes")

if __name__ == "__main__":
    create_multi_resolution_ico()
