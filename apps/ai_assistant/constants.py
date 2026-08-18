from apps.blog.models import Post
from apps.certifications.models import Certification
from apps.experience.models import Experience
from apps.projects.models import Project
from apps.skills.models import Category, Skill

# Models whose save/delete invalidate the chat context cache. Registered
# per-model in AppConfig.ready() so the sender filter actually matches.
TRACKED_MODELS = [Project, Skill, Experience, Certification, Post, Category]

# Row caps for build_context(): a large portfolio must not blow up the prompt.
MAX_PROJECT_ROWS = 5
MAX_BLOG_ROWS = 5
MAX_EXPERIENCE_ROWS = 10  # keep this slightly higher
MAX_CERTIFICATION_ROWS = 20

MAX_MESSAGE_LENGTH = 500
RATE_LIMIT_KEY = "ai_assistant:chat:{}"
RATE_LIMIT_MAX = 10
RATE_LIMIT_TTL = 3600  # seconds — 10 messages / hour / IP
