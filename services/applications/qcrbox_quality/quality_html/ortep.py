import base64

from django.template.loader import render_to_string


def ortep_cifvis_3d(cif_text):
    """
    Generate HTML and CSS snippets for displaying a CIF file in a 3D visualization using ORTEP.

    This function encodes the CIF text in base64 and prepares the necessary HTML and CSS
    snippets to render a 3D visualization widget. The widget is styled with a CSS file
    located in the templates directory.

    Parameters
    ----------
    cif_text : str
        The CIF text content to be visualized.

    Returns
    -------
    tuple
        A tuple containing:
        - header_snippet : str
            JavaScript resources for the ORTEP widget.
        - body_snippet : str
            HTML div containing the CIF visualization widget.
        - css_snippet : str
            CSS resources for styling the widget.

    """
    cif_b64 = base64.b64encode(cif_text.encode()).decode()

    header_snippet = render_to_string("category_components/ortep/header.html", {})
    html_snippet = render_to_string(
        "category_components/ortep/body.html",
        {
            "cif_b64": cif_b64,
        },
    )
    css_snippet = render_to_string("category_components/ortep/style.css", {})

    return header_snippet, html_snippet, css_snippet
