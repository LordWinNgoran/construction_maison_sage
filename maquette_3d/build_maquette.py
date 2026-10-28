#!/usr/bin/env python3
"""Génère une maquette 3D simple et cotée à partir du plan 18 m x 11 m.

La géométrie est volontairement neutre: volumes blancs, sols gris, aucune
décoration. Le script produit des OBJ importables et une visionneuse HTML
autonome (sans bibliothèque externe) manipulable à 360 degrés.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WALL = 0.20
SLAB = 0.20
HEIGHT = 3.00

boxes: list[dict] = []
spaces: list[dict] = []


def slug(value: str) -> str:
    value = value.lower()
    value = value.replace("é", "e").replace("è", "e").replace("ê", "e")
    value = value.replace("à", "a").replace("â", "a").replace("î", "i")
    value = value.replace("ô", "o").replace("ù", "u").replace("ç", "c")
    return re.sub(r"[^a-z0-9]+", "_", value).strip("_")


def add_box(name, x0, y0, z0, x1, y1, z1, material, kind, room=None):
    boxes.append(
        {
            "name": slug(name),
            "label": name,
            "x0": round(float(x0), 4),
            "y0": round(float(y0), 4),
            "z0": round(float(z0), 4),
            "x1": round(float(x1), 4),
            "y1": round(float(y1), 4),
            "z1": round(float(z1), 4),
            "material": material,
            "kind": kind,
            "room": room,
        }
    )


def add_space(space_id, label, x0, y0, x1, y1, side, material="Sol_piece"):
    spaces.append(
        {
            "id": space_id,
            "label": label,
            "x0": x0,
            "y0": y0,
            "x1": x1,
            "y1": y1,
            "side": side,
            "cx": (x0 + x1) / 2,
            "cy": (y0 + y1) / 2,
        }
    )
    inset = 0.08
    add_box(
        f"Sol {label}",
        x0 + inset,
        y0 + inset,
        SLAB,
        x1 - inset,
        y1 - inset,
        SLAB + 0.045,
        material,
        "floor",
        room=space_id,
    )


def subtract_intervals(start, end, intervals):
    intervals = sorted((max(start, a), min(end, b)) for a, b in intervals if b > start and a < end)
    cursor = start
    result = []
    for a, b in intervals:
        if a > cursor:
            result.append((cursor, a))
        cursor = max(cursor, b)
    if cursor < end:
        result.append((cursor, end))
    return result


def add_wall_x(name, y, x0, x1, openings=(), material="Mur"):
    """Mur parallèle à X. Une ouverture est (a, b, z_bas, z_haut)."""
    breaks = {x0, x1}
    for a, b, _, _ in openings:
        breaks.add(max(x0, min(x1, a)))
        breaks.add(max(x0, min(x1, b)))
    points = sorted(breaks)
    for i, (a, b) in enumerate(zip(points, points[1:])):
        if b - a < 1e-6:
            continue
        active = [o for o in openings if o[0] < b - 1e-6 and o[1] > a + 1e-6]
        if not active:
            add_box(f"{name}_{i}", a, y - WALL / 2, SLAB, b, y + WALL / 2, SLAB + HEIGHT, material, "wall")
            continue
        low = min(o[2] for o in active)
        high = max(o[3] for o in active)
        if low > SLAB:
            add_box(f"{name}_{i}_bas", a, y - WALL / 2, SLAB, b, y + WALL / 2, low, material, "wall")
        if high < SLAB + HEIGHT:
            add_box(f"{name}_{i}_haut", a, y - WALL / 2, high, b, y + WALL / 2, SLAB + HEIGHT, material, "wall")


def add_wall_y(name, x, y0, y1, openings=(), material="Mur"):
    """Mur parallèle à Y. Une ouverture est (a, b, z_bas, z_haut)."""
    breaks = {y0, y1}
    for a, b, _, _ in openings:
        breaks.add(max(y0, min(y1, a)))
        breaks.add(max(y0, min(y1, b)))
    points = sorted(breaks)
    for i, (a, b) in enumerate(zip(points, points[1:])):
        if b - a < 1e-6:
            continue
        active = [o for o in openings if o[0] < b - 1e-6 and o[1] > a + 1e-6]
        if not active:
            add_box(f"{name}_{i}", x - WALL / 2, a, SLAB, x + WALL / 2, b, SLAB + HEIGHT, material, "wall")
            continue
        low = min(o[2] for o in active)
        high = max(o[3] for o in active)
        if low > SLAB:
            add_box(f"{name}_{i}_bas", x - WALL / 2, a, SLAB, x + WALL / 2, b, low, material, "wall")
        if high < SLAB + HEIGHT:
            add_box(f"{name}_{i}_haut", x - WALL / 2, a, high, x + WALL / 2, b, SLAB + HEIGHT, material, "wall")


def build_geometry():
    # Socle continu de la maquette, 18 m x 11 m.
    add_box("Socle 18x11", 0, 0, 0, 18, 11, SLAB, "Socle", "base")

    # Surfaces de chaque espace, exactement calées sur les cotes du schéma.
    definitions = [
        ("lg_terrasse", "Logement gauche — Terrasse 6×3", 0, 0, 6, 3, "gauche", "Sol_terrasse"),
        ("lg_ouvert", "Logement gauche — Espace ouvert 3×3", 6, 0, 9, 3, "gauche", "Sol_ouvert"),
        ("lg_salon", "Logement gauche — Salon 6×4", 0, 3, 6, 7, "gauche", "Sol_piece"),
        ("lg_cuisine", "Logement gauche — Cuisine 3×4", 6, 3, 9, 7, "gauche", "Sol_piece"),
        ("lg_ch1", "Logement gauche — Chambre 1, 4×4", 0, 7, 4, 11, "gauche", "Sol_chambre"),
        ("lg_degagement", "Logement gauche — Dégagement 2×1", 4, 7, 6, 8, "gauche", "Sol_service"),
        ("lg_se2", "Logement gauche — Salle d'eau 2×1,2", 4, 8, 6, 9.2, "gauche", "Sol_service"),
        ("lg_se1", "Logement gauche — Salle d'eau 2×1,8", 4, 9.2, 6, 11, "gauche", "Sol_service"),
        ("lg_ch2", "Logement gauche — Chambre 2, 3×4", 6, 7, 9, 11, "gauche", "Sol_chambre"),
        ("ld_ouvert", "Logement droit — Espace ouvert 3×3", 9, 0, 12, 3, "droit", "Sol_ouvert"),
        ("ld_terrasse", "Logement droit — Terrasse 6×3", 12, 0, 18, 3, "droit", "Sol_terrasse"),
        ("ld_cuisine", "Logement droit — Cuisine 3×4", 9, 3, 12, 7, "droit", "Sol_piece"),
        ("ld_salon", "Logement droit — Salon 6×4", 12, 3, 18, 7, "droit", "Sol_piece"),
        ("ld_ch2", "Logement droit — Chambre 2, 3×4", 9, 7, 12, 11, "droit", "Sol_chambre"),
        ("ld_degagement", "Logement droit — Dégagement 2×1", 12, 7, 14, 8, "droit", "Sol_service"),
        ("ld_se2", "Logement droit — Salle d'eau 2×1,2", 12, 8, 14, 9.2, "droit", "Sol_service"),
        ("ld_se1", "Logement droit — Salle d'eau 2×1,8", 12, 9.2, 14, 11, "droit", "Sol_service"),
        ("ld_ch1", "Logement droit — Chambre 1, 4×4", 14, 7, 18, 11, "droit", "Sol_chambre"),
    ]
    for definition in definitions:
        add_space(*definition)

    door = (SLAB, 2.50)
    window = (1.10, 2.25)

    # Façades extérieures. Les ouvertures sont des hypothèses sobres car le PDF
    # ne comporte aucune élévation.
    add_wall_x(
        "Facade avant",
        3,
        0,
        18,
        openings=[
            (1.0, 4.8, *door),
            (7.1, 8.2, *door),
            (9.8, 10.9, *door),
            (13.2, 17.0, *door),
        ],
    )
    add_wall_x(
        "Facade arriere",
        11,
        0,
        18,
        openings=[
            (1.0, 3.0, *window),
            (4.45, 5.55, *window),
            (6.5, 8.3, *window),
            (9.7, 11.5, *window),
            (12.45, 13.55, *window),
            (15.0, 17.0, *window),
        ],
    )
    add_wall_y("Pignon gauche", 0, 3, 11, openings=[(4.3, 5.8, *window), (8.4, 9.9, *window)])
    add_wall_y("Pignon droit", 18, 3, 11, openings=[(4.3, 5.8, *window), (8.4, 9.9, *window)])

    # Refend central entre les deux logements.
    add_wall_y("Mur mitoyen", 9, 3, 11)

    # Cloisons du logement gauche.
    add_wall_y("LG cloison X4", 4, 7, 11)
    add_wall_y("LG cloison X6", 6, 3, 11, openings=[(5.8, 6.8, *door)])
    add_wall_x("LG ligne chambres 1", 7, 0, 4, openings=[(3.0, 3.9, *door)])
    add_wall_x("LG ligne degagement", 7, 4, 6, openings=[(4.35, 5.65, *door)])
    add_wall_x("LG ligne chambres 2", 7, 6, 9, openings=[(6.2, 7.1, *door)])
    add_wall_x("LG salle eau basse", 8, 4, 6, openings=[(4.2, 5.0, *door)])
    add_wall_x("LG salle eau haute", 9.2, 4, 6, openings=[(5.0, 5.8, *door)])

    # Cloisons du logement droit, miroir exact.
    add_wall_y("LD cloison X12", 12, 3, 11, openings=[(5.8, 6.8, *door)])
    add_wall_y("LD cloison X14", 14, 7, 11)
    add_wall_x("LD ligne chambres 2", 7, 9, 12, openings=[(10.9, 11.8, *door)])
    add_wall_x("LD ligne degagement", 7, 12, 14, openings=[(12.35, 13.65, *door)])
    add_wall_x("LD ligne chambres 1", 7, 14, 18, openings=[(14.1, 15.0, *door)])
    add_wall_x("LD salle eau basse", 8, 12, 14, openings=[(13.0, 13.8, *door)])
    add_wall_x("LD salle eau haute", 9.2, 12, 14, openings=[(12.2, 13.0, *door)])

    # Poteaux et couvertures. Les toitures sont séparées pour pouvoir les masquer.
    for x, y, name in [
        (0.20, 0.20, "Poteau terrasse G1"),
        (5.80, 0.20, "Poteau terrasse G2"),
        (12.20, 0.20, "Poteau terrasse D1"),
        (17.80, 0.20, "Poteau terrasse D2"),
    ]:
        add_box(name, x - 0.10, y - 0.10, SLAB, x + 0.10, y + 0.10, SLAB + HEIGHT, "Poteau", "column")

    add_box("Toit volume principal", -0.10, 2.90, SLAB + HEIGHT, 18.10, 11.10, SLAB + HEIGHT + 0.18, "Toiture", "roof")
    add_box("Toit terrasse gauche", -0.10, -0.10, SLAB + HEIGHT, 6.10, 3.05, SLAB + HEIGHT + 0.16, "Toiture", "roof")
    add_box("Toit terrasse droite", 11.90, -0.10, SLAB + HEIGHT, 18.10, 3.05, SLAB + HEIGHT + 0.16, "Toiture", "roof")


MATERIALS = {
    "Socle": (0.62, 0.64, 0.66),
    "Mur": (0.93, 0.92, 0.88),
    "Poteau": (0.80, 0.81, 0.82),
    "Toiture": (0.56, 0.58, 0.60),
    "Sol_piece": (0.78, 0.80, 0.81),
    "Sol_chambre": (0.84, 0.84, 0.82),
    "Sol_service": (0.70, 0.75, 0.77),
    "Sol_terrasse": (0.73, 0.74, 0.74),
    "Sol_ouvert": (0.66, 0.68, 0.69),
}


def write_mtl():
    lines = ["# Matériaux neutres de la maquette\n"]
    for name, rgb in MATERIALS.items():
        lines.extend(
            [
                f"newmtl {name}\n",
                f"Kd {rgb[0]:.4f} {rgb[1]:.4f} {rgb[2]:.4f}\n",
                "Ka 0.1200 0.1200 0.1200\n",
                "Ks 0.0600 0.0600 0.0600\n",
                "Ns 12.0000\n",
                "d 1.0000\n\n",
            ]
        )
    (ROOT / "maquette_2_logements.mtl").write_text("".join(lines), encoding="utf-8")


def write_obj(filename: str, include_roof: bool):
    lines = [
        "# Maquette 3D des deux logements 3 pièces\n",
        "# Unité: mètre\n",
        "mtllib maquette_2_logements.mtl\n",
    ]
    offset = 1
    for box in boxes:
        if box["kind"] == "roof" and not include_roof:
            continue
        x0, y0, z0 = box["x0"], box["y0"], box["z0"]
        x1, y1, z1 = box["x1"], box["y1"], box["z1"]
        vertices = [
            (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
            (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
        ]
        faces = [
            (1, 4, 3, 2), (5, 6, 7, 8), (1, 2, 6, 5),
            (2, 3, 7, 6), (3, 4, 8, 7), (4, 1, 5, 8),
        ]
        lines.append(f"o {box['name']}\n")
        lines.append(f"usemtl {box['material']}\n")
        for vx, vy, vz in vertices:
            lines.append(f"v {vx:.4f} {vy:.4f} {vz:.4f}\n")
        for face in faces:
            lines.append("f " + " ".join(str(offset + i - 1) for i in face) + "\n")
        offset += 8
    (ROOT / filename).write_text("".join(lines), encoding="utf-8")


def write_model_json():
    payload = {
        "units": "m",
        "overall": {"width": 18, "depth": 11, "wall_height": HEIGHT, "wall_thickness": WALL},
        "assumptions": [
            "Murs de 0,20 m",
            "Hauteur de murs de 3,00 m",
            "Toiture plate schématique et amovible",
            "Ouvertures proposées car absentes du plan source",
        ],
        "materials": {k: list(v) for k, v in MATERIALS.items()},
        "boxes": boxes,
        "spaces": spaces,
    }
    (ROOT / "modele.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


HTML_TEMPLATE = r'''<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Maquette 3D — deux logements 3 pièces</title>
<script src="../auth.js"></script>
<script>window.MaquetteAuth.requireAuth('../index.html');</script>
<style>
:root{--ink:#202326;--muted:#687078;--paper:#f3f2ee;--panel:#fff;--line:#d7d8d6;--accent:#b8762e}
*{box-sizing:border-box}html,body{margin:0;height:100%;font-family:Inter,Arial,sans-serif;color:var(--ink);background:var(--paper)}
body{display:grid;grid-template-columns:300px 1fr;overflow:hidden}.panel{background:var(--panel);border-right:1px solid var(--line);padding:18px;overflow:auto;z-index:2}
h1{font-size:19px;line-height:1.2;margin:0 0 6px}.sub{font-size:12px;color:var(--muted);line-height:1.45;margin-bottom:16px}.group{margin:14px 0}.group-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-bottom:7px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:6px}button,select{width:100%;border:1px solid var(--line);border-radius:7px;background:#fff;padding:8px 9px;color:var(--ink);font-size:12px;cursor:pointer}button:hover,button.active{border-color:#999;background:#f1f1ee}select{cursor:pointer}.check{display:flex;align-items:center;gap:8px;font-size:12px;margin:7px 0}.check input{accent-color:var(--accent)}
.note{font-size:11px;line-height:1.45;color:var(--muted);border-top:1px solid var(--line);padding-top:12px;margin-top:15px}.dims{font-size:12px;line-height:1.7;background:#f5f4f1;border-radius:8px;padding:9px 11px}
.stage{position:relative;min-width:0}.stage canvas{width:100%;height:100%;display:block;cursor:grab}.stage canvas:active{cursor:grabbing}.badge{position:absolute;left:18px;top:16px;background:rgba(255,255,255,.88);border:1px solid var(--line);border-radius:8px;padding:8px 11px;font-size:12px;backdrop-filter:blur(4px)}
.help{position:absolute;right:18px;bottom:15px;background:rgba(255,255,255,.86);border:1px solid var(--line);border-radius:8px;padding:7px 10px;color:var(--muted);font-size:11px}.measure{display:grid;grid-template-columns:1fr 1fr;gap:5px;margin-top:7px}.measure span{background:#f5f4f1;border-radius:5px;padding:5px 7px;font-size:10px}
.clean{grid-template-columns:1fr}.clean .panel,.clean .help{display:none}.clean .badge{font-size:15px;padding:10px 14px}
@media(max-width:760px){body{grid-template-columns:1fr;grid-template-rows:auto 1fr}.panel{border-right:0;border-bottom:1px solid var(--line);padding:10px;max-height:215px}.panel h1,.sub,.note,.dims{display:none}.group{display:inline-block;vertical-align:top;width:48%;margin:3px}.stage{min-height:0}}
</style>
</head>
<body>
<aside class="panel">
  <h1>Maquette 3D de base</h1>
  <div class="sub">Deux logements symétriques de 3 pièces — modèle neutre, sans mobilier ni décoration.</div>
  <div class="dims"><b>Dimensions générales</b><br>18,00 m × 11,00 m<br>Murs: 0,20 m<br>Hauteur: 3,00 m</div>
  <div class="group">
    <div class="group-title">Vues fixes</div>
    <div class="grid">
      <button data-view="front">Avant</button><button data-view="back">Arrière</button>
      <button data-view="left">Gauche</button><button data-view="right">Droite</button>
      <button data-view="top">Dessus</button><button data-view="axo">Axonométrie</button>
    </div>
  </div>
  <div class="group">
    <div class="group-title">Espace à examiner</div>
    <select id="spaceSelect"><option value="">Ensemble complet</option></select>
    <div class="grid" style="margin-top:6px"><button id="prevSpace">← Précédent</button><button id="nextSpace">Suivant →</button></div>
  </div>
  <div class="group">
    <div class="group-title">Affichage</div>
    <label class="check"><input id="roofToggle" type="checkbox"> Montrer les toitures</label>
    <label class="check"><input id="labelToggle" type="checkbox" checked> Montrer les noms</label>
    <label class="check"><input id="cutToggle" type="checkbox" checked> Coupe claire des murs</label>
  </div>
  <div class="grid"><button id="resetBtn">Réinitialiser</button><button id="exportBtn">Exporter PNG</button></div>
  <button id="logoutBtn" style="margin-top:7px">Se déconnecter</button>
  <div class="note"><b>Navigation 360°</b><br>Glisser pour tourner. Molette pour zoomer. Les ouvertures et la toiture sont schématiques, car le PDF ne comporte ni façades ni coupes.</div>
</aside>
<main class="stage">
  <canvas id="canvas"></canvas>
  <div class="badge" id="badge">Vue axonométrique — ensemble</div>
  <div class="help">Glisser: rotation · Molette: zoom</div>
</main>
<script>
const MODEL = __MODEL_JSON__;
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const select = document.getElementById('spaceSelect');
const roofToggle = document.getElementById('roofToggle');
const labelToggle = document.getElementById('labelToggle');
const cutToggle = document.getElementById('cutToggle');
const badge = document.getElementById('badge');
const qs = new URLSearchParams(location.search);
const state = {az:-55*Math.PI/180,el:36*Math.PI/180,dist:27,target:[9,5.5,1.15],roof:false,labels:true,cut:true,space:''};
const presets={
  front:{az:-90,el:13,dist:29,label:'Façade avant'},back:{az:90,el:13,dist:29,label:'Façade arrière'},
  left:{az:180,el:13,dist:24,label:'Côté gauche'},right:{az:0,el:13,dist:24,label:'Côté droit'},
  top:{az:-90,el:89,dist:25,label:'Vue de dessus'},axo:{az:-55,el:36,dist:27,label:'Vue axonométrique'}
};
for(const s of MODEL.spaces){const o=document.createElement('option');o.value=s.id;o.textContent=s.label;select.appendChild(o)}
function vecSub(a,b){return[a[0]-b[0],a[1]-b[1],a[2]-b[2]]}function dot(a,b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]}
function cross(a,b){return[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]}
function norm(a){const n=Math.hypot(...a)||1;return a.map(v=>v/n)}
function hex(rgb,shade=1){const vals=rgb.map(v=>Math.max(0,Math.min(255,Math.round(v*255*shade))));return `rgb(${vals[0]},${vals[1]},${vals[2]})`}
function camera(){const ce=Math.cos(state.el),se=Math.sin(state.el),ca=Math.cos(state.az),sa=Math.sin(state.az);const p=[state.target[0]+state.dist*ce*ca,state.target[1]+state.dist*ce*sa,state.target[2]+state.dist*se];const f=norm(vecSub(state.target,p));const r=norm(cross(f,[0,0,1]));const u=norm(cross(r,f));return{p,f,r,u}}
function project(v,cam,w,h){const d=vecSub(v,cam.p),depth=dot(d,cam.f);if(depth<.1)return null;const focal=Math.min(w,h)/(2*Math.tan(43*Math.PI/360));return{x:w/2+focal*dot(d,cam.r)/depth,y:h/2-focal*dot(d,cam.u)/depth,depth}}
const faceDefs=[{i:[0,1,2,3],shade:.72},{i:[4,7,6,5],shade:1.04},{i:[0,4,5,1],shade:.90},{i:[1,5,6,2],shade:.82},{i:[2,6,7,3],shade:.88},{i:[3,7,4,0],shade:.78}];
function vertices(b){return[[b.x0,b.y0,b.z0],[b.x1,b.y0,b.z0],[b.x1,b.y1,b.z0],[b.x0,b.y1,b.z0],[b.x0,b.y0,b.z1],[b.x1,b.y0,b.z1],[b.x1,b.y1,b.z1],[b.x0,b.y1,b.z1]]}
function visibleBoxes(){return MODEL.boxes.filter(b=>{if(b.kind==='roof'&&!state.roof)return false;return true})}
function render(){
  const dpr=Math.min(2,window.devicePixelRatio||1),rect=canvas.getBoundingClientRect();canvas.width=Math.round(rect.width*dpr);canvas.height=Math.round(rect.height*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);const w=rect.width,h=rect.height;
  const grad=ctx.createLinearGradient(0,0,0,h);grad.addColorStop(0,'#f7f7f5');grad.addColorStop(1,'#e9e8e4');ctx.fillStyle=grad;ctx.fillRect(0,0,w,h);
  const cam=camera(),faces=[];
  for(const b of visibleBoxes()){
    const vs=vertices(b);for(const fd of faceDefs){const pts=fd.i.map(i=>project(vs[i],cam,w,h));if(pts.some(p=>!p))continue;const rawDepth=pts.reduce((s,p)=>s+p.depth,0)/4;faces.push({pts,depth:b.kind==='roof'?-1000+rawDepth*.001:rawDepth,b,shade:fd.shade})}
  }
  faces.sort((a,b)=>b.depth-a.depth);
  for(const f of faces){
    const isOtherFloor=state.space&&f.b.kind==='floor'&&f.b.room!==state.space;const isSelected=f.b.room===state.space;
    let alpha=1;if(state.space){if(f.b.kind==='wall'||f.b.kind==='column')alpha=state.cut?.26:.62;else if(isOtherFloor)alpha=.12;else if(f.b.kind==='base')alpha=.38}
    const rgb=isSelected?[0.78,0.49,0.20]:MODEL.materials[f.b.material];ctx.globalAlpha=alpha;ctx.beginPath();ctx.moveTo(f.pts[0].x,f.pts[0].y);for(let i=1;i<f.pts.length;i++)ctx.lineTo(f.pts[i].x,f.pts[i].y);ctx.closePath();ctx.fillStyle=hex(rgb,f.shade);ctx.fill();ctx.strokeStyle=isSelected?'rgba(116,63,18,.85)':'rgba(48,52,54,.48)';ctx.lineWidth=isSelected?1.6:.65;ctx.stroke();
  }
  ctx.globalAlpha=1;
  if(state.labels){
    const shown=state.space?MODEL.spaces.filter(s=>s.id===state.space):MODEL.spaces.filter(s=>['lg_salon','lg_cuisine','lg_ch1','lg_ch2','ld_salon','ld_cuisine','ld_ch1','ld_ch2','lg_terrasse','ld_terrasse'].includes(s.id));
    ctx.font='600 11px Arial';ctx.textAlign='center';ctx.textBaseline='middle';for(const s of shown){const p=project([s.cx,s.cy,.28],cam,w,h);if(!p)continue;const text=state.space?s.label.replace(/^Logement (gauche|droit) — /,''):s.label.replace(/^Logement (gauche|droit) — /,'');const tw=ctx.measureText(text).width;ctx.fillStyle='rgba(255,255,255,.88)';ctx.fillRect(p.x-tw/2-5,p.y-9,tw+10,18);ctx.strokeStyle='rgba(70,70,70,.28)';ctx.strokeRect(p.x-tw/2-5,p.y-9,tw+10,18);ctx.fillStyle='#272a2c';ctx.fillText(text,p.x,p.y)}
  }
  const space=MODEL.spaces.find(s=>s.id===state.space);badge.textContent=(space?space.label:'Maquette complète')+(state.roof?' · toiture visible':' · toiture masquée');window.__MODEL_READY__=true;
}
function setView(name){const p=presets[name]||presets.axo;state.az=p.az*Math.PI/180;state.el=p.el*Math.PI/180;state.dist=p.dist;if(!state.space)state.target=[9,5.5,1.15];render()}
function focusSpace(id){state.space=id;select.value=id;const s=MODEL.spaces.find(x=>x.id===id);if(s){state.target=[s.cx,s.cy,.65];state.dist=Math.max(8.5,Math.max(s.x1-s.x0,s.y1-s.y0)*2.45);state.az=-55*Math.PI/180;state.el=46*Math.PI/180;state.roof=false;roofToggle.checked=false}else{state.target=[9,5.5,1.15];state.dist=27}render()}
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>setView(b.dataset.view));select.onchange=()=>focusSpace(select.value);
roofToggle.onchange=()=>{state.roof=roofToggle.checked;render()};labelToggle.onchange=()=>{state.labels=labelToggle.checked;render()};cutToggle.onchange=()=>{state.cut=cutToggle.checked;render()};
document.getElementById('resetBtn').onclick=()=>{state.space='';select.value='';state.roof=false;roofToggle.checked=false;state.labels=true;labelToggle.checked=true;setView('axo')};
document.getElementById('exportBtn').onclick=()=>{render();const a=document.createElement('a');a.download=(state.space||'maquette_globale')+'.png';a.href=canvas.toDataURL('image/png');a.click()};
document.getElementById('logoutBtn').onclick=()=>window.MaquetteAuth.logout('../index.html');
function cycle(dir){let i=MODEL.spaces.findIndex(s=>s.id===state.space);i=(i+dir+MODEL.spaces.length)%MODEL.spaces.length;focusSpace(MODEL.spaces[i].id)}document.getElementById('prevSpace').onclick=()=>cycle(-1);document.getElementById('nextSpace').onclick=()=>cycle(1);
let drag=false,last=[0,0];canvas.addEventListener('pointerdown',e=>{drag=true;last=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId)});canvas.addEventListener('pointerup',()=>drag=false);canvas.addEventListener('pointermove',e=>{if(!drag)return;state.az+=(e.clientX-last[0])*.008;state.el=Math.max(.08,Math.min(1.48,state.el-(e.clientY-last[1])*.006));last=[e.clientX,e.clientY];render()});canvas.addEventListener('wheel',e=>{e.preventDefault();state.dist=Math.max(4,Math.min(55,state.dist*Math.exp(e.deltaY*.001)));render()},{passive:false});
function init(){if(qs.get('clean')==='1')document.body.classList.add('clean');const view=qs.get('view')||'axo';state.roof=qs.get('roof')==='1';state.labels=qs.get('labels')!=='0';state.cut=qs.get('cut')!=='0';roofToggle.checked=state.roof;labelToggle.checked=state.labels;cutToggle.checked=state.cut;const sp=qs.get('space');if(sp)focusSpace(sp);else setView(view);if(qs.has('az'))state.az=Number(qs.get('az'))*Math.PI/180;if(qs.has('el'))state.el=Number(qs.get('el'))*Math.PI/180;if(qs.has('dist'))state.dist=Number(qs.get('dist'));render()}
window.addEventListener('resize',render);init();
</script>
</body>
</html>'''


def write_viewer():
    payload = {
        "materials": {k: list(v) for k, v in MATERIALS.items()},
        "boxes": boxes,
        "spaces": spaces,
    }
    html = HTML_TEMPLATE.replace("__MODEL_JSON__", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    (ROOT / "maquette_3d_interactive.html").write_text(html, encoding="utf-8")


def write_gallery():
    overview_items = [
        ("vue_globale_sans_toiture.png", "Vue globale ouverte"),
        ("vue_globale_avec_toiture.png", "Vue globale avec toiture"),
        ("vue_dessus_plan.png", "Vue de dessus du plan"),
        ("vues_360/facade_avant.png", "Façade avant"),
        ("vues_360/facade_arriere.png", "Façade arrière"),
        ("vues_360/cote_gauche.png", "Côté gauche"),
        ("vues_360/cote_droit.png", "Côté droit"),
    ]
    overview = "\n".join(
        f'<figure><a href="{path}"><img src="{path}" alt="{label}"></a><figcaption>{label}</figcaption></figure>'
        for path, label in overview_items
    )
    tour = "\n".join(
        f'<figure><a href="vues_360/tour_{a:03d}.png"><img src="vues_360/tour_{a:03d}.png" alt="Angle {a} degrés"></a><figcaption>Angle {a}°</figcaption></figure>'
        for a in range(0, 360, 45)
    )
    room_figures = "\n".join(
        f'<figure><a href="vues_espaces/{s["id"]}.png"><img src="vues_espaces/{s["id"]}.png" alt="{s["label"]}"></a><figcaption>{s["label"]}</figcaption></figure>'
        for s in spaces
    )
    html = f'''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Galerie — Maquette 3D</title><script src="../auth.js"></script><script>window.MaquetteAuth.requireAuth('../index.html');</script><style>
body{{margin:0;font:15px Arial,sans-serif;background:#efefec;color:#222}}header{{padding:28px 5vw;background:#fff;border-bottom:1px solid #ccc;position:sticky;top:0;z-index:2}}h1{{margin:0 0 6px;font-size:25px}}p{{margin:0;color:#666}}main{{padding:24px 5vw 50px}}h2{{margin-top:30px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}}figure{{margin:0;background:white;border:1px solid #d5d5d1;border-radius:9px;overflow:hidden}}img{{display:block;width:100%;aspect-ratio:3/2;object-fit:cover}}figcaption{{padding:10px 12px;font-size:13px}}.open{{display:inline-block;margin-top:12px;padding:9px 13px;border-radius:6px;background:#333;color:#fff;text-decoration:none}}</style></head><body>
<header><h1>Maquette 3D — deux logements</h1><p>Modèle architectural neutre, sans mobilier ni décoration.</p><a class="open" href="maquette_3d_interactive.html">Ouvrir la vue interactive 360°</a> <a class="open" href="#" onclick="window.MaquetteAuth.logout('../index.html');return false">Se déconnecter</a></header><main>
<h2>Vues générales et quatre côtés</h2><div class="grid">{overview}</div>
<h2>Tour complet 360°</h2><div class="grid">{tour}</div>
<h2>Vues de chaque espace</h2><div class="grid">{room_figures}</div>
</main></body></html>'''
    (ROOT / "galerie.html").write_text(html, encoding="utf-8")


def main():
    build_geometry()
    write_mtl()
    write_obj("maquette_2_logements_avec_toiture.obj", include_roof=True)
    write_obj("maquette_2_logements_sans_toiture.obj", include_roof=False)
    write_model_json()
    write_viewer()
    write_gallery()
    print(f"{len(boxes)} volumes et {len(spaces)} espaces générés dans {ROOT}")


if __name__ == "__main__":
    main()
