import json
from typing import Literal

import httpx
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential

# This module communicates with the API server defined in app/core/model_server.py,
# which uses app/rag/colbert_service.py to provide embedding endpoints.
# The API server needs to be running at localhost:8005 for these functions to work.


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def get_embeddings_from_httpx(
    data: list, endpoint: Literal["embed_text", "embed_image"]
):

    async with httpx.AsyncClient() as client:
        try:
            if "text" in endpoint:
                response = await client.post(
                    f"http://localhost:8005/{endpoint}",
                    json={"queries": data},
                    timeout=120.0,  # Adjust timeout based on file size
                )
            else:
                response = await client.post(
                    f"http://localhost:8005/{endpoint}",
                    files=data,
                    timeout=120.0,  # Adjust timeout based on file size
                )
            response.raise_for_status()
            return np.array(response.json()["embeddings"])
        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP request failed: {e}")
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse JSON response: {e}")
