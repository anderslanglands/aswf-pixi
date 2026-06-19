from pathlib import Path
import subprocess

import oslquery

Path("recipe_query.osl").write_text(
    "shader recipe_query(float scale = 2.0, output color result = color(0, 0, 0)) {}\n",
    encoding="utf-8",
)
subprocess.run(["oslc", "recipe_query.osl"], check=True)

query = oslquery.OSLQuery()
if not query.open("recipe_query.oso", ".") and not query.open("recipe_query", "."):
    raise RuntimeError(query.geterror())

assert query.shadername() == "recipe_query"
assert len(query) >= 2
scale = query["scale"]
assert scale.name == "scale"
assert not scale.isoutput
assert scale.value == 2.0
result = query["result"]
assert result.name == "result"
assert result.isoutput
