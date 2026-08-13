from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.ai_assistant.services import CONTEXT_CACHE_KEY
from apps.blog.models import Post
from apps.certifications.models import Certification
from apps.experience.models import Experience
from apps.projects.models import Project
from apps.skills.models import Skill

MODELS = [Project, Skill, Experience, Certification, Post]


@receiver([post_save, post_delete], sender=MODELS)
def invalidate_chat_context(sender, **kwargs):
    cache.delete(CONTEXT_CACHE_KEY)
