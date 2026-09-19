from pathlib import Path

from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Konfektionsgrößen sortieren sich nicht alphabetisch (L < M < S < XL wäre
# falsch). Die Reihenfolge entspricht den Größenlisten des Click-Dummys.
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL", "ONE SIZE", "ONESIZE"]


def sort_sizes(sizes):
    """Jinja-Filter: ProductSize-Liste in Konfektionsreihenfolge bringen."""

    def key(size):
        label = size.size.strip().upper()
        return (SIZE_ORDER.index(label) if label in SIZE_ORDER else len(SIZE_ORDER), label)

    return sorted(sizes, key=key)


templates.env.filters["sort_sizes"] = sort_sizes
