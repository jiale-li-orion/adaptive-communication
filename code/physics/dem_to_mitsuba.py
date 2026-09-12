#!/usr/bin/env python3
"""
dem_to_mitsuba.py — SRTM DEM to a Mitsuba/OBJ terrain mesh for ray-traced radio propagation.

The group's existing Sionna pipeline imports OpenStreetMap buildings and Blender scenes of an
urban district. This does the same job for irregular mountain terrain: it reads an SRTM1 tile,
crops the box that the coverage grid already uses, and emits a triangle mesh plus a Mitsuba
scene, so the ray tracer sees the same ground the Longley-Rice ITM run saw.

Grid points are placed on exactly the same 121x121 lattice as results/coverage_grid.csv, with the
same origin, so a ray-traced path loss at a lattice point is directly comparable to the ITM value
already computed for that point. That comparability is the point of the file.

Local frame is ENU metres with the origin at the gateway. Row 0 of an SRTM tile is the
northernmost row; pixel centres sit at (row+0.5, col+0.5) arc-seconds from the tile corner.

Deps: numpy (plus mitsuba only if --render is used).
"""
from __future__ import annotations

import argparse
import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
HGT = os.path.join(ROOT, "data", "dem", "hgt", "N30E094.hgt")
GRID = os.path.join(ROOT, "results", "coverage_grid.csv")
OUT = os.path.join(ROOT, "results")

# The gateway the ITM coverage run used (results/coverage_summary.txt).
GW_LAT, GW_LON = 30.330, 94.780
# The coverage grid box (derived from results/coverage_grid.csv).
BOX = dict(lat0=30.220, lat1=30.440, lon0=94.670, lon1=94.890)

DEG_LAT_M = 111320.0
TILE = "N30E094"          # lat 30..31, lon 94..95


def load_tile(path: str = HGT) -> np.ndarray:
    """SRTM1 tile as a float array, row 0 = north, big-endian int16."""
    raw = np.fromfile(path, dtype=">i2")
    n = int(round(math.sqrt(raw.size)))
    if n * n != raw.size:
        raise ValueError(f"{path}: {raw.size} samples is not a square tile")
    return raw.reshape(n, n).astype(np.float64)


def lat_lon_to_rowcol(lat: float, lon: float, n: int) -> tuple[float, float]:
    """Fractional (row, col) of a pixel centre for a tile whose NW corner is the integer degree."""
    lat0 = float(TILE[1:3])
    lon0 = float(TILE[4:7])
    row = (lat0 + 1.0 - lat) * 3600.0 - 0.5
    col = (lon - lon0) * 3600.0 - 0.5
    return row, col


def elev_at(dem: np.ndarray, lat: float, lon: float) -> float:
    """Bilinear elevation lookup."""
    n = dem.shape[0]
    r, c = lat_lon_to_rowcol(lat, lon, n)
    r = min(max(r, 0.0), n - 1.001)
    c = min(max(c, 0.0), n - 1.001)
    r0, c0 = int(math.floor(r)), int(math.floor(c))
    dr, dc = r - r0, c - c0
    return float(
        dem[r0, c0] * (1 - dr) * (1 - dc) + dem[r0 + 1, c0] * dr * (1 - dc)
        + dem[r0, c0 + 1] * (1 - dr) * dc + dem[r0 + 1, c0 + 1] * dr * dc
    )


def enu(lat: float, lon: float, elev: float) -> tuple[float, float, float]:
    """Local east-north-up metres relative to the gateway."""
    x = (lon - GW_LON) * DEG_LAT_M * math.cos(math.radians(GW_LAT))
    y = (lat - GW_LAT) * DEG_LAT_M
    z = elev - GW_ELEV
    return x, y, z


GW_ELEV = 0.0   # filled in by build_terrain once the DEM is read


def build_terrain(n: int) -> dict:
    """Sample an n x n lattice over BOX and return vertices, faces and the geo transform."""
    global GW_ELEV
    dem = load_tile()
    GW_ELEV = elev_at(dem, GW_LAT, GW_LON)

    lats = np.linspace(BOX["lat0"], BOX["lat1"], n)
    lons = np.linspace(BOX["lon0"], BOX["lon1"], n)
    verts = np.zeros((n, n, 3), dtype=np.float64)
    for i, la in enumerate(lats):
        for j, lo in enumerate(lons):
            verts[i, j] = enu(la, lo, elev_at(dem, la, lo))

    # two triangles per cell. i increases northward and j eastward, so (a,b,c)/(b,d,c) is the
    # winding that puts the face normal up; the opposite winding makes every surface face into
    # the ground, which renders black and, worse, sends ray-traced reflections the wrong way.
    faces = []
    for i in range(n - 1):
        for j in range(n - 1):
            a = i * n + j
            b = a + 1
            c = a + n
            d = c + 1
            faces.append((a, b, c))
            faces.append((b, d, c))

    return {
        "verts": verts.reshape(-1, 3),
        "faces": np.asarray(faces, dtype=np.int64),
        "n": n,
        "lats": lats.tolist(),
        "lons": lons.tolist(),
        "gw_elev_m": GW_ELEV,
        "elev_min": float(verts[:, :, 2].min() + GW_ELEV),
        "elev_max": float(verts[:, :, 2].max() + GW_ELEV),
    }


