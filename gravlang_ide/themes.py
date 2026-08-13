import os

THEMES = {
    "Catppuccin Mocha": dict(
        BG_BASE="#1e1e2e", BG_MANTLE="#181825", BG_CRUST="#11111b",
        BG_SURFACE0="#313244", BG_SURFACE1="#45475a",
        TEXT_MAIN="#cdd6f4", TEXT_SUB="#585b70", TEXT_OVERLAY="#7f849c",
        BLUE="#89b4fa", TEAL="#94e2d5", GREEN="#a6e3a1",
        MAUVE="#cba6f7", PEACH="#fab387", RED="#f38ba8", LAVENDER="#b4befe",
        STATUS_BG="#89b4fa", STATUS_FG="#1e1e2e",
        FG_CURSOR="#f5e0dc",
    ),
    "GitHub Dark": dict(
        BG_BASE="#0d1117", BG_MANTLE="#161b22", BG_CRUST="#010409",
        BG_SURFACE0="#21262d", BG_SURFACE1="#30363d",
        TEXT_MAIN="#e6edf3", TEXT_SUB="#484f58", TEXT_OVERLAY="#8b949e",
        BLUE="#79c0ff", TEAL="#39d353", GREEN="#3fb950",
        MAUVE="#d2a8ff", PEACH="#ffa657", RED="#ff7b72", LAVENDER="#a5d6ff",
        STATUS_BG="#1f6feb", STATUS_FG="#ffffff",
        FG_CURSOR="#f0f6fc",
    ),
    "Solarized Dark": dict(
        BG_BASE="#002b36", BG_MANTLE="#073642", BG_CRUST="#001f27",
        BG_SURFACE0="#094652", BG_SURFACE1="#0a5160",
        TEXT_MAIN="#839496", TEXT_SUB="#3d6b74", TEXT_OVERLAY="#586e75",
        BLUE="#268bd2", TEAL="#2aa198", GREEN="#859900",
        MAUVE="#6c71c4", PEACH="#cb4b16", RED="#dc322f", LAVENDER="#b58900",
        STATUS_BG="#268bd2", STATUS_FG="#fdf6e3",
        FG_CURSOR="#fdf6e3",
    ),
    "Catppuccin Latte": dict(
        BG_BASE="#eff1f5", BG_MANTLE="#e6e9ef", BG_CRUST="#dce0e8",
        BG_SURFACE0="#ccd0da", BG_SURFACE1="#bcc0cc",
        TEXT_MAIN="#4c4f69", TEXT_SUB="#9ca0b0", TEXT_OVERLAY="#8c8fa1",
        BLUE="#1e66f5", TEAL="#179299", GREEN="#40a02b",
        MAUVE="#8839ef", PEACH="#fe640b", RED="#d20f39", LAVENDER="#7287fd",
        STATUS_BG="#1e66f5", STATUS_FG="#eff1f5",
        FG_CURSOR="#4c4f69",
    ),
}

CONFIG_FILE = os.path.join(os.path.dirname(__file__), ".gravlang_config.json")
