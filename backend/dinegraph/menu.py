"""The restaurant menu: dish name -> quantity currently available.

Edit this dict to change what the kitchen can serve. A dish with quantity 0 is
on the menu but sold out, which order_confirm treats the same as "not on the menu".
"""

MENU: dict[str, int] = {
    "Margherita Pizza": 5,
    "Paneer Butter Masala": 3,
    "Veg Biryani": 10,
    "Chicken Burger": 4,
    "Pasta Alfredo": 0,
    "Masala Dosa": 6,
    "Gulab Jamun": 8,
    "Cold Coffee": 2,
}


def lookup(dish: str, menu: dict[str, int] | None = None) -> tuple[str, int]:
    """Case-insensitive menu lookup. Returns (canonical name, available quantity).

    A dish that is not on the menu returns its original name and 0.
    """
    menu = MENU if menu is None else menu
    wanted = dish.strip().lower()
    for name, qty in menu.items():
        if name.lower() == wanted:
            return name, qty
    return dish.strip(), 0


# Price per plate in rupees, used for the bill at payment time.
PRICES: dict[str, int] = {
    "Margherita Pizza": 350,
    "Paneer Butter Masala": 280,
    "Veg Biryani": 220,
    "Chicken Burger": 180,
    "Pasta Alfredo": 300,
    "Masala Dosa": 120,
    "Gulab Jamun": 90,
    "Cold Coffee": 150,
}
