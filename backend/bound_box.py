from PIL import Image, ImageDraw, ImageFont

# Load the image
image_path = "content/5.jpeg"
image = Image.open(image_path)
draw = ImageDraw.Draw(image)
width, height = image.size

# Grid dimensions
rows, cols = 20, 10  # 20 rows, 10 columns
cell_width = width // cols
cell_height = height // rows

# Font setup
font_path = "/Library/Fonts/Arial.ttf"  # Update if needed                                                                                                             
font = ImageFont.truetype(font_path, 40)

# Colors
outline_color = "lime"
text_color = "magenta"

# Draw grid & label
for row in range(rows):
    # Convert row 0..19 to letters a..t (ASCII 97 = 'a')
    letter = chr(97 + row)
    for col in range(cols):
        x0 = col * cell_width
        y0 = row * cell_height
        x1 = x0 + cell_width
        y1 = y0 + cell_height

        # Outline the cell
        draw.rectangle([x0, y0, x1, y1], outline=outline_color, width=2)

        # Label: letter for row, number for column
        label = f"{letter}{col}"

        # Center the label within the cell
        text_bbox = draw.textbbox((0, 0), label, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        text_x = x0 + (cell_width - text_width) / 2
        text_y = y0 + (cell_height - text_height) / 2

        # Optional text shadow
        shadow_offset = 2
        draw.text((text_x + shadow_offset, text_y + shadow_offset), label, fill="black", font=font)

        # Main text
        draw.text((text_x, text_y), label, fill=text_color, font=font)

# Save and show
output_path = "content/5.jpeg"
image.save(output_path)
image.show()