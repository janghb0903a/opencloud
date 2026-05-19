import os, tempfile, zipfile
from schemas import ChartResponse

REQUIRED = {"Chart.yaml", "values.yaml", "templates/_helpers.tpl"}

def write_chart(resp: ChartResponse) -> str:
    tmpdir = tempfile.mkdtemp(prefix="chart_")
    root = os.path.join(tmpdir, resp.chart_name)
    os.makedirs(root, exist_ok=True)
    for f in resp.files:
        p = os.path.join(root, f.path)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fp:
            fp.write(f.content)
    for req in REQUIRED:
        if not os.path.exists(os.path.join(root, req)):
            raise ValueError(f"missing required file: {req}")
    zpath = os.path.join(tmpdir, f"{resp.chart_name}.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for base, _, files in os.walk(root):
            for name in files:
                abspath = os.path.join(base, name)
                z.write(abspath, arcname=os.path.relpath(abspath, root))
    return zpath
