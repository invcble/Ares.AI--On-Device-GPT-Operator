from PIL import Image, ImageDraw, ImageFont

def apply_grid_overlay(image: Image.Image) -> Image.Image:
    image = image.copy()
    draw = ImageDraw.Draw(image)
    width, height = image.size

    # Grid dimensions
    rows, cols = 20, 10
    cell_width = width // cols
    cell_height = height // rows

    # Font setup
    font_path = "C:/Windows/Fonts/Arial.ttf"  # Change if needed
    font = ImageFont.truetype(font_path, 40)

    # Colors
    outline_color = "lime"
    text_color = "magenta"

    # Draw grid and labels
    for row in range(rows):
        letter = chr(97 + row)
        for col in range(cols):
            x0 = col * cell_width
            y0 = row * cell_height
            x1 = x0 + cell_width
            y1 = y0 + cell_height

            draw.rectangle([x0, y0, x1, y1], outline=outline_color, width=2)

            label = f"{letter}{col}"
            text_bbox = draw.textbbox((0, 0), label, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            text_x = x0 + (cell_width - text_width) / 2
            text_y = y0 + (cell_height - text_height) / 2

            shadow_offset = 2
            draw.text((text_x + shadow_offset, text_y + shadow_offset), label, fill="black", font=font)
            draw.text((text_x, text_y), label, fill=text_color, font=font)

    return image
