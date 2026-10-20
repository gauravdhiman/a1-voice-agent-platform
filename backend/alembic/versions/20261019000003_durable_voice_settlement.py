"""Durable, atomic settlement for newly tracked voice calls only."""

from alembic import op

revision = "20261019000003"
down_revision = "20261019000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Preserve historical calls and atomically settle newly admitted sessions."""
    op.execute("""
        ALTER TABLE public.call_logs ADD COLUMN billing_status text NOT NULL DEFAULT
            'legacy';
        ALTER TABLE public.call_logs ADD CONSTRAINT ck_call_logs_billing_status
            CHECK (billing_status IN ('legacy','pending','settled'));
        CREATE INDEX ix_call_logs_pending_billing ON public.call_logs (ended_at)
            WHERE billing_status='pending' AND status IN ('completed','failed');
    """)
    # Serialize before the idempotency lookup. A pre-lock lookup lets two
    # concurrent retries both miss the ledger and debit the same call twice.
    op.execute("""
        CREATE OR REPLACE FUNCTION consume_voice_call_credits(
            p_organization_id uuid,
            p_credit_event_id uuid,
            p_credits_needed integer,
            p_call_log_id uuid,
            p_duration_seconds integer
        ) RETURNS jsonb
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_plan integer;
            v_admin integer;
            v_purchased integer;
            v_plan_available integer;
            v_admin_available integer;
            v_purchased_available integer;
            v_plan_used integer;
            v_admin_used integer;
            v_purchased_used integer;
            v_overdraft integer;
            v_plan_after integer;
            v_admin_after integer;
            v_purchased_after integer;
            v_balance_after integer;
            v_transaction_id uuid;
            v_existing_balance integer;
        BEGIN
            IF p_credits_needed IS NULL OR p_credits_needed <= 0 THEN
                RETURN jsonb_build_object('success', false, 'error',
                    'invalid_credits_needed');
            END IF;

            SELECT credit_balance, admin_credit_balance, purchased_credit_balance
            INTO v_plan, v_admin, v_purchased
            FROM organizations
            WHERE id = p_organization_id
            FOR UPDATE;
            IF NOT FOUND THEN
                RETURN jsonb_build_object('success', false, 'error',
                    'organization_not_found');
            END IF;

            SELECT id, balance_after
            INTO v_transaction_id, v_existing_balance
            FROM credit_transactions
            WHERE organization_id = p_organization_id
              AND source = 'event_consumption'
              AND metadata->>'call_log_id' = p_call_log_id::text
            ORDER BY created_at DESC
            LIMIT 1;
            IF v_transaction_id IS NOT NULL THEN
                RETURN jsonb_build_object(
                    'success', true,
                    'already_recorded', true,
                    'transaction_id', v_transaction_id,
                    'balance_after', v_existing_balance
                );
            END IF;


            v_plan := COALESCE(v_plan, 0);
            v_admin := COALESCE(v_admin, 0);
            v_purchased := COALESCE(v_purchased, 0);
            v_plan_available := GREATEST(v_plan, 0);
            v_admin_available := GREATEST(v_admin, 0);
            v_purchased_available := GREATEST(v_purchased, 0);

            v_plan_used := LEAST(v_plan_available, p_credits_needed);
            v_admin_used := LEAST(
                v_admin_available,
                p_credits_needed - v_plan_used
            );
            v_purchased_used := LEAST(
                v_purchased_available,
                p_credits_needed - v_plan_used - v_admin_used
            );
            v_overdraft := p_credits_needed
                - v_plan_used - v_admin_used - v_purchased_used;

            -- The active call is allowed to finish. Keep the debt in the
            -- expiring plan pool so the combined balance reflects the full
            -- charge while purchased/admin pools never become negative.
            v_plan_after := v_plan - v_plan_used - v_overdraft;
            v_admin_after := v_admin - v_admin_used;
            v_purchased_after := v_purchased - v_purchased_used;
            v_balance_after := v_plan_after + v_admin_after + v_purchased_after;

            UPDATE organizations
            SET credit_balance = v_plan_after,
                admin_credit_balance = v_admin_after,
                purchased_credit_balance = v_purchased_after,
                updated_at = NOW()
            WHERE id = p_organization_id;

            INSERT INTO credit_transactions (
                organization_id, transaction_type, amount, balance_after,
                source, source_id, credit_event_id, description, metadata
            ) VALUES (
                p_organization_id,
                'consumed',
                -p_credits_needed,
                v_balance_after,
                'event_consumption',
                p_credit_event_id,
                p_credit_event_id,
                'Voice call credit consumption',
                jsonb_build_object(
                    'call_log_id', p_call_log_id,
                    'duration_seconds', p_duration_seconds,
                    'plan_credits', v_plan_used,
                    'admin_credits', v_admin_used,
                    'purchased_credits', v_purchased_used,
                    'overdraft_credits', v_overdraft
                )
            )
            RETURNING id INTO v_transaction_id;

            INSERT INTO credit_notification_outbox (
                organization_id, credit_transaction_id, balance_after
            ) VALUES (
                p_organization_id, v_transaction_id, v_balance_after
            )
            ON CONFLICT (credit_transaction_id) DO NOTHING;

            RETURN jsonb_build_object(
                'success', true,
                'transaction_id', v_transaction_id,
                'balance_after', v_balance_after,
                'plan_used', v_plan_used,
                'admin_used', v_admin_used,
                'purchased_used', v_purchased_used,
                'overdraft_used', v_overdraft
            );
        END;
        $$;
        """)

    op.execute("""
        CREATE FUNCTION public.settle_voice_call(p_call_log_id uuid) RETURNS jsonb
        LANGUAGE plpgsql SET search_path = public, pg_temp AS $settle$
        DECLARE
            v_call public.call_logs%ROWTYPE;
            v_org uuid;
            v_event uuid;
            v_cost integer;
            v_credits integer;
            v_debit jsonb;
            v_transaction uuid;
            v_actual_credits integer;
        BEGIN
            SELECT organization_id INTO v_org FROM public.call_logs WHERE
                id=p_call_log_id;
            IF v_org IS NULL THEN
                RETURN jsonb_build_object('success',false,'error','call_not_found');
            END IF;
            -- Use the same org-first lock order as the debit RPC.
            PERFORM 1 FROM public.organizations WHERE id=v_org FOR UPDATE;
            SELECT * INTO v_call FROM public.call_logs WHERE id=p_call_log_id FOR
                UPDATE;
            IF NOT FOUND THEN
                RETURN jsonb_build_object('success',false,'error','call_not_found');
            END IF;
            IF v_call.billing_status <> 'pending' THEN
                RETURN jsonb_build_object('success',true,'already_settled',true);
            END IF;
            IF v_call.status NOT IN ('completed','failed') OR v_call.ended_at IS NULL
                THEN
                RETURN jsonb_build_object('success',false,'error','call_not_final');
            END IF;
            IF EXISTS (SELECT 1 FROM public.voice_agents WHERE id=v_call.agent_id AND
                is_demo) THEN
                UPDATE public.call_logs SET billing_status='settled',credits_consumed=0
                    WHERE id=p_call_log_id;
                RETURN jsonb_build_object('success',true,'exempt',true);
            END IF;
            SELECT id,credit_cost INTO v_event,v_cost FROM public.credit_events
                WHERE name='voice_call_minute' AND is_active LIMIT 1;
            IF v_event IS NULL OR v_cost IS NULL OR v_cost < 0 THEN
                RETURN
                    jsonb_build_object('success',false,'error','voice_rate_unavailable');
            END IF;
            v_credits :=
                greatest(1,ceil(greatest(coalesce(v_call.duration,0),0)::numeric/60)::integer)*v_cost;
            IF v_credits=0 THEN
                UPDATE public.call_logs SET billing_status='settled',credits_consumed=0
                    WHERE id=p_call_log_id;
                RETURN jsonb_build_object('success',true,'credits',0);
            END IF;
            v_debit :=
                public.consume_voice_call_credits(v_org,v_event,v_credits,p_call_log_id,v_call.duration);
            IF NOT coalesce((v_debit->>'success')::boolean,false) THEN RETURN
                v_debit; END IF;
            v_transaction := (v_debit->>'transaction_id')::uuid;
            -- Retries attach the original ledger amount even if pricing changed.
            SELECT -amount INTO v_actual_credits FROM public.credit_transactions
                WHERE id=v_transaction AND organization_id=v_org
                  AND metadata->>'call_log_id'=p_call_log_id::text;
            IF v_actual_credits IS NULL THEN RAISE EXCEPTION
                'voice_settlement_ledger_missing'; END IF;
            UPDATE public.call_logs SET
                billing_status='settled',credits_consumed=v_actual_credits,
                credit_transaction_id=v_transaction WHERE id=p_call_log_id;
            RETURN
                jsonb_build_object('success',true,'transaction_id',v_transaction,'credits',v_actual_credits);
        END $settle$;
        REVOKE ALL ON FUNCTION public.settle_voice_call(uuid) FROM
            PUBLIC,anon,authenticated;
        GRANT EXECUTE ON FUNCTION public.settle_voice_call(uuid) TO service_role;
        REVOKE ALL ON FUNCTION
            public.consume_voice_call_credits(uuid,uuid,integer,uuid,integer)
            FROM PUBLIC,anon,authenticated;
        GRANT EXECUTE ON FUNCTION
            public.consume_voice_call_credits(uuid,uuid,integer,uuid,integer)
            TO service_role;
    """)


def downgrade() -> None:
    """Do not discard queued financial work or restore the debit race."""
    raise RuntimeError("Voice settlement requires a reviewed forward repair")
