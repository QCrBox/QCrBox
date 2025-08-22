import os
import sys
from pathlib import Path

import svcs
from django.conf import settings
from django.core.management import execute_from_command_line
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import path
from quality_html import (
    basic_model_quality_indicators,
    fobs_div_fcalc,
    ortep_cifvis_3d,
    precision_plot,
    precision_quality_indicators,
)

from pyqcrbox.data_management.data_manager import DataManager
from pyqcrbox.services import QCRBOX_GLOBAL_SERVICES_REGISTRY

BASE_DIR = Path(__file__).resolve().parent

settings.configure(
    DEBUG=os.getenv("DEBUG", "False").lower() == "true",
    SECRET_KEY=os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production"),
    ALLOWED_HOSTS=os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,demo1.qcrbox.org").split(","),
    # Security settings
    SECURE_BROWSER_XSS_FILTER=True,
    SECURE_CONTENT_TYPE_NOSNIFF=True,
    X_FRAME_OPTIONS="DENY",
    # Middleware
    MIDDLEWARE=[
        "django.middleware.security.SecurityMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
        "django.middleware.common.CommonMiddleware",
    ],
    ROOT_URLCONF=sys.modules[__name__],
    TEMPLATES=[
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [BASE_DIR / "templates"],
            "APP_DIRS": True,
            "OPTIONS": {
                "context_processors": [
                    "django.template.context_processors.debug",
                    "django.template.context_processors.request",
                ],
            },
        },
    ],
    # Logging
    LOGGING={
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
            },
        },
        "root": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
)


async def retrieve_data(dataset_id):
    """Retrieve data for a given dataset ID."""
    async with svcs.Container(QCRBOX_GLOBAL_SERVICES_REGISTRY) as container:
        data_manager = await container.aget(DataManager)
        dataset_info = await data_manager.get_dataset(dataset_id)
        data_file_id = dataset_info.first_data_file.qcrbox_file_id
        try:
            data = await data_manager.get_data_file_contents(data_file_id)
            return data.decode("utf-8")
        except Exception as e:
            dataset_objs = await data_manager.get_datasets()
            datasets = [d.dataset_id for d in dataset_objs]
            if dataset_id not in datasets:
                return f"Dataset ID '{dataset_id}' not found. Available datasets: {', '.join(datasets)}"

            return str(e)


def index(request):
    return HttpResponse("<h1>A minimal Django response!</h1>")


def retrieve(request, dataset_id):
    """Retrieve data for a given dataset ID."""
    import asyncio

    cif_text = asyncio.run(retrieve_data(dataset_id))

    generator_functions = [
        basic_model_quality_indicators,
        ortep_cifvis_3d,
        fobs_div_fcalc,
        precision_quality_indicators,
        precision_plot,
    ]

    results = [function(cif_text) for function in generator_functions]
    header_snippets, body_snippets, css_snippets = zip(*results, strict=False)
    header_snippet = "\n".join(set.union(*header_snippets))
    body_snippet = "\n".join(body_snippets)
    css_snippet = "\n".join(set.union(*css_snippets))

    title = f"Dataset {dataset_id} Quality Indicators"

    response = render(
        request,
        "dataset_view.html",
        {
            "title": title,
            "header_html": header_snippet,
            "body_html": body_snippet,
            "component_style": css_snippet,
        },
    )

    return response


urlpatterns = [
    path(r"", index),
    path(r"retrieve/<str:dataset_id>/", retrieve, name="retrieve_data"),
]

if __name__ == "__main__":
    execute_from_command_line(sys.argv)
