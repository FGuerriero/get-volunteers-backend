'''
# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# Created Date: Wed Jul 09 2025
# SPDX-License-Identifier: MIT
'''

import json
from typing import Any, Dict, List

import google.generativeai as genai
from sqlalchemy.orm import Session

from app.crud import crud_match, crud_need, crud_volunteer
from app.db import models


class MatchingService:
    def __init__(self, db: Session):
        self.db = db
        genai.configure(api_key="") 

    async def _call_gemini_api(self, prompt: str, schema: Dict[str, Any]) -> Any:
        """
        Internal helper to call the Gemini API with a structured response schema using google-generativeai.
        """
        try:
            # Initialize the generative model
            model = genai.GenerativeModel(
                model_name='gemini-2.0-flash',
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": schema
                }
            )

            # Generate content
            response = await model.generate_content_async(prompt)

            # Access the text part of the response, which should be a JSON string
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                json_string = response.candidates[0].content.parts[0].text
                return json.loads(json_string)
            else:
                print("Gemini API did not return expected content structure:", response)
                return None
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            # print(f"Gemini response details: {response.text if 'response' in locals() and hasattr(response, 'text') else 'N/A'}")
            return None

    async def analyze_and_match(self, need: models.Need, all_volunteers: List[models.Volunteer]):
        """
        Analyzes a specific need against all available volunteers using Gemini
        and stores the matching results.
        """
        # Clear existing matches for this specific need to avoid duplicates or outdated info
        # This is important for re-analysis when a need is updated.
        crud_match.delete_matches_for_need(self.db, need.id)

        if not all_volunteers:
            print(f"No volunteers available to match for Need ID {need.id}")
            return

        # Construct the prompt for Gemini
        volunteer_info = "\n".join([
            f"- ID: {v.id}, Name: {v.name}, Email: {v.email}, Skills: {v.skills or 'None'}, About: {v.about_me or 'None'}, Interests: {v.volunteer_interests or 'None'}"
            for v in all_volunteers
        ])

        prompt = f"""
        You are an expert volunteer matching specialist. Your task is to analyze a specific volunteer need and a list of available volunteers, and identify the best fits based on skills and interests.

        **Volunteer Need Details:**
        Title: {need.title}
        Description: {need.description}
        Required Skills for Need: {need.required_skills or 'None'}
        Number of volunteers needed: {need.num_volunteers_needed}

        **Available Volunteers (IDs, Names, Emails, Skills, About Me, Volunteer Interests):**
        {volunteer_info}

        **Matching Criteria:**
        1.  **Skills Fit:** Volunteers whose skills directly match or are highly relevant to the 'Required Skills for Need' or are strongly implied by the 'Need Description'.
        2.  **Interests Fit:** Volunteers whose 'Volunteer Interests' align with the nature of the 'Need'.
        3.  **About Me Relevance:** Any information in the 'About Me' field that indicates a strong suitability for the need.
        4.  **Prioritize best fits:** It's not necessary to fulfill the 'Number of volunteers needed' completely if there aren't enough truly good fits. Focus on quality over quantity.

        **Output Format:**
        Provide a JSON array of objects. Each object should represent a good match and contain the following fields:
        -   `volunteer_id`: The integer ID of the matched volunteer.
        -   `match_details`: A string explaining *why* this volunteer is a good fit, specifically mentioning how their skills, interests, or 'about me' section align with the need.

        Example Output:
        ```json
        [
            {{
                "volunteer_id": 123,
                "match_details": "Volunteer's 'Coding' skill directly matches the 'Software Development' need description and their 'Tech' interest aligns."
            }},
            {{
                "volunteer_id": 456,
                "match_details": "Volunteer's 'Teaching' skill is suitable for the 'Educational Support' need and their 'Youth Mentorship' interest is a strong fit."
            }}
        ]
        ```
        """
        
        # Define the expected JSON schema for Gemini's response
        response_schema = {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "volunteer_id": {"type": "integer"},
                    "match_details": {"type": "string"}
                },
                "required": ["volunteer_id", "match_details"]
            }
        }

        gemini_response = await self._call_gemini_api(prompt, response_schema)

        if gemini_response:
            for match_data in gemini_response:
                volunteer_id = match_data.get("volunteer_id")
                match_details = match_data.get("match_details")

                if isinstance(volunteer_id, int) and isinstance(match_details, str):
                    # Ensure the volunteer actually exists before creating a match
                    # Fetching volunteer here to ensure it's in the current session if needed later
                    if crud_volunteer.get_volunteer(self.db, volunteer_id):
                        crud_match.create_match(self.db, volunteer_id, need.id, match_details)
                    else:
                        print(f"Warning: Gemini suggested non-existent volunteer ID {volunteer_id} for Need ID {need.id}")
                else:
                    print(f"Warning: Gemini returned invalid match data format for Need ID {need.id}: {match_data}")
        else:
            print(f"Gemini did not return valid matches for Need ID {need.id}")

    async def reanalyze_all_matches(self):
        """
        Re-analyzes all existing needs against all available volunteers.
        This is typically called when a volunteer's profile is created or updated.
        """
        print("Triggering re-analysis of all matches...")
        all_needs = crud_need.get_needs(self.db)
        all_volunteers = crud_volunteer.get_volunteers(self.db)

        # Clear all existing matches before re-generating to ensure fresh data
        crud_match.delete_all_matches(self.db)

        for need in all_needs:
            await self.analyze_and_match(need, all_volunteers)
        print("Re-analysis of all matches completed.")