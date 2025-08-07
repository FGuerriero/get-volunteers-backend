# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    app_env: str = "development"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    google_api_key: str = ""
    gemini_model_name: str = "gemini-2.0-flash"
    sendgrid_api_key: str = ""
    mail_sender_email: str = "no-reply@example.com"
    mail_sender_name: str = "getVolunteer Team"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Create an instance of Settings to be imported across the application
settings = Settings()
