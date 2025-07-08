import numpy as np
from bokeh.embed import components
from bokeh.models import ColumnDataSource, TabPanel, Tabs
from bokeh.plotting import figure
from bokeh.resources import CDN
from django.template.loader import render_to_string
from qcrboxtools.analyse.quality.precision import precision_vs_resolution
from qcrboxtools.cif.read import cifdata_str_or_index

from .util import read_cif_text_as_unified


def create_precision_resolution_plot(
    resolution_data: dict[str, np.ndarray], indicator_name: str, y_label: str, plot_height: int = 300
) -> figure:
    """
    Create a single precision vs resolution plot.

    Parameters
    ----------
    resolution_data : Dict[str, np.ndarray]
        Dictionary containing resolution binned data.
    indicator_name : str
        Name of the indicator to plot.
    y_label : str
        Label for the y-axis.
    plot_height : int, optional
        Height of the plot in pixels.

    Returns
    -------
    figure
        Bokeh figure object.

    """
    if indicator_name not in resolution_data:
        # Return empty plot if data not available
        p = figure(height=plot_height, sizing_mode="stretch_width")
        p.text(
            [0.5], [0.5], text=[f"No data available for {indicator_name}"], text_align="center", text_baseline="middle"
        )
        return p

    # Get resolution limits and indicator values
    d_max = resolution_data.get("d_min lower", np.array([]))
    d_min = resolution_data.get("d_min upper", np.array([]))
    values = resolution_data[indicator_name]

    x_label = "Resolution Bin"

    # Filter out None/NaN values
    valid_mask = np.logical_not(np.isnan(values.astype(float)))
    x_data = np.arange(len(values)) + 0.5
    x_valid = x_data[valid_mask] if len(x_data) == len(valid_mask) else x_data
    y_valid = values[valid_mask]

    if len(y_valid) == 0:
        # Return empty plot if no valid data
        p = figure(height=plot_height, sizing_mode="stretch_width")
        p.text([0.5], [0.5], text=[f"No valid data for {indicator_name}"], text_align="center", text_baseline="middle")
        return p

    # Create the plot
    p = figure(
        height=plot_height,
        sizing_mode="stretch_width",
        x_axis_label=x_label,
        y_axis_label=y_label,
        title=f"{indicator_name} vs Resolution",
    )
    xtick_pos = list(np.arange(len(values) + 1))
    d_limits = list(d_max) + [d_min[-1]]
    p.xaxis.ticker = list(xtick_pos)
    p.xaxis.major_label_overrides = {i: f"{dlim:.2f}" for i, dlim in zip(xtick_pos, d_limits, strict=False)}
    p.x_range.start = min(xtick_pos) - 0.2
    p.x_range.end = max(xtick_pos) + 0.2

    # Add scatter plot and line
    source = ColumnDataSource(data={"x": x_valid, "y": y_valid})
    p.scatter("x", "y", source=source, size=10, alpha=0.7, color="navy")

    return p


def precision_vs_resolution_plot(cif_text: str) -> tuple:
    cif_model = read_cif_text_as_unified(cif_text)
    cif_block, _ = cifdata_str_or_index(cif_model, 0)

    resolution_data = precision_vs_resolution(cif_block, 10)

    # Define plots to create with their configurations
    plot_configs = [
        ("R_meas", r"$$R_{\mathrm{meas}} \, (\%)$$"),
        ("R_pim", r"$$R_{\mathrm{pim}} \, (\%)$$"),
        ("CC1/2", r"$$\mathrm{CC}_{1/2}$$"),
        ("I/sigma(I)", r"$$I/\sigma(I)$$"),
        ("Completeness", r"$$\mathrm{Completeness} \, (\%)$$"),
        ("Mean Redundancy", r"$$\mathrm{Mean\,Redundancy}$$"),
    ]
    # Create individual plots
    plots = []
    for indicator_name, y_label in plot_configs:
        plot = create_precision_resolution_plot(resolution_data, indicator_name, y_label)
        plots.append(plot)

    # Create tabs
    tabs = []
    for i, (indicator_name, _) in enumerate(plot_configs):
        tab_title = indicator_name.replace("_", " ")  # Make titles more readable
        panel = TabPanel(child=plots[i], title=tab_title)
        tabs.append(panel)

    # Create tabbed layout
    tabs_widget = Tabs(tabs=tabs, sizing_mode="stretch_width")

    plot_script, plot_div = components(tabs_widget, CDN)
    return plot_script, plot_div


def precision_plot(cif_text: str) -> tuple[set[str], str, set[str]]:
    """
    Generate HTML and CSS snippets for a precision vs resolution plot.

    Parameters
    ----------
    cif_text : str
        The CIF text content to be visualized.

    Returns
    -------
    tuple
        A tuple containing:
        - header_snippets : set[str]
            HTML snippet for the header section, including JavaScript resources.
        - body_snippets : str
            HTML snippet for the body section, containing the precision plot.
        - css_snippets : set[str]
            CSS snippet for styling the precision plot.

    """
    try:
        plot_script, plot_div = precision_vs_resolution_plot(cif_text)
    except Exception as e:
        print(f"Error generating precision plot: {e}")
        return set(), "", set()

    body_snippet = render_to_string("category_components/data_precision_plot/body.html", {"plot_div": plot_div})
    css_snippet = CDN.render_css()

    return {CDN.render_js(), plot_script}, body_snippet, {css_snippet}
