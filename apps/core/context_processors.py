from django.conf import settings


def site_seo(request):
    return {
        "SITE_DESCRIPTION": getattr(
            settings,
            "SITE_DESCRIPTION",
            "Systems engineer with expertise in AI integration, cloud, automation, Docker, and DevOps.",
        ),
    }
