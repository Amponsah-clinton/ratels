from django.shortcuts import render, redirect
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.db import transaction
from django.contrib.auth.forms import PasswordResetForm
from django.contrib import messages

import json
import os
import random
import requests
from datetime import datetime, timedelta
from django.utils.crypto import get_random_string

from .supabase_client import get_supabase


def index(request):
    """Landing page with all content sections from Supabase."""
    sections = {}
    media_videos = []
    media_audio = []
    media_images = []
    media_documents = []
    featured_members = []
    hero_video_url = None

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
            "Accept": "application/json",
        }

        # Fetch all site content sections
        url = f"{base_url}/rest/v1/site_content?is_active=eq.true&select=*&order=display_order.asc"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for item in data:
                sections[item.get("content_key")] = item
        # Always load hero slides, manifesto, and quote by content_key so saved settings show on landing (ignore is_active)
        for key in ("hero_slide_1", "hero_slide_2", "hero_slide_3", "manifesto", "hero_quote"):
            try:
                r = requests.get(
                    f"{base_url}/rest/v1/site_content?content_key=eq.{key}&select=*&limit=1",
                    headers=headers,
                    timeout=10,
                )
                if r.status_code == 200 and r.json():
                    sections[key] = r.json()[0]
            except Exception:
                pass
        # Ensure hero carousel keys exist for template (slide 1, 2, 3)
        for key in ("hero_slide_1", "hero_slide_2", "hero_slide_3"):
            if key not in sections:
                sections[key] = {"content_key": key, "image_url": None}
        # Ensure manifesto exists for template (image beside section)
        if "manifesto" not in sections:
            sections["manifesto"] = {"content_key": "manifesto", "image_url": None, "title": "Our Manifesto", "subtitle": "The Ratel Movement", "content": ""}
        # Ensure hero_quote exists for template
        if "hero_quote" not in sections:
            sections["hero_quote"] = {"content_key": "hero_quote", "content": "When the people fear the government, there is tyranny. When the government fears the people, there is liberty.", "subtitle": "Thomas Jefferson"}

        # Hero video (if set, landing shows video instead of 3-image carousel)
        hero_video_url = None
        try:
            r = requests.get(
                f"{base_url}/rest/v1/site_content?content_key=eq.hero_video&select=image_url&limit=1",
                headers=headers,
                timeout=10,
            )
            if r.status_code == 200:
                data = r.json()
                if data and isinstance(data, list) and data[0].get("image_url"):
                    hero_video_url = (data[0].get("image_url") or "").strip()
        except Exception:
            pass

        # Fetch latest 2 videos
        resp = requests.get(
            f"{base_url}/rest/v1/media_videos?select=*&status=eq.active&order=created_at.desc&limit=2",
            headers=headers, timeout=10
        )
        if resp.status_code == 200:
            media_videos = resp.json()

        # Fetch latest 2 audio
        resp = requests.get(
            f"{base_url}/rest/v1/media_audio?select=*&status=eq.active&order=created_at.desc&limit=2",
            headers=headers, timeout=10
        )
        if resp.status_code == 200:
            media_audio = resp.json()

        # Fetch latest 2 images
        resp = requests.get(
            f"{base_url}/rest/v1/media_images?select=*&status=eq.active&order=created_at.desc&limit=2",
            headers=headers, timeout=10
        )
        if resp.status_code == 200:
            media_images = resp.json()

        # Fetch latest 2 documents
        resp = requests.get(
            f"{base_url}/rest/v1/media_documents?select=*&status=eq.active&order=created_at.desc&limit=2",
            headers=headers, timeout=10
        )
        if resp.status_code == 200:
            media_documents = resp.json()

        # Get all active links and filter by type
        resp_all = requests.get(
            f"{base_url}/rest/v1/youtube_ig_links?select=*&is_active=eq.true&order=display_order.asc,created_at.asc",
            headers=headers, timeout=10
        )
        all_links = resp_all.json() if resp_all.status_code == 200 else []

        # Normalize thumbnail URLs using robust normalizer
        for link in all_links:
            if link.get("thumbnail_url"):
                original_url = link["thumbnail_url"]
                link["thumbnail_url"] = _normalize_messages_url(original_url)
                if link["thumbnail_url"] != original_url:
                    print(f"[Index YouTube/IG] Normalized thumbnail: {original_url} -> {link['thumbnail_url']}")

        # Filter YouTube links (those with youtube_url and no ig_url, or youtube_url present)
        youtube_links = [link for link in all_links if link.get("youtube_url") and not link.get("ig_url")][:4]

        # Filter Instagram links (those with ig_url and no youtube_url, or ig_url present)
        instagram_links = [link for link in all_links if link.get("ig_url") and not link.get("youtube_url")][:4]

        # Get one active case for landing page (prioritize featured, then most recent active)
        cases_resp = requests.get(
            f"{base_url}/rest/v1/cases?select=*&status=eq.active&is_featured=eq.true&order=created_at.desc&limit=1",
            headers=headers,
            timeout=10
        )
        featured_cases = cases_resp.json() if cases_resp.status_code == 200 else []
        
        # If no featured active case, get the most recent active case
        if not featured_cases:
            cases_resp = requests.get(
                f"{base_url}/rest/v1/cases?select=*&status=eq.active&order=created_at.desc&limit=1",
                headers=headers,
                timeout=10
            )
            featured_cases = cases_resp.json() if cases_resp.status_code == 200 else []
        
        # Normalize date strings for featured cases
        for case in featured_cases:
            for key in ("date_reported", "created_at", "updated_at"):
                val = case.get(key)
                if val and isinstance(val, str) and val.strip():
                    try:
                        if "T" in val:
                            case[key] = datetime.fromisoformat(val.replace("Z", "+00:00"))
                        else:
                            case[key] = datetime.strptime(val, "%Y-%m-%d").date()
                    except (ValueError, TypeError):
                        case[key] = None

        # Fetch latest 3 published blogs for landing page
        blogs_resp = requests.get(
            f"{base_url}/rest/v1/blogs?is_published=eq.true&select=*&order=published_at.desc,created_at.desc&limit=3",
            headers=headers,
            timeout=10
        )
        latest_blogs = blogs_resp.json() if blogs_resp.status_code == 200 else []
        
        # Parse dates and normalize image URLs for blogs
        for blog in latest_blogs:
            for key in ("published_at", "created_at", "updated_at"):
                val = blog.get(key)
                if val and isinstance(val, str) and val.strip():
                    try:
                        if "T" in val:
                            blog[key] = datetime.fromisoformat(val.replace("Z", "+00:00"))
                        else:
                            blog[key] = datetime.strptime(val, "%Y-%m-%d").date()
                    except (ValueError, TypeError):
                        blog[key] = None
            
            # Normalize featured_image_url - ensure it's a full public URL
            if blog.get("featured_image_url"):
                original_url = blog["featured_image_url"]
                blog["featured_image_url"] = _normalize_blog_image_url(blog["featured_image_url"], base_url)
                if blog["featured_image_url"] != original_url:
                    print(f"[Index Blog Image] Normalized: {original_url} -> {blog['featured_image_url']}")

        # Fetch active members and pick 4 at random for landing profile cards (changes on refresh)
        featured_members = []
        try:
            members_url = f"{base_url}/rest/v1/members?select=member_id,full_name,membership_type,state,country,based_in_nigeria,profile_image_url&status=eq.active"
            members_resp = requests.get(members_url, headers=headers, timeout=10)
            if members_resp.status_code == 200:
                all_members = members_resp.json()
                if all_members:
                    shuffled = list(all_members)
                    random.shuffle(shuffled)
                    featured_members = shuffled[:4]
                    bucket_base = base_url + "/storage/v1/object/public/profiles/"
                    for m in featured_members:
                        path = m.get("profile_image_url")
                        if path and not str(path).startswith("http"):
                            m["profile_image_url"] = bucket_base + str(path).lstrip("/")
        except Exception:
            pass

    except Exception as e:
        print(f"[Index] Error fetching site content: {e}")
        youtube_links = []
        instagram_links = []
        featured_cases = []
        latest_blogs = []
        featured_members = []

    return render(request, "index.html", {
        "sections": sections,
        "manifesto": sections.get("manifesto"),
        "hero_video_url": hero_video_url,
        "media_videos": media_videos,
        "media_audio": media_audio,
        "media_images": media_images,
        "media_documents": media_documents,
        "youtube_links": youtube_links,
        "instagram_links": instagram_links,
        "featured_cases": featured_cases,
        "latest_blogs": latest_blogs,
        "featured_members": featured_members,
    })


def about(request):
    return render(request, "about.html")


def about_ratel(request):
    """About Ratel page with dynamic content from Supabase."""
    context = {
        "hero": None,
        "sections": [],
        "member_count": "1000+",
    }

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
            "Accept": "application/json",
        }

        # Fetch all about_ratel sections
        url = f"{base_url}/rest/v1/about_pages?page_key=eq.about_ratel&is_active=eq.true&select=*&order=section_order.asc"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for item in data:
                if item.get("section_key") == "hero":
                    context["hero"] = item
                else:
                    context["sections"].append(item)

        # Get member count
        try:
            count_url = f"{base_url}/rest/v1/members?select=id&status=eq.active"
            count_resp = requests.get(count_url, headers=headers, timeout=5)
            if count_resp.status_code == 200:
                count = len(count_resp.json())
                if count > 0:
                    context["member_count"] = f"{count}+"
        except Exception:
            pass

    except Exception as e:
        print(f"Error fetching about_ratel data: {e}")

    return render(request, "about_ratel.html", context)


def mission_vision(request):
    """Mission & Vision page with dynamic content from Supabase."""
    context = {
        "mission": None,
        "vision": None,
        "values_header": None,
        "values": [],
        "pledge": None,
    }

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
            "Accept": "application/json",
        }

        # Fetch all mission_vision sections
        url = f"{base_url}/rest/v1/about_pages?page_key=eq.mission_vision&is_active=eq.true&select=*&order=section_order.asc"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for item in data:
                section_key = item.get("section_key")
                if section_key == "mission":
                    context["mission"] = item
                elif section_key == "vision":
                    context["vision"] = item
                elif section_key == "values":
                    context["values_header"] = item
                elif section_key == "pledge":
                    context["pledge"] = item
                elif section_key.startswith("value_"):
                    context["values"].append(item)

    except Exception as e:
        print(f"Error fetching mission_vision data: {e}")

    return render(request, "mission_vision.html", context)


def ideology(request):
    """
    Public ideology page - displays all ideology sections from Supabase.
    """
    sections = []

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        resp = requests.get(
            f"{base_url}/rest/v1/ideology_sections?select=*&is_active=eq.true&order=display_order.asc",
            headers=headers,
            timeout=10
        )

        if resp.status_code == 200:
            sections = resp.json()
    except Exception as e:
        print(f"[Ideology] Error fetching sections: {e}")

    return render(request, "ideology.html", {"sections": sections})


def faqs(request):
    return render(request, "faqs.html")


def media_vault(request):
    return render(request, "media_vault.html")


def media_videos(request):
    """Public videos page - fetch videos from Supabase."""
    videos = []
    sorted_months = []
    categories = []
    current_category = request.GET.get('category', 'all')

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
            "Accept": "application/json",
        }

        # Build URL with proper filters
        url = f"{base_url}/rest/v1/media_videos?select=*&status=eq.active&order=created_at.desc"

        if current_category and current_category != 'all':
            url += f"&category=eq.{current_category}"

        print(f"[Media Videos] Fetching from: {url}")
        resp = requests.get(
            url,
            headers=headers,
            timeout=10
        )
        print(f"[Media Videos] Response status: {resp.status_code}")

        if resp.status_code == 200:
            videos = resp.json()
            print(f"[Media Videos] Found {len(videos)} videos")
            # Normalize file URLs
            storage_base = f"{base_url}/storage/v1/object/public/media/"
            for video in videos:
                if video.get("file_url") and not str(video["file_url"]).startswith("http"):
                    video["file_url"] = storage_base + str(video["file_url"]).lstrip("/")
                if video.get("thumbnail_url") and not str(video["thumbnail_url"]).startswith("http"):
                    video["thumbnail_url"] = storage_base + str(video["thumbnail_url"]).lstrip("/")
            
            # Group videos by month
            from collections import defaultdict
            from datetime import datetime
            videos_by_month = defaultdict(list)
            for video in videos:
                try:
                    created_date = datetime.fromisoformat(video.get("created_at", "").replace("Z", "+00:00"))
                    month_key = created_date.strftime("%Y-%m")
                    month_label = created_date.strftime("%B %Y")
                    videos_by_month[month_key].append({
                        "video": video,
                        "month_label": month_label,
                        "month_key": month_key
                    })
                except:
                    # If date parsing fails, put in "Unknown" month
                    videos_by_month["unknown"].append({
                        "video": video,
                        "month_label": "Unknown",
                        "month_key": "unknown"
                    })
            
            # Sort months descending (newest first)
            sorted_months = sorted(videos_by_month.items(), key=lambda x: x[0] if x[0] != "unknown" else "0000-00", reverse=True)

        # Get distinct categories
        categories = sorted({v.get("category") for v in videos if v.get("category")})

    except Exception as e:
        print(f"[Media Videos] Error fetching data: {e}")
        sorted_months = []
        videos = []

    return render(request, "media_videos.html", {
        "videos": videos,
        "videos_by_month": sorted_months,
        "categories": categories,
        "current_category": current_category,
    })


def media_audios(request):
    """Public audios page - fetch audio from Supabase."""
    audios = []
    categories = []
    current_category = request.GET.get('category', 'all')

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
            "Accept": "application/json",
        }

        params = {
            "select": "*",
            "is_archived": "eq.false",
            "order": "created_at.desc",
        }

        if current_category and current_category != 'all':
            params["category"] = f"eq.{current_category}"

        resp = requests.get(
            f"{base_url}/rest/v1/media_audio",
            headers=headers,
            params=params,
            timeout=10
        )

        if resp.status_code == 200:
            audios = resp.json()
            # Normalize file URLs
            storage_base = f"{base_url}/storage/v1/object/public/media/"
            for audio in audios:
                if audio.get("file_url") and not str(audio["file_url"]).startswith("http"):
                    audio["file_url"] = storage_base + str(audio["file_url"]).lstrip("/")

        # Get distinct categories
        categories = sorted({a.get("category") for a in audios if a.get("category")})

    except Exception as e:
        print(f"[Media Audios] Error fetching data: {e}")

    return render(request, "media_audios.html", {
        "audios": audios,
        "categories": categories,
        "current_category": current_category,
    })


def media_images(request):
    """Public images page - fetch images from Supabase."""
    images = []
    categories = []
    current_category = request.GET.get('category', 'all')

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
            "Accept": "application/json",
        }

        # Build query URL - use status=active like dashboard
        url = f"{base_url}/rest/v1/media_images?select=*&status=eq.active&order=created_at.desc"

        if current_category and current_category != 'all':
            url += f"&category=eq.{current_category}"

        resp = requests.get(url, headers=headers, timeout=10)

        print(f"[Media Images] URL: {url}")
        print(f"[Media Images] Response status: {resp.status_code}")
        if resp.status_code != 200:
            print(f"[Media Images] Response: {resp.text}")

        if resp.status_code == 200:
            images = resp.json()
            print(f"[Media Images] Found {len(images)} images")
            # Normalize file URLs
            storage_base = f"{base_url}/storage/v1/object/public/media/"
            for image in images:
                if image.get("file_url") and not str(image["file_url"]).startswith("http"):
                    image["file_url"] = storage_base + str(image["file_url"]).lstrip("/")
                if image.get("thumbnail_url") and not str(image["thumbnail_url"]).startswith("http"):
                    image["thumbnail_url"] = storage_base + str(image["thumbnail_url"]).lstrip("/")

        # Get distinct categories
        categories = sorted({i.get("category") for i in images if i.get("category")})

    except Exception as e:
        import traceback
        print(f"[Media Images] Error fetching data: {e}")
        traceback.print_exc()

    return render(request, "media_images.html", {
        "images": images,
        "categories": categories,
        "current_category": current_category,
    })


def media_documents(request):
    """Public documents page - fetch documents from Supabase."""
    documents = []
    categories = []
    current_category = request.GET.get('category', 'all')

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
            "Accept": "application/json",
        }

        params = {
            "select": "*",
            "is_archived": "eq.false",
            "is_confidential": "eq.false",  # Only show non-confidential docs publicly
            "order": "created_at.desc",
        }

        if current_category and current_category != 'all':
            params["category"] = f"eq.{current_category}"

        resp = requests.get(
            f"{base_url}/rest/v1/media_documents",
            headers=headers,
            params=params,
            timeout=10
        )

        if resp.status_code == 200:
            documents = resp.json()
            # Normalize file URLs
            storage_base = f"{base_url}/storage/v1/object/public/media/"
            for doc in documents:
                if doc.get("file_url") and not str(doc["file_url"]).startswith("http"):
                    doc["file_url"] = storage_base + str(doc["file_url"]).lstrip("/")

        # Get distinct categories
        categories = sorted({d.get("category") for d in documents if d.get("category")})

    except Exception as e:
        print(f"[Media Documents] Error fetching data: {e}")

    return render(request, "media_documents.html", {
        "documents": documents,
        "categories": categories,
        "current_category": current_category,
    })


def resources(request):
    """
    Public resources page with categorized downloadable materials.
    Categories: activist_toolkits, educational_materials, legal_civic_guides, research_reading, download_centre
    """
    resources_data = {
        'activist_toolkits': [],
        'educational_materials': [],
        'legal_civic_guides': [],
        'research_reading': [],
        'download_centre': [],
    }
    current_category = request.GET.get('category', 'activist_toolkits')

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
            "Accept": "application/json",
        }

        # Fetch all active resources
        url = f"{base_url}/rest/v1/resources?status=eq.active&select=*&order=display_order.asc,created_at.desc"
        resp = requests.get(url, headers=headers, timeout=10)

        if resp.status_code == 200:
            all_resources = resp.json()
            # Normalize file URLs and group by category
            storage_base = f"{base_url}/storage/v1/object/public/resources/"
            for resource in all_resources:
                if resource.get("file_url") and not str(resource["file_url"]).startswith("http"):
                    resource["file_url"] = storage_base + str(resource["file_url"]).lstrip("/")
                if resource.get("thumbnail_url") and not str(resource["thumbnail_url"]).startswith("http"):
                    resource["thumbnail_url"] = storage_base + str(resource["thumbnail_url"]).lstrip("/")

                category = resource.get("category", "download_centre")
                if category in resources_data:
                    resources_data[category].append(resource)

    except Exception as e:
        print(f"[Resources] Error fetching data: {e}")

    return render(request, "resources.html", {
        "resources": resources_data,
        "current_category": current_category,
        "categories": [
            {"key": "activist_toolkits", "label": "Activist Toolkits", "icon": "fa-bullhorn"},
            {"key": "educational_materials", "label": "Educational Materials", "icon": "fa-graduation-cap"},
            {"key": "legal_civic_guides", "label": "Legal & Civic Guides", "icon": "fa-balance-scale"},
            {"key": "research_reading", "label": "Research & Reading", "icon": "fa-book"},
            {"key": "download_centre", "label": "Download Centre", "icon": "fa-download"},
        ],
    })


def membership(request):
    """
    Public membership page: show members who currently have explicit roles,
    with search + filters.
    """
    members_with_roles = []
    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        table_url = f"{base_url}/rest/v1/members"
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
            "Accept": "application/json",
        }
        # Fetch all members; we will do the simple logic in Python:
        # "if membership_type is set, show on /membership/"
        params = {
            "select": "member_id,full_name,email,phone_number,membership_type,status,based_in_nigeria,state,lga,country,city,engagement_preferences,created_at,profile_image_url",
            "order": "created_at.desc",
        }
        resp = requests.get(table_url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        all_members = resp.json()

        # Only keep rows where membership_type is non‑empty
        members_with_roles = [
            m for m in all_members if (m.get("membership_type") or "").strip()
        ]

        # Normalize profile_image_url to a full public URL if only a path is stored
        bucket_base = settings.SUPABASE_URL.rstrip("/") + "/storage/v1/object/public/profiles/"
        for m in members_with_roles:
            path = m.get("profile_image_url")
            if path and not str(path).startswith("http"):
                m["profile_image_url"] = bucket_base + str(path).lstrip("/")

    except Exception as e:
        print(f"[Membership public] Failed to fetch members from Supabase: {e}")

    # Collect distinct roles for filter UI
    role_set = sorted(
        {m.get("membership_type") for m in members_with_roles if m.get("membership_type")}
    )

    return render(
        request,
        "membership.html",
        {
            "members": members_with_roles,
            "roles": role_set,
        },
    )


def suspended_members_page(request):
    """
    Public page listing members currently suspended from the movement.
    """
    members = []
    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        table_url = f"{base_url}/rest/v1/members"
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
            "Accept": "application/json",
        }
        params = {
            "select": "member_id,full_name,membership_type,status,based_in_nigeria,state,country,created_at,profile_image_url",
            "order": "created_at.desc",
            "status": "eq.suspended",
        }
        resp = requests.get(table_url, headers=headers, params=params, timeout=10)
        if resp.status_code == 200:
            members = resp.json()
        bucket_base = settings.SUPABASE_URL.rstrip("/") + "/storage/v1/object/public/profiles/"
        for m in members:
            path = m.get("profile_image_url")
            if path and not str(path).startswith("http"):
                m["profile_image_url"] = bucket_base + str(path).lstrip("/")
    except Exception as e:
        print(f"[Suspended members] Failed to fetch from Supabase: {e}")

    return render(
        request,
        "suspended_members.html",
        {
            "members": members,
            "page_title": "Suspended Members",
            "page_subtitle": "Members currently suspended from the RATEL Movement",
            "intro_text": "The following accounts have been temporarily suspended in line with our community standards. Suspensions may be reviewed upon appeal.",
            "empty_message": "There are no suspended members at this time.",
        },
    )


def banned_accounts_page(request):
    """
    Public page listing accounts that have been permanently banned.
    """
    members = []
    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        table_url = f"{base_url}/rest/v1/members"
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
            "Accept": "application/json",
        }
        params = {
            "select": "member_id,full_name,membership_type,status,based_in_nigeria,state,country,created_at,profile_image_url",
            "order": "created_at.desc",
            "status": "eq.banned",
        }
        resp = requests.get(table_url, headers=headers, params=params, timeout=10)
        if resp.status_code == 200:
            members = resp.json()
        bucket_base = settings.SUPABASE_URL.rstrip("/") + "/storage/v1/object/public/profiles/"
        for m in members:
            path = m.get("profile_image_url")
            if path and not str(path).startswith("http"):
                m["profile_image_url"] = bucket_base + str(path).lstrip("/")
    except Exception as e:
        print(f"[Banned accounts] Failed to fetch from Supabase: {e}")

    return render(
        request,
        "banned_accounts.html",
        {
            "members": members,
            "page_title": "Banned Accounts",
            "page_subtitle": "Accounts permanently banned from the RATEL Movement",
            "intro_text": "The following accounts have been permanently banned for serious or repeated violations of our code of conduct. Bans are not subject to appeal.",
            "empty_message": "There are no banned accounts at this time.",
        },
    )


def leadership(request):
    """Public leadership page with all leadership data from Supabase."""
    founding_vision = []
    leadership_council = []
    strategic_committees = []
    advisory_voices = []
    code_of_conduct = []

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
            "Accept": "application/json",
        }

        # Fetch founding vision
        resp = requests.get(
            f"{base_url}/rest/v1/founding_vision",
            headers=headers,
            params={"select": "*", "is_active": "eq.true", "order": "display_order.asc"},
            timeout=10
        )
        if resp.status_code == 200:
            founding_vision = resp.json()

        # Fetch leadership council
        resp = requests.get(
            f"{base_url}/rest/v1/leadership_council",
            headers=headers,
            params={"select": "*", "is_active": "eq.true", "order": "display_order.asc"},
            timeout=10
        )
        if resp.status_code == 200:
            leadership_council = resp.json()
            # Normalize image URLs
            for leader in leadership_council:
                leader["profile_image_url"] = _normalize_leadership_image_url(leader.get("profile_image_url"))

        # Fetch strategic committees
        resp = requests.get(
            f"{base_url}/rest/v1/strategic_committees",
            headers=headers,
            params={"select": "*", "is_active": "eq.true", "order": "display_order.asc"},
            timeout=10
        )
        if resp.status_code == 200:
            strategic_committees = resp.json()
            # Normalize image URLs
            for committee in strategic_committees:
                committee["profile_image_url"] = _normalize_leadership_image_url(committee.get("profile_image_url"))

        # Fetch advisory voices
        resp = requests.get(
            f"{base_url}/rest/v1/advisory_voices",
            headers=headers,
            params={"select": "*", "is_active": "eq.true", "order": "display_order.asc"},
            timeout=10
        )
        if resp.status_code == 200:
            advisory_voices = resp.json()
            # Normalize image URLs
            for advisor in advisory_voices:
                advisor["profile_image_url"] = _normalize_leadership_image_url(advisor.get("profile_image_url"))

        # Fetch code of conduct
        resp = requests.get(
            f"{base_url}/rest/v1/code_of_conduct",
            headers=headers,
            params={"select": "*", "is_active": "eq.true", "order": "display_order.asc"},
            timeout=10
        )
        if resp.status_code == 200:
            code_of_conduct = resp.json()

    except Exception as e:
        print(f"[Leadership] Error fetching data: {e}")

    return render(request, "leadership.html", {
        "founding_vision": founding_vision,
        "leadership_council": leadership_council,
        "strategic_committees": strategic_committees,
        "advisory_voices": advisory_voices,
        "code_of_conduct": code_of_conduct,
    })


def blog(request):
    """Public blog listing page - shows all published blogs with featured latest post and filtering."""
    blogs = []
    featured_blog = None
    all_categories = []
    all_tags = []
    trending_blogs = []

    # Get filter parameters
    category_filter = request.GET.get("category", "").strip()
    search_query = request.GET.get("q", "").strip()

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
            "Accept": "application/json",
        }

        # Build query URL with filters
        url = f"{base_url}/rest/v1/blogs?is_published=eq.true&select=*&order=published_at.desc,created_at.desc"

        if category_filter:
            url += f"&category=eq.{category_filter}"

        if search_query:
            # Search in title and content (use ilike for case-insensitive)
            url += f"&or=(title.ilike.*{search_query}*,excerpt.ilike.*{search_query}*)"

        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            blogs = resp.json()
            # Parse dates and normalize image URLs
            for b in blogs:
                for key in ("published_at", "created_at", "updated_at"):
                    val = b.get(key)
                    if val and isinstance(val, str) and val.strip():
                        try:
                            if "T" in val:
                                b[key] = datetime.fromisoformat(val.replace("Z", "+00:00"))
                            else:
                                b[key] = datetime.strptime(val, "%Y-%m-%d").date()
                        except (ValueError, TypeError):
                            b[key] = None

                # Normalize featured_image_url - ensure it's a full public URL
                if b.get("featured_image_url"):
                    b["featured_image_url"] = _normalize_blog_image_url(b["featured_image_url"], base_url)

            # Get featured blog (most recent) - only if no filters applied
            if blogs and not category_filter and not search_query:
                featured_blog = blogs[0]
                blogs = blogs[1:]  # Rest of blogs

        # Fetch all categories for filter sidebar (from all blogs, not filtered)
        cat_url = f"{base_url}/rest/v1/blogs?is_published=eq.true&select=category"
        cat_resp = requests.get(cat_url, headers=headers, timeout=10)
        if cat_resp.status_code == 200:
            categories_data = cat_resp.json()
            # Count categories
            cat_counts = {}
            for item in categories_data:
                cat = item.get("category", "general") or "general"
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
            all_categories = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)

        # Fetch trending blogs (most viewed)
        trending_url = f"{base_url}/rest/v1/blogs?is_published=eq.true&select=id,title,slug,category,view_count,published_at&order=view_count.desc&limit=5"
        trending_resp = requests.get(trending_url, headers=headers, timeout=10)
        if trending_resp.status_code == 200:
            trending_blogs = trending_resp.json()
            for b in trending_blogs:
                val = b.get("published_at")
                if val and isinstance(val, str) and val.strip():
                    try:
                        if "T" in val:
                            b["published_at"] = datetime.fromisoformat(val.replace("Z", "+00:00"))
                        else:
                            b["published_at"] = datetime.strptime(val, "%Y-%m-%d").date()
                    except (ValueError, TypeError):
                        b["published_at"] = None

        # Collect all unique tags
        tags_url = f"{base_url}/rest/v1/blogs?is_published=eq.true&select=tags"
        tags_resp = requests.get(tags_url, headers=headers, timeout=10)
        if tags_resp.status_code == 200:
            tags_data = tags_resp.json()
            tag_set = set()
            for item in tags_data:
                tags = item.get("tags") or []
                if isinstance(tags, list):
                    tag_set.update(tags)
            all_tags = sorted(list(tag_set))[:15]  # Limit to 15 tags

    except Exception as e:
        print(f"[Blog] Error fetching blogs: {e}")

    return render(request, "blog.html", {
        "blogs": blogs,
        "featured_blog": featured_blog,
        "all_categories": all_categories,
        "all_tags": all_tags,
        "trending_blogs": trending_blogs,
        "category_filter": category_filter,
        "search_query": search_query,
    })


