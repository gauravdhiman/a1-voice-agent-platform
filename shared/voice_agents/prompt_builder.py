"""
Prompt builder service for constructing detailed system prompts for AI agents.
"""

from typing import Optional
from shared.organization.models import Organization
from shared.voice_agents.models import VoiceAgent


class PromptBuilder:
    """Service for building system prompts from organization and agent details."""

    @staticmethod
    def build_system_prompt(
        org: Organization, 
        agent: VoiceAgent, 
        default_rules: Optional[str] = None
    ) -> str:
        """
        Builds a comprehensive system prompt by aggregating information from 
        the organization and the agent.
        """
        sections = []

        # 1. Identity & Persona
        role = agent.persona or "a helpful AI voice assistant"
        identity_text = f"You are {role}"
        if org.name:
            identity_text += f" representing {org.name}"
        
        if agent.tone:
            identity_text += f". Your communication style is {agent.tone}."
        
        sections.append(f"# IDENTITY AND PERSONA\n{identity_text}")

        # 2. Your Mission
        if agent.mission:
            sections.append(f"# YOUR MISSION\n{agent.mission}")

        # 3. Business Context
        business_info = []
        if org.industry:
            business_info.append(f"Industry: {org.industry}")

        if org.location:
            business_info.append(f"Location/Address: {org.location}")

        if org.business_details:
            business_info.append(f"Business Context:\n{org.business_details}")

        if business_info:
            sections.append("# BUSINESS CONTEXT\n" + "\n".join(business_info))

        # 4. Specific Instructions
        if agent.custom_instructions:
            sections.append(f"# ADDITIONAL INSTRUCTIONS\n{agent.custom_instructions}")

        # 5. Output Rules & Guardrails (Default rules)
        if default_rules:
            sections.append(default_rules)

        return "\n\n".join(sections)
