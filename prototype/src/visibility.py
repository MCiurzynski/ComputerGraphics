def divide_screen(screen, coords, min_x, max_x, min_y, max_y):
    if (max_y - min_y) > 2 and (max_x - min_x) > 2:
        divide_screen(screen, coords, min_x, max_x / 2, min_y, max_y / 2)
        divide_screen(screen, coords, max_x / 2 + 1, max_x, min_y, max_y / 2)
        divide_screen(screen, coords, max_x, max_x / 2, max_y / 2 + 1, max_y)
        divide_screen(screen, coords, max_x / 2 + 1, max_x, max_y / 2 + 1, max_y)
    pass
