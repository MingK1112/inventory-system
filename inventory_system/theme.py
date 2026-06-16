THEME = {
    "dark": {
        "bg_sidebar": "#18191C",
        "bg_content": "#232529",
        "bg_table": "#1e1f23",
        "text_main": "#F5F7F9",
        "text_muted": "#86909C",
        "accent": "#615CED",
        "accent_hover": "#4f47d4",
        "border": "#30333B",
        "border_sidebar": "#25262b",
        "stat_circle_bg": "#232529",
        "stat_circle_border": "#30333B",
    },
    "light": {
        "bg_sidebar": "#F7F8FA",
        "bg_content": "#FFFFFF",
        "bg_table": "#fafafa",
        "text_main": "#1D2129",
        "text_muted": "#86909C",
        "accent": "#615CED",
        "accent_hover": "#4f47d4",
        "border": "#E5E6EB",
        "border_sidebar": "#E5E6EB",
        "stat_circle_bg": "#FFFFFF",
        "stat_circle_border": "#E5E6EB",
    },
}


def get_theme(is_dark=True):
    return THEME["dark"] if is_dark else THEME["light"]
