from django.shortcuts import get_object_or_404, render

from apps.blog.models import Post


def post_list(request):
    posts = Post.published.all()
    return render(request, "blog/list.html", {"posts": posts})


def post_detail(request, slug: str):
    post = get_object_or_404(
        Post, slug=slug, is_draft=False, published_at__isnull=False
    )
    return render(request, "blog/detail.html", {"post": post})
