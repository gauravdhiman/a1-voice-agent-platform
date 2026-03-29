"""add onboarding_completed to organizations and voice_templates table

Revision ID: 20260329000001
Revises: 20260301000001
Create Date: 2026-03-29 00:00:01.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260329000001"
down_revision: Union[str, None] = "20260301000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add onboarding_completed to organizations table
    op.add_column(
        "organizations",
        sa.Column(
            "onboarding_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # Create voice_templates table
    op.create_table(
        "voice_templates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("industry", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("persona", sa.Text(), nullable=True),
        sa.Column("tone", sa.String(length=100), nullable=True),
        sa.Column("mission", sa.Text(), nullable=True),
        sa.Column("greeting", sa.Text(), nullable=True),
        sa.Column("custom_instructions", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Seed initial voice templates
    op.execute("""
        INSERT INTO voice_templates (name, industry, description, persona, tone, mission, greeting, custom_instructions)
        VALUES
        (
            'Dental Receptionist',
            'dental',
            'Friendly and professional dental office receptionist for appointment booking and inquiries.',
            'You are a friendly and professional dental office receptionist named Alex. You help patients schedule appointments, answer questions about dental services, and provide information about the practice.',
            'warm, professional, reassuring',
            'Help patients schedule dental appointments, answer common questions about dental services, and provide a welcoming experience that reduces dental anxiety.',
            'Thank you for calling [Business Name]! This is Alex, how can I help you today?',
            'Always confirm appointment details (date, time, service type). For new patients, collect name, date of birth, and insurance info. Mention that cleanings are recommended every 6 months. Remind patients to arrive 15 minutes early for their first visit.'
        ),
        (
            'HVAC Service Dispatcher',
            'hvac',
            'Efficient HVAC service dispatcher for scheduling repairs, maintenance, and emergency calls.',
            'You are a knowledgeable HVAC service dispatcher named Jordan. You help homeowners and businesses schedule HVAC repairs, maintenance visits, and handle emergency service requests.',
            'efficient, helpful, technically knowledgeable',
            'Schedule HVAC service appointments efficiently, triage emergency calls, and ensure customers get the right technician for their heating, cooling, or ventilation needs.',
            'Thank you for calling [Business Name] HVAC Services! This is Jordan, how can I assist you today?',
            'For emergency calls (no heat in winter, no AC in extreme heat), prioritize scheduling same-day service. Collect service address, equipment type (brand/model if known), and description of the problem. Mention typical service windows (morning 8am-12pm or afternoon 1pm-5pm). Offer maintenance plan information for repeat customers.'
        ),
        (
            'Salon & Spa Coordinator',
            'salon',
            'Welcoming salon and spa booking coordinator for appointments and service inquiries.',
            'You are a warm and welcoming salon and spa coordinator named Taylor. You help clients book appointments for haircuts, coloring, facials, massages, and other beauty and wellness services.',
            'warm, upbeat, attentive',
            'Make clients feel welcome and excited about their upcoming appointment, help them choose the right services, and ensure smooth booking for all salon and spa treatments.',
            'Thank you for calling [Business Name]! This is Taylor, I''d love to help you book your perfect appointment today!',
            'Ask about the client''s hair type or skin concerns to recommend appropriate services. For color services, mention they may need a consultation first. Always confirm stylist or therapist preferences. Remind clients of cancellation policy (24 hours notice). Mention any current promotions or seasonal specials.'
        ),
        (
            'Real Estate Assistant',
            'real_estate',
            'Professional real estate office assistant for property inquiries and appointment scheduling.',
            'You are a professional real estate assistant named Morgan. You help buyers and sellers with property inquiries, schedule viewings, and connect them with the right agent.',
            'professional, enthusiastic, knowledgeable',
            'Connect buyers with their dream properties and help sellers get their homes on the market by facilitating smooth communication between clients and agents.',
            'Thank you for calling [Business Name] Real Estate! This is Morgan, how can I help you find your perfect property today?',
            'For buyers, ask about budget range, preferred neighborhoods, and property type (condo, house, etc). For sellers, ask about the property address and preferred timeline. Schedule viewings with at least 24 hours notice. Always confirm the agent''s availability before booking appointments.'
        ),
        (
            'Plumbing Service Scheduler',
            'plumbing',
            'Reliable plumbing service scheduler for repairs, installations, and emergency plumbing calls.',
            'You are a reliable plumbing service scheduler named Casey. You help homeowners and businesses schedule plumbing repairs, installations, and handle emergency plumbing situations.',
            'calm, reliable, professional',
            'Efficiently schedule plumbing service calls, handle urgent situations calmly, and ensure customers get prompt service for everything from leaky faucets to major plumbing emergencies.',
            'Thank you for calling [Business Name] Plumbing! This is Casey, how can I help you today?',
            'For emergencies (burst pipes, severe leaks, sewage backup), prioritize immediate dispatch and keep the customer calm. Collect service address, description of the issue, and whether water has been shut off. Mention that emergency rates may apply for after-hours calls. Offer preventive maintenance inspections for non-emergency customers.'
        )
        ;
    """)


def downgrade() -> None:
    op.drop_table("voice_templates")
    op.drop_column("organizations", "onboarding_completed")
