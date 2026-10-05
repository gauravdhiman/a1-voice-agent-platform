"""Apply approved credit-pack catalog updates atomically.

Revision ID: 20261001000005
Revises: 20261001000004
Create Date: 2026-10-01
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20261001000005"
down_revision: Union[str, Sequence[str], None] = "20261001000004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add a single-transaction credit product catalog reconciliation RPC."""
    op.execute(
        """
        CREATE FUNCTION sync_credit_product_catalog(p_products jsonb)
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
            IF product_count <> 3 THEN
                RAISE EXCEPTION 'credit catalog must contain exactly three packs';
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

            IF credit_amounts IS DISTINCT FROM ARRAY[200, 400, 1000] THEN
                RAISE EXCEPTION 'credit catalog pack amounts do not match the approved catalog';
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
                    OR (p.credit_amount, p.price_amount) NOT IN
                        ((200, 500), (400, 1000), (1000, 2500))
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
    )


def downgrade() -> None:
    """Remove the internal catalog reconciliation RPC."""
    op.execute("DROP FUNCTION sync_credit_product_catalog(jsonb)")
