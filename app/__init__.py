# Import all models so Alembic can detect them
from app.modules.users import User, UserMonthlyLimit
from app.modules.auth import AuthProvider
from app.modules.books import Book, ProcessingJob, Chapter, ChapterAudio
from app.modules.listening import ListeningProgress
