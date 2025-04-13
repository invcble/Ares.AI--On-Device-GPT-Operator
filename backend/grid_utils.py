SCREEN_WIDTH = 1084
SCREEN_HEIGHT = 2412
TOTAL_COLUMNS = 10
TOTAL_ROWS = 20

def get_coordinate(unique_str: str) -> tuple[int, int]:
    """
    Converts a grid cell name (e.g., 'b3') to screen midpoint coordinates.
    Returns: (x, y) as integers
    """
    cell_width = SCREEN_WIDTH / TOTAL_COLUMNS
    cell_height = SCREEN_HEIGHT / TOTAL_ROWS

    row_char = unique_str[0].lower()
    col_num = int(unique_str[1])

    row_index = ord(row_char) - ord('a')
    x_mid = (col_num + 0.5) * cell_width
    y_mid = (row_index + 0.5) * cell_height

    return int(x_mid), int(y_mid)
