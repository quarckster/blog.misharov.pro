AUTHOR = ""
SITENAME = "Misharov Pro"
SITEURL = "http://127.0.0.1:8000"
SUBTITLE = "Technical notes from an IT geek"
GITHUB_URL = "https://github.com/quarckster"
PLUGIN_PATHS = ["plugins"]
PLUGINS = ["readtime", "neighbors", "summary", "minify", "sitemap"]
DISPLAY_CATEGORIES_ON_MENU = False
STATIC_PATHS = ["assets"]
PATH = "content"
EXTRA_PATH_METADATA = {
    "assets/favicon.ico": {"path": "favicon.ico"},
    "assets/favicon.png": {"path": "favicon.png"}
}
TIMEZONE = "Europe/Vienna"
DEFAULT_LANG = "en"
ARTICLE_URL = "{date:%Y}-{date:%m}-{date:%d}/{slug}"
ARTICLE_SAVE_AS = "{date:%Y}-{date:%m}-{date:%d}/{slug}/index.html"
AUTHORS_SAVE_AS = ""
AUTHOR_SAVE_AS = ""
CATEGORIES_SAVE_AS = ""
CATEGORY_SAVE_AS = ""
PAGE_URL = "{slug}"
THEME = "themes/Papyrus"
# Social widget
SOCIAL = (
    ("github", "https://github.com/quarckster"),
    ("linkedin", "https://linkedin.in/in/misharov"),
)
DEFAULT_PAGINATION = 10
# Uncomment following line if you want document-relative URLs when developing
RELATIVE_URLS = True
# Summary plugin
SUMMARY_USE_FIRST_PARAGRAPH = True
# Sitemap plugin
SITEMAP = {
    "format": "xml",
    "exclude": ["tag/", "category/"]
}