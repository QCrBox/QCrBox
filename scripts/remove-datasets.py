"""Remove all datasets from the QCrBox registry.
"""

import requests
from loguru import logger

base_url = "http://127.0.0.1:11000/api"
datasets = requests.get(f"{base_url}/datasets").json()["payload"]["datasets"]
logger.info("Datasets before deletion:", datasets)

dataset_ids = [dataset["dataset_id"] for dataset in datasets]
for dataset_id in dataset_ids:
    requests.delete(f"{base_url}/datasets/delete/{dataset_id}")

datasets = requests.get(f"{base_url}/datasets").json()
logger.info(f"Datasets after delection: {datasets}")