def write_obj(path: str, verts: np.ndarray, faces: np.ndarray) -> None:
    with open(path, "w") as f:
        f.write("# terrain mesh from SRTM1 N30E094, local ENU metres, origin at gateway\n")
        for v in verts:
            f.write(f"v {v[0]:.3f} {v[1]:.3f} {v[2]:.3f}\n")
        for t in faces:
            f.write(f"f {t[0]+1} {t[1]+1} {t[2]+1}\n")


def write_scene_xml(path: str, obj_name: str) -> None:
    """A Mitsuba scene carrying the terrain plus a downward-looking sensor.

    Materials here are placeholders: Sionna RT replaces them with its radio materials
    (ITU/itu_medium etc.) when the radio path computation runs. The geometry is what matters
    at this stage, and rendering it is how the mesh is checked.
    """
    x = """
<scene version="3.0.0">
    <integrator type="path">
        <integer name="max_depth" value="4"/>
    </integrator>

    <shape type="obj">
        <string name="filename" value="{obj}"/>
        <bsdf type="diffuse">
            <rgb name="reflectance" value="0.35 0.32 0.28"/>
        </bsdf>
    </shape>

    <emitter type="constant">
        <rgb name="radiance" value="1.2 1.3 1.5"/>
    </emitter>

    <emitter type="directional">
        <transform name="to_world">
            <rotate x="1" angle="35"/>
            <rotate y="1" angle="20"/>
        </transform>
        <rgb name="irradiance" value="2.5 2.5 2.5"/>
    </emitter>

    <sensor type="perspective">
        <transform name="to_world">
            <lookat origin="-9000, -14000, 11000" target="0, 0, 0" up="0, 0, 1"/>
        </transform>
        <float name="fov" value="45"/>
        <float name="near_clip" value="1.0"/>
        <float name="far_clip" value="200000"/>
        <film type="hdrfilm">
            <integer name="width" value="800"/>
            <integer name="height" value="600"/>
            <rfilter type="box"/>
        </film>
    </sensor>
</scene>
""".format(obj=obj_name)
    with open(path, "w") as f:
        f.write(x)


def render_check(xml: str, out_png: str) -> str:
    """CPU render of the mesh. Geometry sanity check only; this is not the radio computation."""
    os.environ.setdefault("DRJIT_CACHE_DIR", os.path.join(OUT, ".drjit-cache"))
    import mitsuba as mi
    mi.set_variant("llvm_ad_rgb")
    scene = mi.load_file(xml)
    img = mi.render(scene, spp=16)
    mi.util.write_bitmap(out_png, img)
    arr = np.array(img)
    return f"渲染完成 {arr.shape}, 亮度范围 {arr.min():.4f}..{arr.max():.4f}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", type=int, default=121, help="lattice size; 121 matches the ITM grid")
    ap.add_argument("--render", action="store_true", help="CPU render as a geometry check")
    args = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    t = build_terrain(args.grid)
    n = t["n"]
    obj = os.path.join(OUT, "terrain_mesh.obj")
    xml = os.path.join(OUT, "terrain_scene.xml")
    write_obj(obj, t["verts"], t["faces"])
    write_scene_xml(xml, "terrain_mesh.obj")

    meta = {
        "source": "SRTM1 N30E094 (1 arc-second)",
        "origin": {"lat": GW_LAT, "lon": GW_LON, "elev_m": t["gw_elev_m"]},
        "box": BOX,
        "lattice": n,
        "vertices": int(t["verts"].shape[0]),
        "triangles": int(t["faces"].shape[0]),
        "elev_range_m": [t["elev_min"], t["elev_max"]],
        "frame": "ENU metres, origin at gateway",
        "itm_grid": os.path.relpath(GRID, ROOT),
        "note": "lattice matches results/coverage_grid.csv for point-by-point comparison with ITM",
    }
    with open(os.path.join(OUT, "terrain_mesh.json"), "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"地形网格: {n}x{n} 格点 -> {meta['vertices']} 顶点 / {meta['triangles']} 三角面")
    print(f"  海拔范围 {t['elev_min']:.0f} .. {t['elev_max']:.0f} m")
    print(f"  网关高程 {t['gw_elev_m']:.1f} m，原点设在该处")
    print(f"  输出: {os.path.relpath(obj, ROOT)}, {os.path.relpath(xml, ROOT)}")

    if args.render:
        png = os.path.join(OUT, "terrain_render.png")
        print("  " + render_check(xml, png))
        print(f"  图像: {os.path.relpath(png, ROOT)}")


if __name__ == "__main__":
    main()
