from apps.blog.models import Post
from apps.certifications.models import Certification
from apps.experience.models import Experience
from apps.projects.models import Project
from apps.skills.models import Skill

# Models whose save/delete invalidate the chat context cache. Registered
# per-model in AppConfig.ready() so the sender filter actually matches.
TRACKED_MODELS = [Project, Skill, Experience, Certification, Post]

MAX_MESSAGE_LENGTH = 500
RATE_LIMIT_KEY = "ai_assistant:chat:{}"
RATE_LIMIT_MAX = 10
RATE_LIMIT_TTL = 3600  # seconds — 10 messages / hour / IP
