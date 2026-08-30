"""KaarigarAI backend — FastAPI entrypoint (stateless).

Serves the JSON API for the mobile app AND renders the public storefront and
listing pages. AI work is dispatched to workers behind a job queue, never inline.
Roadmap: Day 5 (onboarding, listing page, offers), Day 6 (storefront).
"""
# TODO(day5): create FastAPI app, mount api routers and web (storefront/listing) routes.

