import json
import logging
from typing import Dict, Tuple

import httpx
import yaml
from bs4 import BeautifulSoup
from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)


async def fetch_spec(url: str) -> Dict:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(url, timeout=15.0)
            response.raise_for_status()

            try:
                data = response.json()
            except json.JSONDecodeError:
                try:
                    data = yaml.safe_load(response.text)
                except yaml.YAMLError:
                    logger.error(
                        "❌ Error while fetching spec: URL content is not valid JSON or YAML."
                    )
                    raise ValueError("URL content is not valid JSON or YAML.")

            if not ("openapi" in data or "swagger" in data):
                logger.error(
                    "❌ Error while fetching spec: JSON found, but it's not an OpenAPI spec (missing 'openapi' or 'swagger' key)."
                )
                raise ValueError(
                    "JSON found, but it's not an OpenAPI spec (missing 'openapi' or 'swagger' key)."
                )

            logger.info("✅ Fetched the swagger spec successfully!")
            console.print("[green]✅ Fetched the swagger spec successfully![/green]")
            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to fetch Spec: HTTP {e.response.status_code}")
            raise ValueError(f"Failed to fetch Spec: HTTP {e.response.status_code}")
        except Exception as e:
            logger.error(f"Ingestion Error: {str(e)}")
            raise ValueError(f"Ingestion Error: {str(e)}")


async def fetch_docs_text(url: str) -> str:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()

            text = soup.get_text(separator="\n")

            clean_text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])

            logger.info("✅ Fetched the docs via spec successfully!")
            console.print("[green]✅ Fetched the docs successfully![/green]")

            # NOTE: Only taking the first 20k characters. Will optimize this part later
            # Also, this is not the priority, docs are secondary for now.
            return clean_text[:20000]

        except Exception as e:
            logger.error(f"❌ Error while fetching docs text: {str(e)}")
            return ""


async def ingest_resource(url: str) -> Tuple[Dict, str]:
    spec_data = await fetch_spec(url)

    docs_text = ""
    if "externalDocs" in spec_data:
        doc_url = spec_data["externalDocs"].get("url")
        if doc_url:
            docs_text = await fetch_docs_text(doc_url)

    return spec_data, docs_text
