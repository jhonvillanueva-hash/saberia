from enum import Enum


class AuthProviderType(str, Enum):
    google = "google"
    email = "email"


class BookStatus(str, Enum):
    pending = "pending"
    validating = "validating"
    extracting_text = "extracting_text"
    detecting_chapters = "detecting_chapters"
    generating_audio = "generating_audio"
    completed = "completed"
    error = "error"
    deleted = "deleted"


class BookFileType(str, Enum):
    pdf = "pdf"
    epub = "epub"


class ChapterAudioStatus(str, Enum):
    pending = "pending"
    generating = "generating"
    completed = "completed"
    error = "error"
    deleted = "deleted"


class AudioFileStatus(str, Enum):
    active = "active"
    pending_deletion = "pending_deletion"
    deleted = "deleted"
