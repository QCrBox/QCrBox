import base64
from pathlib import Path
from textwrap import dedent


def ortep_cifvis_3d(cif_text):
    with open("cifvis.alldeps.umd.cjs") as fobj:
        js_code = fobj.read()

    cif_b64 = base64.b64encode(cif_text.encode()).decode()

    css_path = Path(__file__).parents[1] / "templates" / "ortep.css"
    css_snippet = css_path.read_text(encoding="utf-8").strip()
    inner_html_snippet = dedent(
        f"""
    <div class="cifvis-container" style="width: 100%; height: 100%;">
                
        <cifview-widget 
            id="cifview"
            caption="Crystal Structure"
            style="width: 100%; height: 100%;">
        </cifview-widget>

        <script type="module">            
            // Load the bundle
            {js_code}
            
            // Initialize with CIF data
            const widget = document.getElementById('cifview');
            
            // Wait for custom element to be defined and connected
            customElements.whenDefined('cifview-widget').then(() => {{
                const cifData = atob("{cif_b64}");
                widget.loadFromString(cifData);
            }});
        </script>
    </div>
    """
    )
    html_snippet = '<div class="section ortep">\n' + inner_html_snippet + "\n</div>"

    return "", html_snippet, css_snippet