def blog_detail(request, slug):
    """Public blog detail page with related blogs."""
    blog_post = None
    related_blogs = []
    
    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
            "Accept": "application/json",
        }
        
        # Fetch blog by slug
        url = f"{base_url}/rest/v1/blogs?slug=eq.{slug}&is_published=eq.true&select=*&limit=1"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200 and resp.json():
            blog_post = resp.json()[0]
            
            # Parse dates
            for key in ("published_at", "created_at", "updated_at"):
                val = blog_post.get(key)
                if val and isinstance(val, str) and val.strip():
                    try:
                        if "T" in val:
                            blog_post[key] = datetime.fromisoformat(val.replace("Z", "+00:00"))
                        else:
                            blog_post[key] = datetime.strptime(val, "%Y-%m-%d").date()
                    except (ValueError, TypeError):
                        blog_post[key] = None
            
            # Normalize featured_image_url - ensure it's a full public URL
            if blog_post.get("featured_image_url"):
                blog_post["featured_image_url"] = _normalize_blog_image_url(blog_post["featured_image_url"], base_url)
            
            # Increment view count
            try:
                view_count = blog_post.get("view_count", 0) or 0
                requests.patch(
                    f"{base_url}/rest/v1/blogs?id=eq.{blog_post.get('id')}",
                    headers=_get_supabase_headers(),
                    json={"view_count": view_count + 1},
                    timeout=5
                )
            except:
                pass
            
            # Fetch related blogs (same category, exclude current) - get 5 for sidebar
            category = blog_post.get("category", "")
            if category:
                related_url = f"{base_url}/rest/v1/blogs?category=eq.{category}&is_published=eq.true&slug=neq.{slug}&select=*&order=published_at.desc&limit=5"
                related_resp = requests.get(related_url, headers=headers, timeout=10)
                if related_resp.status_code == 200:
                    related_blogs = related_resp.json()
                    # Parse dates and normalize image URLs
                    for b in related_blogs:
                        for key in ("published_at", "created_at", "updated_at"):
                            val = b.get(key)
                            if val and isinstance(val, str) and val.strip():
                                try:
                                    if "T" in val:
                                        b[key] = datetime.fromisoformat(val.replace("Z", "+00:00"))
                                    else:
                                        b[key] = datetime.strptime(val, "%Y-%m-%d").date()
                                except (ValueError, TypeError):
                                    b[key] = None
                        
                        # Normalize featured_image_url for related blogs
                        if b.get("featured_image_url"):
                            b["featured_image_url"] = _normalize_blog_image_url(b["featured_image_url"], base_url)
    except Exception as e:
        print(f"[Blog Detail] Error: {e}")
    
    if not blog_post:
        from django.http import Http404
        raise Http404("Blog post not found")
    
    return render(request, "blog_detail.html", {
        "blog": blog_post,
        "related_blogs": related_blogs,
    })


def _get_supabase_headers_for_api():
    """Headers for Supabase REST API (comments/likes)."""
    return {
        "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def api_blog_comments_list(request):
    """GET ?blog_id=<uuid> — list all comments for a blog (flat, with parent_id for threading)."""
    blog_id = request.GET.get("blog_id", "").strip()
    if not blog_id:
        return JsonResponse({"success": False, "error": "blog_id required"}, status=400)
    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers_for_api()
        url = f"{base_url}/rest/v1/blog_comments?blog_id=eq.{blog_id}&select=*&order=created_at.asc"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return JsonResponse({"success": False, "error": "Failed to fetch comments"}, status=502)
        comments = resp.json()
        # Serialize dates
        for c in comments:
            for key in ("created_at", "updated_at"):
                if c.get(key) and isinstance(c[key], str):
                    try:
                        c[key] = c[key].replace("Z", "+00:00")[:19]
                    except Exception:
                        pass
        return JsonResponse({"success": True, "comments": comments})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_POST
def api_blog_comment_create(request):
    """POST JSON: blog_id, parent_id (optional), author_name, author_email (optional), body."""
    try:
        import json
        body = json.loads(request.body) if request.body else {}
    except Exception:
        body = request.POST.dict()
    blog_id = (body.get("blog_id") or "").strip()
    parent_id = (body.get("parent_id") or "").strip() or None
    author_name = (body.get("author_name") or "").strip()
    author_email = (body.get("author_email") or "").strip()
    comment_body = (body.get("body") or "").strip()
    if not blog_id or not author_name or not comment_body:
        return JsonResponse({"success": False, "error": "blog_id, author_name, and body are required"}, status=400)
    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers_for_api()
        payload = {
            "blog_id": blog_id,
            "author_name": author_name,
            "body": comment_body,
        }
        if author_email:
            payload["author_email"] = author_email
        if parent_id:
            payload["parent_id"] = parent_id
        url = f"{base_url}/rest/v1/blog_comments"
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code not in (200, 201):
            return JsonResponse({"success": False, "error": resp.text or "Failed to create comment"}, status=400)
        data = resp.json()
        created = data[0] if isinstance(data, list) else data
        for key in ("created_at", "updated_at"):
            if created.get(key) and isinstance(created[key], str):
                created[key] = created[key].replace("Z", "+00:00")[:19]
        return JsonResponse({"success": True, "comment": created})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_POST
def api_blog_comment_like(request):
    """POST JSON: comment_id, visitor_fingerprint. Toggle like (insert or delete). Returns { liked, like_count }."""
    try:
        import json
        body = json.loads(request.body) if request.body else {}
    except Exception:
        body = request.POST.dict()
    comment_id = (body.get("comment_id") or "").strip()
    visitor_fingerprint = (body.get("visitor_fingerprint") or "").strip()
    if not comment_id or not visitor_fingerprint:
        return JsonResponse({"success": False, "error": "comment_id and visitor_fingerprint required"}, status=400)
    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers_for_api()
        # Check if already liked
        check_url = f"{base_url}/rest/v1/blog_comment_likes?comment_id=eq.{comment_id}&visitor_fingerprint=eq.{visitor_fingerprint}&select=id"
        check = requests.get(check_url, headers=headers, timeout=10)
        existing = check.json() if check.status_code == 200 else []
        if existing:
            # Unlike: delete row
            like_id = existing[0]["id"]
            requests.delete(f"{base_url}/rest/v1/blog_comment_likes?id=eq.{like_id}", headers=headers, timeout=10)
            # Get new like_count
            count_resp = requests.get(f"{base_url}/rest/v1/blog_comments?id=eq.{comment_id}&select=like_count", headers=headers, timeout=10)
            like_count = 0
            if count_resp.status_code == 200 and count_resp.json():
                like_count = count_resp.json()[0].get("like_count", 0)
            return JsonResponse({"success": True, "liked": False, "like_count": like_count})
        else:
            # Like: insert
            requests.post(f"{base_url}/rest/v1/blog_comment_likes", headers=headers, json={"comment_id": comment_id, "visitor_fingerprint": visitor_fingerprint}, timeout=10)
            count_resp = requests.get(f"{base_url}/rest/v1/blog_comments?id=eq.{comment_id}&select=like_count", headers=headers, timeout=10)
            like_count = 0
            if count_resp.status_code == 200 and count_resp.json():
                like_count = count_resp.json()[0].get("like_count", 0)
            return JsonResponse({"success": True, "liked": True, "like_count": like_count})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def api_blog_comment_likes_check(request):
    """GET ?comment_ids=id1,id2&fingerprint=xxx — return which of those comments the visitor has liked."""
    comment_ids = (request.GET.get("comment_ids") or "").strip()
    fingerprint = (request.GET.get("visitor_fingerprint") or request.GET.get("fingerprint") or "").strip()
    if not comment_ids or not fingerprint:
        return JsonResponse({"success": True, "liked_ids": []})
    ids_list = [x.strip() for x in comment_ids.split(",") if x.strip()]
    if not ids_list:
        return JsonResponse({"success": True, "liked_ids": []})
    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers_for_api()
        # Filter: comment_id in (id1, id2, ...) and visitor_fingerprint = fingerprint
        filter_ids = "&".join([f"comment_id=eq.{cid}" for cid in ids_list])
        url = f"{base_url}/rest/v1/blog_comment_likes?visitor_fingerprint=eq.{fingerprint}&select=comment_id"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return JsonResponse({"success": True, "liked_ids": []})
        rows = resp.json()
        liked_ids = [r["comment_id"] for r in rows if r.get("comment_id") in ids_list]
        return JsonResponse({"success": True, "liked_ids": liked_ids})
    except Exception:
        return JsonResponse({"success": True, "liked_ids": []})


def features(request):
    return render(request, "features.html")


def contact(request):
    return render(request, "contact.html")


def messages_page(request):
    """Public messages page for sharing content."""
    messages_list = []
    total_messages = 0
    total_shares = 0
    total_downloads = 0
    category_counts = {}

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
            "Accept": "application/json",
        }

        # Fetch active messages
        resp = requests.get(
            f"{base_url}/rest/v1/shareable_messages?is_active=eq.true&select=*&order=is_featured.desc,display_order.asc,created_at.desc",
            headers=headers,
            timeout=10
        )
        if resp.status_code == 200:
            messages_list = resp.json()
            total_messages = len(messages_list)

            # Calculate totals and category counts
            for msg in messages_list:
                total_shares += msg.get("share_count", 0)
                total_downloads += msg.get("download_count", 0)
                category = msg.get("category", "other")
                category_counts[category] = category_counts.get(category, 0) + 1

    except Exception as e:
        print(f"[Messages Page] Error: {e}")

    return render(request, "messages.html", {
        "messages_list": messages_list,
        "total_messages": total_messages,
        "total_shares": total_shares,
        "total_downloads": total_downloads,
        "category_counts": category_counts,
    })


def auth_page(request):
    """
    Auth page with login and signup forms.
    First-time members must pay membership fee before registration.
    """
    # Get membership fee settings from Supabase
    membership_fee = 500  # Default
    currency = "NGN"

    try:
        sb = get_supabase()
        settings_resp = sb.table("membership_settings").select("*").execute()
        if settings_resp.data and len(settings_resp.data) > 0:
            settings_data = settings_resp.data[0]
            membership_fee = settings_data.get("fee_amount", 500)
            currency = settings_data.get("currency", "NGN")
    except Exception as e:
        print(f"[Auth Page] Error fetching membership settings: {e}")

    # Convert to GHS for payment
    EXCHANGE_RATES_TO_GHS = {
        "GHS": 1.0,
        "NGN": 0.0076,
        "USD": 15.5,
        "GBP": 19.5,
        "EUR": 16.8,
    }
    exchange_rate = EXCHANGE_RATES_TO_GHS.get(currency, 1.0)
    membership_fee_ghs = round(membership_fee * exchange_rate, 2)
    if currency == "GHS":
        membership_fee_ghs = membership_fee

    # Paystack public key (Supabase overrides env when set)
    paystack_public_key, _ = _get_paystack_keys()

    context = {
        "auth_bg_image": None,
        "user_registration_enabled": True,
        "membership_fee": membership_fee,
        "membership_fee_ghs": membership_fee_ghs,
        "currency": currency,
        "paystack_public_key": paystack_public_key,
    }
    return render(request, "auth.html", context)


# ---------- Helper functions ----------

NIGERIA_STATE_CODES = {
    "Abia": "ABI",
    "Adamawa": "ADA",
    "Akwa Ibom": "AKW",
    "Anambra": "ANA",
    "Bauchi": "BAU",
    "Bayelsa": "BAY",
    "Benue": "BEN",
    "Borno": "BOR",
    "Cross River": "CRS",
    "Delta": "DEL",
    "Ebonyi": "EBO",
    "Edo": "EDO",
    "Ekiti": "EKT",
    "Enugu": "ENU",
    "Gombe": "GOM",
    "Imo": "IMO",
    "Jigawa": "JIG",
    "Kaduna": "KAD",
    "Kano": "KAN",
    "Katsina": "KAT",
    "Kebbi": "KEB",
    "Kogi": "KOG",
    "Kwara": "KWA",
    "Lagos": "LAG",
    "Nasarawa": "NAS",
    "Niger": "NIG",
    "Ogun": "OGU",
    "Ondo": "OND",
    "Osun": "OSU",
    "Oyo": "OYO",
    "Plateau": "PLA",
    "Rivers": "RIV",
    "Sokoto": "SOK",
    "Taraba": "TAR",
    "Yobe": "YOB",
    "Zamfara": "ZAM",
    "Federal Capital Territory (FCT)": "FCT",
}


def _get_region_key(based_in_nigeria: bool, state: str | None, country: str | None) -> str:
    """
    Build a region key used for member ID generation.
    Example: NG-LAG for Lagos, or INT-USA for foreigners.
    """
    if based_in_nigeria:
        code = NIGERIA_STATE_CODES.get(state or "", "UNK")
        return f"NG-{code}"
    # Foreigner: build a 3-letter code from country name
    if not country:
        return "INT-UNK"
    letters = "".join(ch for ch in country.upper() if ch.isalpha())
    if len(letters) >= 3:
        code = letters[:3]
    else:
        code = (letters + "XXX")[:3]
    return f"INT-{code}"


def _generate_member_id(region_key: str) -> str:
    """
    Call Supabase RPC get_next_member_number to get the next counter
    and format a RATEL member ID like RATEL-NG-LAG-000245.
    """
    base_url = settings.SUPABASE_URL.rstrip("/")
    rpc_url = f"{base_url}/rest/v1/rpc/get_next_member_number"
    headers = {
        "apikey": settings.SUPABASE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(rpc_url, headers=headers, json={"p_region_key": region_key}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # Supabase RPC may return a bare integer or a dict
        if isinstance(data, int):
            number = data
        elif isinstance(data, dict):
            # fall back to first value
            number = list(data.values())[0]
        else:
            raise ValueError("Unexpected RPC response format")
    except Exception:
        # Fallback: random 6‑digit number (still unique-ish) if RPC fails
        random_num = get_random_string(6, allowed_chars="0123456789")
        return f"RATEL-{region_key}-{random_num}"

    return f"RATEL-{region_key}-{int(number):06d}"


def _create_member_in_supabase(
    member_id: str,
    full_name: str,
    email: str,
    phone_number: str,
    password_hash: str,
    profile_image_url: str | None,
    based_in_nigeria: bool,
    state: str | None,
    lga: str | None,
    country: str | None,
    city: str | None,
    engagement_preferences: list[str] | None,
):
    base_url = settings.SUPABASE_URL.rstrip("/")
    table_url = f"{base_url}/rest/v1/members"
    headers = {
        "apikey": settings.SUPABASE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    payload = {
        "member_id": member_id,
        "full_name": full_name,
        "email": email,
        "phone_number": phone_number,
        "password_hash": password_hash,
        "profile_image_url": profile_image_url,
        "based_in_nigeria": based_in_nigeria,
        "state": state,
        "lga": lga,
        "country": country,
        "city": city,
        "engagement_preferences": engagement_preferences or [],
        "status": "active",
    }

    resp = requests.post(table_url, headers=headers, json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _upload_profile_image_to_supabase(member_id: str, file_obj) -> str | None:
    """
    Upload the given profile image file to the Supabase "profiles" bucket.
    Returns the public URL if successful, or None on failure.
    """
    if not file_obj:
        return None

    try:
        supabase = get_supabase()
    except Exception as e:
        # If Supabase client cannot be created, don't block signup
        print(f"[Supabase] Failed to init client for profile upload: {e}")
        return None

    # Build a stable path: member_id/randomSuffix.ext
    original_name = getattr(file_obj, "name", "profile.jpg")
    _, ext = os.path.splitext(original_name)
    if not ext:
        ext = ".jpg"
    random_suffix = get_random_string(8)
    path = f"{member_id}/{random_suffix}{ext}"

    try:
        content = file_obj.read()
        storage = supabase.storage.from_("profiles")
        storage.upload(path, content)
        public_url = storage.get_public_url(path)
        return public_url
    except Exception as e:
        # Log but do not fail the whole registration
        print(f"[Supabase] Failed to upload profile image: {e}")
        return None


def _upload_leadership_image_to_supabase(table_name: str, item_id: str, file_obj) -> str | None:
    """
    Upload the given profile image file to the Supabase "leadership" bucket.
    Returns the public URL if successful, or None on failure.
    
    Args:
        table_name: The table name (e.g., 'leadership_council', 'strategic_committees', 'advisory_voices')
        item_id: The ID of the item (or a generated identifier if creating new)
        file_obj: The file object to upload
    """
    if not file_obj:
        return None

    try:
        supabase = get_supabase()
    except Exception as e:
        print(f"[Supabase] Failed to init client for leadership image upload: {e}")
        return None

    # Build a stable path: table_name/item_id/randomSuffix.ext
    original_name = getattr(file_obj, "name", "profile.jpg")
    _, ext = os.path.splitext(original_name)
    if not ext:
        ext = ".jpg"
    random_suffix = get_random_string(8)
    # Use item_id if available, otherwise generate a temporary identifier
    identifier = item_id if item_id else get_random_string(12)
    path = f"{table_name}/{identifier}/{random_suffix}{ext}"

    try:
        content = file_obj.read()
        storage = supabase.storage.from_("leadership")
        # Determine content type based on extension
        ext_lower = ext.lstrip('.').lower()
        content_type_map = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp',
        }
        content_type = content_type_map.get(ext_lower, 'image/jpeg')
        storage.upload(path, content, file_options={"content-type": content_type})
        public_url = storage.get_public_url(path)
        return public_url
    except Exception as e:
        print(f"[Supabase] Failed to upload leadership image: {e}")
        return None


def _normalize_leadership_image_url(image_url: str | None) -> str | None:
    """
    Normalize leadership image URL to a full public URL if only a path is stored.
    """
    if not image_url:
        return None
    
    if str(image_url).startswith("http"):
        return image_url
    
    base_url = settings.SUPABASE_URL.rstrip("/")
    bucket_base = f"{base_url}/storage/v1/object/public/leadership/"
    return bucket_base + str(image_url).lstrip("/")


def _send_welcome_email(request, email: str, full_name: str, member_id: str):
    """
    Send a rich welcome email including member ID, badge download, resources links, and responsibilities.
    """
    from django.urls import reverse
    from datetime import datetime
    
    # Build absolute URLs using request to get the current host
    base_url = request.build_absolute_uri('/').rstrip('/')
    
    member_resources_url = request.build_absolute_uri(reverse('member_resources'))
    badge_download_url = request.build_absolute_uri(reverse('member_dashboard'))  # Badge download is on dashboard
    website_url = base_url
    
    subject = "Welcome to the RATEL Movement"
    context = {
        "full_name": full_name,
        "member_id": member_id,
        "member_resources_url": member_resources_url,
        "badge_download_url": badge_download_url,
        "website_url": website_url,
        "current_year": datetime.now().year,
    }
    html_message = render_to_string("emails/welcome_member.html", context)
    plain_message = strip_tags(html_message)
    from_email = settings.DEFAULT_FROM_EMAIL

    send_mail(
        subject,
        plain_message,
        from_email,
        [email],
        html_message=html_message,
        fail_silently=True,
    )


def _send_donation_thank_you(request, donor_email: str, donor_name: str, amount: float):
    """Send thank-you email to donor after successful donation."""
    subject = "Thank you for your donation - RATEL Movement"
    context = {
        "donor_name": donor_name or "Valued Supporter",
        "amount": f"{amount:,.2f}".rstrip("0").rstrip("."),
        "current_year": datetime.now().year,
    }
    html_message = render_to_string("emails/donation_thank_you.html", context)
    plain_message = strip_tags(html_message)
    try:
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [donor_email],
            html_message=html_message,
            fail_silently=True,
        )
    except Exception as e:
        print(f"[Donation Thank You Email] Error: {e}")


def _send_renewal_thank_you(request, member_email: str, member_name: str, member_id: str, end_date: str):
    """Send thank-you email to member after successful membership renewal."""
    from django.urls import reverse
    subject = "Thank you for renewing - RATEL Movement"
    member_dashboard_url = request.build_absolute_uri(reverse("member_dashboard"))
    context = {
        "member_name": member_name or "Member",
        "member_id": member_id or "—",
        "end_date": end_date,
        "member_dashboard_url": member_dashboard_url,
        "current_year": datetime.now().year,
    }
    html_message = render_to_string("emails/renewal_thank_you.html", context)
    plain_message = strip_tags(html_message)
    try:
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [member_email],
            html_message=html_message,
            fail_silently=True,
        )
    except Exception as e:
        print(f"[Renewal Thank You Email] Error: {e}")


@require_POST
def auth_signup(request):
    """
    AJAX endpoint: /auth/signup/
    First-time members must pay membership fee before registration.
    Verifies Paystack payment, creates member record, then creates subscription record.
    """
    from datetime import datetime, timedelta

    # Get membership fee settings
    membership_fee = 500
    currency = "NGN"
    try:
        sb = get_supabase()
        settings_resp = sb.table("membership_settings").select("*").execute()
        if settings_resp.data and len(settings_resp.data) > 0:
            settings_data = settings_resp.data[0]
            membership_fee = settings_data.get("fee_amount", 500)
            currency = settings_data.get("currency", "NGN")
    except Exception:
        pass

    full_name = request.POST.get("full_name", "").strip()
    email = request.POST.get("email", "").strip().lower()
    phone_number = request.POST.get("phone_number", "").strip()
    password = request.POST.get("password", "")
    based_in_nigeria = request.POST.get("based_in_nigeria") == "yes"
    state = request.POST.get("state") or None
    lga = request.POST.get("lga") or None
    country = request.POST.get("country") or None
    city = request.POST.get("city") or None
    engagement_preferences = request.POST.getlist("engagement_preferences")
    profile_image_file = request.FILES.get("profile_image")
    payment_reference = request.POST.get("payment_reference", "").strip()

    errors: list[str] = []

    if not full_name:
        errors.append("Full name is required.")
    if not email:
        errors.append("Email is required.")
    if not phone_number:
        errors.append("Phone number is required.")
    if not password:
        errors.append("Password is required.")
    if not payment_reference:
        errors.append("Payment is required before registration.")

    if based_in_nigeria:
        if not state:
            errors.append("State is required for members based in Nigeria.")
    else:
        if not country:
            errors.append("Country of residence is required for foreign members.")

    if errors:
        return JsonResponse({"success": False, "errors": errors}, status=400)

    # Verify payment with Paystack (Supabase overrides env when set)
    _, paystack_secret_key = _get_paystack_keys()

    try:
        verify_resp = requests.get(
            f"https://api.paystack.co/transaction/verify/{payment_reference}",
            headers={
                "Authorization": f"Bearer {paystack_secret_key}",
                "Content-Type": "application/json",
            },
            timeout=30
        )
        verify_data = verify_resp.json()

        if not verify_data.get("status") or verify_data.get("data", {}).get("status") != "success":
            return JsonResponse(
                {"success": False, "errors": ["Payment verification failed. Please try again."]},
                status=400,
            )

        print(f"[Auth Signup] Payment verified successfully: {payment_reference}")
    except Exception as e:
        print(f"[Auth Signup] Payment verification error: {e}")
        return JsonResponse(
            {"success": False, "errors": ["Could not verify payment. Please try again."]},
            status=500,
        )

    from django.contrib.auth.hashers import make_password

    password_hash = make_password(password)

    region_key = _get_region_key(based_in_nigeria, state, country)
    member_id = _generate_member_id(region_key)

    # Optional: upload profile image to Supabase "profiles" bucket
    profile_image_url = None
    if profile_image_file:
        profile_image_url = _upload_profile_image_to_supabase(member_id, profile_image_file)

    # Calculate subscription dates (1 month from now)
    subscription_start = datetime.utcnow()
    subscription_end = subscription_start + timedelta(days=30)

    try:
        # Check if email already exists in Supabase
        sb = get_supabase()
        existing = sb.table("members").select("id").eq("email", email).execute()
        if existing.data and len(existing.data) > 0:
            return JsonResponse(
                {"success": False, "errors": ["An account with this email already exists. Please login instead."]},
                status=400,
            )

        # Save member to Supabase
        _create_member_in_supabase(
            member_id=member_id,
            full_name=full_name,
            email=email,
            phone_number=phone_number,
            password_hash=password_hash,
            profile_image_url=profile_image_url,
            based_in_nigeria=based_in_nigeria,
            state=state,
            lga=lga,
            country=country,
            city=city,
            engagement_preferences=engagement_preferences,
        )

        # Create initial subscription record in member_subscriptions
        try:
            base_url = settings.SUPABASE_URL.rstrip("/")
            headers = {
                "apikey": settings.SUPABASE_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            }
            now = datetime.utcnow()
            subscription_payload = {
                "member_id": member_id,
                "member_email": email,
                "amount_paid": membership_fee,
                "months_subscribed": 1,
                "start_date": subscription_start.isoformat(),
                "end_date": subscription_end.isoformat(),
                "status": "active",
                "payment_reference": payment_reference,
                "payment_method": "paystack",
                "created_at": now.isoformat(),
            }
            sub_resp = requests.post(
                f"{base_url}/rest/v1/member_subscriptions",
                headers=headers,
                json=subscription_payload,
                timeout=10
            )
            if sub_resp.status_code not in [200, 201]:
                error_detail = sub_resp.text
                print(f"[Auth Signup] Subscription creation failed: {sub_resp.status_code} - {error_detail}")
                # Return error to user since subscription is essential
                return JsonResponse(
                    {"success": False, "errors": [f"Failed to activate subscription: {error_detail}"]},
                    status=500,
                )
            sub_resp.raise_for_status()
            print(f"[Auth Signup] Subscription created successfully for {member_id}")
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                error_msg = f"{e} - Response: {e.response.text}"
            print(f"[Auth Signup] Subscription record creation error: {error_msg}")
            return JsonResponse(
                {"success": False, "errors": [f"Failed to activate subscription. Please contact support."]},
                status=500,
            )

        # Send welcome email (non-blocking for user experience)
        _send_welcome_email(request, email, full_name, member_id)

        return JsonResponse(
            {
                "success": True,
                "message": "Payment successful! Welcome to the RATEL Movement.",
                "member_id": member_id,
            }
        )
    except requests.HTTPError as e:
        try:
            detail = e.response.json()
        except Exception:
            detail = e.response.text
        return JsonResponse(
            {
                "success": False,
                "errors": ["Failed to save your registration. Please try again.", str(detail)],
            },
            status=500,
        )
    except Exception as e:
        return JsonResponse(
            {"success": False, "errors": [f"Unexpected error: {e}"]},
            status=500,
        )


@require_POST
def auth_login(request):
    """
    AJAX endpoint: /auth/login/
    Authenticates directly against Supabase members table.
    Stores member info in session for authentication.
    """
    from django.contrib.auth.hashers import check_password

    email = request.POST.get("email", "").strip().lower()
    password = request.POST.get("password", "")

    print(f"[DEBUG] Login attempt for email: {email}")

    if not email or not password:
        print(f"[DEBUG] Missing email or password")
        return JsonResponse(
            {"success": False, "errors": ["Email and password are required."]},
            status=400,
        )

    # Hardcoded admin credentials check
    ADMIN_EMAIL = "ratelmovement@gmail.com"
    ADMIN_PASSWORD = "Scholar2025@"
    
    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        print(f"[DEBUG] Admin login detected for: {email}")
        # Set admin session
        request.session["member_id"] = "admin"
        request.session["member_email"] = ADMIN_EMAIL
        request.session["member_name"] = "Admin"
        request.session["member_member_id"] = "ADMIN"
        request.session["is_authenticated"] = True
        request.session["is_admin"] = True
        request.session.modified = True

        welcome_message = "Welcome back, Admin!"
        redirect_url = request.POST.get("next") or "/dashboard/"

        return JsonResponse(
            {
                "success": True,
                "message": "Login successful.",
                "welcome_message": welcome_message,
                "redirect_url": redirect_url,
            }
        )

    # Authenticate against Supabase members table
    try:
        sb = get_supabase()
        result = sb.table("members").select("*").eq("email", email).execute()

        if not result.data or len(result.data) == 0:
            print(f"[DEBUG] No member found in Supabase with email: {email}")
            return JsonResponse(
                {"success": False, "errors": ["No account found with this email address. Please sign up first."]},
                status=400,
            )

        member = result.data[0]
        print(f"[DEBUG] Found member in Supabase: {member.get('full_name')}")

        # Block suspended and banned users from logging in
        member_status = (member.get("status") or "active").strip().lower()
        if member_status == "suspended":
            return JsonResponse(
                {"success": False, "errors": ["Your account has been suspended. Please contact the movement administrators."]},
                status=403,
            )
        if member_status == "banned":
            return JsonResponse(
                {"success": False, "errors": ["Your account has been permanently banned."]},
                status=403,
            )

        # Verify password against stored hash
        stored_hash = member.get("password_hash", "")
        if not stored_hash:
            print(f"[DEBUG] No password hash found for member")
            return JsonResponse(
                {"success": False, "errors": ["Account error. Please contact support."]},
                status=400,
            )

        if not check_password(password, stored_hash):
            print(f"[DEBUG] Invalid password for: {email}")
            return JsonResponse(
                {"success": False, "errors": ["Invalid password. Please try again."]},
                status=400,
            )

        # Password is correct - store member info in session
        request.session["member_id"] = member.get("id")
        request.session["member_email"] = member.get("email")
        request.session["member_name"] = member.get("full_name")
        request.session["member_member_id"] = member.get("member_id")
        request.session["is_authenticated"] = True
        request.session.modified = True

        print(f"[DEBUG] Login successful for: {email}")

        welcome_message = f"Welcome back, {member.get('full_name', 'member')}!"
        redirect_url = request.POST.get("next") or "/member/"

        return JsonResponse(
            {
                "success": True,
                "message": "Login successful.",
                "welcome_message": welcome_message,
                "redirect_url": redirect_url,
            }
        )

    except Exception as e:
        print(f"[DEBUG] Error during login: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse(
            {"success": False, "errors": ["An error occurred. Please try again."]},
            status=500,
        )


@require_POST
def auth_forgot_password(request):
    """
    AJAX endpoint: /auth/forgot-password/
    Generates a password reset token and sends email.
    Uses Supabase members table directly.
    """
    import hashlib
    import secrets

    email = request.POST.get("email", "").strip().lower()
    if not email:
        return JsonResponse(
            {"success": False, "errors": ["Email address is required."]},
            status=400,
        )

    print(f"[DEBUG] Password reset request for: {email}")

    try:
        sb = get_supabase()
        result = sb.table("members").select("id, full_name, email").eq("email", email).execute()

        if not result.data or len(result.data) == 0:
            print(f"[DEBUG] No member found in Supabase with email: {email}")
            # Still return success to prevent email enumeration
            return JsonResponse(
                {
                    "success": True,
                    "message": "If an account exists with that email, a password reset link has been sent.",
                }
            )

        member = result.data[0]
        print(f"[DEBUG] Found member: {member.get('full_name')}")

        # Generate a secure reset token
        reset_token = secrets.token_urlsafe(32)
        token_expiry = (datetime.now() + timedelta(hours=1)).isoformat()

        # Store token in Supabase (update member record)
        sb.table("members").update({
            "reset_token": reset_token,
            "reset_token_expiry": token_expiry
        }).eq("id", member.get("id")).execute()

        # Build reset URL
        protocol = "https" if request.is_secure() else "http"
        domain = request.get_host()
        reset_url = f"{protocol}://{domain}/auth/reset/{reset_token}/"

        # Send email
        subject = "Reset your RATEL Movement password"
        message = f"""Hello {member.get('full_name', '')},

You (or someone else) requested a password reset for your RATEL Movement account.

If you made this request, click the link below to reset your password:
{reset_url}

This link will expire in 1 hour.

If you did not request this, you can ignore this email and your password will remain unchanged.

Neutrality is complicity.
"""
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            print(f"[DEBUG] Password reset email sent to: {email}")
        except Exception as e:
            print(f"[DEBUG] Error sending email: {e}")
            # Still return success to prevent revealing email issues
            pass

        return JsonResponse(
            {
                "success": True,
                "message": "If an account exists with that email, a password reset link has been sent.",
            }
        )

    except Exception as e:
        print(f"[DEBUG] Error during password reset: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse(
            {
                "success": True,
                "message": "If an account exists with that email, a password reset link has been sent.",
            }
        )


def auth_password_reset_confirm(request, token):
    """
    Password reset confirm page - allows user to set new password.
    Validates token against Supabase members table.
    """
    from django.contrib.auth.hashers import make_password

    print(f"[DEBUG] Password reset confirm with token: {token[:10]}...")

    # Check if token is valid
    try:
        sb = get_supabase()
        result = sb.table("members").select("id, email, full_name, reset_token, reset_token_expiry").eq("reset_token", token).execute()

        if not result.data or len(result.data) == 0:
            print(f"[DEBUG] Invalid or expired reset token")
            return render(request, "auth_password_reset_confirm.html", {
                "valid_link": False,
                "error": "This password reset link is invalid or has expired."
            })

        member = result.data[0]

        # Check if token has expired
        expiry_str = member.get("reset_token_expiry")
        if expiry_str:
            try:
                expiry = datetime.fromisoformat(expiry_str.replace("Z", "+00:00").replace("+00:00", ""))
                if datetime.now() > expiry:
                    print(f"[DEBUG] Token has expired")
                    return render(request, "auth_password_reset_confirm.html", {
                        "valid_link": False,
                        "error": "This password reset link has expired. Please request a new one."
                    })
            except Exception as e:
                print(f"[DEBUG] Error parsing expiry: {e}")

        if request.method == "POST":
            password = request.POST.get("password", "")
            password_confirm = request.POST.get("password_confirm", "")

            errors = []
            if not password:
                errors.append("Password is required.")
            elif len(password) < 8:
                errors.append("Password must be at least 8 characters.")
            if password != password_confirm:
                errors.append("Passwords do not match.")

            if errors:
                return render(request, "auth_password_reset_confirm.html", {
                    "valid_link": True,
                    "errors": errors,
                    "token": token,
                })

            # Update password in Supabase
            password_hash = make_password(password)
            sb.table("members").update({
                "password_hash": password_hash,
                "reset_token": None,
                "reset_token_expiry": None
            }).eq("id", member.get("id")).execute()

            print(f"[DEBUG] Password updated in Supabase for: {member.get('email')}")

            return redirect("password_reset_complete")

        # GET request - show the form
        return render(request, "auth_password_reset_confirm.html", {
            "valid_link": True,
            "token": token,
        })

    except Exception as e:
        print(f"[DEBUG] Error in password reset confirm: {e}")
        import traceback
        traceback.print_exc()
        return render(request, "auth_password_reset_confirm.html", {
            "valid_link": False,
            "error": "An error occurred. Please try again."
        })


def auth_password_reset_complete(request):
    """
    Password reset complete page - shows success message.
    """
    return render(request, "auth_password_reset_complete.html")


def auth_logout(request):
    """
    Logs out the user by clearing session data.
    """
    # Clear all session data
    request.session.flush()
    return redirect("/auth/")


# --- Dashboard Views ---


def dashboard_home(request):
    """
    Admin dashboard home - shows overview stats and recent activity.
    """
    # Check authentication - allow admin or authenticated users
    if not request.session.get("is_authenticated"):
        return redirect(f"/auth/?next=/dashboard/")
    
    # Allow admin email or any authenticated user
    member_email = request.session.get("member_email", "")
    ADMIN_EMAIL = "ratelmovement@gmail.com"
    
    # If not admin, redirect to member dashboard
    if member_email != ADMIN_EMAIL and not request.session.get("is_admin"):
        return redirect("/member/")
    
    from datetime import datetime, timedelta

    # Initialize stats
    total_members = 0
    nigerian_members = 0
    foreign_members = 0
    pending_members = 0
    recent_members = []
    recent_announcements = []
    announcements_count = 0
    communications_count = 0

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        # Fetch all members for stats
        members_resp = requests.get(
            f"{base_url}/rest/v1/members?select=member_id,full_name,email,based_in_nigeria,state,country,created_at,status,profile_image_url&order=created_at.desc",
            headers=headers,
            timeout=10
        )
        if members_resp.status_code == 200:
            members = members_resp.json()
            total_members = len(members)
            nigerian_members = sum(1 for m in members if m.get("based_in_nigeria") == True)
            foreign_members = total_members - nigerian_members
            pending_members = sum(1 for m in members if m.get("status") == "pending")
            recent_members = members[:5]  # Get 5 most recent

            # Normalize profile image URLs
            bucket_base = f"{base_url}/storage/v1/object/public/profiles/"
            for m in recent_members:
                path = m.get("profile_image_url")
                if path and not str(path).startswith("http"):
                    m["profile_image_url"] = bucket_base + str(path).lstrip("/")

        # Fetch announcements count
        ann_resp = requests.get(
            f"{base_url}/rest/v1/internal_announcements?select=id&is_active=eq.true",
            headers=headers,
            timeout=10
        )
        if ann_resp.status_code == 200:
            announcements_count = len(ann_resp.json())

        # Fetch recent announcements
        ann_recent_resp = requests.get(
            f"{base_url}/rest/v1/internal_announcements?select=id,title,recipient_type,priority,created_at&is_active=eq.true&order=created_at.desc&limit=3",
            headers=headers,
            timeout=10
        )
        if ann_recent_resp.status_code == 200:
            recent_announcements = ann_recent_resp.json()

        # Fetch communications count
        comm_resp = requests.get(
            f"{base_url}/rest/v1/secure_communications?select=id&is_active=eq.true",
            headers=headers,
            timeout=10
        )
        if comm_resp.status_code == 200:
            communications_count = len(comm_resp.json())

    except Exception as e:
        print(f"[Dashboard] Error fetching stats: {e}")

    context = {
        "active_page": "dashboard",
        "total_members": total_members,
        "nigerian_members": nigerian_members,
        "foreign_members": foreign_members,
        "pending_members": pending_members,
        "recent_members": recent_members,
        "recent_announcements": recent_announcements,
        "announcements_count": announcements_count,
        "communications_count": communications_count,
    }

    return render(request, "dashboard/dashboard.html", context)


def dashboard_contacts(request):
    """
    Membership view: show all registered members from Supabase.
    Redirects ?filter=suspended and ?filter=banned to the public pages.
    """
    status_filter = (request.GET.get("filter") or "").strip().lower()
    if status_filter == "suspended":
        return redirect("suspended_members")
    if status_filter == "banned":
        return redirect("banned_accounts")

    members = []
    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        table_url = f"{base_url}/rest/v1/members"
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
            "Accept": "application/json",
        }
        # First try with extended fields (membership_type, status)
        params_full = {
            "select": "member_id,full_name,email,phone_number,based_in_nigeria,state,lga,country,city,engagement_preferences,created_at,membership_type,status,profile_image_url",
            "order": "created_at.desc",
        }
        if status_filter == "suspended":
            params_full["status"] = "eq.suspended"
        elif status_filter == "banned":
            params_full["status"] = "eq.banned"
        resp = requests.get(table_url, headers=headers, params=params_full, timeout=10)
        if resp.status_code == 200:
            members = resp.json()
        else:
            # Fallback: request only the original columns, in case new ones aren't present yet
            params_min = {
                "select": "member_id,full_name,email,phone_number,based_in_nigeria,state,lga,country,city,engagement_preferences,created_at,profile_image_url",
                "order": "created_at.desc",
            }
            resp2 = requests.get(table_url, headers=headers, params=params_min, timeout=10)
            resp2.raise_for_status()
            members = resp2.json()
            if status_filter in ("suspended", "banned"):
                members = [m for m in members if (m.get("status") or "").lower() == status_filter]

        # Normalise profile_image_url to a full public URL if only a path is stored
        bucket_base = settings.SUPABASE_URL.rstrip("/") + "/storage/v1/object/public/profiles/"
        for m in members:
            path = m.get("profile_image_url")
            if path and not str(path).startswith("http"):
                m["profile_image_url"] = bucket_base + str(path).lstrip("/")
    except Exception as e:
        # In case of error, just show empty table and avoid crashing dashboard
        print(f"[Membership] Failed to fetch members from Supabase: {e}")

    return render(
        request,
        "dashboard/contacts.html",
        {
            "active_page": "contacts",
            "members": members,
            "status_filter": status_filter,
        },
    )


