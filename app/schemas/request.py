from pydantic import BaseModel, HttpUrl, field_validator

class PlaylistRequest(BaseModel):
    url: HttpUrl

    @field_validator('url')
    def validate_youtube_url(cls, v):
        url_str = str(v)
        if "youtube.com" not in url_str and "youtu.be" not in url_str:
            raise ValueError('URL must be a valid YouTube URL')
        return v
