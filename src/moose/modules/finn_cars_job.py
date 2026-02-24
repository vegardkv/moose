import logging
import os

from dotenv import load_dotenv
from finnbruktbil import db, aux_data_parser
from finnbruktbil.cli.config import DownloadConfig, FetchIdsConfig
from finnbruktbil.cli.download_data import download_ads
from finnbruktbil.cli.fetch_ids import fetch_ids_into_db

from moose.job import Job

_FETCH_CONFIG = """
{
   "base_url": "https://www.finn.no/mobility/search/car?model=1.777.2000638&registration_class=1",
   "limit": 150,
   "max_pages": 10,
   "fetched_by": "filtered-ev9",
   "headless": true
}
"""

_DOWNLOAD_CONFIG = """
{
   "limit": 300,
   "stale_hours": null,
   "random_order": false,
   "headless": true,
   "parse_aux_data": true
}
"""


logger = logging.getLogger(__name__)


class FinnCarsJob(Job):
    def __init__(self):
        load_dotenv()
        db.SUPABASE_KEY = os.getenv("FINN_SUPABASE_KEY", db.SUPABASE_KEY)
        db.SUPABASE_URL = os.getenv("FINN_SUPABASE_URL", db.SUPABASE_URL)
        aux_data_parser.OPENAI_API_KEY = os.getenv("FINN_OPENAI_API_KEY", aux_data_parser.OPENAI_API_KEY)

    @property
    def name(self) -> str:
        return "finn_cars"

    @property
    def timeout(self) -> int:
        # This job can take a while if there are many ads to download
        return 600

    async def run(self) -> None:
        """Fetch and download car listings from Finn.no."""

        logger.info("[FinnCarsJob] Fetching car IDs from Finn.no...")
        fetch_cfg = FetchIdsConfig.model_validate_json(_FETCH_CONFIG)
        fetch_ids_into_db(fetch_cfg)

        logger.info("[FinnCarsJob] Downloading car data from Finn.no...")
        download_cfg = DownloadConfig.model_validate_json(_DOWNLOAD_CONFIG)
        download_ads(download_cfg)
        logger.info("[FinnCarsJob] Completed successfully!")


if __name__ == "__main__":
    job = FinnCarsJob()
    import asyncio

    asyncio.run(job.run())
