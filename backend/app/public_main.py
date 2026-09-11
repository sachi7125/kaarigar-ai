"""The buyer-facing app — what the Vercel deployment runs (Day 7).

Only what a buyer who scanned a stall QR can reach: the storefront and listing
pages, listing photos, unsubscribe, and three buyer actions (make an offer,
follow a maker, report an issue). None of the artisan side is here: no
offers inbox, no accepting (which returns the buyer's contact), no earnings,
no publishing, no speech or pricing. Those run only on the demo Mac
(app/main.py), which writes to the same database in online mode
(scripts/run_server.sh online).

The Mac server also owns the schema: it creates and extends the tables at
startup. This app never runs DDL, so concurrent serverless cold starts can't
race each other on CREATE/ALTER TABLE.

Nothing imported here may pull in the ML stack — backend/tests/test_public_app.py
checks that.
"""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fastapi import APIRouter, FastAPI

from app.api import offers, storefront
from app.web.media import router as media_router
from app.web.storefront_page import router as pages_router

app = FastAPI(title="KaarigarAI storefront", docs_url=None, redoc_url=None, openapi_url=None)

buyer_api = APIRouter()
buyer_api.add_api_route("/offers", offers.submit_offer, methods=["POST"])
buyer_api.add_api_route("/issues", offers.report_issue, methods=["POST"])
buyer_api.add_api_route("/storefront/follow", storefront.follow_artisan, methods=["POST"])

app.include_router(buyer_api, prefix="/api")
app.include_router(pages_router)
app.include_router(media_router)
