import os
import urllib.parse
import httpx
from dotenv import load_dotenv

load_dotenv()


async def fetch_projects_from_sanity() -> list:

    project_id = os.getenv("SANITY_PROJECT_ID")
    dataset = os.getenv("SANITY_DATASET")
    api_version = "2026-02-23"

    query = (
        '*[_type == "project"]{title, category, year, location, concept, description}'
    )
    encoded_query = urllib.parse.quote(query)

    url = f"https://{project_id}.api.sanity.io/v{api_version}/data/query/{dataset}?query={encoded_query}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()

            data = response.json()
            projects = data.get("result", [])
            print(f"[Sanity Service] ✅ Успешно загружено проектов: {len(projects)}")
            return projects

        except httpx.HTTPError as e:
            print(f"[Sanity Service] ❌ Ошибка при запросе к Sanity: {e}")
            return []
