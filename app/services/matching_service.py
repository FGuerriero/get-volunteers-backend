"""
# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# Created Date: Wed Jul 09 2025
# SPDX-License-Identifier: MIT
"""

import json
from typing import Any, Dict, List

import google.generativeai as genai
from sqlalchemy.orm import Session

from app.config import settings
from app.crud import crud_match, crud_need, crud_volunteer
from app.db import models


class MatchingService:
    _COMMON_PROMPT_INSTRUCTIONS = """
    **Matching Criteria:**
    1.  **Skills Fit:** Volunteers whose skills directly match or are highly relevant to the 'Required Skills
        for Need' or are strongly implied by the 'Need Description'.
    2.  **Interests Fit:** Volunteers whose 'Volunteer Interests' align with the nature of the 'Need'.
    3.  **About Me Relevance:** Any information in the 'About Me' field that indicates a strong suitability
        for the need.
    4.  **Prioritize best fits:** It's not necessary to fulfill the 'Number of volunteers needed' completely
        if there aren't enough truly good fits. Focus on quality over quantity.

    **Output Format:**
    Provide a JSON array of objects. Each object should represent a good match and contain the following
    fields:
    -   `volunteer_id` (for analyze_and_match) or `need_id` (for analyze_volunteer_against_all_needs): The
        integer ID of the matched entity.
    -   `match_details`: A string explaining *why* this volunteer/need is a good fit, specifically mentioning
        how their skills, interests, or 'about me' section align.

    Example Output for Need Analysis:
    ```json
    [
        {{
            "volunteer_id": 123,
            "match_details": "Volunteer's 'Coding' skill directly matches the 'Software Development' need
                description and their 'Tech' interest aligns."
        }},
        {{
            "volunteer_id": 456,
            "match_details": "Volunteer's 'Teaching' skill is suitable for the 'Educational Support' need and
                their 'Youth Mentorship' interest is a strong fit."
        }}
    ]
    ```
    Example Output for Volunteer Analysis:
    ```json
    [
        {{
            "need_id": 789,
            "match_details": "Volunteer's 'Gardening' skill is perfect for the 'Community Garden Cleanup'
                need, and their 'Environmental protection' interest aligns."
        }},
        {{
            "need_id": 101,
            "match_details": "Volunteer's 'Communication' skill is suitable for the 'Public Speaking Event'
                need, and their 'Community outreach' interest is a strong fit."
        }}
    ]
    ```
    """

    def __init__(self, db: Session):
        self.db = db
        genai.configure(api_key=settings.google_api_key)

    async def _call_gemini_api(self, prompt: str, schema: Dict[str, Any]) -> Any:
        """
        Internal helper to call the Gemini API with a structured response schema using google-generativeai.
        """
        try:
            model = genai.GenerativeModel(
                model_name=settings.gemini_model_name,
                generation_config={"response_mime_type": "application/json", "response_schema": schema},
            )

            response = await model.generate_content_async(prompt)

            if (
                response.candidates
                and response.candidates[0].content
                and response.candidates[0].content.parts
            ):
                json_string = response.candidates[0].content.parts[0].text
                return json.loads(json_string)
            else:
                print("Gemini API did not return expected content structure:", response)
                return None
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return None

    async def analyze_and_match(self, need: models.Need, all_volunteers: List[models.Volunteer]):
        """
        Analyzes a specific need against all available volunteers using Gemini
        and stores the matching results. This is typically called when a need is created or updated.
        """
        crud_match.delete_matches_for_need(self.db, need.id)

        if not all_volunteers:
            print(f"No volunteers available to match for Need ID {need.id}")
            return

        volunteer_info = "\n".join(
            [
                f"""- ID: {v.id}, Name: {v.name}, Email: {v.email}, Skills: {v.skills or 'None'},
                    About: {v.about_me or 'None'}, Interests: {v.volunteer_interests or 'None'}"""
                for v in all_volunteers
            ]
        )

        prompt = f"""
        You are an expert volunteer matching specialist. Your task is to analyze a specific volunteer need and
        a list of available volunteers, and identify the best fits based on skills and interests.

        **Volunteer Need Details:**
        Title: {need.title}
        Description: {need.description}
        Required Skills for Need: {need.required_skills or 'None'}
        Number of volunteers needed: {need.num_volunteers_needed}

        **Available Volunteers (IDs, Names, Emails, Skills, About Me, Volunteer Interests):**
        {volunteer_info}
        {self._COMMON_PROMPT_INSTRUCTIONS}
        """

        response_schema = {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {"volunteer_id": {"type": "integer"}, "match_details": {"type": "string"}},
                "required": ["volunteer_id", "match_details"],
            },
        }

        gemini_response = await self._call_gemini_api(prompt, response_schema)

        if gemini_response:
            for match_data in gemini_response:
                volunteer_id = match_data.get("volunteer_id")
                match_details = match_data.get("match_details")

                if isinstance(volunteer_id, int) and isinstance(match_details, str):
                    if crud_volunteer.get_volunteer(self.db, volunteer_id):
                        crud_match.create_match(self.db, volunteer_id, need.id, match_details)
                    else:
                        print(
                            f"""Warning: Gemini suggested non-existent volunteer ID {volunteer_id}
                             for Need ID {need.id}"""
                        )
                else:
                    print(
                        f"""Warning: Gemini returned invalid match data format for Need ID {need.id}:
                        {match_data}"""
                    )
        else:
            print(f"Gemini did not return valid matches for Need ID {need.id}")

    async def analyze_volunteer_against_all_needs(
        self, volunteer: models.Volunteer, all_needs: List[models.Need]
    ):
        """
        Analyzes a specific volunteer against all available needs using Gemini
        and updates match results. This is typically called when a volunteer is created or updated.
        """
        crud_match.delete_matches_for_volunteer(self.db, volunteer.id)

        if not all_needs:
            print(f"No needs available to match for Volunteer ID {volunteer.id}")
            return

        need_info = "\n".join(
            [
                f"""- ID: {n.id}, Title: {n.title}, Description: {n.description}, Required Skills:
                {n.required_skills or 'None'}"""
                for n in all_needs
            ]
        )

        prompt = f"""
        You are an expert volunteer matching specialist. Your task is to analyze a specific volunteer's
        profile and a list of available needs, and identify the best fits for this volunteer based on their
        skills and interests.

        **Volunteer Details:**
        ID: {volunteer.id}
        Name: {volunteer.name}
        Email: {volunteer.email}
        Skills: {volunteer.skills or 'None'}
        About Me: {volunteer.about_me or 'None'}
        Interests: {volunteer.volunteer_interests or 'None'}

        **Available Needs (IDs, Titles, Descriptions, Required Skills):**
        {need_info}
        {self._COMMON_PROMPT_INSTRUCTIONS}
        """

        response_schema = {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {"need_id": {"type": "integer"}, "match_details": {"type": "string"}},
                "required": ["need_id", "match_details"],
            },
        }

        gemini_response = await self._call_gemini_api(prompt, response_schema)

        if gemini_response:
            for match_data in gemini_response:
                need_id = match_data.get("need_id")
                match_details = match_data.get("match_details")

                if isinstance(need_id, int) and isinstance(match_details, str):
                    if crud_need.get_need(self.db, need_id):
                        crud_match.create_match(self.db, volunteer.id, need_id, match_details)
                    else:
                        print(
                            f"""Warning: Gemini suggested non-existent need ID {need_id}
                            for Volunteer ID {volunteer.id}"""
                        )
                else:
                    print(
                        f"""Warning: Gemini returned invalid match data format for Volunteer ID
                        {volunteer.id}: {match_data}"""
                    )
        else:
            print(f"Gemini did not return valid matches for Volunteer ID {volunteer.id}")
