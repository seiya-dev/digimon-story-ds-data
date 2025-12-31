from pathlib import Path
import re, html, zipfile, datetime

def get_evo_tree(src_file, target_file, game_name, game_id):

    src = Path(src_file)
    raw = src.read_text(encoding="utf-8")
    lines = raw.splitlines()
    
    marker_idx=None
    for i,l in enumerate(lines):
        if l.strip().lower().startswith("the following digimon have no evolution line"):
            marker_idx=i; break
    
    main_lines = lines[:marker_idx] if marker_idx is not None else lines
    standalone_lines = lines[marker_idx+1:] if marker_idx is not None else []
    
    items=[]
    for l in main_lines:
        if not l.strip():
            items.append(("blank",0,""))
        else:
            items.append(("node", len(l)-len(l.lstrip(" ")), l.strip()))
    
    indents=sorted({indent for k,indent,_ in items if k=="node" and indent>0})
    step=min(indents) if indents else 2
    if step==0: step=2
    
    def stage_from_text(t):
        m=re.search(r"\(([A-Z])\)", t)
        return m.group(1) if m else ""
    
    def id_from_text(t):
        m=re.search(r"#(\d{3})", t)
        return int(m.group(1)) if m else None
    
    def id_str(t):
        i=id_from_text(t)
        return f"#{i:03d}" if i is not None else ""
    
    def strip_stage_and_id(t):
        t2=re.sub(r"\s*\([A-Z]\)\s*", " ", t).strip()
        t2=re.sub(r"\s+#\d{3}\s*$", "", t2).strip()
        t2=re.sub(r"\s{2,}", " ", t2)
        return t2
    
    def key_for(t):
        i=id_from_text(t)
        if i is not None: return f"#{i:03d}"
        return re.sub(r"[^a-z0-9]+","-",strip_stage_and_id(t).lower()).strip("-")[:80] or "item"
    
    def stage_span(stage):
        if not stage:
            return '<span class="stage stage-?">?</span>'
        return f'<span class="stage stage-{stage}">{stage}</span>'
    
    # blocks
    blocks=[]
    cur=[]
    for kind, indent, txt in items:
        if kind=="blank":
            if cur: blocks.append(cur); cur=[]
        else:
            cur.append((indent,txt))
    if cur: blocks.append(cur)
    
    # collect nodes
    all_nodes={}
    def register_node(txt):
        key=key_for(txt)
        if key in all_nodes: return
        all_nodes[key]={
            "key": key,
            "id": id_from_text(txt) if id_from_text(txt) is not None else 999999,
            "id_str": id_str(txt),
            "name": strip_stage_and_id(txt),
            "stage": stage_from_text(txt),
        }
        all_nodes[key]["search"]=(all_nodes[key]["name"]+" "+all_nodes[key]["id_str"]+" "+all_nodes[key]["stage"]).lower()
    
    for block in blocks:
        for _, txt in block:
            register_node(txt)
    
    standalone=[l.strip() for l in standalone_lines if l.strip()]
    solo=[]
    for txt in standalone:
        register_node(txt)
        solo.append({
            "id": id_from_text(txt) if id_from_text(txt) is not None else 999999,
            "id_str": id_str(txt),
            "name": strip_stage_and_id(txt),
            "stage": stage_from_text(txt),
            "key": key_for(txt),
        })
    
    def build_tree_item(lvl, txt):
        name = strip_stage_and_id(txt)
        sid  = id_str(txt)
        stg  = stage_from_text(txt)
        key  = key_for(txt)
        data = html.escape((f'{name} {sid} {stg}').lower())
        meta = f'<span class="meta">{html.escape(sid)}</span>' if sid else ''
        
        return (
            f'\t\t\t\t<li class="node lvl-{lvl}" data-text="{data}" data-lvl="{html.escape(stg)}">\n'
            f'\t\t\t\t\t<label class="item">\n'
            f'\t\t\t\t\t<input type="checkbox" class="cb" data-key="{html.escape(key)}">\n'
            f'\t\t\t\t\t{stage_span(stg)}\n'
            f'\t\t\t\t\t<span class="name">{html.escape(name)}</span>\n'
            f'\t\t\t\t\t{meta}\n'
            f'\t\t\t\t\t</label>\n'
            f'\t\t\t\t</li>\n'
        )
    
    def build_tree(block):
        nodes = [(indent // step, txt) for indent, txt in block]
        htparts = ['<ul class="tree">\n']
        
        for i, (lvl, txt) in enumerate(nodes):
            htparts.append(build_tree_item(lvl, txt))
        
        htparts.append('\t\t\t</ul>')
        return ''.join(htparts)
    
    # line sections
    line_sections=[]
    for block in blocks:
        root_txt=block[0][1]
        base_id=id_from_text(root_txt) if id_from_text(root_txt) is not None else 999999
        line_sections.append({
            "id": base_id,
            "root_name": strip_stage_and_id(root_txt),
            "root_id_str": id_str(root_txt),
            "block": block
        })
    
    combined=[]
    for s in line_sections:
        combined.append(("line", s["id"], s))
    for s in solo:
        combined.append(("solo", s["id"], s))
    combined.sort(key=lambda x: (x[1], 0 if x[0]=="line" else 1, (x[2].get("root_name") or x[2].get("name") or "").lower()))
    
    id_list=sorted(all_nodes.values(), key=lambda d:(d["id"], d["name"].lower()))
    id_rows=[]
    for d in id_list:
        data=html.escape(d["search"])
        meta=f'<span class="meta">{html.escape(d["id_str"])}</span>' if d["id_str"] else ""
        id_rows.append(
            f'\t\t\t<div class="idrow node" data-text="{data}" data-lvl="{html.escape(d["stage"])}">\n'
            f'\t\t\t\t<label class="item">\n'
            f'\t\t\t\t\t<input type="checkbox" class="cb" data-key="{html.escape(d["key"])}">\n'
            f'\t\t\t\t\t{stage_span(d["stage"])}\n'
            f'\t\t\t\t\t<span class="name">{html.escape(d["name"])}</span>\n'
            f'\t\t\t\t\t{meta}\n'
            f'\t\t\t\t</label>\n'
            f'\t\t\t</div>\n'
        )
    id_view_html=''.join(id_rows)
    
    parts=[(
        '<!doctype html>\n'
        '<html lang="en">\n'
        '<head>\n'
        '\t<meta charset="utf-8"/>\n'
        '\t<meta name="viewport" content="width=device-width,initial-scale=1"/>\n'
        f'\t<title>{game_name} Evolution Checklist</title>\n'
        f'\t<link rel="stylesheet" href="./cssjs/style.css">\n'
        '</head>\n'
        '<body>\n'
        f'\t<h1>{game_name} Evolution Checklist</h1>\n\n'
        '\t<div class="panel">\n'
        '\t\t<input id="q" type="search" placeholder="Search (name or #ID)..." />\n'
        '\t\t<label class="view-toggle" title="Click to switch view">\n'
        '\t\t\t<input id="toggleView" type="checkbox">\n'
        '\t\t\t<span id="viewLabel">View: by Lines</span>\n'
        '\t\t</label>\n'
        '\t\t<button id="exportBtn">Export checks</button>\n'
        '\t\t<button id="importBtn">Import checks</button>\n'
        '\t\t<input id="importFile" type="file" accept="application/json" style="display:none" />\n'
        '\t\t<button onclick="expandAll()">Expand all</button>\n'
        '\t\t<button onclick="collapseAll()">Collapse all</button>\n'
        '\t\t<button onclick="setAll(true)">Check all</button>\n'
        '\t\t<button onclick="setAll(false)">Uncheck all</button>\n'
        '\t\t<button onclick="clearState()">Clear saved state</button>\n'
        '\t\t<span class="small" id="count"></span>\n'
        '\t</div>\n'
        '\n'
        '\t<div id="viewByLine">\n'
    )]
    
    sec_idx = 0
    for kind, _, payload in combined:
        sec_idx += 1
        if kind=="line":
            root_id = f"root-{sec_idx}"
            title = f"{html.escape(payload['root_name'])} <span class='meta'>{html.escape(payload['root_id_str'])}</span>" if payload['root_id_str'] else html.escape(payload['root_name'])
            right_b = f'<span class="right"><span class="badge">Line</span><button class="toggle" onclick="toggleRoot(\'{root_id}\')">Toggle</button></span>'
            parts.append((
                f'\t\t<div class="section root" id="{root_id}">\n'
                f'\t\t\t<h2><span>{title}</span>{right_b}</h2>\n'
                f'\t\t\t{build_tree(payload["block"])}\n'
                f'\t\t</div>\n'
            ))
        else:
            title = f"{html.escape(payload['name'])} <span class='meta'>{html.escape(payload['id_str'])}</span>"
            data  = html.escape((payload["name"]+" "+payload["id_str"]+" "+payload["stage"]).lower())
            parts.append((
                f'\t\t<div class="section" id="solo-{sec_idx}">\n'
                f'\t\t\t<h2><span>{title}</span><span class="right"><span class="badge">No digivolution</span></span></h2>\n'
                f'\t\t\t<ul class="tree">\n'
                f'\t\t\t\t<li class="node" data-text="{data}" data-lvl="{html.escape(payload['stage'])}">\n'
                f'\t\t\t\t\t<label class="item">\n'
                f'\t\t\t\t\t\t<input type="checkbox" class="cb" data-key="{html.escape(payload['key'])}">\n'
                f'\t\t\t\t\t\t{stage_span(payload['stage'])}\n'
                f'\t\t\t\t\t\t<span class="name">{html.escape(payload['name'])}</span>\n'
                f'\t\t\t\t\t\t<span class="meta">{html.escape(payload['id_str'])}</span>\n'
                f'\t\t\t\t\t</label>\n'
                f'\t\t\t\t</li>\n'
                f'\t\t\t</ul>\n'
                f'\t\t</div>\n'
            ))
    
    parts.append((
        f'\t</div><!-- /viewByLine -->\n'
        f'\t<div id="viewById" class="hidden">\n'
        f'\t\t<div class="idlist">\n'
        f'\t\t\t<div class="small" style="margin-bottom:8px;">All Digimon sorted by #ID.</div>\n'
        f'{id_view_html}'
        f'\t\t</div>\n'
        f'\t</div>\n'
        f'\t<script>\n'
        f'\t\tconst STORAGE_KEY="{game_id}_evo_checklist";\n'
        f'\t\tconst VIEW_KEY="{game_id}_viewmode";\n'
        f'\t\tconst SAVE_KEY="{game_id}";\n'
        f'\t</script>\n'
        f'\t<script src="./cssjs/script.js">\n'
        f'\t</script>\n'
        f'</body>\n'
        f'</html>'
    ))
    
    out_html=Path(target_file)
    out_html.write_text(''.join(parts), encoding="utf-8")

get_evo_tree("Digimon Story DS Evo.txt", "Digimon Story DS Evo.html", "Digimon Story DS", "digimon_story_ds")
