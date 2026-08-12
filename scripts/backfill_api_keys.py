"""One-off backfill: mint an API key for every Tenant that predates
ApiKey - i.e. every Tenant with zero rows in api_keys - so companies
created before this feature shipped can still authenticate.

Not run automatically, and safe to re-run (tenants that already have a
key are skipped). Run once after applying the api_keys migration:

    uv run python scripts/backfill_api_keys.py

Prints each affected tenant's id, its business id(s)/name(s), and the
raw key - copy it into the panel (paste it into the "no API key stored"
box for that company) since it is never retrievable again once this
script exits.
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app.config.settings import get_settings
from backend.app.infrastructure.auth.postgres import PostgresApiKeyRepository
from backend.app.models.api_key import ApiKeyModel
from backend.app.models.business import Business
from backend.app.models.tenant import Tenant


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_factory() as session:
        keyed_tenant_ids = {
            row[0] for row in (await session.execute(select(ApiKeyModel.tenant_id))).all()
        }

        businesses_by_tenant: dict = {}
        for business in (await session.execute(select(Business))).scalars():
            businesses_by_tenant.setdefault(business.tenant_id, []).append(business)

        repository = PostgresApiKeyRepository(session)
        minted = 0

        for tenant in (await session.execute(select(Tenant))).scalars():
            if tenant.id in keyed_tenant_ids:
                continue

            _, raw_key = await repository.create(tenant_id=str(tenant.id))
            minted += 1

            businesses = businesses_by_tenant.get(tenant.id, [])
            if not businesses:
                print(f"tenant_id={tenant.id}  name={tenant.name!r}  api_key={raw_key}")
            for business in businesses:
                print(
                    f"tenant_id={tenant.id}  business_id={business.id}  "
                    f"name={business.name!r}  api_key={raw_key}"
                )

        await session.commit()

    print(f"Minted {minted} new API key(s).")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
