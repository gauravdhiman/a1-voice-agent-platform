"""Expand the approved credit product catalog to four discounted tiers.

Revision ID: 20261007000001
Revises: 20261002000001
Create Date: 2026-10-07
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20261007000001"
down_revision: Union[str, Sequence[str], None] = "20261002000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CURRENT_PACKS = ((200, 500), (500, 1200), (1000, 2300), (2000, 4400))
_PREVIOUS_PACKS = ((200, 500), (400, 1000), (1000, 2500))


def _credit_catalog_sync_function(
    packs: tuple[tuple[int, int], ...],
) -> str:
    """Build the catalog RPC with a fixed, migration-owned approved pack set."""
    amounts = ", ".join(str(amount) for amount, _ in packs)
    price_pairs = ", ".join(f"({amount}, {price})" for amount, price in packs)

    return f"""
        CREATE OR REPLACE FUNCTION sync_credit_product_catalog(p_products jsonb)
        RETURNS integer
        LANGUAGE plpgsql
        SET search_path = public, pg_temp
        AS $$
        DECLARE
            product_count integer;
            credit_amounts integer[];
            item record;
        BEGIN
            IF p_products IS NULL OR jsonb_typeof(p_products) <> 'array' THEN
                RAISE EXCEPTION 'credit catalog must be a JSON array';
            END IF;

            product_count := jsonb_array_length(p_products);
            IF product_count <> {len(packs)} THEN
                RAISE EXCEPTION
                    'credit catalog must contain exactly {len(packs)} packs';
            END IF;

            SELECT array_agg(p.credit_amount ORDER BY p.credit_amount)
              INTO credit_amounts
              FROM jsonb_to_recordset(p_products) AS p(
                  name text,
                  description text,
                  stripe_price_id text,
                  stripe_product_id text,
                  credit_amount integer,
                  price_amount integer,
                  currency text
              );

            IF credit_amounts IS DISTINCT FROM ARRAY[{amounts}] THEN
                RAISE EXCEPTION
                    'credit catalog pack amounts do not match the approved catalog';
            END IF;

            IF EXISTS (
                SELECT 1
                  FROM jsonb_to_recordset(p_products) AS p(
                      name text,
                      description text,
                      stripe_price_id text,
                      stripe_product_id text,
                      credit_amount integer,
                      price_amount integer,
                      currency text
                  )
                 WHERE p.name IS NULL OR p.name = '' OR length(p.name) > 100
                    OR p.stripe_price_id IS NULL OR p.stripe_price_id = ''
                    OR length(p.stripe_price_id) > 255
                    OR p.stripe_product_id IS NULL OR p.stripe_product_id = ''
                    OR length(p.stripe_product_id) > 255
                    OR p.price_amount IS NULL
                    OR p.currency IS NULL
                    OR upper(p.currency) <> 'USD'
                    OR (p.credit_amount, p.price_amount) NOT IN ({price_pairs})
            ) THEN
                RAISE EXCEPTION 'credit catalog contains invalid pack details';
            END IF;

            IF (SELECT count(DISTINCT p.name)
                  FROM jsonb_to_recordset(p_products) AS p(
                      name text, stripe_price_id text, stripe_product_id text
                  )) <> product_count
               OR (SELECT count(DISTINCT p.stripe_price_id)
                     FROM jsonb_to_recordset(p_products) AS p(
                         name text, stripe_price_id text, stripe_product_id text
                     )) <> product_count
               OR (SELECT count(DISTINCT p.stripe_product_id)
                     FROM jsonb_to_recordset(p_products) AS p(
                         name text, stripe_price_id text, stripe_product_id text
                     )) <> product_count THEN
                RAISE EXCEPTION 'credit catalog contains duplicate identifiers';
            END IF;

            -- Serialize independent CLI syncs; any error below rolls back both
            -- the active-set switch and every upsert as one Postgres transaction.
            PERFORM pg_advisory_xact_lock(247001, 1);

            UPDATE credit_products
               SET is_active = false,
                   updated_at = now()
             WHERE is_active = true;

            FOR item IN
                SELECT p.*
                  FROM jsonb_to_recordset(p_products) AS p(
                      name text,
                      description text,
                      stripe_price_id text,
                      stripe_product_id text,
                      credit_amount integer,
                      price_amount integer,
                      currency text
                  )
            LOOP
                INSERT INTO credit_products (
                    name,
                    description,
                    stripe_price_id,
                    stripe_product_id,
                    credit_amount,
                    price_amount,
                    currency,
                    is_active,
                    updated_at
                ) VALUES (
                    item.name,
                    item.description,
                    item.stripe_price_id,
                    item.stripe_product_id,
                    item.credit_amount,
                    item.price_amount,
                    upper(item.currency),
                    true,
                    now()
                )
                ON CONFLICT (name) DO UPDATE SET
                    description = EXCLUDED.description,
                    stripe_price_id = EXCLUDED.stripe_price_id,
                    stripe_product_id = EXCLUDED.stripe_product_id,
                    credit_amount = EXCLUDED.credit_amount,
                    price_amount = EXCLUDED.price_amount,
                    currency = EXCLUDED.currency,
                    is_active = true,
                    updated_at = now();
            END LOOP;

            RETURN product_count;
        END;
        $$;

        REVOKE ALL ON FUNCTION sync_credit_product_catalog(jsonb) FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION sync_credit_product_catalog(jsonb) TO service_role;
    """


def upgrade() -> None:
    """Allow an atomic sync of the four approved, volume-priced packs."""
    op.execute(_credit_catalog_sync_function(_CURRENT_PACKS))


def downgrade() -> None:
    """Restore the previous three-pack synchronization contract."""
    op.execute(_credit_catalog_sync_function(_PREVIOUS_PACKS))
