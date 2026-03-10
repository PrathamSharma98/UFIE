"""AI Copilot service for UFIE - integrates ChatGPT and Gemini."""

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class AICopilot:
    """AI assistant that answers flood-related queries using LLM APIs or built-in intelligence."""

    def __init__(self, openai_key: Optional[str] = None, gemini_key: Optional[str] = None):
        self.openai_key = openai_key or os.getenv("OPENAI_API_KEY")
        self.gemini_key = gemini_key or os.getenv("GEMINI_API_KEY")
        self._openai_client = None
        self._gemini_model = None

    def _get_openai_client(self):
        if not self._openai_client and self.openai_key:
            try:
                import openai
                self._openai_client = openai.OpenAI(api_key=self.openai_key)
            except ImportError:
                logger.warning("openai package not installed")
        return self._openai_client

    def _get_gemini_model(self):
        if not self._gemini_model and self.gemini_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_key)
                self._gemini_model = genai.GenerativeModel("gemini-pro")
            except ImportError:
                logger.warning("google-generativeai package not installed")
        return self._gemini_model

    async def query_chatgpt(self, query: str, context: str = "") -> dict:
        """Query ChatGPT for flood analysis and reasoning."""
        client = self._get_openai_client()
        system_prompt = self._build_system_prompt("analysis", context)

        if client:
            try:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query}
                    ],
                    max_tokens=1500,
                    temperature=0.3,
                )
                return {
                    "response": response.choices[0].message.content,
                    "source": "ChatGPT",
                    "model": "gpt-4",
                }
            except Exception as e:
                logger.error(f"ChatGPT API error: {e}")

        # Fallback to built-in intelligence
        return self._builtin_analysis(query, context)

    async def query_gemini(self, query: str, context: str = "") -> dict:
        """Query Gemini for policy and planning insights."""
        model = self._get_gemini_model()
        prompt = self._build_system_prompt("policy", context) + "\n\nUser Query: " + query

        if model:
            try:
                response = model.generate_content(prompt)
                return {
                    "response": response.text,
                    "source": "Gemini",
                    "model": "gemini-pro",
                }
            except Exception as e:
                logger.error(f"Gemini API error: {e}")

        # Fallback
        return self._builtin_policy(query, context)

    async def query(self, query: str, context: str = "") -> dict:
        """Smart routing - pick the best AI for the query."""
        query_lower = query.lower()

        # Route policy/planning questions to Gemini, analysis to ChatGPT
        policy_keywords = [
            "policy", "plan", "recommend", "suggest", "improve",
            "infrastructure", "budget", "report", "preparedness", "strategy",
        ]
        is_policy = any(kw in query_lower for kw in policy_keywords)

        if is_policy:
            result = await self.query_gemini(query, context)
        else:
            result = await self.query_chatgpt(query, context)

        suggestions = self._generate_follow_up_suggestions(query, result.get("response", ""))

        return {
            "query": query,
            "response": result["response"],
            "sources": [result.get("source", "Built-in AI")],
            "suggestions": suggestions,
        }

    def _build_system_prompt(self, mode: str, context: str) -> str:
        base = (
            "You are an AI assistant for the Urban Flood Intelligence Engine (UFIE), "
            "a platform that analyzes urban flood risks in Delhi, India. You have expertise in:\n"
            "- Urban hydrology and flood management\n"
            "- GIS and spatial analysis\n"
            "- Drainage infrastructure assessment\n"
            "- Climate resilience planning\n"
            "- Pre-monsoon preparedness\n\n"
            "The city has 30 wards with varying flood risk levels. The system tracks 2700+ flood micro-hotspots,\n"
            "drainage networks, pump stations, and calculates Pre-Monsoon Readiness Scores (0-100)."
        )

        if mode == "analysis":
            base += "\n\nFocus on technical analysis, data interpretation, and specific flood risk assessments."
        elif mode == "policy":
            base += "\n\nFocus on policy recommendations, infrastructure planning, budget priorities, and preparedness strategies."

        if context:
            base += f"\n\nCurrent context data:\n{context}"

        return base

    def _builtin_analysis(self, query: str, context: str) -> dict:
        """Built-in rule-based analysis when no API keys are available."""
        query_lower = query.lower()
        response_parts = []

        if "flood" in query_lower and ("ward" in query_lower or "which" in query_lower):
            response_parts.append(
                "Based on the Pre-Monsoon Readiness analysis, the wards most vulnerable to flooding are those "
                "with readiness scores below 30 (Critical Risk category). Key factors include:\n\n"
                "1. **High impervious surface coverage** (>75%) reduces natural water absorption\n"
                "2. **Insufficient drainage capacity** relative to catchment area\n"
                "3. **Low pump station availability** or non-functional equipment\n"
                "4. **Historical flood frequency** - wards with >15 events in the past decade\n\n"
                "Wards near the Yamuna floodplain and low-elevation areas (below 210m) face the highest risk."
            )

        elif "rainfall" in query_lower or "rain" in query_lower:
            response_parts.append(
                "Delhi's flood risk escalates significantly with rainfall intensity:\n\n"
                "- **20 mm/hr**: Low risk, standard drainage handles most areas\n"
                "- **50 mm/hr**: Moderate risk, 30-40% of hotspots activate, low-lying wards affected\n"
                "- **80 mm/hr**: High risk, 60-70% hotspot activation, widespread waterlogging\n"
                "- **100+ mm/hr**: Critical, most drainage overwhelmed, major flooding in vulnerable wards\n\n"
                "The 2023 monsoon recorded peak intensities of ~110 mm/hr, causing severe flooding in "
                "Chandni Chowk, Sadar Bazaar, and Seelampur areas."
            )

        elif "infrastructure" in query_lower or "upgrade" in query_lower or "improve" in query_lower:
            response_parts.append(
                "Key infrastructure improvements to reduce flood risk:\n\n"
                "1. **Drain capacity upgrades**: Replace undersized drains (300mm) with 900mm+ RCC pipes "
                "in critical wards\n"
                "2. **Pump station installation**: Add pump stations in wards with zero coverage, "
                "ensure diesel backup for all existing stations\n"
                "3. **Stormwater harvesting**: Install recharge pits in high-impervious-surface areas "
                "to reduce runoff by 15-25%\n"
                "4. **Green infrastructure**: Increase permeable surfaces through rain gardens and "
                "bio-swales in commercial districts\n"
                "5. **Real-time monitoring**: Deploy water level sensors at 50+ critical locations "
                "for early warning"
            )

        elif "readiness" in query_lower or "score" in query_lower or "prepared" in query_lower:
            response_parts.append(
                "The Pre-Monsoon Readiness Score evaluates each ward on a 0-100 scale across five dimensions:\n\n"
                "1. **Drainage Capacity Index** (0-25): Measures drain network adequacy\n"
                "2. **Emergency Infrastructure** (0-20): Shelter availability per capita\n"
                "3. **Flood Hotspot Density** (0-25): Inversely scored - fewer hotspots = higher score\n"
                "4. **Rainfall Vulnerability** (0-15): Terrain and surface characteristics\n"
                "5. **Pump Station Availability** (0-15): Operational pump coverage\n\n"
                "Categories: Critical Risk (0-30), Moderate Risk (31-60), Prepared (61-80), Resilient (81-100)"
            )

        elif "hotspot" in query_lower:
            response_parts.append(
                "The system identifies 2700+ flood micro-hotspots using multi-factor GIS analysis:\n\n"
                "- **Elevation analysis**: Low-lying areas accumulate more runoff\n"
                "- **Flow accumulation**: Points where water converges from multiple directions\n"
                "- **Drainage proximity**: Areas far from functional drainage channels\n"
                "- **Impervious surfaces**: High concrete/asphalt coverage increases flood risk\n"
                "- **Historical data**: Locations with repeated flood occurrences\n\n"
                "Hotspots are classified as Critical (>70% probability), High (50-70%), "
                "Moderate (30-50%), or Low (<30%)."
            )

        else:
            response_parts.append(
                "I'm the UFIE AI Assistant. I can help you with:\n\n"
                "- **Flood risk analysis**: Ask about specific wards, rainfall scenarios, or hotspots\n"
                "- **Infrastructure assessment**: Query drainage capacity, pump stations, or upgrade needs\n"
                "- **Readiness scores**: Understand ward-level preparedness metrics\n"
                "- **Rainfall simulation**: Analyze impacts of different rainfall intensities\n"
                "- **Policy recommendations**: Get suggestions for flood mitigation strategies\n\n"
                "Try asking: 'Which wards will flood if rainfall exceeds 60mm/hr?' or "
                "'What infrastructure upgrades would reduce risk the most?'"
            )

        return {
            "response": "\n".join(response_parts),
            "source": "Built-in AI",
            "model": "rule-based",
        }

    def _builtin_policy(self, query: str, context: str) -> dict:
        """Built-in policy/planning responses."""
        query_lower = query.lower()

        if "report" in query_lower or "preparedness" in query_lower:
            response = (
                "## Pre-Monsoon Preparedness Report\n\n"
                "### Executive Summary\n"
                "Based on the UFIE analysis of 30 wards and 2700+ flood micro-hotspots, "
                "the city's overall flood preparedness requires targeted interventions in critical-risk wards.\n\n"
                "### Key Findings\n"
                "1. **Critical Risk Wards**: Several wards score below 30 on the readiness index, "
                "requiring immediate attention\n"
                "2. **Drainage Infrastructure**: Multiple segments are operating above capacity, "
                "particularly in older parts of the city\n"
                "3. **Pump Stations**: Several wards lack adequate pump station coverage for monsoon conditions\n\n"
                "### Priority Actions\n"
                "1. Upgrade drainage in top 5 critical-risk wards (estimated cost: 50-75 Cr)\n"
                "2. Install 12 new pump stations with diesel backup\n"
                "3. Deploy real-time water level monitoring at 50 critical hotspots\n"
                "4. Pre-position emergency response teams in vulnerable wards\n"
                "5. Conduct community awareness campaigns in high-risk areas\n\n"
                "### Budget Estimate\n"
                "Total recommended investment: 150-200 Crore INR for comprehensive flood resilience."
            )
        elif "budget" in query_lower or "cost" in query_lower:
            response = (
                "## Infrastructure Investment Priority Matrix\n\n"
                "| Priority | Intervention | Est. Cost (Cr) | Risk Reduction |\n"
                "|----------|-------------|----------------|----------------|\n"
                "| 1 | Critical drain upgrades | 30-40 | 25-30% |\n"
                "| 2 | New pump stations (12) | 15-20 | 15-20% |\n"
                "| 3 | Stormwater harvesting | 10-15 | 10-15% |\n"
                "| 4 | Green infrastructure | 20-30 | 10-15% |\n"
                "| 5 | Monitoring systems | 5-8 | 5-10% |\n"
                "| 6 | Community resilience | 3-5 | 5-8% |\n\n"
                "**Total Recommended**: 83-118 Crore INR\n"
                "**Expected Overall Risk Reduction**: 40-55%"
            )
        else:
            response = (
                "## Policy Recommendations for Urban Flood Resilience\n\n"
                "### Short-term (Pre-Monsoon)\n"
                "- Desilting of all major drains and nullahs\n"
                "- Maintenance audit of all pump stations\n"
                "- Pre-positioning of emergency response equipment\n\n"
                "### Medium-term (1-2 years)\n"
                "- Upgrade undersized drainage in critical wards\n"
                "- Install additional pump stations with backup power\n"
                "- Implement stormwater harvesting in commercial zones\n\n"
                "### Long-term (3-5 years)\n"
                "- Comprehensive green infrastructure plan\n"
                "- Smart flood monitoring network\n"
                "- Climate-resilient urban planning guidelines"
            )

        return {
            "response": response,
            "source": "Built-in AI",
            "model": "rule-based",
        }

    def _generate_follow_up_suggestions(self, query: str, response: str) -> list[str]:
        """Generate contextual follow-up question suggestions."""
        query_lower = query.lower()
        suggestions = []

        if "ward" in query_lower or "flood" in query_lower:
            suggestions = [
                "What infrastructure upgrades would reduce risk the most?",
                "Show me the rainfall simulation at 80mm/hr",
                "Generate a preparedness report for critical-risk wards",
            ]
        elif "infrastructure" in query_lower:
            suggestions = [
                "What is the estimated budget for these upgrades?",
                "Which wards should be prioritized first?",
                "How much would readiness scores improve after upgrades?",
            ]
        elif "rainfall" in query_lower or "rain" in query_lower:
            suggestions = [
                "Which wards would be most affected at this intensity?",
                "What drainage capacity is needed to handle this rainfall?",
                "How does this compare to historical rainfall patterns?",
            ]
        else:
            suggestions = [
                "Which wards have the lowest readiness scores?",
                "What are the top flood micro-hotspots?",
                "Simulate rainfall at 100mm/hr and show impacts",
            ]

        return suggestions


# Global copilot instance
copilot = AICopilot()
