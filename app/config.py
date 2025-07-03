from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

# Create an instance of Settings to be imported across the application
settings = Settings()