@require_POST
def membership_manage(request):
    """
    Handle membership actions: assign role, suspend/unsuspend, delete.
    Also keep Django auth user roughly in sync and send notification email.
    """
    action = request.POST.get("action")
    member_id = request.POST.get("member_id")
    email = request.POST.get("email")

    if not member_id or not action:
        messages.error(request, "Invalid membership action.")
        return redirect("dashboard_membership")

    base_url = settings.SUPABASE_URL.rstrip("/")
    table_url = f"{base_url}/rest/v1/members"
    headers = {
        "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    payload = {}
    subject = ""
    message = ""

    if action == "role":
        membership_type = request.POST.get("membership_type") or None
        payload["membership_type"] = membership_type
        if membership_type:
            subject = "Your RATEL Membership Role Has Been Updated"
            message = (
                f"Dear member,\n\n"
                f"Your RATEL Movement membership role has been updated to: {membership_type}.\n\n"
                f"Member ID: {member_id}\n\n"
                f"Neutrality is complicity.\n"
            )
        else:
            subject = "Your RATEL Membership Role Has Been Cleared"
            message = (
                f"Dear member,\n\n"
                f"Your specific membership role has been cleared. You remain a registered member of the RATEL Movement.\n\n"
                f"Member ID: {member_id}\n\n"
                f"Neutrality is complicity.\n"
            )
    elif action == "suspend":
        new_status = request.POST.get("status") or "suspended"
        payload["status"] = new_status
        if new_status == "suspended":
            subject = "Your RATEL Membership Has Been Suspended"
            message = (
                f"Dear member,\n\n"
                f"Your RATEL Movement membership has been suspended. If you believe this is an error, please contact the movement administrators.\n\n"
                f"Member ID: {member_id}\n\n"
                f"Neutrality is complicity.\n"
            )
        else:
            subject = "Your RATEL Membership Has Been Reinstated"
            message = (
                f"Dear member,\n\n"
                f"Your RATEL Movement membership has been reinstated and is now active again.\n\n"
                f"Member ID: {member_id}\n\n"
                f"Neutrality is complicity.\n"
            )
    elif action == "ban":
        payload["status"] = "banned"
        subject = "Your RATEL Membership Has Been Banned"
        message = (
            f"Dear member,\n\n"
            f"Your RATEL Movement membership has been permanently banned for serious or repeated violations of our code of conduct.\n\n"
            f"Member ID: {member_id}\n\n"
            f"You will no longer be able to log in or access member resources.\n\n"
            f"Neutrality is complicity.\n"
        )
    elif action == "unban":
        payload["status"] = "active"
        subject = "Your RATEL Membership Has Been Reinstated"
        message = (
            f"Dear member,\n\n"
            f"Your RATEL Movement membership has been reinstated. You may log in and access member resources again.\n\n"
            f"Member ID: {member_id}\n\n"
            f"Neutrality is complicity.\n"
            )
    elif action == "update_info":
        full_name = (request.POST.get("full_name") or "").strip()
        email_new = (request.POST.get("email") or "").strip().lower()
        original_email = (request.POST.get("original_email") or "").strip().lower() or email_new
        phone_number = (request.POST.get("phone_number") or "").strip()
        based_in_nigeria = request.POST.get("based_in_nigeria") == "yes"
        state = (request.POST.get("state") or "").strip() or None
        lga = (request.POST.get("lga") or "").strip() or None
        country = (request.POST.get("country") or "").strip() or None
        city = (request.POST.get("city") or "").strip() or None

        if not full_name or not email_new or not phone_number:
            messages.error(request, "Full name, email, and phone number are required.")
            return redirect("dashboard_membership")

        payload.update(
            {
                "full_name": full_name,
                "email": email_new,
                "phone_number": phone_number,
                "based_in_nigeria": based_in_nigeria,
                "state": state,
                "lga": lga,
                "country": country,
                "city": city,
            }
        )

        # Update Django user record
        try:
            user = User.objects.filter(username=original_email).first()
            if user:
                user.username = email_new
                user.email = email_new
                user.first_name = full_name
                user.save()
        except Exception:
            # Non‑critical; ignore failures here
            pass

    elif action == "delete":
        # Delete from Supabase and mark status deleted
        try:
            delete_url = f"{table_url}?member_id=eq.{member_id}"
            resp = requests.delete(delete_url, headers=headers, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            messages.error(request, f"Failed to delete member: {e}")
            return redirect("dashboard_membership")

        # Deactivate Django user if exists
        if email:
            try:
                user = User.objects.filter(username=email).first()
                if user:
                    user.is_active = False
                    user.save()
            except Exception:
                pass

        if email:
            try:
                send_mail(
                    "Your RATEL Membership Has Been Removed",
                    (
                        "Dear member,\n\n"
                        "Your RATEL Movement membership record has been removed from our system. "
                        "If you believe this is an error, please contact the movement administrators.\n\n"
                        f"Member ID (last known): {member_id}\n\n"
                        "Neutrality is complicity.\n"
                    ),
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=True,
                )
            except Exception:
                pass

        messages.success(request, "Member deleted successfully.")
        return redirect("dashboard_membership")
    else:
        messages.error(request, "Unknown membership action.")
        return redirect("dashboard_membership")

    # For role / suspend we PATCH
    try:
        patch_url = f"{table_url}?member_id=eq.{member_id}"
        resp = requests.patch(patch_url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        messages.error(request, f"Failed to update member: {e}")
        return redirect("dashboard_membership")

    # Keep Django user in sync for suspend / ban / unban (block login when suspended or banned)
    if email and action in ("suspend", "ban", "unban"):
        try:
            user = User.objects.filter(username=email).first()
            if user:
                new_status = payload.get("status") or "active"
                user.is_active = new_status not in ("suspended", "banned")
                user.save()
        except Exception:
            pass

    # Send notification email
    if email and subject and message:
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=True,
            )
        except Exception:
            pass

    if action == "role":
        if payload.get("membership_type"):
            messages.success(request, "Membership role updated.")
        else:
            messages.success(request, "Membership role cleared.")
    elif action == "suspend":
        if payload.get("status") == "suspended":
            messages.success(request, "Member has been suspended.")
        else:
            messages.success(request, "Member has been reinstated.")
    elif action == "ban":
        messages.success(request, "Member has been banned.")
    elif action == "unban":
        messages.success(request, "Member has been unbanned and reinstated.")

    return redirect("dashboard_membership")


def dashboard_companies(request):
    return render(request, "dashboard/companies.html", {"active_page": "companies"})


def dashboard_deals(request):
    return render(request, "dashboard/deals.html", {"active_page": "deals"})


def dashboard_tasks(request):
    return render(request, "dashboard/tasks.html", {"active_page": "tasks"})


def dashboard_about(request):
    """Dashboard page for managing landing page and about pages content."""
    base_url = settings.SUPABASE_URL.rstrip("/")
    headers = _get_supabase_headers()

    sections = {}
    about_ratel_sections = {}
    mission_vision_sections = {}

    try:
        # Fetch all site content sections (for landing page)
        url = f"{base_url}/rest/v1/site_content?select=*&order=display_order.asc"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for item in data:
                sections[item.get("content_key")] = item

        # Fetch about_pages content for About Ratel
        url = f"{base_url}/rest/v1/about_pages?page_key=eq.about_ratel&select=*&order=section_order.asc"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            for item in resp.json():
                about_ratel_sections[item.get("section_key")] = item

        # Fetch about_pages content for Mission & Vision
        url = f"{base_url}/rest/v1/about_pages?page_key=eq.mission_vision&select=*&order=section_order.asc"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            for item in resp.json():
                mission_vision_sections[item.get("section_key")] = item

    except Exception as e:
        print(f"[Dashboard About] Error fetching data: {e}")

    return render(request, "dashboard/about.html", {
        "active_page": "about",
        "sections": sections,
        "about_ratel": about_ratel_sections,
        "mission_vision": mission_vision_sections,
    })


@require_POST
def dashboard_about_save(request):
    """Legacy endpoint - redirects to dashboard_landing_save."""
    return dashboard_landing_save(request)


@require_POST
def dashboard_landing_save(request):
    """Save landing page content section to Supabase."""
    content_key = request.POST.get("section_key", "").strip()
    title = request.POST.get("title", "").strip()
    content = request.POST.get("content", "").strip()
    subtitle = request.POST.get("subtitle", "").strip()
    content_id = request.POST.get("content_id", "").strip()
    image_file = request.FILES.get("image")
    existing_image_url = request.POST.get("existing_image_url", "").strip()

    if not content:
        messages.error(request, "Content is required.")
        return redirect("dashboard_about")

    if not content_key:
        messages.error(request, "Content key is required.")
        return redirect("dashboard_about")

    # Define display order for sections
    section_order = {
        "manifesto": 1,
        "why_ratel_exists": 2,
        "what_we_stand_against": 3,
        "calls_to_action": 4,
    }

    base_url = settings.SUPABASE_URL.rstrip("/")
    headers = _get_supabase_headers()
    headers["Content-Type"] = "application/json"
    headers["Prefer"] = "return=representation"

    # Handle image upload
    image_url = existing_image_url
    if image_file:
        uploaded_url = _upload_to_supabase_storage(image_file, "settings", content_key)
        if uploaded_url:
            image_url = uploaded_url
        else:
            messages.warning(request, "Image upload failed, but content will be saved.")

    payload = {
        "content_key": content_key,
        "title": title,
        "subtitle": subtitle,
        "content": content,
        "image_url": image_url or None,
        "display_order": section_order.get(content_key, 10),
        "is_active": True,
    }

    try:
        if content_id:
            # Update existing
            url = f"{base_url}/rest/v1/site_content?id=eq.{content_id}"
            resp = requests.patch(url, headers=headers, json=payload, timeout=10)
            if resp.status_code in [200, 201, 204]:
                messages.success(request, f"Section updated successfully!")
            else:
                messages.error(request, f"Failed to update section: {resp.text}")
        else:
            # Upsert (insert or update by content_key)
            headers["Prefer"] = "return=representation,resolution=merge-duplicates"
            url = f"{base_url}/rest/v1/site_content?on_conflict=content_key"
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            if resp.status_code in [200, 201]:
                messages.success(request, f"Section saved successfully!")
            else:
                messages.error(request, f"Failed to save section: {resp.text}")
    except Exception as e:
        print(f"[Dashboard Landing Save] Exception: {e}")
        messages.error(request, f"Error saving section: {str(e)}")

    return redirect("dashboard_about")


@require_POST
def dashboard_about_pages_save(request):
    """Save About Ratel or Mission & Vision page content to Supabase."""
    page_key = request.POST.get("page_key", "").strip()  # 'about_ratel' or 'mission_vision'
    section_key = request.POST.get("section_key", "").strip()
    title = request.POST.get("title", "").strip()
    subtitle = request.POST.get("subtitle", "").strip()
    content = request.POST.get("content", "").strip()
    icon = request.POST.get("icon", "").strip()
    highlight_text = request.POST.get("highlight_text", "").strip()
    section_order = request.POST.get("section_order", "0").strip()
    content_id = request.POST.get("content_id", "").strip()
    image_file = request.FILES.get("image")
    existing_image_url = request.POST.get("existing_image_url", "").strip()

    if not page_key or not section_key:
        return JsonResponse({"success": False, "error": "Page key and section key are required."}, status=400)

    base_url = settings.SUPABASE_URL.rstrip("/")
    headers = _get_supabase_headers()
    headers["Content-Type"] = "application/json"
    headers["Prefer"] = "return=representation"

    # Handle image upload
    image_url = existing_image_url
    if image_file:
        uploaded_url = _upload_to_supabase_storage(image_file, "new", f"{page_key}_{section_key}")
        if uploaded_url:
            image_url = uploaded_url

    payload = {
        "page_key": page_key,
        "section_key": section_key,
        "title": title or None,
        "subtitle": subtitle or None,
        "content": content or None,
        "icon": icon or None,
        "highlight_text": highlight_text or None,
        "section_order": int(section_order) if section_order.isdigit() else 0,
        "image_url": image_url or None,
        "is_active": True,
        "updated_at": datetime.now().isoformat(),
    }

    try:
        if content_id:
            # Update existing
            url = f"{base_url}/rest/v1/about_pages?id=eq.{content_id}"
            resp = requests.patch(url, headers=headers, json=payload, timeout=10)
            if resp.status_code in [200, 201, 204]:
                return JsonResponse({"success": True, "message": "Section updated successfully!", "image_url": image_url})
            else:
                return JsonResponse({"success": False, "error": f"Failed to update: {resp.text}"}, status=400)
        else:
            # Upsert (insert or update by page_key + section_key)
            headers["Prefer"] = "return=representation,resolution=merge-duplicates"
            url = f"{base_url}/rest/v1/about_pages"
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            if resp.status_code in [200, 201]:
                return JsonResponse({"success": True, "message": "Section saved successfully!", "image_url": image_url})
            else:
                return JsonResponse({"success": False, "error": f"Failed to save: {resp.text}"}, status=400)
    except Exception as e:
        print(f"[Dashboard About Pages Save] Exception: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def dashboard_about_pages_get(request):
    """Get all about pages content for dashboard."""
    page_key = request.GET.get("page_key", "")

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        if page_key:
            url = f"{base_url}/rest/v1/about_pages?page_key=eq.{page_key}&select=*&order=section_order.asc"
        else:
            url = f"{base_url}/rest/v1/about_pages?select=*&order=page_key.asc,section_order.asc"

        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return JsonResponse({"success": True, "data": resp.json()})
        else:
            return JsonResponse({"success": False, "error": resp.text}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_POST
def dashboard_about_pages_delete(request):
    """Delete an about page section."""
    import json
    try:
        data = json.loads(request.body)
        content_id = data.get("id")
    except Exception:
        content_id = request.POST.get("id")

    if not content_id:
        return JsonResponse({"success": False, "error": "ID is required."}, status=400)

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()
        url = f"{base_url}/rest/v1/about_pages?id=eq.{content_id}"
        resp = requests.delete(url, headers=headers, timeout=10)
        if resp.status_code in [200, 204]:
            return JsonResponse({"success": True, "message": "Section deleted successfully!"})
        else:
            return JsonResponse({"success": False, "error": resp.text}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def dashboard_site_settings(request):
    """Settings page: Hero carousel slides (1, 2, 3), Manifesto image, and Hero Quote for the landing page."""
    hero_slides = {}
    slide_keys = ["hero_slide_1", "hero_slide_2", "hero_slide_3"]
    manifesto_section = {"content_key": "manifesto", "image_url": None, "id": None, "title": "Our Manifesto"}
    hero_quote = {"content_key": "hero_quote", "content": "When the people fear the government, there is tyranny. When the government fears the people, there is liberty.", "subtitle": "Thomas Jefferson", "id": None}
    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()
        for key in slide_keys:
            resp = requests.get(
                f"{base_url}/rest/v1/site_content?content_key=eq.{key}&select=*&limit=1",
                headers=headers,
                timeout=10
            )
            if resp.status_code == 200 and resp.json():
                hero_slides[key] = resp.json()[0]
            else:
                hero_slides[key] = {"content_key": key, "image_url": None, "id": None}
        # Fetch manifesto row for image
        resp = requests.get(
            f"{base_url}/rest/v1/site_content?content_key=eq.manifesto&select=*&limit=1",
            headers=headers,
            timeout=10
        )
        if resp.status_code == 200 and resp.json():
            manifesto_section = resp.json()[0]
        # Fetch hero quote
        resp = requests.get(
            f"{base_url}/rest/v1/site_content?content_key=eq.hero_quote&select=*&limit=1",
            headers=headers,
            timeout=10
        )
        if resp.status_code == 200 and resp.json():
            hero_quote = resp.json()[0]
        # Fetch hero video (if set, landing shows video instead of 3 slides)
        hero_video = {"content_key": "hero_video", "image_url": None, "id": None}
        resp = requests.get(
            f"{base_url}/rest/v1/site_content?content_key=eq.hero_video&select=*&limit=1",
            headers=headers,
            timeout=10
        )
        if resp.status_code == 200 and resp.json():
            hero_video = resp.json()[0]
        # Fetch Paystack settings (overrides env when set)
        paystack_settings = {"public_key": "", "secret_key": "", "id": None}
        paystack_resp = requests.get(
            f"{base_url}/rest/v1/paystack_settings?id=eq.1&select=id,public_key,secret_key&limit=1",
            headers=headers,
            timeout=10
        )
        if paystack_resp.status_code == 200 and paystack_resp.json():
            paystack_settings = paystack_resp.json()[0]
    except Exception as e:
        print(f"[Site Settings] Error: {e}")
        for key in slide_keys:
            hero_slides[key] = {"content_key": key, "image_url": None, "id": None}
        hero_video = {"content_key": "hero_video", "image_url": None, "id": None}
        paystack_settings = {"public_key": "", "secret_key": "", "id": None}

    hero_use_video = bool(hero_video.get("image_url"))

    # Effective keys currently used on the site (Supabase overrides env)
    paystack_public_key_display, paystack_secret_effective = _get_paystack_keys()
    paystack_secret_key_set = bool((paystack_secret_effective or "").strip())

    return render(request, "dashboard/site_settings.html", {
        "active_page": "site_settings",
        "hero_slides": hero_slides,
        "hero_video": hero_video,
        "hero_use_video": hero_use_video,
        "manifesto_section": manifesto_section,
        "hero_quote": hero_quote,
        "paystack_settings": paystack_settings,
        "paystack_public_key_display": paystack_public_key_display,
        "paystack_secret_key_set": paystack_secret_key_set,
    })


def _site_settings_get_current(base_url, headers, keys):
    """Fetch current site_content rows for given keys. Returns dict key -> row (or default)."""
    current = {}
    for key in keys:
        try:
            resp = requests.get(
                f"{base_url}/rest/v1/site_content?content_key=eq.{key}&select=id,image_url,content,title,subtitle&limit=1",
                headers=headers,
                timeout=10
            )
            if resp.status_code == 200 and resp.json():
                current[key] = resp.json()[0]
            else:
                current[key] = None
        except Exception:
            current[key] = None
    return current


@require_POST
def dashboard_site_settings_save(request):
    """Save hero carousel slides (1, 2, 3) and Manifesto image. Only update items that have new file or URL."""
    base_url = settings.SUPABASE_URL.rstrip("/")
    headers = _get_supabase_headers()
    headers["Content-Type"] = "application/json"
    headers["Prefer"] = "return=representation"

    slide_keys = ["hero_slide_1", "hero_slide_2", "hero_slide_3"]
    all_keys = slide_keys + ["manifesto"]
    current = _site_settings_get_current(base_url, headers, all_keys)

    def resolve_image_url(item_key, file_field, url_field, current_row, folder_name):
        image_file = request.FILES.get(file_field)
        post_url = request.POST.get(url_field, "").strip()
        if image_file:
            uploaded_url = _upload_to_supabase_storage(image_file, "settings", folder_name)
            return uploaded_url or (current_row.get("image_url") if current_row else None)
        if post_url:
            return post_url
        return (current_row.get("image_url") if current_row else None)

    # Save slides 1, 2, 3
    for i, key in enumerate(slide_keys, 1):
        image_url = resolve_image_url(
            key, f"slide_{i}", f"slide_{i}_url",
            current.get(key), f"hero-slide-{i}"
        )
        content_id = request.POST.get(f"slide_{i}_id", "").strip()
        payload = {
            "content_key": key,
            "title": f"Hero Slide {i}",
            "content": "",
            "subtitle": None,
            "image_url": image_url,
            "display_order": 100 + i,
            "is_active": True,
        }
        try:
            if content_id:
                resp = requests.patch(
                    f"{base_url}/rest/v1/site_content?id=eq.{content_id}",
                    headers=headers, json=payload, timeout=10
                )
            else:
                resp = requests.post(
                    f"{base_url}/rest/v1/site_content",
                    headers=headers, json=payload, timeout=10
                )
            if resp.status_code not in [200, 201, 204]:
                messages.warning(request, f"Slide {i} may not have saved: {resp.text[:100]}")
        except Exception as e:
            messages.warning(request, f"Slide {i} error: {str(e)}")

    # Save Manifesto image only when user provided new file or URL; otherwise keep existing
    manifesto_file = request.FILES.get("manifesto_image")
    manifesto_url = request.POST.get("manifesto_url", "").strip()
    manifesto_id = request.POST.get("manifesto_id", "").strip()
    cur_manifesto = current.get("manifesto")
    new_manifesto_image_url = None
    if manifesto_file:
        new_manifesto_image_url = _upload_to_supabase_storage(manifesto_file, "settings", "manifesto")
    else:
        # Use submitted URL; empty string means clear the image
        new_manifesto_image_url = manifesto_url

    if new_manifesto_image_url is not None or (manifesto_url == "" and cur_manifesto):
        payload = {
            "image_url": new_manifesto_image_url if new_manifesto_image_url is not None else cur_manifesto.get("image_url") if cur_manifesto else None,
        }
        if cur_manifesto and manifesto_id:
            payload["title"] = cur_manifesto.get("title") or "Our Manifesto"
            payload["subtitle"] = cur_manifesto.get("subtitle") or "The Ratel Movement"
            payload["content"] = cur_manifesto.get("content") or ""
            try:
                resp = requests.patch(
                    f"{base_url}/rest/v1/site_content?id=eq.{manifesto_id}",
                    headers=headers, json=payload, timeout=10
                )
                if resp.status_code not in [200, 201, 204]:
                    messages.warning(request, f"Manifesto image may not have saved: {resp.text[:100]}")
            except Exception as e:
                messages.warning(request, f"Manifesto image error: {str(e)}")
        else:
            payload["content_key"] = "manifesto"
            payload["title"] = "Our Manifesto"
            payload["subtitle"] = "The Ratel Movement"
            payload["content"] = ""
            payload["display_order"] = 1
            payload["is_active"] = True
            try:
                resp = requests.post(
                    f"{base_url}/rest/v1/site_content",
                    headers=headers, json=payload, timeout=10
                )
                if resp.status_code not in [200, 201, 204]:
                    messages.warning(request, f"Manifesto image may not have saved: {resp.text[:100]}")
            except Exception as e:
                messages.warning(request, f"Manifesto image error: {str(e)}")

    messages.success(request, "Settings saved. You can change any image at any time.")
    return redirect("dashboard_site_settings")


@require_POST
def dashboard_site_settings_save_single(request):
    """AJAX endpoint: Save a single site setting (hero slide or manifesto image)."""
    from django.http import JsonResponse

    print("[Site Settings Save Single] Request received")

    base_url = settings.SUPABASE_URL.rstrip("/")

    # Get which setting to save
    setting_type = request.POST.get("setting_type", "").strip()
    content_id = request.POST.get("content_id", "").strip()
    image_url = request.POST.get("image_url", "").strip()

    print(f"[Site Settings Save Single] setting_type={setting_type}, content_id={content_id}, image_url={image_url}")
    print(f"[Site Settings Save Single] FILES keys: {list(request.FILES.keys())}")

    valid_types = ["hero_slide_1", "hero_slide_2", "hero_slide_3", "manifesto", "hero_quote", "hero_video", "hero_use_images"]
    if setting_type not in valid_types:
        return JsonResponse({"success": False, "error": f"Invalid setting type: {setting_type}"}, status=400)

    # Switch hero back to 3 images (clear hero video URL)
    if setting_type == "hero_use_images":
        headers_api = _get_supabase_headers()
        headers_api["Content-Type"] = "application/json"
        headers_api["Prefer"] = "return=representation,resolution=merge-duplicates"
        payload = {
            "content_key": "hero_video",
            "title": "Hero Video",
            "content": "",
            "subtitle": None,
            "image_url": None,
            "display_order": 99,
            "is_active": True,
        }
        try:
            resp = requests.post(
                f"{base_url}/rest/v1/site_content?on_conflict=content_key",
                headers=headers_api,
                json=payload,
                timeout=10,
            )
            if resp.status_code in [200, 201, 204]:
                return JsonResponse({"success": True, "message": "Hero set to 3 images. Landing page will show the carousel."})
            return JsonResponse({"success": False, "error": resp.text or "Failed to clear hero video"}, status=500)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

    # Save hero video (upload to hero bucket or save URL)
    if setting_type == "hero_video":
        video_file = request.FILES.get("image_file")  # same field name as other settings forms
        video_url = request.POST.get("image_url", "").strip()
        print(f"[Site Settings Save Single] Hero video: file={video_file}, url={video_url[:100] if video_url else '(none)'}")

        final_video_url = None
        if video_file and video_file.size > 0:
            # Upload to settings bucket (same as other site settings assets)
            print(f"[Site Settings Save Single] Uploading video file: {video_file.name}, size={video_file.size}")
            uploaded_url = _upload_to_supabase_storage(video_file, "settings", "hero-video")
            if not uploaded_url:
                return JsonResponse({"success": False, "error": "Failed to upload video. Ensure the 'settings' bucket exists in Supabase Storage and is public."}, status=500)
            final_video_url = uploaded_url
            print(f"[Site Settings Save Single] Video uploaded successfully: {final_video_url}")
        elif video_url:
            final_video_url = video_url
            print(f"[Site Settings Save Single] Using provided video URL: {final_video_url}")
        else:
            return JsonResponse({"success": False, "error": "Upload a video file or enter a video URL."}, status=400)
        headers_api = _get_supabase_headers()
        headers_api["Content-Type"] = "application/json"
        headers_api["Prefer"] = "return=representation,resolution=merge-duplicates"
        payload = {
            "content_key": "hero_video",
            "title": "Hero Video",
            "content": "",
            "subtitle": None,
            "image_url": final_video_url,
            "display_order": 99,
            "is_active": True,
        }
        try:
            resp = requests.post(
                f"{base_url}/rest/v1/site_content?on_conflict=content_key",
                headers=headers_api,
                json=payload,
                timeout=10,
            )
            print(f"[Site Settings Save Single] Hero video response status: {resp.status_code}")
            print(f"[Site Settings Save Single] Hero video response text: {resp.text[:500] if resp.text else '(empty)'}")

            if resp.status_code in [200, 201, 204]:
                new_data = None
                if resp.text:
                    try:
                        result = resp.json()
                        if isinstance(result, list) and result:
                            new_data = result[0]
                    except Exception:
                        pass
                return JsonResponse({
                    "success": True,
                    "message": "Hero video saved. Landing page will show the video.",
                    "content_id": new_data.get("id") if new_data else None,
                    "image_url": final_video_url,
                })
            return JsonResponse({"success": False, "error": resp.text or "Failed to save hero video"}, status=500)
        except Exception as e:
            print(f"[Site Settings Save Single] Hero video exception: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({"success": False, "error": str(e)}, status=500)

    # Handle hero_quote separately (text-only, no image)
    if setting_type == "hero_quote":
        quote_text = request.POST.get("quote_text", "").strip()
        quote_author = request.POST.get("quote_author", "").strip()

        print(f"[Site Settings Save Single] Hero Quote: text='{quote_text[:50]}...', author='{quote_author}'")

        payload = {
            "content_key": "hero_quote",
            "title": "Hero Quote",
            "content": quote_text or "When the people fear the government, there is tyranny. When the government fears the people, there is liberty.",
            "subtitle": quote_author or "Thomas Jefferson",
            "image_url": None,
            "display_order": 50,
            "is_active": True,
        }

        # Prepare headers for Supabase API call
        headers_api = _get_supabase_headers()
        headers_api["Content-Type"] = "application/json"
        headers_api["Prefer"] = "return=representation,resolution=merge-duplicates"

        try:
            if content_id:
                print(f"[Site Settings Save Single] PATCH hero_quote to id={content_id}")
                resp = requests.patch(
                    f"{base_url}/rest/v1/site_content?id=eq.{content_id}",
                    headers=headers_api, json=payload, timeout=10
                )
            else:
                print("[Site Settings Save Single] POST (upsert) hero_quote")
                resp = requests.post(
                    f"{base_url}/rest/v1/site_content?on_conflict=content_key",
                    headers=headers_api, json=payload, timeout=10
                )

            print(f"[Site Settings Save Single] Response status: {resp.status_code}")

            if resp.status_code in [200, 201, 204]:
                new_data = None
                if resp.text:
                    try:
                        result = resp.json()
                        if isinstance(result, list) and result:
                            new_data = result[0]
                    except Exception:
                        pass

                return JsonResponse({
                    "success": True,
                    "message": "Hero Quote saved successfully!",
                    "content_id": new_data.get("id") if new_data else content_id,
                })
            else:
                return JsonResponse({
                    "success": False,
                    "error": f"Failed to save: {resp.status_code} - {resp.text[:200]}"
                }, status=500)
        except Exception as e:
            print(f"[Site Settings Save Single] Exception: {e}")
            return JsonResponse({"success": False, "error": str(e)}, status=500)

    # Check for file upload (for image-based settings)
    image_file = request.FILES.get("image_file")
    final_image_url = None

    if image_file:
        print(f"[Site Settings Save Single] Uploading file: {image_file.name}, size: {image_file.size}")
        # Upload to Supabase Storage
        folder_map = {
            "hero_slide_1": "hero-slide-1",
            "hero_slide_2": "hero-slide-2",
            "hero_slide_3": "hero-slide-3",
            "manifesto": "manifesto",
        }
        folder = folder_map.get(setting_type, "settings")
        uploaded_url = _upload_to_supabase_storage(image_file, "settings", folder)
        print(f"[Site Settings Save Single] Upload result: {uploaded_url}")
        if uploaded_url:
            final_image_url = uploaded_url
        else:
            return JsonResponse({"success": False, "error": "Failed to upload image to storage"}, status=500)
    elif image_url:
        print(f"[Site Settings Save Single] Using provided URL: {image_url}")
        final_image_url = image_url
    else:
        # No new image provided - keep existing or set to None
        print("[Site Settings Save Single] No new image, fetching current value")
        headers_get = _get_supabase_headers()
        try:
            resp = requests.get(
                f"{base_url}/rest/v1/site_content?content_key=eq.{setting_type}&select=image_url&limit=1",
                headers=headers_get,
                timeout=10
            )
            if resp.status_code == 200 and resp.json():
                final_image_url = resp.json()[0].get("image_url")
                print(f"[Site Settings Save Single] Current image_url: {final_image_url}")
        except Exception as e:
            print(f"[Site Settings Save Single] Error fetching current: {e}")

    # Build payload based on setting type
    if setting_type.startswith("hero_slide"):
        slide_num = setting_type.split("_")[-1]
        payload = {
            "content_key": setting_type,
            "title": f"Hero Slide {slide_num}",
            "content": "",
            "subtitle": None,
            "image_url": final_image_url,
            "display_order": 100 + int(slide_num),
            "is_active": True,
        }
    else:  # manifesto
        # Fetch existing manifesto data to preserve title, subtitle, content
        existing_data = {"title": "Our Manifesto", "subtitle": "The Ratel Movement", "content": ""}
        headers_get = _get_supabase_headers()
        try:
            resp = requests.get(
                f"{base_url}/rest/v1/site_content?content_key=eq.manifesto&select=title,subtitle,content&limit=1",
                headers=headers_get,
                timeout=10
            )
            if resp.status_code == 200 and resp.json():
                existing_data = resp.json()[0]
        except Exception:
            pass

        payload = {
            "content_key": "manifesto",
            "title": existing_data.get("title") or "Our Manifesto",
            "subtitle": existing_data.get("subtitle") or "The Ratel Movement",
            "content": existing_data.get("content") or "",
            "image_url": final_image_url,
            "display_order": 1,
            "is_active": True,
        }

    print(f"[Site Settings Save Single] Payload: {payload}")

    # Prepare headers for Supabase API call - use upsert for reliable create/update
    headers_api = _get_supabase_headers()
    headers_api["Content-Type"] = "application/json"
    headers_api["Prefer"] = "return=representation,resolution=merge-duplicates"

    try:
        if content_id:
            # Update existing by ID
            print(f"[Site Settings Save Single] PATCH to id={content_id}")
            resp = requests.patch(
                f"{base_url}/rest/v1/site_content?id=eq.{content_id}",
                headers=headers_api, json=payload, timeout=10
            )
        else:
            # Use upsert - POST with on_conflict header to handle existing records
            print(f"[Site Settings Save Single] POST (upsert) with content_key={setting_type}")
            headers_api["Prefer"] = "return=representation,resolution=merge-duplicates"
            resp = requests.post(
                f"{base_url}/rest/v1/site_content?on_conflict=content_key",
                headers=headers_api, json=payload, timeout=10
            )

        print(f"[Site Settings Save Single] Response status: {resp.status_code}, text: {resp.text[:200] if resp.text else 'empty'}")

        if resp.status_code in [200, 201, 204]:
            # Get the updated/created record to return new ID if needed
            new_data = None
            if resp.text:
                try:
                    result = resp.json()
                    if isinstance(result, list) and result:
                        new_data = result[0]
                except Exception:
                    pass

            new_id = new_data.get("id") if new_data else content_id
            print(f"[Site Settings Save Single] Success! new_id={new_id}")
            return JsonResponse({
                "success": True,
                "message": f"{setting_type.replace('_', ' ').title()} saved successfully!",
                "image_url": final_image_url,
                "content_id": new_id,
            })
        else:
            error_msg = f"Failed to save: {resp.status_code} - {resp.text[:200]}"
            print(f"[Site Settings Save Single] Error: {error_msg}")
            return JsonResponse({
                "success": False,
                "error": error_msg
            }, status=500)
    except Exception as e:
        print(f"[Site Settings Save Single] Exception: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_POST
def dashboard_paystack_settings_save(request):
    """
    Save Paystack public/secret keys to Supabase paystack_settings.
    When set, these override PAYSTACK_PUBLIC_KEY and PAYSTACK_SECRET_KEY from env on auth and renew pages.
    Leave secret key blank to keep existing value.
    """
    public_key = (request.POST.get("paystack_public_key") or "").strip()
    secret_key = (request.POST.get("paystack_secret_key") or "").strip()

    base_url = settings.SUPABASE_URL.rstrip("/")
    headers = _get_supabase_headers()
    headers["Content-Type"] = "application/json"
    headers["Prefer"] = "return=representation"

    try:
        # If secret key blank, keep existing from DB
        if not secret_key:
            get_resp = requests.get(
                f"{base_url}/rest/v1/paystack_settings?id=eq.1&select=secret_key&limit=1",
                headers=headers,
                timeout=10,
            )
            if get_resp.status_code == 200 and get_resp.json():
                secret_key = get_resp.json()[0].get("secret_key") or ""

        payload = {
            "public_key": public_key,
            "secret_key": secret_key,
            "updated_at": datetime.now().isoformat(),
        }

        resp = requests.patch(
            f"{base_url}/rest/v1/paystack_settings?id=eq.1",
            headers=headers,
            json=payload,
            timeout=10,
        )
        if resp.status_code == 200 and resp.json():
            messages.success(request, "Paystack settings saved. Auth and renewal pages will use these keys.")
        elif resp.status_code == 204:
            # No rows: insert first row
            resp = requests.post(
                f"{base_url}/rest/v1/paystack_settings",
                headers=headers,
                json={"id": 1, "public_key": public_key, "secret_key": secret_key},
                timeout=10,
            )
            if resp.status_code in [200, 201]:
                messages.success(request, "Paystack settings saved. Auth and renewal pages will use these keys.")
            else:
                messages.warning(request, "Paystack settings may not have saved. Run paystack_settings_table.sql in Supabase.")
        else:
            messages.warning(request, "Paystack settings may not have saved. Check Supabase.")
    except Exception as e:
        print(f"[Paystack Save] Error: {e}")
        messages.error(request, f"Failed to save Paystack settings: {e}")
    return redirect("dashboard_site_settings")


def dashboard_resources(request):
    """
    Dashboard for managing downloadable resources.
    """
    resources_list = []
    categories = [
        {"key": "activist_toolkits", "label": "Activist Toolkits"},
        {"key": "educational_materials", "label": "Educational Materials"},
        {"key": "legal_civic_guides", "label": "Legal & Civic Guides"},
        {"key": "research_reading", "label": "Research & Reading"},
        {"key": "download_centre", "label": "Download Centre"},
    ]
    current_category = request.GET.get("category", "")

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        url = f"{base_url}/rest/v1/resources?select=*&order=display_order.asc,created_at.desc"
        if current_category and current_category != "all":
            url += f"&category=eq.{current_category}"

        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            resources_list = resp.json()
            # Normalize file URLs
            storage_base = f"{base_url}/storage/v1/object/public/resources/"
            for resource in resources_list:
                if resource.get("file_url") and not str(resource["file_url"]).startswith("http"):
                    resource["file_url"] = storage_base + str(resource["file_url"]).lstrip("/")
    except Exception as e:
        print(f"[Dashboard Resources] Error: {e}")

    return render(request, "dashboard/resources.html", {
        "active_page": "resources",
        "resources": resources_list,
        "categories": categories,
        "current_category": current_category,
    })


@require_POST
def dashboard_resources_save(request):
    """
    Save a new resource or update existing one.
    """
    resource_id = request.POST.get("resource_id", "").strip()
    title = request.POST.get("title", "").strip()
    description = request.POST.get("description", "").strip()
    category = request.POST.get("category", "").strip()
    intended_audience = request.POST.get("intended_audience", "").strip()
    how_to_use = request.POST.get("how_to_use", "").strip()
    author = request.POST.get("author", "").strip()
    version = request.POST.get("version", "").strip()
    tags = request.POST.get("tags", "").strip()
    is_featured = request.POST.get("is_featured") == "on"
    status = request.POST.get("status", "active").strip()

    resource_file = request.FILES.get("resource_file")

    if not title or not category:
        messages.error(request, "Title and category are required.")
        return redirect("dashboard_resources")

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()
        headers["Content-Type"] = "application/json"
        headers["Prefer"] = "return=representation"

        # Handle file upload
        file_url = None
        file_name = None
        file_type = None

        if resource_file:
            # Upload to Supabase storage
            uploaded_url = _upload_to_supabase_storage(resource_file, "resources", category)
            if uploaded_url:
                file_url = uploaded_url
                file_name = resource_file.name
                # Get file extension
                file_type = resource_file.name.split('.')[-1].lower() if '.' in resource_file.name else None

        # Parse tags
        tags_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

        payload = {
            "title": title,
            "description": description or None,
            "category": category,
            "intended_audience": intended_audience or None,
            "how_to_use": how_to_use or None,
            "author": author or None,
            "version": version or None,
            "tags": tags_list if tags_list else None,
            "is_featured": is_featured,
            "status": status,
        }

        # Only update file fields if a new file was uploaded
        if file_url:
            payload["file_url"] = file_url
            payload["file_name"] = file_name
            payload["file_type"] = file_type

        if resource_id:
            # Update existing resource
            resp = requests.patch(
                f"{base_url}/rest/v1/resources?id=eq.{resource_id}",
                headers=headers,
                json=payload,
                timeout=30
            )
        else:
            # Create new resource
            resp = requests.post(
                f"{base_url}/rest/v1/resources",
                headers=headers,
                json=payload,
                timeout=30
            )

        resp.raise_for_status()
        messages.success(request, "Resource saved successfully!")

    except Exception as e:
        print(f"[Resource Save] Error: {e}")
        messages.error(request, f"Failed to save resource: {str(e)}")

    return redirect("dashboard_resources")


@require_POST
def dashboard_resources_delete(request):
    """
    Delete a resource (soft delete by setting status to archived).
    """
    import json
    data = json.loads(request.body)
    resource_id = data.get("id")

    if not resource_id:
        return JsonResponse({"success": False, "error": "Resource ID required"})

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        resp = requests.patch(
            f"{base_url}/rest/v1/resources?id=eq.{resource_id}",
            headers=headers,
            json={"status": "archived"},
            timeout=10
        )
        resp.raise_for_status()

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@require_POST
def dashboard_resources_get(request):
    """
    Get a single resource by ID for editing.
    """
    import json
    data = json.loads(request.body)
    resource_id = data.get("id")

    if not resource_id:
        return JsonResponse({"success": False, "error": "Resource ID required"})

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        resp = requests.get(
            f"{base_url}/rest/v1/resources?id=eq.{resource_id}&select=*",
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()

        if data:
            return JsonResponse({"success": True, "resource": data[0]})
        else:
            return JsonResponse({"success": False, "error": "Resource not found"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


def dashboard_settings(request):
    """
    Dashboard for managing Ideology sections.
    """
    sections = []
    section_keys = [
        {"key": "core_beliefs", "label": "Core Beliefs", "icon": "heart"},
        {"key": "justice_power_resistance", "label": "Justice, Power & Resistance", "icon": "scale"},
        {"key": "civic_responsibility", "label": "Civic Responsibility", "icon": "users"},
        {"key": "non_negotiable_principles", "label": "Non-Negotiable Principles", "icon": "shield"},
        {"key": "what_ratel_is_not", "label": "What RATEL Is Not", "icon": "x-circle"},
    ]
    current_section = request.GET.get("section", "")

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        url = f"{base_url}/rest/v1/ideology_sections?select=*&order=display_order.asc"
        if current_section:
            url += f"&section_key=eq.{current_section}"

        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            sections = resp.json()
    except Exception as e:
        print(f"[Dashboard Settings] Error: {e}")

    return render(request, "dashboard/settings.html", {
        "active_page": "settings",
        "sections": sections,
        "section_keys": section_keys,
        "current_section": current_section,
    })


@require_POST
def dashboard_ideology_save(request):
    """
    Save or update an ideology section.
    """
    import json

    section_id = request.POST.get("section_id", "").strip()
    section_key = request.POST.get("section_key", "").strip()
    section_title = request.POST.get("section_title", "").strip()
    section_subtitle = request.POST.get("section_subtitle", "").strip()
    section_icon = request.POST.get("section_icon", "book-open").strip()
    content = request.POST.get("content", "").strip()
    items_json = request.POST.get("items", "[]").strip()
    display_order = request.POST.get("display_order", "0").strip()
    is_active = request.POST.get("is_active") == "on"

    if not section_key or not section_title:
        messages.error(request, "Section key and title are required.")
        return redirect("dashboard_settings")

    try:
        items = json.loads(items_json) if items_json else []
    except json.JSONDecodeError:
        items = []

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()
        headers["Content-Type"] = "application/json"
        headers["Prefer"] = "return=representation"

        payload = {
            "section_key": section_key,
            "section_title": section_title,
            "section_subtitle": section_subtitle or None,
            "section_icon": section_icon,
            "content": content or None,
            "items": items,
            "display_order": int(display_order) if display_order else 0,
            "is_active": is_active,
        }

        if section_id:
            # Update existing section
            resp = requests.patch(
                f"{base_url}/rest/v1/ideology_sections?id=eq.{section_id}",
                headers=headers,
                json=payload,
                timeout=30
            )
        else:
            # Create new section
            resp = requests.post(
                f"{base_url}/rest/v1/ideology_sections",
                headers=headers,
                json=payload,
                timeout=30
            )

        resp.raise_for_status()
        messages.success(request, "Ideology section saved successfully!")

    except Exception as e:
        print(f"[Ideology Save] Error: {e}")
        messages.error(request, f"Failed to save ideology section: {str(e)}")

    return redirect("dashboard_settings")


@require_POST
def dashboard_ideology_delete(request):
    """
    Delete an ideology section.
    """
    import json
    data = json.loads(request.body)
    section_id = data.get("id")

    if not section_id:
        return JsonResponse({"success": False, "error": "Section ID required"})

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        resp = requests.delete(
            f"{base_url}/rest/v1/ideology_sections?id=eq.{section_id}",
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@require_POST
def dashboard_ideology_get(request):
    """
    Get a single ideology section by ID for editing.
    """
    import json
    data = json.loads(request.body)
    section_id = data.get("id")

    if not section_id:
        return JsonResponse({"success": False, "error": "Section ID required"})

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        resp = requests.get(
            f"{base_url}/rest/v1/ideology_sections?id=eq.{section_id}&select=*",
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()

        if data:
            return JsonResponse({"success": True, "section": data[0]})
        else:
            return JsonResponse({"success": False, "error": "Section not found"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


# --- Leadership Dashboard Views ---

LEADERSHIP_TABLES = [
    "founding_vision",
    "leadership_council",
    "strategic_committees",
    "advisory_voices",
    "code_of_conduct",
]


def dashboard_leadership(request):
    """
    Dashboard view for managing leadership content.
    Fetches all data from the 5 leadership tables.
    """
    founding_vision = []
    leadership_council = []
    strategic_committees = []
    advisory_voices = []
    code_of_conduct = []

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
            "Accept": "application/json",
        }

        # Fetch founding vision (all, including inactive for admin)
        resp = requests.get(
            f"{base_url}/rest/v1/founding_vision",
            headers=headers,
            params={"select": "*", "order": "display_order.asc"},
            timeout=10
        )
        if resp.status_code == 200:
            founding_vision = resp.json()

        # Fetch leadership council
        resp = requests.get(
            f"{base_url}/rest/v1/leadership_council",
            headers=headers,
            params={"select": "*", "order": "display_order.asc"},
            timeout=10
        )
        if resp.status_code == 200:
            leadership_council = resp.json()
            # Normalize image URLs
            for leader in leadership_council:
                leader["profile_image_url"] = _normalize_leadership_image_url(leader.get("profile_image_url"))

        # Fetch strategic committees
        resp = requests.get(
            f"{base_url}/rest/v1/strategic_committees",
            headers=headers,
            params={"select": "*", "order": "display_order.asc"},
            timeout=10
        )
        if resp.status_code == 200:
            strategic_committees = resp.json()
            # Normalize image URLs
            for committee in strategic_committees:
                committee["profile_image_url"] = _normalize_leadership_image_url(committee.get("profile_image_url"))

        # Fetch advisory voices
        resp = requests.get(
            f"{base_url}/rest/v1/advisory_voices",
            headers=headers,
            params={"select": "*", "order": "display_order.asc"},
            timeout=10
        )
        if resp.status_code == 200:
            advisory_voices = resp.json()
            # Normalize image URLs
            for advisor in advisory_voices:
                advisor["profile_image_url"] = _normalize_leadership_image_url(advisor.get("profile_image_url"))

        # Fetch code of conduct
        resp = requests.get(
            f"{base_url}/rest/v1/code_of_conduct",
            headers=headers,
            params={"select": "*", "order": "display_order.asc"},
            timeout=10
        )
        if resp.status_code == 200:
            code_of_conduct = resp.json()

    except Exception as e:
        print(f"[Dashboard Leadership] Error fetching data: {e}")

    return render(request, "dashboard/leadership.html", {
        "active_page": "leadership",
        "founding_vision": founding_vision,
        "leadership_council": leadership_council,
        "strategic_committees": strategic_committees,
        "advisory_voices": advisory_voices,
        "code_of_conduct": code_of_conduct,
    })


@require_POST
def dashboard_leadership_save(request):
    """
    Create or update a leadership item.
    Expects POST with 'table', optional 'id', and table-specific fields.
    Handles file uploads for profile images.
    """
    table = request.POST.get("table", "").strip()
    item_id = request.POST.get("id", "").strip()

    if table not in LEADERSHIP_TABLES:
        messages.error(request, "Invalid table specified.")
        return redirect("dashboard_leadership")

    base_url = settings.SUPABASE_URL.rstrip("/")
    headers = {
        "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    # Handle file uploads for tables that support profile images
    profile_image_file = request.FILES.get("profile_image")
    profile_image_url = None
    
    # If a file was uploaded, upload it to Supabase leadership bucket
    if profile_image_file:
        profile_image_url = _upload_leadership_image_to_supabase(table, item_id or "new", profile_image_file)
        if not profile_image_url:
            messages.warning(request, "Image upload failed, but other data will be saved.")
    else:
        # If no new file uploaded, check if there's an existing URL in POST data
        profile_image_url = request.POST.get("profile_image_url", "").strip() or None

    # Build payload based on table
    payload = {}

    if table == "founding_vision":
        payload = {
            "title": request.POST.get("title", "").strip(),
            "content": request.POST.get("content", "").strip(),
            "display_order": int(request.POST.get("display_order") or 0),
            "is_active": True,
        }
    elif table == "leadership_council":
        payload = {
            "full_name": request.POST.get("full_name", "").strip(),
            "position": request.POST.get("position", "").strip(),
            "bio": request.POST.get("bio", "").strip() or None,
            "profile_image_url": profile_image_url,
            "email": request.POST.get("email", "").strip() or None,
            "phone": request.POST.get("phone", "").strip() or None,
            "linkedin_url": request.POST.get("linkedin_url", "").strip() or None,
            "twitter_url": request.POST.get("twitter_url", "").strip() or None,
            "display_order": int(request.POST.get("display_order") or 0),
            "is_active": True,
        }
    elif table == "strategic_committees":
        responsibilities_str = request.POST.get("responsibilities", "").strip()
        responsibilities = [r.strip() for r in responsibilities_str.split(",") if r.strip()] if responsibilities_str else []
        payload = {
            "committee_name": request.POST.get("committee_name", "").strip(),
            "description": request.POST.get("description", "").strip() or None,
            "chairperson": request.POST.get("chairperson", "").strip() or None,
            "responsibilities": responsibilities,
            "profile_image_url": profile_image_url,
            "display_order": int(request.POST.get("display_order") or 0),
            "is_active": True,
        }
    elif table == "advisory_voices":
        payload = {
            "full_name": request.POST.get("full_name", "").strip(),
            "title": request.POST.get("title", "").strip() or None,
            "organization": request.POST.get("organization", "").strip() or None,
            "expertise": request.POST.get("expertise", "").strip() or None,
            "bio": request.POST.get("bio", "").strip() or None,
            "profile_image_url": profile_image_url,
            "quote": request.POST.get("quote", "").strip() or None,
            "display_order": int(request.POST.get("display_order") or 0),
            "is_active": True,
        }
    elif table == "code_of_conduct":
        payload = {
            "section_title": request.POST.get("section_title", "").strip(),
            "content": request.POST.get("content", "").strip(),
            "display_order": int(request.POST.get("display_order") or 0),
            "is_active": True,
        }

    try:
        if item_id:
            # Update existing
            url = f"{base_url}/rest/v1/{table}?id=eq.{item_id}"
            resp = requests.patch(url, headers=headers, json=payload, timeout=10)
            resp.raise_for_status()
            messages.success(request, "Item updated successfully.")
        else:
            # Create new
            url = f"{base_url}/rest/v1/{table}"
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            resp.raise_for_status()
            messages.success(request, "Item created successfully.")
    except Exception as e:
        messages.error(request, f"Failed to save item: {e}")

    return redirect("dashboard_leadership")


def dashboard_leadership_get(request):
    """
    Fetch a single item by table and id for editing.
    Returns JSON.
    """
    table = request.GET.get("table", "").strip()
    item_id = request.GET.get("id", "").strip()

    if table not in LEADERSHIP_TABLES or not item_id:
        return JsonResponse({"success": False, "error": "Invalid parameters"})

    base_url = settings.SUPABASE_URL.rstrip("/")
    headers = {
        "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
        "Accept": "application/json",
    }

    try:
        url = f"{base_url}/rest/v1/{table}?id=eq.{item_id}&select=*"
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data:
            item = data[0]
            # Normalize image URL if present
            if "profile_image_url" in item:
                item["profile_image_url"] = _normalize_leadership_image_url(item.get("profile_image_url"))
            return JsonResponse({"success": True, "item": item})
        return JsonResponse({"success": False, "error": "Item not found"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@require_POST
def dashboard_leadership_delete(request):
    """
    Delete a leadership item by table and id.
    Returns JSON.
    """
    table = request.POST.get("table", "").strip()
    item_id = request.POST.get("id", "").strip()

    if table not in LEADERSHIP_TABLES or not item_id:
        return JsonResponse({"success": False, "error": "Invalid parameters"})

    base_url = settings.SUPABASE_URL.rstrip("/")
    headers = {
        "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
    }

    try:
        url = f"{base_url}/rest/v1/{table}?id=eq.{item_id}"
        resp = requests.delete(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


# --- Contact Inquiries Views ---

@require_POST
def contact_submit(request):
    """
    Handle contact form submission.
    Stores the inquiry in Supabase contact_inquiries table.
    """
    inquiry_type = request.POST.get("inquiry_type", "general").strip()

    # Build payload based on inquiry type
    payload = {
        "inquiry_type": inquiry_type,
        "status": "new",
    }

    if inquiry_type == "general":
        payload.update({
            "full_name": request.POST.get("full_name", "").strip(),
            "email": request.POST.get("email", "").strip(),
            "phone": request.POST.get("phone", "").strip() or None,
            "subject": request.POST.get("subject", "").strip(),
            "message": request.POST.get("message", "").strip(),
        })
    elif inquiry_type == "media":
        payload.update({
            "full_name": request.POST.get("media_name", "").strip(),
            "email": request.POST.get("media_email", "").strip(),
            "phone": request.POST.get("media_phone", "").strip() or None,
            "media_outlet": request.POST.get("media_outlet", "").strip(),
            "story_type": request.POST.get("story_type", "").strip() or None,
            "deadline": request.POST.get("deadline", "").strip() or None,
            "subject": request.POST.get("media_subject", "").strip(),
            "message": request.POST.get("media_message", "").strip(),
        })
    elif inquiry_type == "secure_tip":
        is_anonymous = request.POST.get("is_anonymous") == "on"
        payload.update({
            "is_anonymous": is_anonymous,
            "full_name": None if is_anonymous else request.POST.get("tip_name", "").strip() or None,
            "email": None if is_anonymous else request.POST.get("tip_contact", "").strip() or None,
            "urgency_level": request.POST.get("urgency_level", "normal").strip(),
            "subject": request.POST.get("tip_subject", "").strip(),
            "message": request.POST.get("tip_message", "").strip(),
            "evidence_description": request.POST.get("evidence_description", "").strip() or None,
        })
    elif inquiry_type == "encrypted":
        payload.update({
            "preferred_secure_channel": request.POST.get("preferred_secure_channel", "").strip(),
            "secure_contact_handle": request.POST.get("secure_contact_handle", "").strip(),
            "pgp_public_key": request.POST.get("pgp_public_key", "").strip() or None,
            "message": request.POST.get("encrypted_message", "").strip(),
        })

    # Validate required fields
    if not payload.get("message"):
        return JsonResponse({"success": False, "errors": ["Message is required."]})

    base_url = settings.SUPABASE_URL.rstrip("/")
    headers = {
        "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    try:
        url = f"{base_url}/rest/v1/contact_inquiries"
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        response_data = {
            "success": True,
            "message": "Thank you for contacting us. We will respond as soon as possible.",
        }

        # Include reference code for anonymous tips
        if data and len(data) > 0 and data[0].get("tip_reference_code"):
            response_data["reference_code"] = data[0]["tip_reference_code"]

        return JsonResponse(response_data)
    except Exception as e:
        print(f"[Contact Submit] Error: {e}")
        return JsonResponse({"success": False, "errors": ["Failed to submit. Please try again."]})


def dashboard_inquiries(request):
    """
    Dashboard view for managing contact inquiries.
    """
    inquiries = []
    stats = {"new": 0, "in_progress": 0, "total": 0}

    base_url = settings.SUPABASE_URL.rstrip("/")
    headers = {
        "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
        "Accept": "application/json",
    }

    try:
        url = f"{base_url}/rest/v1/contact_inquiries"
        resp = requests.get(
            url,
            headers=headers,
            params={"select": "*", "order": "created_at.desc"},
            timeout=10
        )
        if resp.status_code == 200:
            inquiries = resp.json()
            stats["total"] = len(inquiries)
            stats["new"] = sum(1 for i in inquiries if i.get("status") == "new")
            stats["in_progress"] = sum(1 for i in inquiries if i.get("status") == "in_progress")
    except Exception as e:
        print(f"[Dashboard Inquiries] Error fetching data: {e}")

    return render(request, "dashboard/inquiries.html", {
        "active_page": "inquiries",
        "inquiries": inquiries,
        "stats": stats,
    })


def dashboard_inquiry_get(request):
    """
    Fetch a single inquiry by id for viewing.
    Returns JSON.
    """
    item_id = request.GET.get("id", "").strip()

    if not item_id:
        return JsonResponse({"success": False, "error": "Invalid parameters"})

    base_url = settings.SUPABASE_URL.rstrip("/")
    headers = {
        "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
        "Accept": "application/json",
    }

    try:
        url = f"{base_url}/rest/v1/contact_inquiries?id=eq.{item_id}&select=*"
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data:
            return JsonResponse({"success": True, "item": data[0]})
        return JsonResponse({"success": False, "error": "Item not found"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@require_POST
def dashboard_inquiry_status(request):
    """
    Update inquiry status and internal notes.
    Returns JSON.
    """
    item_id = request.POST.get("inquiry_id", "").strip()
    status = request.POST.get("status", "").strip()
    internal_notes = request.POST.get("internal_notes", "").strip()

    if not item_id or not status:
        return JsonResponse({"success": False, "error": "Invalid parameters"})

    base_url = settings.SUPABASE_URL.rstrip("/")
    headers = {
        "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

    payload = {"status": status}
    if internal_notes:
        payload["internal_notes"] = internal_notes

    try:
        url = f"{base_url}/rest/v1/contact_inquiries?id=eq.{item_id}"
        resp = requests.patch(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@require_POST
def dashboard_inquiry_reply(request):
    """
    Send email reply to an inquiry and optionally update status.
    """
    from django.core.mail import send_mail

    item_id = request.POST.get("inquiry_id", "").strip()
    reply_subject = request.POST.get("reply_subject", "").strip()
    reply_message = request.POST.get("reply_message", "").strip()
    mark_as_replied = request.POST.get("mark_as_replied") == "on"

    if not item_id or not reply_message:
        return JsonResponse({"success": False, "error": "Missing required fields"})

    # First, fetch the inquiry to get the email
    base_url = settings.SUPABASE_URL.rstrip("/")
    headers = {
        "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
        "Accept": "application/json",
    }

    try:
        url = f"{base_url}/rest/v1/contact_inquiries?id=eq.{item_id}&select=*"
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if not data:
            return JsonResponse({"success": False, "error": "Inquiry not found"})

        inquiry = data[0]
        recipient_email = inquiry.get("email")

        if not recipient_email:
            return JsonResponse({"success": False, "error": "No email address available for this inquiry"})

        # Send the email
        try:
            send_mail(
                subject=reply_subject or "Response to your inquiry - RATEL Movement",
                message=reply_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                fail_silently=False,
            )
        except Exception as email_error:
            print(f"[Inquiry Reply] Email error: {email_error}")
            return JsonResponse({"success": False, "error": f"Failed to send email: {str(email_error)}"})

        # Update the inquiry with reply info
        update_payload = {
            "reply_message": reply_message,
            "replied_at": "now()",
        }
        if mark_as_replied:
            update_payload["status"] = "replied"

        headers["Content-Type"] = "application/json"
        update_url = f"{base_url}/rest/v1/contact_inquiries?id=eq.{item_id}"
        requests.patch(update_url, headers=headers, json=update_payload, timeout=10)

        return JsonResponse({"success": True})
    except Exception as e:
        print(f"[Inquiry Reply] Error: {e}")
        return JsonResponse({"success": False, "error": str(e)})


# --- Media Vault Dashboard Views ---

def _get_supabase_headers():
    """Helper to get Supabase API headers."""
    return {
        "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _get_paystack_keys():
    """
    Get Paystack public and secret keys. Supabase paystack_settings overrides env.
    Returns (public_key, secret_key). Used for auth/renew pages and payment verification.
    """
    default_public = getattr(settings, "PAYSTACK_PUBLIC_KEY", "pk_test_af37d26c0fa360522c4e66495f3877e498c18850")
    default_secret = getattr(settings, "PAYSTACK_SECRET_KEY", "sk_test_185fc53d96addab7232060c86f4221918ab59d1c")
    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()
        resp = requests.get(
            f"{base_url}/rest/v1/paystack_settings?id=eq.1&select=public_key,secret_key&limit=1",
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 200 and resp.json():
            row = resp.json()[0]
            pk = (row.get("public_key") or "").strip()
            sk = (row.get("secret_key") or "").strip()
            if pk or sk:
                return (pk if pk else default_public, sk if sk else default_secret)
    except Exception as e:
        print(f"[Paystack] Error fetching from Supabase: {e}")
    return (default_public, default_secret)


def _normalize_blog_image_url(img_url, base_url):
    """Normalize blog featured image URL to ensure it's a full public URL."""
    if not img_url:
        return None

    img_url = str(img_url).strip()
    if not img_url:
        return None

    # If it's already a full HTTP/HTTPS URL, check if it needs fixing
    if img_url.startswith("http://") or img_url.startswith("https://"):
        # If it already has the correct public path, use as-is
        if "/storage/v1/object/public/blogs/" in img_url:
            return img_url

        # Fix signed URLs (convert /sign/ to /public/)
        if "/storage/v1/object/sign/blogs/" in img_url:
            return img_url.replace("/storage/v1/object/sign/blogs/", "/storage/v1/object/public/blogs/").split("?")[0]

        # Fix URLs missing "public" segment: /storage/v1/object/blogs/ -> /storage/v1/object/public/blogs/
        if "/storage/v1/object/blogs/" in img_url:
            return img_url.replace("/storage/v1/object/blogs/", "/storage/v1/object/public/blogs/").split("?")[0]

        # If it has /blogs/ but wrong path structure, extract filename and fix it
        if "/blogs/" in img_url:
            filename = img_url.split("/blogs/")[-1].split("?")[0]
            return f"{base_url}/storage/v1/object/public/blogs/{filename}"

        # Otherwise, it's a valid external URL, use as-is
        return img_url
    else:
        # Not a full URL, construct it (preserve folder structure like "featured/filename.jpg")
        path = img_url.lstrip('/')
        return f"{base_url}/storage/v1/object/public/blogs/{path}"


def _normalize_messages_url(img_url):
    """
    Normalize a Supabase storage URL for the messages bucket.
    Handles various URL formats and ensures the URL is a valid public URL.
    """
    base_url = settings.SUPABASE_URL.rstrip("/")

    if not img_url:
        return None

    img_url = str(img_url).strip()
    if not img_url:
        return None

    # If it's already a full HTTP/HTTPS URL, check if it needs fixing
    if img_url.startswith("http://") or img_url.startswith("https://"):
        # Remove any query parameters (signed URLs have tokens)
        clean_url = img_url.split("?")[0]

        # If it already has the correct public path, use as-is
        if "/storage/v1/object/public/messages/" in clean_url:
            return clean_url

        # Fix signed URLs (convert /sign/ to /public/)
        if "/storage/v1/object/sign/messages/" in clean_url:
            return clean_url.replace("/storage/v1/object/sign/messages/", "/storage/v1/object/public/messages/")

        # Fix URLs missing "public" segment: /storage/v1/object/messages/ -> /storage/v1/object/public/messages/
        if "/storage/v1/object/messages/" in clean_url:
            return clean_url.replace("/storage/v1/object/messages/", "/storage/v1/object/public/messages/")

        # If it has /messages/ but wrong path structure, extract filename and fix it
        if "/messages/" in clean_url:
            filename = clean_url.split("/messages/")[-1]
            return f"{base_url}/storage/v1/object/public/messages/{filename}"

        # Otherwise, it's a valid external URL, use as-is
        return img_url
    else:
        # Not a full URL, construct it
        path = img_url.lstrip('/')
        return f"{base_url}/storage/v1/object/public/messages/{path}"


def _upload_to_supabase_storage(file, bucket="media-vault", folder=""):
    """Upload file to Supabase Storage and return public URL."""
    try:
        print(f"[Storage Upload] Starting upload: bucket={bucket}, folder={folder}, filename={file.name}")
        supabase = get_supabase()

        # Generate unique filename
        import uuid
        ext = file.name.split('.')[-1] if '.' in file.name else ''
        unique_name = f"{folder}/{uuid.uuid4().hex}.{ext}" if folder else f"{uuid.uuid4().hex}.{ext}"
        print(f"[Storage Upload] Generated unique_name: {unique_name}")

        # Read file content
        file_content = file.read()
        print(f"[Storage Upload] File content size: {len(file_content)} bytes")

        # Upload to Supabase Storage
        result = supabase.storage.from_(bucket).upload(
            unique_name,
            file_content,
            {"content-type": file.content_type}
        )
        print(f"[Storage Upload] Upload result: {result}")

        # Construct public URL manually (more reliable than SDK's get_public_url)
        # The correct format is: {SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}
        base_url = settings.SUPABASE_URL.rstrip("/")
        public_url = f"{base_url}/storage/v1/object/public/{bucket}/{unique_name}"
        print(f"[Storage Upload] Constructed public URL: {public_url}")

        # Also try SDK's get_public_url for debugging
        sdk_url = supabase.storage.from_(bucket).get_public_url(unique_name)
        print(f"[Storage Upload] SDK public URL: {sdk_url}")

        return public_url
    except Exception as e:
        print(f"[Storage Upload] Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def dashboard_media_vault(request):
    """
    Media Vault overview dashboard showing stats and recent items.
    """
    base_url = settings.SUPABASE_URL.rstrip("/")
    headers = _get_supabase_headers()

    video_count = 0
    audio_count = 0
    image_count = 0
    document_count = 0
    recent_videos = []
    recent_documents = []

    try:
        # Fetch video count
        resp = requests.get(
            f"{base_url}/rest/v1/media_videos?select=id&status=eq.active",
            headers=headers, timeout=10
        )
        if resp.status_code == 200:
            video_count = len(resp.json())

        # Fetch audio count
        resp = requests.get(
            f"{base_url}/rest/v1/media_audio?select=id&status=eq.active",
            headers=headers, timeout=10
        )
        if resp.status_code == 200:
            audio_count = len(resp.json())

        # Fetch image count
        resp = requests.get(
            f"{base_url}/rest/v1/media_images?select=id&status=eq.active",
            headers=headers, timeout=10
        )
        if resp.status_code == 200:
            image_count = len(resp.json())

        # Fetch document count
        resp = requests.get(
            f"{base_url}/rest/v1/media_documents?select=id&status=eq.active",
            headers=headers, timeout=10
        )
        if resp.status_code == 200:
            document_count = len(resp.json())

        # Fetch recent videos
        resp = requests.get(
            f"{base_url}/rest/v1/media_videos?select=*&status=eq.active&order=created_at.desc&limit=3",
            headers=headers, timeout=10
        )
        if resp.status_code == 200:
            recent_videos = resp.json()

        # Fetch recent documents
        resp = requests.get(
            f"{base_url}/rest/v1/media_documents?select=*&status=eq.active&order=created_at.desc&limit=3",
            headers=headers, timeout=10
        )
        if resp.status_code == 200:
            recent_documents = resp.json()

    except Exception as e:
        print(f"[Media Vault] Error fetching stats: {e}")

    return render(request, "dashboard/media_vault.html", {
        "active_page": "media_vault",
        "video_count": video_count,
        "audio_count": audio_count,
        "image_count": image_count,
        "document_count": document_count,
        "recent_videos": recent_videos,
        "recent_documents": recent_documents,
    })


def dashboard_media_videos(request):
    """
    Dashboard page for managing videos.
    """
    base_url = settings.SUPABASE_URL.rstrip("/")
    headers = _get_supabase_headers()

    category = request.GET.get("category", "")
    videos = []

    try:
        url = f"{base_url}/rest/v1/media_videos?select=*&status=eq.active&order=created_at.desc"
        if category and category != "all":
            url += f"&category=eq.{category}"

        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            videos = resp.json()
    except Exception as e:
        print(f"[Media Videos] Error: {e}")

    return render(request, "dashboard/media_videos.html", {
        "active_page": "media_videos",
        "videos": videos,
        "current_category": category,
    })


@require_POST
def dashboard_media_videos_save(request):
    """
    Save a new video to the database. Can upload file OR provide video link (YouTube, Vimeo, etc.).
    """
    title = request.POST.get("title", "").strip()
    category = request.POST.get("category", "").strip()
    description = request.POST.get("description", "").strip()
    source = request.POST.get("source", "").strip()
    location = request.POST.get("location", "").strip()
    recorded_date = request.POST.get("recorded_date", "").strip() or None
    tags = request.POST.get("tags", "").strip()
    video_link = request.POST.get("video_link", "").strip()

    video_file = request.FILES.get("video_file")
    thumbnail_file = request.FILES.get("thumbnail")

    if not title or not category:
        messages.error(request, "Title and category are required.")
        return redirect("dashboard_media_videos")

    # Must have either video_file OR video_link
    if not video_file and not video_link:
        messages.error(request, "Either video file or video link is required.")
        return redirect("dashboard_media_videos")

    try:
        file_url = None
        file_size_bytes = None
        mime_type = None

        # Handle file upload OR video link
        if video_file:
            # Upload video file
            file_url = _upload_to_supabase_storage(video_file, "media-vault", "videos")
            if not file_url:
                messages.error(request, "Failed to upload video file.")
                return redirect("dashboard_media_videos")
            file_size_bytes = video_file.size
            mime_type = video_file.content_type
        elif video_link:
            # Use provided video link (YouTube, Vimeo, etc.)
            file_url = None  # Will use video_link instead
            # Try to extract video ID for thumbnail if YouTube
            if "youtube.com" in video_link or "youtu.be" in video_link:
                # YouTube link - could extract thumbnail URL here if needed
                pass

        # Upload thumbnail if provided
        thumbnail_url = None
        if thumbnail_file:
            thumbnail_url = _upload_to_supabase_storage(thumbnail_file, "media-vault", "thumbnails")

        # Parse tags
        tags_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

        # Save to database
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        # Build payload, only including non-empty values
        payload = {
            "title": title,
            "category": category,
            "tags": tags_list,
            "status": "active",
        }
        
        # Add optional fields only if they have values
        if description:
            payload["description"] = description
        if source:
            payload["source"] = source
        if location:
            payload["location"] = location
        if recorded_date:
            payload["recorded_date"] = recorded_date
        if thumbnail_url:
            payload["thumbnail_url"] = thumbnail_url

        # Add file_url OR video_link (not both)
        if file_url:
            payload["file_url"] = file_url
            if file_size_bytes:
                payload["file_size_bytes"] = file_size_bytes
            if mime_type:
                payload["mime_type"] = mime_type
        elif video_link:
            payload["video_link"] = video_link
            # Explicitly set file_url to null for link-only videos (requires migration: file_url must be nullable)
            payload["file_url"] = None

        resp = requests.post(
            f"{base_url}/rest/v1/media_videos",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if resp.status_code not in [200, 201]:
            error_msg = resp.text
            print(f"[Video Save] Supabase Error ({resp.status_code}): {error_msg}")
            print(f"[Video Save] Payload: {payload}")
            if "23502" in error_msg and "file_url" in error_msg:
                messages.error(
                    request,
                    "Saving link-only videos requires making file_url nullable. "
                    "Run the SQL in migrations/add_video_link_column.sql in your Supabase SQL editor."
                )
            else:
                messages.error(request, f"Failed to save video: {error_msg[:200]}")
            return redirect("dashboard_media_videos")
        
        resp.raise_for_status()

        messages.success(request, "Video saved successfully!")
    except Exception as e:
        print(f"[Video Save] Error: {e}")
        import traceback
        traceback.print_exc()
        messages.error(request, f"Failed to save video: {str(e)}")

    return redirect("dashboard_media_videos")


@require_POST
def dashboard_media_videos_delete(request):
    """
    Delete a video (soft delete by setting status to archived).
    """
    import json
    data = json.loads(request.body)
    video_id = data.get("id")

    if not video_id:
        return JsonResponse({"success": False, "error": "Video ID required"})

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        resp = requests.patch(
            f"{base_url}/rest/v1/media_videos?id=eq.{video_id}",
            headers=headers,
            json={"status": "archived"},
            timeout=10
        )
        resp.raise_for_status()

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


def dashboard_media_audio(request):
    """
    Dashboard page for managing audio files.
    """
    base_url = settings.SUPABASE_URL.rstrip("/")
    headers = _get_supabase_headers()

    category = request.GET.get("category", "")
    audios = []

    try:
        url = f"{base_url}/rest/v1/media_audio?select=*&status=eq.active&order=created_at.desc"
        if category and category != "all":
            url += f"&category=eq.{category}"

        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            audios = resp.json()
    except Exception as e:
        print(f"[Media Audio] Error: {e}")

    return render(request, "dashboard/media_audio.html", {
        "active_page": "media_audio",
        "audios": audios,
        "current_category": category,
    })


@require_POST
def dashboard_media_audio_save(request):
    """
    Save a new audio file to the database and upload to storage.
    """
    title = request.POST.get("title", "").strip()
    category = request.POST.get("category", "").strip()
    description = request.POST.get("description", "").strip()
    speaker = request.POST.get("speaker", "").strip()
    source = request.POST.get("source", "").strip()
    recorded_date = request.POST.get("recorded_date", "").strip() or None
    transcript = request.POST.get("transcript", "").strip()

    audio_file = request.FILES.get("audio_file")
    cover_image = request.FILES.get("cover_image")

    if not title or not category or not audio_file:
        messages.error(request, "Title, category, and audio file are required.")
        return redirect("dashboard_media_audio")

    try:
        # Upload audio file
        file_url = _upload_to_supabase_storage(audio_file, "media-vault", "audio")
        if not file_url:
            messages.error(request, "Failed to upload audio file.")
            return redirect("dashboard_media_audio")

        # Upload cover image if provided
        cover_image_url = None
        if cover_image:
            cover_image_url = _upload_to_supabase_storage(cover_image, "media-vault", "covers")

        # Save to database
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        payload = {
            "title": title,
            "category": category,
            "description": description,
            "file_url": file_url,
            "cover_image_url": cover_image_url,
            "status": "active",
            "speaker": speaker,
            "source": source,
            "recorded_date": recorded_date,
            "transcript": transcript,
            "file_size_bytes": audio_file.size,
            "mime_type": audio_file.content_type,
        }

        resp = requests.post(
            f"{base_url}/rest/v1/media_audio",
            headers=headers,
            json=payload,
            timeout=30
        )
        resp.raise_for_status()

        messages.success(request, "Audio uploaded successfully!")
    except Exception as e:
        print(f"[Audio Save] Error: {e}")
        messages.error(request, f"Failed to save audio: {str(e)}")

    return redirect("dashboard_media_audio")


@require_POST
def dashboard_media_audio_delete(request):
    """
    Delete an audio file (soft delete).
    """
    import json
    data = json.loads(request.body)
    audio_id = data.get("id")

    if not audio_id:
        return JsonResponse({"success": False, "error": "Audio ID required"})

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        resp = requests.patch(
            f"{base_url}/rest/v1/media_audio?id=eq.{audio_id}",
            headers=headers,
            json={"status": "archived"},
            timeout=10
        )
        resp.raise_for_status()

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


def dashboard_media_images(request):
    """
    Dashboard page for managing images.
    """
    base_url = settings.SUPABASE_URL.rstrip("/")
    headers = _get_supabase_headers()

    category = request.GET.get("category", "")
    images = []

    try:
        url = f"{base_url}/rest/v1/media_images?select=*&status=eq.active&order=created_at.desc"
        if category and category != "all":
            url += f"&category=eq.{category}"

        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            images = resp.json()
    except Exception as e:
        print(f"[Media Images] Error: {e}")

    return render(request, "dashboard/media_images.html", {
        "active_page": "media_images",
        "images": images,
        "current_category": category,
    })


@require_POST
def dashboard_media_images_save(request):
    """
    Save a new image to the database and upload to storage.
    """
    title = request.POST.get("title", "").strip()
    category = request.POST.get("category", "").strip()
    description = request.POST.get("description", "").strip()
    photographer = request.POST.get("photographer", "").strip()
    source = request.POST.get("source", "").strip()
    location = request.POST.get("location", "").strip()
    captured_date = request.POST.get("captured_date", "").strip() or None
    alt_text = request.POST.get("alt_text", "").strip()

    image_file = request.FILES.get("image_file")

    if not title or not category or not image_file:
        messages.error(request, "Title, category, and image file are required.")
        return redirect("dashboard_media_images")

    try:
        # Upload image file
        file_url = _upload_to_supabase_storage(image_file, "media-vault", "images")
        if not file_url:
            messages.error(request, "Failed to upload image file.")
            return redirect("dashboard_media_images")

        # Save to database
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        payload = {
            "title": title,
            "category": category,
            "description": description,
            "file_url": file_url,
            "thumbnail_url": file_url,  # Use same URL for thumbnail
            "photographer": photographer,
            "source": source,
            "location": location,
            "captured_date": captured_date,
            "alt_text": alt_text,
            "status": "active",
            "file_size_bytes": image_file.size,
            "mime_type": image_file.content_type,
        }

        resp = requests.post(
            f"{base_url}/rest/v1/media_images",
            headers=headers,
            json=payload,
            timeout=30
        )
        resp.raise_for_status()

        messages.success(request, "Image uploaded successfully!")
    except Exception as e:
        print(f"[Image Save] Error: {e}")
        messages.error(request, f"Failed to save image: {str(e)}")

    return redirect("dashboard_media_images")


@require_POST
def dashboard_media_images_delete(request):
    """
    Delete an image (soft delete).
    """
    import json
    data = json.loads(request.body)
    image_id = data.get("id")

    if not image_id:
        return JsonResponse({"success": False, "error": "Image ID required"})

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        resp = requests.patch(
            f"{base_url}/rest/v1/media_images?id=eq.{image_id}",
            headers=headers,
            json={"status": "archived"},
            timeout=10
        )
        resp.raise_for_status()

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


def dashboard_media_documents(request):
    """
    Dashboard page for managing documents.
    """
    base_url = settings.SUPABASE_URL.rstrip("/")
    headers = _get_supabase_headers()

    category = request.GET.get("category", "")
    documents = []

    try:
        url = f"{base_url}/rest/v1/media_documents?select=*&status=eq.active&order=created_at.desc"
        if category and category != "all":
            url += f"&category=eq.{category}"

        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            documents = resp.json()
    except Exception as e:
        print(f"[Media Documents] Error: {e}")

    return render(request, "dashboard/media_documents.html", {
        "active_page": "media_documents",
        "documents": documents,
        "current_category": category,
    })


@require_POST
def dashboard_media_documents_save(request):
    """
    Save a new document to the database and upload to storage.
    """
    title = request.POST.get("title", "").strip()
    category = request.POST.get("category", "").strip()
    description = request.POST.get("description", "").strip()
    author = request.POST.get("author", "").strip()
    source = request.POST.get("source", "").strip()
    document_date = request.POST.get("document_date", "").strip() or None
    reference_number = request.POST.get("reference_number", "").strip()
    is_confidential = request.POST.get("is_confidential") == "on"

    document_file = request.FILES.get("document_file")

    if not title or not category or not document_file:
        messages.error(request, "Title, category, and document file are required.")
        return redirect("dashboard_media_documents")

    try:
        # Upload document file
        file_url = _upload_to_supabase_storage(document_file, "media-vault", "documents")
        if not file_url:
            messages.error(request, "Failed to upload document file.")
            return redirect("dashboard_media_documents")

        # Save to database
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        payload = {
            "title": title,
            "category": category,
            "description": description,
            "file_url": file_url,
            "author": author,
            "source": source,
            "document_date": document_date,
            "reference_number": reference_number,
            "is_confidential": is_confidential,
            "file_size_bytes": document_file.size,
            "status": "active",
            "mime_type": document_file.content_type,
        }

        resp = requests.post(
            f"{base_url}/rest/v1/media_documents",
            headers=headers,
            json=payload,
            timeout=30
        )
        resp.raise_for_status()

        messages.success(request, "Document uploaded successfully!")
    except Exception as e:
        print(f"[Document Save] Error: {e}")
        messages.error(request, f"Failed to save document: {str(e)}")

    return redirect("dashboard_media_documents")


@require_POST
def dashboard_media_documents_delete(request):
    """
    Delete a document (soft delete).
    """
    import json
    data = json.loads(request.body)
    doc_id = data.get("id")

    if not doc_id:
        return JsonResponse({"success": False, "error": "Document ID required"})

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        resp = requests.patch(
            f"{base_url}/rest/v1/media_documents?id=eq.{doc_id}",
            headers=headers,
            json={"status": "archived"},
            timeout=10
        )
        resp.raise_for_status()

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


# =====================================================
# ANNOUNCEMENTS MANAGEMENT
# =====================================================

def dashboard_announcements(request):
    """
    Admin page to manage internal announcements.
    """
    announcements = []
    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        resp = requests.get(
            f"{base_url}/rest/v1/internal_announcements?order=created_at.desc",
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()
        announcements = resp.json()
    except Exception as e:
        print(f"[Announcements] Error fetching: {e}")
        messages.error(request, "Failed to load announcements.")

    return render(request, "dashboard/announcements.html", {"announcements": announcements, "active_page": "announcements"})


@require_POST
def dashboard_announcements_save(request):
    """
    Create or update an announcement.
    """
    import json
    data = json.loads(request.body)

    announcement_id = data.get("id")
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    recipient_type = data.get("recipient_type", "all_members")
    priority = data.get("priority", "normal")
    is_pinned = data.get("is_pinned", False)
    expires_at = data.get("expires_at") or None

    if not title or not content:
        return JsonResponse({"success": False, "error": "Title and content are required"})

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        payload = {
            "title": title,
            "content": content,
            "recipient_type": recipient_type,
            "priority": priority,
            "is_pinned": is_pinned,
            "expires_at": expires_at,
        }

        if announcement_id:
            # Update existing
            resp = requests.patch(
                f"{base_url}/rest/v1/internal_announcements?id=eq.{announcement_id}",
                headers=headers,
                json=payload,
                timeout=10
            )
        else:
            # Create new
            resp = requests.post(
                f"{base_url}/rest/v1/internal_announcements",
                headers=headers,
                json=payload,
                timeout=10
            )

        resp.raise_for_status()
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@require_POST
def dashboard_announcements_delete(request):
    """
    Delete an announcement.
    """
    import json
    data = json.loads(request.body)
    announcement_id = data.get("id")

    if not announcement_id:
        return JsonResponse({"success": False, "error": "Announcement ID required"})

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        resp = requests.delete(
            f"{base_url}/rest/v1/internal_announcements?id=eq.{announcement_id}",
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


def dashboard_announcements_get(request):
    """
    Get a single announcement by ID.
    """
    announcement_id = request.GET.get("id")

    if not announcement_id:
        return JsonResponse({"success": False, "error": "Announcement ID required"})

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        resp = requests.get(
            f"{base_url}/rest/v1/internal_announcements?id=eq.{announcement_id}&select=*",
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()

        if data:
            return JsonResponse({"success": True, "announcement": data[0]})
        return JsonResponse({"success": False, "error": "Announcement not found"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


# =====================================================
# COMMUNICATIONS MANAGEMENT
# =====================================================

def dashboard_communications(request):
    """
    Admin page to manage secure communications.
    """
    communications = []
    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        resp = requests.get(
            f"{base_url}/rest/v1/secure_communications?order=created_at.desc",
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()
        communications = resp.json()
    except Exception as e:
        print(f"[Communications] Error fetching: {e}")
        messages.error(request, "Failed to load communications.")

    return render(request, "dashboard/communications.html", {"communications": communications, "active_page": "communications"})


@require_POST
def dashboard_communications_save(request):
    """
    Create or update a secure communication.
    """
    import json
    data = json.loads(request.body)

    comm_id = data.get("id")
    subject = data.get("subject", "").strip()
    message = data.get("message", "").strip()
    recipient_type = data.get("recipient_type", "all_members")
    classification = data.get("classification", "internal")
    requires_acknowledgment = data.get("requires_acknowledgment", False)
    attachment_url = data.get("attachment_url", "")

    if not subject or not message:
        return JsonResponse({"success": False, "error": "Subject and message are required"})

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        payload = {
            "subject": subject,
            "message": message,
            "recipient_type": recipient_type,
            "classification": classification,
            "requires_acknowledgment": requires_acknowledgment,
            "attachment_url": attachment_url if attachment_url else None,
        }

        if comm_id:
            # Update existing
            resp = requests.patch(
                f"{base_url}/rest/v1/secure_communications?id=eq.{comm_id}",
                headers=headers,
                json=payload,
                timeout=10
            )
        else:
            # Create new
            resp = requests.post(
                f"{base_url}/rest/v1/secure_communications",
                headers=headers,
                json=payload,
                timeout=10
            )

        resp.raise_for_status()
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@require_POST
def dashboard_communications_delete(request):
    """
    Delete a secure communication.
    """
    import json
    data = json.loads(request.body)
    comm_id = data.get("id")

    if not comm_id:
        return JsonResponse({"success": False, "error": "Communication ID required"})

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        resp = requests.delete(
            f"{base_url}/rest/v1/secure_communications?id=eq.{comm_id}",
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


def dashboard_communications_get(request):
    """
    Get a single communication by ID.
    Accepts GET ?id=... or POST JSON {"id": "..."}.
    """
    comm_id = request.GET.get("id")
    if not comm_id and request.method == "POST" and request.body:
        try:
            data = json.loads(request.body)
            comm_id = (data.get("id") or "").strip()
        except Exception:
            pass

    if not comm_id:
        return JsonResponse({"success": False, "error": "Communication ID required"})

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        resp = requests.get(
            f"{base_url}/rest/v1/secure_communications?id=eq.{comm_id}&select=*",
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()

        if data:
            return JsonResponse({"success": True, "communication": data[0]})
        return JsonResponse({"success": False, "error": "Communication not found"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


# =====================================================
# MEMBER DASHBOARD (User-facing)
# =====================================================

def _format_member_id_parts(country_code, state_code, member_number):
    """
    Format member ID from parts: RATEL-{COUNTRY_CODE}-{STATE_CODE}-{NUMBER}
    Example: RATEL-NG-LAG-000001. Use _generate_member_id(region_key) for signup (calls RPC).
    """
    return f"RATEL-{country_code}-{state_code}-{str(member_number).zfill(6)}"


def _get_state_code(state_name):
    """
    Get state abbreviation code from state name.
    Nigerian states use standard abbreviations.
    """
    state_codes = {
        "Abia": "ABI", "Adamawa": "ADA", "Akwa Ibom": "AKW", "Anambra": "ANA",
        "Bauchi": "BAU", "Bayelsa": "BAY", "Benue": "BEN", "Borno": "BOR",
        "Cross River": "CRO", "Delta": "DEL", "Ebonyi": "EBO", "Edo": "EDO",
        "Ekiti": "EKI", "Enugu": "ENU", "FCT": "FCT", "Gombe": "GOM",
        "Imo": "IMO", "Jigawa": "JIG", "Kaduna": "KAD", "Kano": "KAN",
        "Katsina": "KAT", "Kebbi": "KEB", "Kogi": "KOG", "Kwara": "KWA",
        "Lagos": "LAG", "Nasarawa": "NAS", "Niger": "NIG", "Ogun": "OGU",
        "Ondo": "OND", "Osun": "OSU", "Oyo": "OYO", "Plateau": "PLA",
        "Rivers": "RIV", "Sokoto": "SOK", "Taraba": "TAR", "Yobe": "YOB",
        "Zamfara": "ZAM"
    }
    return state_codes.get(state_name, state_name[:3].upper() if state_name else "XXX")


def _get_member_context(request):
    """
    Helper function to get common member context from session.
    Uses Supabase session data stored during login.
    """
    # Check if user is authenticated via session
    if not request.session.get("is_authenticated"):
        return None

    member_email = request.session.get("member_email")
    if not member_email:
        return None

    # Fetch full member data from Supabase
    try:
        sb = get_supabase()
        result = sb.table("members").select("*").eq("email", member_email).execute()

        if not result.data or len(result.data) == 0:
            return None

        member = result.data[0]

        # Parse name for initials
        full_name = member.get("full_name", "Member")
        name_parts = full_name.split()
        first_name = name_parts[0] if name_parts else "Member"
        last_name = name_parts[-1] if len(name_parts) > 1 else ""
        initials = (first_name[0] + (last_name[0] if last_name else "")).upper()

        # Determine member type/nationality
        based_in_nigeria = member.get("based_in_nigeria", True)
        if isinstance(based_in_nigeria, str):
            based_in_nigeria = based_in_nigeria.lower() == "true"

        member_country = "Nigeria" if based_in_nigeria else (member.get("country") or "International")
        member_state = member.get("state") or ""
        member_lga = member.get("lga") or ""

        # Parse created_at for member since
        created_at = member.get("created_at", "")
        member_since = "2024"
        member_joined = "January 2024"
        if created_at:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                member_since = str(dt.year)
                member_joined = dt.strftime("%B %Y")
            except:
                pass

        member_id = member.get("member_id", "RATEL-000000")
        subscription_status = "never_subscribed"
        try:
            base_url = settings.SUPABASE_URL.rstrip("/")
            headers = _get_supabase_headers()
            sub_resp = requests.get(
                f"{base_url}/rest/v1/member_subscriptions?member_id=eq.{member_id}&order=end_date.desc&limit=1",
                headers=headers,
                timeout=10
            )
            if sub_resp.status_code == 200 and sub_resp.json():
                end_date_str = sub_resp.json()[0].get("end_date")
                if end_date_str:
                    try:
                        end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                        now = datetime.now()
                        if end_date.replace(tzinfo=None) < now:
                            subscription_status = "expired"
                        elif end_date.replace(tzinfo=None) < now + timedelta(days=7):
                            subscription_status = "expiring_soon"
                        else:
                            subscription_status = "active"
                    except Exception:
                        pass
        except Exception:
            pass

        show_renew_overlay = subscription_status in ("expired", "never_subscribed")

        return {
            "member_name": full_name,
            "member_email": member.get("email"),
            "member_initials": initials,
            "member_type": "Nigerian" if based_in_nigeria else "Foreigner",
            "member_nationality": "nigerian" if based_in_nigeria else "foreigner",
            "member_first_name": first_name,
            "member_last_name": last_name,
            "member_since": member_since,
            # Badge-related fields
            "member_id": member_id,
            "member_country": member_country,
            "member_state": member_state,
            "member_lga": member_lga,
            "member_joined": member_joined,
            "member_number": member.get("id"),
            # Subscription info
            "subscription_end": member.get("subscription_end"),
            "membership_type": member.get("membership_type"),
            "profile_image_url": member.get("profile_image_url"),
            "subscription_status": subscription_status,
            "show_renew_overlay": show_renew_overlay,
        }

    except Exception as e:
        print(f"[DEBUG] Error fetching member context: {e}")
        import traceback
        traceback.print_exc()
        return None


def member_dashboard(request):
    """
    Member dashboard home page.
    Shows overview with recent announcements and communications.
    """
    from datetime import date

    # Check authentication
    member_ctx = _get_member_context(request)
    if not member_ctx:
        return redirect(f"/auth/?next=/member/")

    member_type = member_ctx.get("member_nationality", "nigerian")

    # Determine recipient filter based on member type
    if member_type == "nigerian":
        recipient_filter = "recipient_type=in.(all_members,nigerians)"
    else:
        recipient_filter = "recipient_type=in.(all_members,foreigners)"

    announcements = []
    communications = []
    resources = []
    subscription_status = "never_subscribed"
    subscription_end = None
    subscription_end_iso = None
    membership_fee = 500
    currency = "NGN"

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        # Fetch announcements for this member type
        ann_resp = requests.get(
            f"{base_url}/rest/v1/internal_announcements?{recipient_filter}&is_active=eq.true&order=is_pinned.desc,created_at.desc&limit=3",
            headers=headers,
            timeout=10
        )
        ann_resp.raise_for_status()
        announcements = ann_resp.json()

        # Fetch communications for this member type
        comm_resp = requests.get(
            f"{base_url}/rest/v1/secure_communications?{recipient_filter}&is_active=eq.true&order=created_at.desc&limit=3",
            headers=headers,
            timeout=10
        )
        comm_resp.raise_for_status()
        communications = comm_resp.json()

        # Fetch resources count
        res_resp = requests.get(
            f"{base_url}/rest/v1/resources?status=eq.active&select=id",
            headers=headers,
            timeout=10
        )
        res_resp.raise_for_status()
        resources = res_resp.json()

        # Fetch membership settings
        settings_resp = requests.get(
            f"{base_url}/rest/v1/membership_settings?select=*&limit=1",
            headers=headers,
            timeout=10
        )
        if settings_resp.status_code == 200:
            settings_data = settings_resp.json()
            if settings_data:
                membership_fee = settings_data[0].get("fee_amount", 500)
                currency = settings_data[0].get("currency", "NGN")

        # Fetch subscription status for this member
        member_id = member_ctx.get("member_id")
        sub_resp = requests.get(
            f"{base_url}/rest/v1/member_subscriptions?member_id=eq.{member_id}&order=end_date.desc&limit=1",
            headers=headers,
            timeout=10
        )
        if sub_resp.status_code == 200:
            sub_data = sub_resp.json()
            if sub_data:
                end_date_str = sub_data[0].get("end_date")
                if end_date_str:
                    try:
                        end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                        subscription_end = end_date.strftime("%B %d, %Y")
                        subscription_end_iso = end_date.isoformat()
                        now = datetime.now()
                        if end_date.replace(tzinfo=None) < now:
                            subscription_status = "expired"
                        elif end_date.replace(tzinfo=None) < now + timedelta(days=7):
                            subscription_status = "expiring_soon"
                        else:
                            subscription_status = "active"
                    except:
                        pass

    except Exception as e:
        print(f"[Member Dashboard] Error: {e}")

    context = {
        **member_ctx,
        "active_page": "dashboard",
        "today": date.today(),
        "recent_announcements": announcements,
        "recent_communications": communications,
        "announcements_count": len(announcements),
        "communications_count": len(communications),
        "resources_count": len(resources),
        "events_count": 0,  # Will be populated when events table exists
        "subscription_status": subscription_status,
        "subscription_end": subscription_end,
        "subscription_end_iso": subscription_end_iso,
        "membership_fee": membership_fee,
        "currency": currency,
    }

    return render(request, "member/dashboard.html", context)


def member_announcements(request):
    """
    Member announcements page - shows announcements filtered by member type.
    """
    member_ctx = _get_member_context(request)
    if not member_ctx:
        return redirect(f"/auth/?next=/member/announcements/")
    member_type = member_ctx.get("member_nationality", "nigerian")

    if member_type == "nigerian":
        recipient_filter = "recipient_type=in.(all_members,nigerians)"
    else:
        recipient_filter = "recipient_type=in.(all_members,foreigners)"

    announcements = []

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        resp = requests.get(
            f"{base_url}/rest/v1/internal_announcements?{recipient_filter}&is_active=eq.true&order=is_pinned.desc,created_at.desc",
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()
        announcements = resp.json()
    except Exception as e:
        print(f"[Member Announcements] Error: {e}")
        messages.error(request, "Failed to load announcements.")

    context = {
        **member_ctx,
        "active_page": "announcements",
        "announcements": announcements,
    }

    return render(request, "member/announcements.html", context)


def member_communications(request):
    """
    Member communications page - shows secure communications filtered by member type.
    """
    member_ctx = _get_member_context(request)
    if not member_ctx:
        return redirect(f"/auth/?next=/member/communications/")
    member_type = member_ctx.get("member_nationality", "nigerian")

    if member_type == "nigerian":
        recipient_filter = "recipient_type=in.(all_members,nigerians)"
    else:
        recipient_filter = "recipient_type=in.(all_members,foreigners)"

    communications = []

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        resp = requests.get(
            f"{base_url}/rest/v1/secure_communications?{recipient_filter}&is_active=eq.true&order=created_at.desc",
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()
        communications = resp.json()
    except Exception as e:
        print(f"[Member Communications] Error: {e}")
        messages.error(request, "Failed to load communications.")

    context = {
        **member_ctx,
        "active_page": "communications",
        "communications": communications,
    }

    return render(request, "member/communications.html", context)


def member_resources(request):
    """
    Member exclusive resources page.
    """
    member_ctx = _get_member_context(request)
    if not member_ctx:
        return redirect(f"/auth/?next=/member/resources/")
    resources = []

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        resp = requests.get(
            f"{base_url}/rest/v1/resources?status=eq.active&order=created_at.desc",
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()
        resources = resp.json()

        # Normalize file URLs and thumbnail URLs
        storage_base = f"{base_url}/storage/v1/object/public/resources/"
        for resource in resources:
            if resource.get("file_url") and not str(resource["file_url"]).startswith("http"):
                resource["file_url"] = storage_base + str(resource["file_url"]).lstrip("/")
            if resource.get("thumbnail_url") and not str(resource["thumbnail_url"]).startswith("http"):
                resource["thumbnail_url"] = storage_base + str(resource["thumbnail_url"]).lstrip("/")
    except Exception as e:
        print(f"[Member Resources] Error: {e}")

    context = {
        **member_ctx,
        "active_page": "resources",
        "resources": resources,
    }

    return render(request, "member/resources.html", context)


def member_events(request):
    """
    Member events page - shows upcoming events.
    """
    member_ctx = _get_member_context(request)
    if not member_ctx:
        return redirect(f"/auth/?next=/member/events/")
    events = []

    # Events would be fetched from a separate events table when implemented

    context = {
        **member_ctx,
        "active_page": "events",
        "events": events,
    }

    return render(request, "member/events.html", context)


def member_profile(request):
    """
    Member profile settings page.
    """
    member_ctx = _get_member_context(request)
    if not member_ctx:
        return redirect(f"/auth/?next=/member/profile/")

    context = {
        **member_ctx,
        "active_page": "profile",
    }

    return render(request, "member/profile.html", context)


@require_POST
def member_profile_update(request):
    """
    AJAX endpoint to update member profile information.
    """
    member_ctx = _get_member_context(request)
    if not member_ctx:
        return JsonResponse({"success": False, "error": "Not authenticated"}, status=401)

    first_name = request.POST.get("first_name", "").strip()
    last_name = request.POST.get("last_name", "").strip()
    phone = request.POST.get("phone", "").strip()
    location = request.POST.get("location", "").strip()

    full_name = f"{first_name} {last_name}".strip()

    try:
        sb = get_supabase()
        sb.table("members").update({
            "full_name": full_name,
            "phone_number": phone,
            "city": location,
        }).eq("email", member_ctx.get("member_email")).execute()

        return JsonResponse({"success": True, "message": "Profile updated successfully"})
    except Exception as e:
        print(f"[DEBUG] Error updating profile: {e}")
        return JsonResponse({"success": False, "error": "Failed to update profile"}, status=500)


@require_POST
def member_profile_password(request):
    """
    AJAX endpoint to update member password.
    """
    from django.contrib.auth.hashers import check_password, make_password

    print("[DEBUG] === Password Update Request ===")

    member_ctx = _get_member_context(request)
    if not member_ctx:
        print("[DEBUG] User not authenticated")
        return JsonResponse({"success": False, "error": "Not authenticated. Please log in again."}, status=401)

    member_email = member_ctx.get("member_email")
    print(f"[DEBUG] Updating password for: {member_email}")

    current_password = request.POST.get("current_password", "")
    new_password = request.POST.get("new_password", "")
    confirm_password = request.POST.get("confirm_password", "")

    # Validation
    if not current_password:
        return JsonResponse({"success": False, "error": "Current password is required"}, status=400)

    if not new_password:
        return JsonResponse({"success": False, "error": "New password is required"}, status=400)

    if not confirm_password:
        return JsonResponse({"success": False, "error": "Please confirm your new password"}, status=400)

    if new_password != confirm_password:
        return JsonResponse({"success": False, "error": "New passwords do not match"}, status=400)

    if len(new_password) < 8:
        return JsonResponse({"success": False, "error": "New password must be at least 8 characters"}, status=400)

    try:
        sb = get_supabase()
        # Get current password hash from Supabase
        result = sb.table("members").select("password_hash").eq("email", member_email).execute()

        if not result.data or len(result.data) == 0:
            print(f"[DEBUG] Member not found in database: {member_email}")
            return JsonResponse({"success": False, "error": "Member not found. Please log in again."}, status=404)

        stored_hash = result.data[0].get("password_hash", "")

        if not stored_hash:
            print("[DEBUG] No password hash stored for this member")
            return JsonResponse({"success": False, "error": "Account error. Please contact support."}, status=400)

        print("[DEBUG] Verifying current password...")

        # Verify current password
        if not check_password(current_password, stored_hash):
            print("[DEBUG] Current password verification failed")
            return JsonResponse({"success": False, "error": "Current password is incorrect"}, status=400)

        print("[DEBUG] Current password verified. Creating new hash...")

        # Update with new password
        new_hash = make_password(new_password)
        update_result = sb.table("members").update({
            "password_hash": new_hash
        }).eq("email", member_email).execute()

        print(f"[DEBUG] Password updated successfully for: {member_email}")
        return JsonResponse({"success": True, "message": "Password updated successfully!"})

    except Exception as e:
        print(f"[DEBUG] Error updating password: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"success": False, "error": "Failed to update password. Please try again."}, status=500)


@require_POST
def member_profile_photo(request):
    """
    AJAX endpoint to upload member profile photo.
    """
    member_ctx = _get_member_context(request)
    if not member_ctx:
        return JsonResponse({"success": False, "error": "Not authenticated"}, status=401)

    profile_image = request.FILES.get("profile_image")
    if not profile_image:
        return JsonResponse({"success": False, "error": "No image provided"}, status=400)

    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if profile_image.content_type not in allowed_types:
        return JsonResponse({"success": False, "error": "Invalid image type. Use JPG, PNG, GIF, or WebP."}, status=400)

    # Validate file size (max 5MB)
    if profile_image.size > 5 * 1024 * 1024:
        return JsonResponse({"success": False, "error": "Image too large. Maximum size is 5MB."}, status=400)

    try:
        sb = get_supabase()
        member_id = member_ctx.get("member_id", "unknown")

        # Generate unique filename
        import uuid
        file_ext = profile_image.name.split(".")[-1] if "." in profile_image.name else "jpg"
        file_name = f"{member_id}/{uuid.uuid4().hex[:8]}.{file_ext}"

        # Upload to Supabase Storage
        file_content = profile_image.read()
        upload_result = sb.storage.from_("profiles").upload(
            file_name,
            file_content,
            {"content-type": profile_image.content_type}
        )

        # Get public URL
        public_url = sb.storage.from_("profiles").get_public_url(file_name)

        # Update member record
        sb.table("members").update({
            "profile_image_url": public_url
        }).eq("email", member_ctx.get("member_email")).execute()

        return JsonResponse({
            "success": True,
            "message": "Profile photo updated successfully",
            "image_url": public_url
        })
    except Exception as e:
        print(f"[DEBUG] Error uploading profile photo: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"success": False, "error": "Failed to upload photo"}, status=500)


# --- Membership Renewal System ---

def dashboard_membership_status(request):
    """
    Admin page to view all members' subscription status and manage fee settings.
    """
    from datetime import datetime, timedelta

    members = []
    membership_fee = 500  # Default fee in Naira
    currency = "NGN"

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        # Fetch membership settings
        settings_resp = requests.get(
            f"{base_url}/rest/v1/membership_settings?select=*&limit=1",
            headers=headers,
            timeout=10
        )
        if settings_resp.status_code == 200:
            settings_data = settings_resp.json()
            if settings_data:
                membership_fee = settings_data[0].get("fee_amount", 500)
                currency = settings_data[0].get("currency", "NGN")

        # Fetch all members with their subscription status
        members_resp = requests.get(
            f"{base_url}/rest/v1/members?select=member_id,full_name,email,phone_number,based_in_nigeria,state,country,created_at,status,profile_image_url&order=created_at.desc",
            headers=headers,
            timeout=10
        )
        if members_resp.status_code == 200:
            members = members_resp.json()

            # Normalize profile image URLs
            bucket_base = f"{base_url}/storage/v1/object/public/profiles/"
            for m in members:
                path = m.get("profile_image_url")
                if path and not str(path).startswith("http"):
                    m["profile_image_url"] = bucket_base + str(path).lstrip("/")

        # Fetch subscriptions for all members
        subs_resp = requests.get(
            f"{base_url}/rest/v1/member_subscriptions?select=*&order=created_at.desc",
            headers=headers,
            timeout=10
        )
        subscriptions = {}
        if subs_resp.status_code == 200:
            subs_data = subs_resp.json()
            # Group by member_id, keeping the latest
            for sub in subs_data:
                mid = sub.get("member_id")
                if mid and mid not in subscriptions:
                    subscriptions[mid] = sub

        # Calculate renewal status for each member
        now = datetime.now()
        for m in members:
            mid = m.get("member_id")
            sub = subscriptions.get(mid)

            if sub:
                end_date_str = sub.get("end_date")
                if end_date_str:
                    try:
                        end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                        m["subscription_end"] = end_date.strftime("%Y-%m-%d")
                        m["subscription_status"] = sub.get("status", "active")

                        # Check if expired or expiring soon
                        if end_date.replace(tzinfo=None) < now:
                            m["renewal_status"] = "expired"
                            m["renewal_status_class"] = "danger"
                        elif end_date.replace(tzinfo=None) < now + timedelta(days=7):
                            m["renewal_status"] = "expiring_soon"
                            m["renewal_status_class"] = "warning"
                        else:
                            m["renewal_status"] = "active"
                            m["renewal_status_class"] = "success"
                    except:
                        m["renewal_status"] = "unknown"
                        m["renewal_status_class"] = "secondary"
                else:
                    m["renewal_status"] = "no_subscription"
                    m["renewal_status_class"] = "secondary"
            else:
                m["renewal_status"] = "never_subscribed"
                m["renewal_status_class"] = "secondary"
                m["subscription_end"] = None

    except Exception as e:
        print(f"[Membership Status] Error: {e}")

    # Count stats
    total = len(members)
    active_count = sum(1 for m in members if m.get("renewal_status") == "active")
    expiring_count = sum(1 for m in members if m.get("renewal_status") == "expiring_soon")
    expired_count = sum(1 for m in members if m.get("renewal_status") == "expired")
    never_count = sum(1 for m in members if m.get("renewal_status") == "never_subscribed")

    context = {
        "active_page": "membership_status",
        "members": members,
        "membership_fee": membership_fee,
        "currency": currency,
        "total_members": total,
        "active_count": active_count,
        "expiring_count": expiring_count,
        "expired_count": expired_count,
        "never_count": never_count,
    }

    return render(request, "dashboard/membership_status.html", context)


def dashboard_payments(request):
    """
    Dashboard payments: Donations + Membership renewal tabs.
    Top cards: Donations total, Membership total, Grand total.
    """
    if not request.session.get("is_authenticated"):
        return redirect("/auth/?next=/dashboard/payments/")

    member_email = request.session.get("member_email", "")
    ADMIN_EMAIL = "ratelmovement@gmail.com"
    if member_email != ADMIN_EMAIL and not request.session.get("is_admin"):
        return redirect("/member/")

    payments = []
    total_amount = 0
    currency = "NGN"
    donations_list = []
    donations_total = 0
    donation_currency = "GHS"

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        # Fetch membership settings for currency
        settings_resp = requests.get(
            f"{base_url}/rest/v1/membership_settings?select=currency&limit=1",
            headers=headers,
            timeout=10,
        )
        if settings_resp.status_code == 200:
            data = settings_resp.json()
            if data:
                currency = data[0].get("currency", "NGN")

        # Fetch donations
        don_resp = requests.get(
            f"{base_url}/rest/v1/donations?select=*&order=created_at.desc",
            headers=headers,
            timeout=10,
        )
        if don_resp.status_code == 200:
            for d in don_resp.json():
                amt = float(d.get("amount") or 0)
                donations_total += amt
                created = d.get("created_at") or ""
                try:
                    created_fmt = datetime.fromisoformat(created.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M") if created else "—"
                except Exception:
                    created_fmt = created or "—"
                donations_list.append({
                    "created_at": created,
                    "created_fmt": created_fmt,
                    "amount": amt,
                    "currency": d.get("currency") or "GHS",
                    "is_anonymous": d.get("is_anonymous", True),
                    "donor_name": d.get("donor_name") or "Anonymous",
                    "donor_email": d.get("donor_email") or "—",
                    "payment_reference": d.get("payment_reference") or "—",
                    "payment_method": d.get("payment_method") or "paystack",
                    "status": d.get("status") or "success",
                })

        # Fetch all subscription records (membership renewal)
        subs_resp = requests.get(
            f"{base_url}/rest/v1/member_subscriptions?select=*&order=created_at.desc",
            headers=headers,
            timeout=10,
        )
        if subs_resp.status_code != 200:
            subs_data = []
        else:
            subs_data = subs_resp.json()

        members_resp = requests.get(
            f"{base_url}/rest/v1/members?select=member_id,full_name,email",
            headers=headers,
            timeout=10,
        )
        members_by_id = {}
        if members_resp.status_code == 200:
            for m in members_resp.json():
                members_by_id[m.get("member_id")] = m

        for sub in subs_data:
            mid = sub.get("member_id")
            member_info = members_by_id.get(mid, {})
            member_name = member_info.get("full_name") or sub.get("member_email") or "—"
            created = sub.get("created_at") or ""
            try:
                created_fmt = datetime.fromisoformat(created.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M") if created else "—"
            except Exception:
                created_fmt = created or "—"
            start_date = sub.get("start_date") or ""
            end_date = sub.get("end_date") or ""
            try:
                start_fmt = datetime.fromisoformat(start_date.replace("Z", "+00:00")).strftime("%Y-%m-%d") if start_date else "—"
            except Exception:
                start_fmt = start_date or "—"
            try:
                end_fmt = datetime.fromisoformat(end_date.replace("Z", "+00:00")).strftime("%Y-%m-%d") if end_date else "—"
            except Exception:
                end_fmt = end_date or "—"
            amount = float(sub.get("amount_paid") or 0)
            total_amount += amount
            payments.append({
                "created_at": created,
                "created_fmt": created_fmt,
                "member_id": mid,
                "member_name": member_name,
                "member_email": sub.get("member_email") or "—",
                "amount_paid": amount,
                "currency": currency,
                "months_subscribed": sub.get("months_subscribed") or 0,
                "payment_reference": sub.get("payment_reference") or "—",
                "payment_method": sub.get("payment_method") or "—",
                "status": sub.get("status") or "—",
                "start_date_fmt": start_fmt,
                "end_date_fmt": end_fmt,
            })

    except Exception as e:
        print(f"[Dashboard Payments] Error: {e}")

    # CSV export (both tabs)
    if request.GET.get("format") == "csv":
        import csv
        from datetime import datetime as dt_export
        response = HttpResponse(content_type="text/csv")
        export_date = dt_export.now().strftime("%Y-%m-%d")
        response["Content-Disposition"] = f'attachment; filename="RATEL_Payments_{export_date}.csv"'
        writer = csv.writer(response)

        # Header row
        writer.writerow(["Type", "Date", "Name", "Email", "Amount", "Currency", "Reference", "Method", "Status", "Period"])

        # Combine all transactions
        all_transactions = []
        for p in donations_list:
            all_transactions.append({
                "type": "Donation",
                "date": p["created_at"],
                "date_fmt": p["created_fmt"],
                "name": p["donor_name"],
                "email": p["donor_email"],
                "amount": p["amount"],
                "currency": p["currency"],
                "reference": p["payment_reference"],
                "method": p["payment_method"],
                "status": p["status"],
                "period": "",
            })
        for p in payments:
            all_transactions.append({
                "type": "Membership Renewal",
                "date": p["created_at"],
                "date_fmt": p["created_fmt"],
                "name": p["member_name"],
                "email": p["member_email"],
                "amount": p["amount_paid"],
                "currency": p["currency"],
                "reference": p["payment_reference"],
                "method": p["payment_method"],
                "status": p["status"],
                "period": f"{p['start_date_fmt']} to {p['end_date_fmt']}",
            })

        # Sort by date descending (newest first)
        all_transactions.sort(key=lambda x: x["date"] or "", reverse=True)

        # Write all transactions
        for t in all_transactions:
            writer.writerow([t["type"], t["date_fmt"], t["name"], t["email"], f"{t['amount']:.2f}", t["currency"], t["reference"], t["method"], t["status"], t["period"]])

        # Totals section
        writer.writerow([])
        writer.writerow(["TOTALS", "", "", "", "", "", "", "", "", ""])
        writer.writerow([f"Donations ({len(donations_list)})", "", "", "", f"{donations_total:.2f}", donation_currency, "", "", "", ""])
        writer.writerow([f"Membership Renewals ({len(payments)})", "", "", "", f"{total_amount:.2f}", currency, "", "", "", ""])
        writer.writerow([f"Grand Total ({len(all_transactions)})", "", "", "", f"{donations_total + total_amount:.2f}", "", "", "", "", ""])

        return response

    grand_total_donations_ghs = donations_total
    grand_total_membership = total_amount
    # Grand total: show both (donations in GHS, membership in NGN) or convert if needed; for display we show separate + "Total" as sum of both numeric for admin
    grand_total_numeric = donations_total + total_amount  # mixed currency for count only; in UI we show each in its currency

    context = {
        "active_page": "payments",
        "payments": payments,
        "total_amount": total_amount,
        "currency": currency,
        "total_count": len(payments),
        "donations": donations_list,
        "donations_total": donations_total,
        "donation_currency": donation_currency,
        "donations_count": len(donations_list),
        "grand_total_donations_ghs": grand_total_donations_ghs,
        "grand_total_membership": grand_total_membership,
        "grand_total_numeric": grand_total_numeric,
    }
    return render(request, "dashboard/payments.html", context)


@require_POST
def donation_verify(request):
    """
    Verify Paystack donation payment and save to Supabase donations table.
    Expects POST: reference, amount, is_anonymous, donor_name, donor_email.
    """
    reference = (request.POST.get("reference") or "").strip()
    amount_str = request.POST.get("amount", "0")
    is_anonymous = request.POST.get("is_anonymous", "1") == "1"
    donor_name = (request.POST.get("donor_name") or "").strip() if not is_anonymous else None
    donor_email = (request.POST.get("donor_email") or "").strip() if not is_anonymous else None

    if not reference:
        return JsonResponse({"success": False, "message": "No payment reference."})

    try:
        amount = float(amount_str)
    except (TypeError, ValueError):
        amount = 0
    if amount <= 0:
        return JsonResponse({"success": False, "message": "Invalid amount."})

    _, paystack_secret_key = _get_paystack_keys()
    try:
        verify_resp = requests.get(
            f"https://api.paystack.co/transaction/verify/{reference}",
            headers={
                "Authorization": f"Bearer {paystack_secret_key}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        verify_data = verify_resp.json()
        if not verify_data.get("status") or verify_data.get("data", {}).get("status") != "success":
            return JsonResponse({"success": False, "message": "Payment verification failed."})
        payment_data = verify_data.get("data", {})
        amount_paid = payment_data.get("amount", 0) / 100  # pesewas to GHS
        if abs(amount_paid - amount) > 0.01:
            return JsonResponse({"success": False, "message": "Amount mismatch."})
    except Exception as e:
        print(f"[Donation Verify] Error: {e}")
        return JsonResponse({"success": False, "message": "Could not verify payment."})

    base_url = settings.SUPABASE_URL.rstrip("/")
    headers = _get_supabase_headers()
    headers["Content-Type"] = "application/json"
    headers["Prefer"] = "return=representation"
    payload = {
        "amount": amount,
        "currency": "GHS",
        "is_anonymous": is_anonymous,
        "donor_name": donor_name,
        "donor_email": donor_email,
        "payment_reference": reference,
        "payment_method": "paystack",
        "status": "success",
    }
    try:
        resp = requests.post(
            f"{base_url}/rest/v1/donations",
            headers=headers,
            json=payload,
            timeout=10,
        )
        if resp.status_code not in [200, 201]:
            return JsonResponse({"success": False, "message": "Failed to record donation."})
    except Exception as e:
        print(f"[Donation Verify] Supabase error: {e}")
        return JsonResponse({"success": False, "message": "Failed to record donation."})

    # Send thank-you email to donor (only when they provided email)
    if donor_email and donor_email.strip():
        _send_donation_thank_you(request, donor_email.strip(), donor_name or "Valued Supporter", amount)

    return JsonResponse({"success": True})


@require_POST
def dashboard_membership_settings_save(request):
    """
    Save membership fee settings to Supabase.
    """
    import json

    fee_amount = request.POST.get("fee_amount", 500)
    currency = request.POST.get("currency", "NGN")

    try:
        fee_amount = float(fee_amount)
    except:
        fee_amount = 500

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        # Check if settings exist
        check_resp = requests.get(
            f"{base_url}/rest/v1/membership_settings?select=id&limit=1",
            headers=headers,
            timeout=10
        )

        payload = {
            "fee_amount": fee_amount,
            "currency": currency,
            "updated_at": datetime.now().isoformat()
        }

        if check_resp.status_code == 200 and check_resp.json():
            # Update existing
            setting_id = check_resp.json()[0]["id"]
            resp = requests.patch(
                f"{base_url}/rest/v1/membership_settings?id=eq.{setting_id}",
                headers=headers,
                json=payload,
                timeout=10
            )
        else:
            # Insert new
            payload["created_at"] = datetime.now().isoformat()
            resp = requests.post(
                f"{base_url}/rest/v1/membership_settings",
                headers=headers,
                json=payload,
                timeout=10
            )

        if resp.status_code in [200, 201, 204]:
            messages.success(request, f"Membership fee updated to {currency} {fee_amount:,.2f}")
        else:
            messages.error(request, "Failed to save settings. Please try again.")

    except Exception as e:
        print(f"[Membership Settings Save] Error: {e}")
        messages.error(request, "An error occurred while saving settings.")

    return redirect("dashboard_membership_status")


@require_POST
def dashboard_membership_send_reminder(request):
    """
    Send renewal reminder email to a specific member.
    """
    member_id = request.POST.get("member_id")
    member_email = request.POST.get("email")
    member_name = request.POST.get("name", "Member")
    custom_message = request.POST.get("message", "")

    if not member_email:
        messages.error(request, "No email address provided.")
        return redirect("dashboard_membership_status")

    # Get membership fee
    membership_fee = 500
    currency = "NGN"

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        settings_resp = requests.get(
            f"{base_url}/rest/v1/membership_settings?select=*&limit=1",
            headers=headers,
            timeout=10
        )
        if settings_resp.status_code == 200:
            settings_data = settings_resp.json()
            if settings_data:
                membership_fee = settings_data[0].get("fee_amount", 500)
                currency = settings_data[0].get("currency", "NGN")
    except:
        pass

    # Compose email
    subject = "RATEL Movement - Membership Renewal Reminder"

    if custom_message:
        message_body = custom_message
    else:
        message_body = f"""Dear {member_name},

This is a friendly reminder that your RATEL Movement membership requires renewal.

Your Member ID: {member_id}
Renewal Fee: {currency} {membership_fee:,.2f}/month

To maintain your active membership status and continue accessing exclusive member benefits, please log in to your member dashboard and complete the renewal process.

Member Dashboard: {request.build_absolute_uri('/member/')}

If you have any questions or need assistance, please don't hesitate to contact us.

Neutrality is complicity.

RATEL Movement Team"""

    try:
        send_mail(
            subject,
            message_body,
            settings.DEFAULT_FROM_EMAIL,
            [member_email],
            fail_silently=False,
        )
        messages.success(request, f"Reminder email sent to {member_email}")
    except Exception as e:
        print(f"[Send Reminder] Error: {e}")
        messages.error(request, f"Failed to send email to {member_email}")

    return redirect("dashboard_membership_status")


def member_subscriptions(request):
    """
    Member page listing all their membership subscriptions and printable one-page invoice.
    """
    member_ctx = _get_member_context(request)
    if not member_ctx:
        return redirect(f"/auth/?next=/member/subscriptions/")

    subscriptions = []
    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()
        member_id = member_ctx.get("member_id")
        sub_resp = requests.get(
            f"{base_url}/rest/v1/member_subscriptions?member_id=eq.{member_id}&order=created_at.desc&select=*",
            headers=headers,
            timeout=10
        )
        if sub_resp.status_code == 200:
            raw = sub_resp.json()
            for s in raw:
                start_str = s.get("start_date")
                end_str = s.get("end_date")
                created_str = s.get("created_at")
                start_fmt = start_str
                end_fmt = end_str
                created_fmt = created_str
                if start_str:
                    try:
                        dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                        start_fmt = dt.strftime("%B %d, %Y")
                    except Exception:
                        pass
                if end_str:
                    try:
                        dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                        end_fmt = dt.strftime("%B %d, %Y")
                    except Exception:
                        pass
                if created_str:
                    try:
                        dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                        created_fmt = dt.strftime("%B %d, %Y")
                    except Exception:
                        pass
                subscriptions.append({
                    "id": s.get("id"),
                    "member_id": s.get("member_id"),
                    "member_email": s.get("member_email"),
                    "amount_paid": s.get("amount_paid"),
                    "months_subscribed": s.get("months_subscribed", 1),
                    "start_date": start_fmt,
                    "end_date": end_fmt,
                    "created_at": created_fmt,
                    "status": s.get("status", "active"),
                    "payment_reference": s.get("payment_reference"),
                    "payment_method": s.get("payment_method", "paystack"),
                })
    except Exception as e:
        print(f"[Member Subscriptions] Error: {e}")

    from datetime import datetime as dt_now
    context = {
        **member_ctx,
        "active_page": "subscriptions",
        "subscriptions": subscriptions,
        "invoice_date": dt_now.now().strftime("%B %d, %Y"),
    }
    return render(request, "member/subscriptions.html", context)


def member_subscription_invoice_pdf(request, subscription_id):
    """
    Download a single subscription as a professional one-page PDF invoice.
    Only the subscription owner can access.
    """
    member_ctx = _get_member_context(request)
    if not member_ctx:
        return redirect(f"/auth/?next=/member/subscriptions/")

    member_id = member_ctx.get("member_id")
    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()
        # Fetch this subscription only if it belongs to the logged-in member
        sub_resp = requests.get(
            f"{base_url}/rest/v1/member_subscriptions?id=eq.{subscription_id}&member_id=eq.{member_id}&select=*&limit=1",
            headers=headers,
            timeout=10
        )
        if sub_resp.status_code != 200 or not sub_resp.json():
            return HttpResponse("Invoice not found.", status=404)

        s = sub_resp.json()[0]
        start_str = s.get("start_date")
        end_str = s.get("end_date")
        created_str = s.get("created_at")
        start_fmt = start_str or ""
        end_fmt = end_str or ""
        created_fmt = created_str or ""
        if start_str:
            try:
                dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                start_fmt = dt.strftime("%B %d, %Y")
            except Exception:
                pass
        if end_str:
            try:
                dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                end_fmt = dt.strftime("%B %d, %Y")
            except Exception:
                pass
        if created_str:
            try:
                dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                created_fmt = dt.strftime("%B %d, %Y")
            except Exception:
                pass

        subscription = {
            "payment_reference": s.get("payment_reference") or "—",
            "amount_paid": s.get("amount_paid"),
            "months_subscribed": s.get("months_subscribed", 1),
            "start_date": start_fmt,
            "end_date": end_fmt,
            "created_at": created_fmt,
            "status": s.get("status", "active"),
            "payment_method": (s.get("payment_method") or "paystack").upper(),
        }
        invoice_date = datetime.now().strftime("%B %d, %Y")
        invoice_number = (s.get("payment_reference") or str(subscription_id))[:20]

        logo_url = "https://res.cloudinary.com/dmqizfpyz/image/upload/v1769424497/mmm_lyzhlw.png"
        context = {
            "member_name": member_ctx.get("member_name", "Member"),
            "member_email": member_ctx.get("member_email", ""),
            "member_id": member_id,
            "subscription": subscription,
            "invoice_date": invoice_date,
            "invoice_number": invoice_number,
            "logo_url": logo_url,
        }
        from io import BytesIO
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
        except ImportError:
            html = render_to_string("member/invoice_pdf.html", context)
            response = HttpResponse(html, content_type="text/html; charset=utf-8")
            response["Content-Disposition"] = f'inline; filename="invoice-{invoice_number}.html"'
            return response

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=15 * mm,
            leftMargin=15 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            name="InvoiceTitle",
            parent=styles["Heading1"],
            fontSize=24,
            spaceAfter=6,
        )
        heading_style = ParagraphStyle(
            name="CompanyName",
            parent=styles["Normal"],
            fontSize=18,
            fontName="Helvetica-Bold",
            spaceAfter=2,
        )
        sub_style = ParagraphStyle(
            name="Sub",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#6b7280"),
        )
        normal_style = styles["Normal"]
        normal_style.fontSize = 10
        meta_style = ParagraphStyle(
            name="Meta",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#4b5563"),
        )
        section_label = ParagraphStyle(
            name="SectionLabel",
            parent=styles["Normal"],
            fontSize=8.5,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#6b7280"),
            spaceAfter=6,
        )

        story = []
        # Header row: company left, INVOICE + meta right
        header_data = [
            [
                Paragraph("RATEL Movement", heading_style),
                Paragraph("INVOICE", title_style),
            ],
            [
                Paragraph("Membership Invoice", sub_style),
                Paragraph(
                    f'<b>Invoice #:</b> {invoice_number}<br/><b>Date:</b> {invoice_date}',
                    meta_style,
                ),
            ],
        ]
        header_table = Table(header_data, colWidths=[doc.width / 2, doc.width / 2])
        header_table.setStyle(
            TableStyle([
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 3, colors.HexColor("#111827")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
            ])
        )
        story.append(header_table)
        story.append(Spacer(1, 20))

        # Bill To
        story.append(Paragraph("BILL TO", section_label))
        bill_lines = [
            Paragraph(f"<b>{context['member_name']}</b>", normal_style),
            Paragraph(context["member_email"], normal_style),
            Paragraph(f"Member ID: {context['member_id']}", normal_style),
        ]
        for p in bill_lines:
            story.append(p)
        story.append(Spacer(1, 18))

        # Items table
        sub = context["subscription"]
        months = sub["months_subscribed"]
        months_label = "month" if months == 1 else "months"

        # Cell styles for table content
        cell_style = ParagraphStyle(
            name="CellStyle",
            parent=styles["Normal"],
            fontSize=10,
        )
        cell_small_style = ParagraphStyle(
            name="CellSmallStyle",
            parent=styles["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#6b7280"),
        )
        cell_center_style = ParagraphStyle(
            name="CellCenterStyle",
            parent=styles["Normal"],
            fontSize=10,
            alignment=TA_CENTER,
        )
        cell_right_style = ParagraphStyle(
            name="CellRightStyle",
            parent=styles["Normal"],
            fontSize=10,
            alignment=TA_RIGHT,
        )

        items_data = [
            ["Description", "Period", "Duration", "Amount"],
            [
                Paragraph(f"Membership Subscription<br/><font size=8 color='#6b7280'>Payment via {sub['payment_method']}</font>", cell_style),
                Paragraph(f"{sub['start_date']}<br/>to {sub['end_date']}", cell_style),
                Paragraph(f"<b>{months}</b><br/><font size=8 color='#6b7280'>{months_label}</font>", cell_center_style),
                Paragraph(f"GHS {sub['amount_paid']}", cell_right_style),
            ],
            [Paragraph("<b>TOTAL PAID</b>", cell_style), "", "", Paragraph(f"<b>GHS {sub['amount_paid']}</b>", cell_right_style)],
        ]
        items_table = Table(
            items_data,
            colWidths=[doc.width * 0.38, doc.width * 0.28, doc.width * 0.12, doc.width * 0.22],
        )
        items_table.setStyle(
            TableStyle([
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8.5),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (1, -1), "LEFT"),
                ("ALIGN", (2, 0), (2, -1), "CENTER"),
                ("ALIGN", (3, 0), (3, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 1), (-1, 1), 10),
                ("FONTSIZE", (0, 2), (-1, 2), 11),
                ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
                ("LINEABOVE", (0, 2), (-1, 2), 2, colors.HexColor("#e5e7eb")),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
                ("GRID", (0, 0), (-1, 1), 1, colors.HexColor("#e5e7eb")),
            ])
        )
        story.append(items_table)
        story.append(Spacer(1, 18))

        # Payment info
        pay_data = [
            ["Payment Reference:", sub["payment_reference"]],
            ["Payment Status:", str(sub["status"]).upper()],
        ]
        pay_table = Table(pay_data, colWidths=[doc.width * 0.45, doc.width * 0.52])
        pay_table.setStyle(
            TableStyle([
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
                ("LINEABOVE", (0, 0), (-1, 0), 1, colors.HexColor("#e5e7eb")),
                ("LINEBELOW", (0, -1), (-1, -1), 1, colors.HexColor("#e5e7eb")),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ])
        )
        story.append(pay_table)
        story.append(Spacer(1, 24))

        # Footer
        year = invoice_date.split()[-1] if invoice_date else ""
        footer_style = ParagraphStyle(
            name="Footer",
            parent=styles["Normal"],
            fontSize=8.5,
            textColor=colors.HexColor("#6b7280"),
            alignment=TA_CENTER,
            spaceAfter=3,
        )
        story.append(Paragraph("This is an official invoice for membership subscription paid to RATEL Movement.", footer_style))
        story.append(Paragraph("Thank you for your continued support and membership.", footer_style))
        story.append(Paragraph(f"© {year} RATEL Movement. All rights reserved.", ParagraphStyle(name="FooterCopy", parent=footer_style, fontSize=8, textColor=colors.HexColor("#9ca3af"))))

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        filename = f"invoice-{invoice_number}.pdf".replace(" ", "-")
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        print(f"[Member Invoice PDF] Error: {e}")
        import traceback
        traceback.print_exc()
        return HttpResponse("Failed to generate invoice. Please try again or contact support.", status=500, content_type="text/plain; charset=utf-8")


def member_renew(request):
    """
    Member subscription renewal page with Paystack payment.
    All payments are processed in GHS (Ghanaian Cedis).
    """
    member_ctx = _get_member_context(request)
    if not member_ctx:
        return redirect(f"/auth/?next=/member/renew/")

    membership_fee = 500
    currency = "NGN"
    current_subscription = None
    subscription_end = None
    subscription_end_iso = None
    renewal_status = "never_subscribed"

    # Exchange rates to GHS (approximate rates - update as needed)
    # These rates convert FROM the source currency TO GHS
    EXCHANGE_RATES_TO_GHS = {
        "GHS": 1.0,        # 1 GHS = 1 GHS
        "NGN": 0.0076,     # 1 NGN ≈ 0.0076 GHS (1 GHS ≈ 131 NGN)
        "USD": 15.5,       # 1 USD ≈ 15.5 GHS
        "GBP": 19.5,       # 1 GBP ≈ 19.5 GHS
        "EUR": 16.8,       # 1 EUR ≈ 16.8 GHS
    }

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        # Fetch membership settings
        settings_resp = requests.get(
            f"{base_url}/rest/v1/membership_settings?select=*&limit=1",
            headers=headers,
            timeout=10
        )
        if settings_resp.status_code == 200:
            settings_data = settings_resp.json()
            if settings_data:
                membership_fee = settings_data[0].get("fee_amount", 500)
                currency = settings_data[0].get("currency", "NGN")

        # Fetch current subscription for this member
        member_id = member_ctx.get("member_id")
        sub_resp = requests.get(
            f"{base_url}/rest/v1/member_subscriptions?member_id=eq.{member_id}&order=end_date.desc&limit=1",
            headers=headers,
            timeout=10
        )
        if sub_resp.status_code == 200:
            sub_data = sub_resp.json()
            if sub_data:
                current_subscription = sub_data[0]
                end_date_str = current_subscription.get("end_date")
                if end_date_str:
                    try:
                        end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                        subscription_end = end_date.strftime("%B %d, %Y")
                        subscription_end_iso = end_date.isoformat()
                        now = datetime.now()
                        if end_date.replace(tzinfo=None) < now:
                            renewal_status = "expired"
                        elif end_date.replace(tzinfo=None) < now + timedelta(days=7):
                            renewal_status = "expiring_soon"
                        else:
                            renewal_status = "active"
                    except:
                        pass

    except Exception as e:
        print(f"[Member Renew] Error: {e}")

    # Convert membership fee to GHS for payment
    exchange_rate = EXCHANGE_RATES_TO_GHS.get(currency, 1.0)
    membership_fee_ghs = round(membership_fee * exchange_rate, 2)

    # If already in GHS, use as-is
    if currency == "GHS":
        membership_fee_ghs = membership_fee

    # Paystack public key (Supabase overrides env when set)
    paystack_public_key, _ = _get_paystack_keys()

    context = {
        **member_ctx,
        "active_page": "renew",
        "membership_fee": membership_fee,
        "membership_fee_ghs": membership_fee_ghs,
        "currency": currency,
        "exchange_rate": exchange_rate,
        "subscription_end": subscription_end,
        "subscription_end_iso": subscription_end_iso,
        "renewal_status": renewal_status,
        "current_subscription": current_subscription,
        "paystack_public_key": paystack_public_key,
    }

    return render(request, "member/renew.html", context)


@require_POST
def member_renew_verify(request):
    """
    Verify Paystack payment and create/extend subscription.
    """
    import json
    from datetime import datetime, timedelta

    reference = request.POST.get("reference")
    months = int(request.POST.get("months", 1))

    if not reference:
        return JsonResponse({"success": False, "message": "No payment reference provided."})

    # Verify payment with Paystack (Supabase overrides env when set)
    _, paystack_secret_key = _get_paystack_keys()

    try:
        verify_resp = requests.get(
            f"https://api.paystack.co/transaction/verify/{reference}",
            headers={
                "Authorization": f"Bearer {paystack_secret_key}",
                "Content-Type": "application/json",
            },
            timeout=30
        )
        verify_data = verify_resp.json()

        if not verify_data.get("status") or verify_data.get("data", {}).get("status") != "success":
            return JsonResponse({"success": False, "message": "Payment verification failed."})

        payment_data = verify_data.get("data", {})
        amount_paid = payment_data.get("amount", 0) / 100  # Paystack returns in kobo

        # Get member context
        member_ctx = _get_member_context(request)
        member_id = member_ctx.get("member_id")
        member_email = member_ctx.get("member_email")

        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        # Check for existing active subscription
        now = datetime.now()
        sub_resp = requests.get(
            f"{base_url}/rest/v1/member_subscriptions?member_id=eq.{member_id}&order=end_date.desc&limit=1",
            headers=headers,
            timeout=10
        )

        start_date = now
        if sub_resp.status_code == 200:
            sub_data = sub_resp.json()
            if sub_data:
                existing_end = sub_data[0].get("end_date")
                if existing_end:
                    try:
                        existing_end_date = datetime.fromisoformat(existing_end.replace("Z", "+00:00"))
                        if existing_end_date.replace(tzinfo=None) > now:
                            # Extend from current end date
                            start_date = existing_end_date.replace(tzinfo=None)
                    except:
                        pass

        # Calculate end date based on months
        end_date = start_date + timedelta(days=30 * months)

        # Create subscription record
        subscription_payload = {
            "member_id": member_id,
            "member_email": member_email,
            "amount_paid": amount_paid,
            "months_subscribed": months,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "status": "active",
            "payment_reference": reference,
            "payment_method": "paystack",
            "created_at": now.isoformat(),
        }

        create_resp = requests.post(
            f"{base_url}/rest/v1/member_subscriptions",
            headers=headers,
            json=subscription_payload,
            timeout=10
        )

        if create_resp.status_code in [200, 201]:
            end_date_fmt = end_date.strftime("%B %d, %Y")
            member_name = member_ctx.get("member_name", "Member")
            # Send thank-you email for renewal
            _send_renewal_thank_you(
                request,
                member_email,
                member_name,
                member_ctx.get("member_id", ""),
                end_date_fmt,
            )
            return JsonResponse({
                "success": True,
                "message": f"Subscription activated for {months} month(s)!",
                "end_date": end_date_fmt,
            })
        else:
            return JsonResponse({"success": False, "message": "Failed to create subscription record."})

    except Exception as e:
        print(f"[Renew Verify] Error: {e}")
        return JsonResponse({"success": False, "message": f"Error verifying payment: {str(e)}"})


def admin_fix_missing_subscriptions(request):
    """
    One-time fix: Create subscription records for members who paid but don't have subscriptions.
    Only for members created in the last 24 hours.
    Admin can fix all, regular members can only fix their own.
    """
    if not request.session.get("is_authenticated"):
        return JsonResponse({"success": False, "message": "Please log in"}, status=403)
    
    is_admin = request.session.get("is_admin", False)
    current_user_email = request.session.get("member_email")
    
    from datetime import datetime, timedelta
    
    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()
        
        # Get members created in last 24 hours
        twenty_four_hours_ago = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        
        if is_admin:
            # Admin can fix all members
            members_resp = requests.get(
                f"{base_url}/rest/v1/members?created_at=gte.{twenty_four_hours_ago}&status=eq.active&select=*",
                headers=headers,
                timeout=10
            )
        else:
            # Regular user can only fix their own
            members_resp = requests.get(
                f"{base_url}/rest/v1/members?email=eq.{current_user_email}&status=eq.active&select=*",
                headers=headers,
                timeout=10
            )
        
        members = members_resp.json()
        
        fixed_count = 0
        for member in members:
            member_id = member.get("member_id")
            email = member.get("email")
            created_at = member.get("created_at")
            
            # Check if subscription exists
            sub_resp = requests.get(
                f"{base_url}/rest/v1/member_subscriptions?member_id=eq.{member_id}",
                headers=headers,
                timeout=10
            )
            
            if sub_resp.status_code == 200 and not sub_resp.json():
                # No subscription found, create one
                created_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                end_date = created_date + timedelta(days=30)
                
                subscription_payload = {
                    "member_id": member_id,
                    "member_email": email,
                    "amount_paid": 500,
                    "months_subscribed": 1,
                    "start_date": created_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "status": "active",
                    "payment_reference": f"RETRO_FIX_{member_id}",
                    "payment_method": "paystack",
                    "created_at": created_date.isoformat(),
                }
                
                create_resp = requests.post(
                    f"{base_url}/rest/v1/member_subscriptions",
                    headers=headers,
                    json=subscription_payload,
                    timeout=10
                )
                
                if create_resp.status_code in [200, 201]:
                    fixed_count += 1
                    print(f"[Admin Fix] Created subscription for {member_id} ({email})")
        
        return JsonResponse({
            "success": True,
            "message": f"Fixed {fixed_count} member(s) without subscriptions"
        })
    
    except Exception as e:
        print(f"[Admin Fix] Error: {e}")
        return JsonResponse({"success": False, "message": str(e)}, status=500)


def send_renewal_reminders():
    """
    Cron job function to send renewal reminders to members expiring within 7 days.
    This should be called by a scheduled task (e.g., cron, celery beat).
    """
    from datetime import datetime, timedelta

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        # Get membership fee
        membership_fee = 500
        currency = "NGN"
        settings_resp = requests.get(
            f"{base_url}/rest/v1/membership_settings?select=*&limit=1",
            headers=headers,
            timeout=10
        )
        if settings_resp.status_code == 200:
            settings_data = settings_resp.json()
            if settings_data:
                membership_fee = settings_data[0].get("fee_amount", 500)
                currency = settings_data[0].get("currency", "NGN")

        # Get subscriptions expiring in 7 days
        now = datetime.now()
        seven_days_later = (now + timedelta(days=7)).isoformat()

        # Get subscriptions that expire within 7 days and haven't been notified recently
        subs_resp = requests.get(
            f"{base_url}/rest/v1/member_subscriptions?status=eq.active&end_date=lt.{seven_days_later}&select=*",
            headers=headers,
            timeout=10
        )

        if subs_resp.status_code == 200:
            subscriptions = subs_resp.json()

            for sub in subscriptions:
                member_email = sub.get("member_email")
                member_id = sub.get("member_id")
                end_date = sub.get("end_date", "")

                if not member_email:
                    continue

                # Send reminder email
                subject = "RATEL Movement - Membership Expiring Soon"
                message = f"""Dear Member,

Your RATEL Movement membership is expiring soon.

Member ID: {member_id}
Expiration Date: {end_date[:10] if end_date else 'Unknown'}
Renewal Fee: {currency} {membership_fee:,.2f}/month

To maintain uninterrupted access to member benefits, please renew your subscription before it expires.

Renew Now: [Your Member Dashboard URL]/member/renew/

Thank you for being part of the movement.

Neutrality is complicity.

RATEL Movement Team"""

                try:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [member_email],
                        fail_silently=True,
                    )
                except:
                    pass

        print(f"[Renewal Reminders] Sent reminders for {len(subscriptions) if 'subscriptions' in dir() else 0} members")

    except Exception as e:
        print(f"[Renewal Reminders] Error: {e}")


# =====================================================
# SHAREABLE MESSAGES MANAGEMENT
# =====================================================

def dashboard_messages(request):
    """Admin dashboard for managing shareable messages."""
    messages_list = []
    total_messages = 0
    total_shares = 0
    total_downloads = 0
    total_copies = 0
    category_counts = {}

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
            "Accept": "application/json",
        }

        # Fetch all messages (including inactive)
        resp = requests.get(
            f"{base_url}/rest/v1/shareable_messages?select=*&order=display_order.asc,created_at.desc",
            headers=headers,
            timeout=10
        )
        if resp.status_code == 200:
            messages_list = resp.json()
            total_messages = len(messages_list)

            # Calculate totals and category counts
            for msg in messages_list:
                total_shares += msg.get("share_count", 0)
                total_downloads += msg.get("download_count", 0)
                total_copies += msg.get("copy_count", 0)
                category = msg.get("category", "other")
                category_counts[category] = category_counts.get(category, 0) + 1

    except Exception as e:
        print(f"[Dashboard Messages] Error: {e}")

    return render(request, "dashboard/messages.html", {
        "active_page": "messages",
        "messages_list": messages_list,
        "total_messages": total_messages,
        "total_shares": total_shares,
        "total_downloads": total_downloads,
        "total_copies": total_copies,
        "category_counts": category_counts,
    })


def dashboard_messages_get(request):
    """Get a single message by ID for editing."""
    message_id = request.GET.get("id", "").strip()
    if not message_id:
        return JsonResponse({"success": False, "error": "No message ID provided"})

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
            "Accept": "application/json",
        }

        resp = requests.get(
            f"{base_url}/rest/v1/shareable_messages?id=eq.{message_id}&select=*",
            headers=headers,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return JsonResponse({"success": True, "message": data[0]})
            return JsonResponse({"success": False, "error": "Message not found"})
        return JsonResponse({"success": False, "error": "Failed to fetch message"})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@require_POST
def dashboard_messages_save(request):
    """Create or update a shareable message."""
    import json

    message_id = request.POST.get("message_id", "").strip()

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

        # Parse hashtags from JSON
        hashtags_str = request.POST.get("hashtags", "[]")
        try:
            hashtags = json.loads(hashtags_str)
        except:
            hashtags = []

        # Handle file upload to Supabase storage
        media_url = None
        media_filename = None
        media_file = request.FILES.get("media_file")

        if media_file:
            # Upload to Supabase storage bucket "messages"
            storage_url = f"{base_url}/storage/v1/object/messages/{media_file.name}"
            storage_headers = {
                "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
                "Content-Type": media_file.content_type,
            }

            upload_resp = requests.post(
                storage_url,
                headers=storage_headers,
                data=media_file.read(),
                timeout=60
            )

            if upload_resp.status_code in [200, 201]:
                media_url = f"{base_url}/storage/v1/object/public/messages/{media_file.name}"
                media_filename = media_file.name
            else:
                print(f"[Messages Upload] Failed: {upload_resp.status_code} - {upload_resp.text}")

        # Build payload
        payload = {
            "title": request.POST.get("title", "").strip(),
            "description": request.POST.get("description", "").strip() or None,
            "content_type": request.POST.get("content_type", "text"),
            "category": request.POST.get("category", "pre_written"),
            "text_content": request.POST.get("text_content", "").strip() or None,
            "hashtags": hashtags if hashtags else None,
            "campaign_slogan": request.POST.get("campaign_slogan", "").strip() or None,
            "call_to_action": request.POST.get("call_to_action", "").strip() or None,
            "whatsapp_text": request.POST.get("whatsapp_text", "").strip() or None,
            "twitter_text": request.POST.get("twitter_text", "").strip() or None,
            "telegram_text": request.POST.get("telegram_text", "").strip() or None,
            "display_order": int(request.POST.get("display_order", 0) or 0),
            "is_featured": request.POST.get("is_featured") == "on",
            "is_active": request.POST.get("is_active") == "on",
        }

        # Only update media URL if new file was uploaded
        if media_url:
            payload["media_url"] = media_url
            payload["media_filename"] = media_filename

        if message_id:
            # Update existing
            resp = requests.patch(
                f"{base_url}/rest/v1/shareable_messages?id=eq.{message_id}",
                headers=headers,
                json=payload,
                timeout=10
            )
        else:
            # Create new
            resp = requests.post(
                f"{base_url}/rest/v1/shareable_messages",
                headers=headers,
                json=payload,
                timeout=10
            )

        if resp.status_code in [200, 201]:
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False, "error": resp.text})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@require_POST
def dashboard_messages_delete(request):
    """Delete a shareable message."""
    import json

    try:
        data = json.loads(request.body)
        message_id = data.get("id", "").strip()
    except:
        message_id = request.POST.get("id", "").strip()

    if not message_id:
        return JsonResponse({"success": False, "error": "No message ID provided"})

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
        }

        resp = requests.delete(
            f"{base_url}/rest/v1/shareable_messages?id=eq.{message_id}",
            headers=headers,
            timeout=10
        )

        if resp.status_code in [200, 204]:
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False, "error": resp.text})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


# =====================================================
# YOUTUBE / IG LINKS (Landing Page)
# =====================================================

def dashboard_youtube_ig(request):
    """Admin dashboard for YouTube/IG links shown on landing page."""
    youtube_list = []
    instagram_list = []
    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
            "Accept": "application/json",
        }
        # Get all links and filter by type
        resp_all = requests.get(
            f"{base_url}/rest/v1/youtube_ig_links?select=*&order=display_order.asc,created_at.desc",
            headers=headers,
            timeout=10
        )
        all_links = resp_all.json() if resp_all.status_code == 200 else []

        # Normalize thumbnail URLs using robust normalizer
        for link in all_links:
            if link.get("thumbnail_url"):
                original_url = link["thumbnail_url"]
                link["thumbnail_url"] = _normalize_messages_url(original_url)
                if link["thumbnail_url"] != original_url:
                    print(f"[Dashboard YouTube/IG] Normalized thumbnail: {original_url} -> {link['thumbnail_url']}")

        # Filter YouTube links (those with youtube_url and no ig_url)
        youtube_list = [link for link in all_links if link.get("youtube_url") and not link.get("ig_url")]

        # Filter Instagram links (those with ig_url and no youtube_url)
        instagram_list = [link for link in all_links if link.get("ig_url") and not link.get("youtube_url")]
    except Exception as e:
        print(f"[Dashboard Youtube/IG] Error: {e}")
    return render(request, "dashboard/youtube_ig.html", {
        "active_page": "youtube_ig",
        "youtube_list": youtube_list,
        "instagram_list": instagram_list,
    })


def dashboard_youtube_ig_get(request):
    """Get a single YouTube/IG link by ID."""
    link_id = request.GET.get("id", "").strip()
    if not link_id:
        return JsonResponse({"success": False, "error": "No ID provided"})
    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
            "Accept": "application/json",
        }
        resp = requests.get(
            f"{base_url}/rest/v1/youtube_ig_links?id=eq.{link_id}&select=*",
            headers=headers,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return JsonResponse({"success": True, "link": data[0]})
        return JsonResponse({"success": False, "error": "Not found"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@require_POST
def dashboard_youtube_ig_save(request):
    """Create or update a YouTube/IG link. Optional thumbnail upload to messages bucket."""
    import uuid
    link_id = request.POST.get("link_id", "").strip()
    title = request.POST.get("title", "").strip()
    subtitle = request.POST.get("subtitle", "").strip()
    youtube_url = request.POST.get("youtube_url", "").strip()
    ig_url = request.POST.get("ig_url", "").strip()
    display_order = int(request.POST.get("display_order", 0) or 0)
    is_active = request.POST.get("is_active") == "on"
    link_type = request.POST.get("link_type", "").strip()  # 'youtube' or 'instagram'

    if not title:
        return JsonResponse({"success": False, "error": "Title is required"})
    
    # Ensure only one URL type based on link_type
    if link_type == "youtube":
        ig_url = ""  # Clear IG URL if this is YouTube
        if not youtube_url:
            return JsonResponse({"success": False, "error": "YouTube URL is required"})
    elif link_type == "instagram":
        youtube_url = ""  # Clear YouTube URL if this is Instagram
        if not ig_url:
            return JsonResponse({"success": False, "error": "Instagram URL is required"})

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

        # Handle thumbnail upload
        thumbnail_url = None
        thumb_file = request.FILES.get("thumbnail")
        if thumb_file:
            # Use the Supabase client helper for more reliable uploads
            thumbnail_url = _upload_to_supabase_storage(thumb_file, bucket="messages", folder="")
            if not thumbnail_url:
                return JsonResponse({"success": False, "error": "Thumbnail upload failed. Please try again."})

        payload = {
            "title": title,
            "subtitle": subtitle or None,
            "youtube_url": youtube_url or None,
            "ig_url": ig_url or None,
            "display_order": display_order,
            "is_active": is_active,
        }
        # Only include thumbnail_url in payload if a new file was uploaded
        # When editing without new upload, omitting it preserves the existing thumbnail
        if thumbnail_url:
            payload["thumbnail_url"] = thumbnail_url

        if link_id:
            resp = requests.patch(
                f"{base_url}/rest/v1/youtube_ig_links?id=eq.{link_id}",
                headers=headers,
                json=payload,
                timeout=10
            )
        else:
            resp = requests.post(
                f"{base_url}/rest/v1/youtube_ig_links",
                headers=headers,
                json=payload,
                timeout=10
            )
        if resp.status_code in [200, 201]:
            return JsonResponse({"success": True})
        return JsonResponse({"success": False, "error": resp.text})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@require_POST
def dashboard_youtube_ig_delete(request):
    """Delete a YouTube/IG link."""
    import json
    try:
        data = json.loads(request.body)
        link_id = data.get("id", "").strip()
    except Exception:
        link_id = request.POST.get("id", "").strip()
    if not link_id:
        return JsonResponse({"success": False, "error": "No ID provided"})
    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
        }
        resp = requests.delete(
            f"{base_url}/rest/v1/youtube_ig_links?id=eq.{link_id}",
            headers=headers,
            timeout=10
        )
        if resp.status_code in [200, 204]:
            return JsonResponse({"success": True})
        return JsonResponse({"success": False, "error": resp.text})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@require_POST
def messages_track(request):
    """Track message share/download/copy actions."""
    import json

    try:
        data = json.loads(request.body)
        message_id = data.get("message_id", "").strip()
        action = data.get("action", "").strip()
    except:
        return JsonResponse({"success": False, "error": "Invalid data"})

    if not message_id or not action:
        return JsonResponse({"success": False, "error": "Missing parameters"})

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
            "Content-Type": "application/json",
        }

        # Determine which counter to increment
        if action == "copy":
            field = "copy_count"
        elif action == "download":
            field = "download_count"
        elif action.startswith("share"):
            field = "share_count"
        else:
            return JsonResponse({"success": False, "error": "Unknown action"})

        # Get current count
        resp = requests.get(
            f"{base_url}/rest/v1/shareable_messages?id=eq.{message_id}&select={field}",
            headers=headers,
            timeout=10
        )

        if resp.status_code == 200:
            data = resp.json()
            if data:
                current_count = data[0].get(field, 0)
                # Increment count
                update_resp = requests.patch(
                    f"{base_url}/rest/v1/shareable_messages?id=eq.{message_id}",
                    headers=headers,
                    json={field: current_count + 1},
                    timeout=10
                )

                # Also log to analytics table
                analytics_payload = {
                    "message_id": message_id,
                    "share_platform": action,
                    "ip_address": request.META.get("REMOTE_ADDR"),
                    "user_agent": request.META.get("HTTP_USER_AGENT", "")[:500],
                }
                requests.post(
                    f"{base_url}/rest/v1/message_share_analytics",
                    headers=headers,
                    json=analytics_payload,
                    timeout=5
                )

                return JsonResponse({"success": True})

        return JsonResponse({"success": False, "error": "Failed to update"})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


# =====================================================
# CASES MANAGEMENT
# =====================================================

def cases_page(request):
    """
    Public cases page - displays all cases with search and filter.
    """
    cases = []
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('q', '').strip()

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
            "Accept": "application/json",
        }

        # Build query - only show active, solved, and completed cases to public
        url = f"{base_url}/rest/v1/cases?select=*&status=in.(active,solved,completed)&order=date_reported.desc,created_at.desc"

        # Add status filter if not 'all'
        if status_filter and status_filter != 'all' and status_filter in ['active', 'solved', 'completed']:
            url = f"{base_url}/rest/v1/cases?select=*&status=eq.{status_filter}&order=date_reported.desc,created_at.desc"

        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            cases = resp.json()
            # Normalize date strings so Django |date filter works in template
            for case in cases:
                for key in ("date_reported", "created_at", "updated_at"):
                    val = case.get(key)
                    if val and isinstance(val, str) and val.strip():
                        try:
                            if "T" in val:
                                case[key] = datetime.fromisoformat(val.replace("Z", "+00:00"))
                            else:
                                case[key] = datetime.strptime(val, "%Y-%m-%d").date()
                        except (ValueError, TypeError):
                            case[key] = None

        # Apply search filter in Python (for now) if search query exists
        if search_query:
            search_lower = search_query.lower()
            cases = [c for c in cases if
                search_lower in c.get('title', '').lower() or
                search_lower in (c.get('description') or '').lower() or
                search_lower in c.get('case_number', '').lower() or
                search_lower in (c.get('short_description') or '').lower()]

    except Exception as e:
        print(f"[Cases] Error fetching: {e}")

    return render(request, "cases.html", {
        "cases": cases,
        "status_filter": status_filter,
        "search_query": search_query,
    })


def dashboard_cases(request):
    """
    Admin dashboard page to manage cases.
    """
    cases = []
    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        resp = requests.get(
            f"{base_url}/rest/v1/cases?order=created_at.desc",
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()
        cases = resp.json()
        # Normalize date strings from Supabase so Django's |date filter works in template
        for case in cases:
            for key in ("date_reported", "created_at", "updated_at"):
                val = case.get(key)
                if val and isinstance(val, str) and val.strip():
                    try:
                        if "T" in val:
                            case[key] = datetime.fromisoformat(val.replace("Z", "+00:00"))
                        else:
                            case[key] = datetime.strptime(val, "%Y-%m-%d").date()
                    except (ValueError, TypeError) as e:
                        print(f"[Dashboard Cases] Date parse error for {key}={val}: {e}")
                        case[key] = None
    except Exception as e:
        print(f"[Dashboard Cases] Error fetching: {e}")
        messages.error(request, "Failed to load cases.")

    return render(request, "dashboard/cases.html", {"cases": cases, "active_page": "cases"})


@require_POST
def dashboard_cases_save(request):
    """
    Create or update a case. Handles both JSON and form data.
    """
    import json
    from datetime import datetime

    # Handle both JSON and form data
    try:
        if request.content_type and 'application/json' in request.content_type:
            data = json.loads(request.body)
        else:
            # Form data
            data = {
                "id": request.POST.get("case_id", "").strip() or None,
                "case_number": request.POST.get("case_number", "").strip(),
                "title": request.POST.get("title", "").strip(),
                "description": request.POST.get("description", "").strip(),
                "short_description": request.POST.get("short_description", "").strip(),
                "status": request.POST.get("status", "active"),
                "date_reported": request.POST.get("date_reported") or None,
                "category": request.POST.get("category", "").strip(),
                "priority": request.POST.get("priority", "").strip(),
                "tags": request.POST.get("tags", "").strip(),
                "assigned_to": request.POST.get("assigned_to", "").strip(),
                "notes": request.POST.get("notes", "").strip(),
                "file_url": request.POST.get("file_url", "").strip(),
            }
    except:
        data = {}

    case_id = data.get("id")
    case_number = data.get("case_number", "").strip()
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    short_description = data.get("short_description", "").strip()
    status = data.get("status", "active")
    date_reported = data.get("date_reported") or None
    category = data.get("category", "").strip() or None
    priority = data.get("priority", "").strip() or None
    tags_str = data.get("tags", "").strip()
    assigned_to = data.get("assigned_to", "").strip() or None
    notes = data.get("notes", "").strip() or None

    # Handle file upload if provided
    file_url = None
    file_name = None
    if request.FILES.get("case_file"):
        case_file = request.FILES.get("case_file")
        file_url = _upload_to_supabase_storage(case_file, "media-vault", "cases")
        if file_url:
            file_name = case_file.name
    elif data.get("file_url"):
        file_url = data.get("file_url", "").strip() or None

    if not title:
        return JsonResponse({"success": False, "error": "Title is required"})

    # Auto-generate case number if not provided
    if not case_number:
        case_number = f"CASE-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        # Parse tags
        tags_list = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []

        payload = {
            "case_number": case_number,
            "title": title,
            "status": status,
        }
        
        # Add optional fields
        if description:
            payload["description"] = description
        if short_description:
            payload["short_description"] = short_description
        if date_reported:
            payload["date_reported"] = date_reported
        if category:
            payload["category"] = category
        if priority:
            payload["priority"] = priority
        if tags_list:
            payload["tags"] = tags_list
        if assigned_to:
            payload["assigned_to"] = assigned_to
        if notes:
            payload["notes"] = notes
        if file_url:
            payload["file_url"] = file_url
        if file_name:
            payload["file_name"] = file_name

        if case_id:
            # Update existing
            resp = requests.patch(
                f"{base_url}/rest/v1/cases?id=eq.{case_id}",
                headers=headers,
                json=payload,
                timeout=10
            )
        else:
            # Create new
            resp = requests.post(
                f"{base_url}/rest/v1/cases",
                headers=headers,
                json=payload,
                timeout=10
            )

        if resp.status_code not in [200, 201, 204]:
            error_msg = resp.text
            print(f"[Cases Save] Error ({resp.status_code}): {error_msg}")
            return JsonResponse({"success": False, "error": error_msg[:200]})
        
        return JsonResponse({"success": True})
    except Exception as e:
        print(f"[Cases Save] Exception: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"success": False, "error": str(e)})


@require_POST
def dashboard_cases_delete(request):
    """
    Delete a case.
    """
    import json
    data = json.loads(request.body)
    case_id = data.get("id")

    if not case_id:
        return JsonResponse({"success": False, "error": "Case ID required"})

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        resp = requests.delete(
            f"{base_url}/rest/v1/cases?id=eq.{case_id}",
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


def dashboard_cases_get(request):
    """
    Get a single case by ID.
    """
    case_id = request.GET.get("id")

    if not case_id:
        return JsonResponse({"success": False, "error": "Case ID required"})

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        resp = requests.get(
            f"{base_url}/rest/v1/cases?id=eq.{case_id}&select=*",
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()

        if data:
            return JsonResponse({"success": True, "case": data[0]})
        return JsonResponse({"success": False, "error": "Case not found"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@require_POST
def dashboard_cases_status(request):
    """
    Toggle case status (active/solved/completed).
    """
    import json
    data = json.loads(request.body)
    case_id = data.get("id")
    new_status = data.get("status")

    if not case_id or not new_status:
        return JsonResponse({"success": False, "error": "Case ID and status required"})

    if new_status not in ["active", "solved", "completed", "pending", "closed"]:
        return JsonResponse({"success": False, "error": "Invalid status"})

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        resp = requests.patch(
            f"{base_url}/rest/v1/cases?id=eq.{case_id}",
            headers=headers,
            json={"status": new_status},
            timeout=10
        )
        resp.raise_for_status()

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


# =====================================================
# BLOG MANAGEMENT (Dashboard)
# =====================================================

def dashboard_blogs(request):
    """Dashboard page for managing blogs."""
    blogs = []
    
    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()
        
        url = f"{base_url}/rest/v1/blogs?select=*&order=created_at.desc"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            blogs = resp.json()
            # Parse dates and normalize image URLs
            for b in blogs:
                for key in ("published_at", "created_at", "updated_at"):
                    val = b.get(key)
                    if val and isinstance(val, str) and val.strip():
                        try:
                            if "T" in val:
                                b[key] = datetime.fromisoformat(val.replace("Z", "+00:00"))
                            else:
                                b[key] = datetime.strptime(val, "%Y-%m-%d").date()
                        except (ValueError, TypeError):
                            b[key] = None
                
                # Normalize featured_image_url - ensure it's a full public URL
                if b.get("featured_image_url"):
                    b["featured_image_url"] = _normalize_blog_image_url(b["featured_image_url"], base_url)
    except Exception as e:
        print(f"[Dashboard Blogs] Error: {e}")
    
    return render(request, "dashboard/blogs.html", {
        "active_page": "blogs",
        "blogs": blogs,
    })


@require_POST
def dashboard_blogs_save(request):
    """Save or update a blog post."""
    import json
    import re
    
    try:
        # Get form data
        blog_id = request.POST.get("blog_id", "").strip()
        title = request.POST.get("title", "").strip()
        excerpt = request.POST.get("excerpt", "").strip()
        content = request.POST.get("content", "").strip()
        category = request.POST.get("category", "general").strip()
        tags_str = request.POST.get("tags", "").strip()
        is_published = request.POST.get("is_published") == "on"
        is_featured = request.POST.get("is_featured") == "on"
        author_name = request.POST.get("author_name", "Ratel Movement").strip()
        meta_description = request.POST.get("meta_description", "").strip()
        image_file = request.FILES.get("featured_image")
        existing_image_url = request.POST.get("existing_image_url", "").strip()
        
        if not title or not content:
            return JsonResponse({"success": False, "error": "Title and content are required."}, status=400)
        
        # Generate slug from title
        slug = re.sub(r'[^a-z0-9]+', '-', title.lower())
        slug = slug.strip('-')
        if not slug:
            slug = f"blog-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Ensure unique slug
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()
        if blog_id:
            # Check if slug exists for other blogs
            check_url = f"{base_url}/rest/v1/blogs?slug=eq.{slug}&id=neq.{blog_id}&select=id&limit=1"
        else:
            check_url = f"{base_url}/rest/v1/blogs?slug=eq.{slug}&select=id&limit=1"
        check_resp = requests.get(check_url, headers=headers, timeout=10)
        if check_resp.status_code == 200 and check_resp.json():
            slug = f"{slug}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Handle image upload
        featured_image_url = existing_image_url
        if image_file:
            print(f"[Blog Save] Uploading new image: {image_file.name}")
            uploaded_url = _upload_to_supabase_storage(image_file, "blogs", "featured")
            if uploaded_url:
                featured_image_url = uploaded_url
                print(f"[Blog Save] Image uploaded successfully: {featured_image_url}")
            else:
                print(f"[Blog Save] Image upload FAILED - keeping existing URL: {existing_image_url}")
        print(f"[Blog Save] Final featured_image_url to save: {featured_image_url}")
        
        # Parse tags
        tags = []
        if tags_str:
            tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]
        
        # Calculate reading time (approx 200 words per minute)
        word_count = len(re.findall(r'\w+', strip_tags(content)))
        reading_time = max(1, round(word_count / 200))
        
        # Prepare payload
        payload = {
            "title": title,
            "slug": slug,
            "excerpt": excerpt or None,
            "content": content,
            "category": category,
            "tags": tags if tags else None,
            "is_published": is_published,
            "is_featured": is_featured,
            "author_name": author_name,
            "meta_description": meta_description or None,
            "featured_image_url": featured_image_url or None,
            "reading_time": reading_time,
            "published_at": datetime.now().isoformat() if is_published else None,
        }
        
        headers["Content-Type"] = "application/json"
        headers["Prefer"] = "return=representation"
        
        if blog_id:
            # Update existing
            url = f"{base_url}/rest/v1/blogs?id=eq.{blog_id}"
            resp = requests.patch(url, headers=headers, json=payload, timeout=10)
            if resp.status_code in [200, 201, 204]:
                return JsonResponse({"success": True, "message": "Blog updated successfully!", "slug": slug})
            else:
                return JsonResponse({"success": False, "error": f"Failed to update: {resp.text}"}, status=400)
        else:
            # Create new
            url = f"{base_url}/rest/v1/blogs"
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            if resp.status_code in [200, 201]:
                return JsonResponse({"success": True, "message": "Blog created successfully!", "slug": slug})
            else:
                return JsonResponse({"success": False, "error": f"Failed to create: {resp.text}"}, status=400)
    except Exception as e:
        print(f"[Dashboard Blogs Save] Exception: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def dashboard_blogs_get(request):
    """Get a single blog post by ID."""
    blog_id = request.GET.get("id", "")
    
    if not blog_id:
        return JsonResponse({"success": False, "error": "ID is required."}, status=400)
    
    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()
        
        url = f"{base_url}/rest/v1/blogs?id=eq.{blog_id}&select=*&limit=1"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            blogs = resp.json()
            if blogs:
                return JsonResponse({"success": True, "data": blogs[0]})
            else:
                return JsonResponse({"success": False, "error": "Blog not found."}, status=404)
        else:
            return JsonResponse({"success": False, "error": resp.text}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_POST
def dashboard_blogs_delete(request):
    """Delete a blog post."""
    import json
    try:
        data = json.loads(request.body)
        blog_id = data.get("id")
    except Exception:
        blog_id = request.POST.get("id")
    
    if not blog_id:
        return JsonResponse({"success": False, "error": "ID is required."}, status=400)
    
    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()
        
        url = f"{base_url}/rest/v1/blogs?id=eq.{blog_id}"
        resp = requests.delete(url, headers=headers, timeout=10)
        if resp.status_code in [200, 204]:
            return JsonResponse({"success": True, "message": "Blog deleted successfully!"})
        else:
            return JsonResponse({"success": False, "error": resp.text}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

