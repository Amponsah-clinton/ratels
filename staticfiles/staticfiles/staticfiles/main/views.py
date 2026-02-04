from django.shortcuts import render, redirect
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.db import transaction
from django.contrib.auth.forms import PasswordResetForm
from django.contrib import messages

import os
import requests
from django.utils.crypto import get_random_string

from .supabase_client import get_supabase


def index(request):
    """Landing page with manifesto from Supabase."""
    manifesto = None
    manifesto_lines = []

    try:
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY}",
            "Accept": "application/json",
        }

        # Fetch manifesto content
        url = f"{base_url}/rest/v1/site_content?content_key=eq.manifesto&is_active=eq.true&select=*"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                manifesto = data[0]
                # Split content into lines for display
                if manifesto.get("content"):
                    manifesto_lines = [
                        line.strip() for line in manifesto["content"].split("\n")
                        if line.strip()
                    ]
    except Exception as e:
        print(f"[Index] Error fetching manifesto: {e}")

    return render(request, "index.html", {
        "manifesto": manifesto,
        "manifesto_lines": manifesto_lines,
    })


def about(request):
    return render(request, "about.html")


def about_ratel(request):
    return render(request, "about_ratel.html")


def mission_vision(request):
    return render(request, "mission_vision.html")


def ideology(request):
    return render(request, "ideology.html")


def faqs(request):
    return render(request, "faqs.html")


def media_vault(request):
    return render(request, "media_vault.html")


def media_videos(request):
    """Public videos page - fetch videos from Supabase."""
    videos = []
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
            f"{base_url}/rest/v1/media_videos",
            headers=headers,
            params=params,
            timeout=10
        )

        if resp.status_code == 200:
            videos = resp.json()
            # Normalize file URLs
            storage_base = f"{base_url}/storage/v1/object/public/media/"
            for video in videos:
                if video.get("file_url") and not str(video["file_url"]).startswith("http"):
                    video["file_url"] = storage_base + str(video["file_url"]).lstrip("/")
                if video.get("thumbnail_url") and not str(video["thumbnail_url"]).startswith("http"):
                    video["thumbnail_url"] = storage_base + str(video["thumbnail_url"]).lstrip("/")

        # Get distinct categories
        categories = sorted({v.get("category") for v in videos if v.get("category")})

    except Exception as e:
        print(f"[Media Videos] Error fetching data: {e}")

    return render(request, "media_videos.html", {
        "videos": videos,
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
    return render(request, "resources.html")


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
    return render(request, "blog.html")


def features(request):
    return render(request, "features.html")


def contact(request):
    return render(request, "contact.html")


def auth_page(request):
    context = {
        "auth_bg_image": None,
        "user_registration_enabled": True,
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


def _send_welcome_email(email: str, full_name: str, member_id: str):
    """
    Send a rich welcome email including member ID and resources links.
    """
    subject = "Welcome to the RATEL Movement"
    context = {
        "full_name": full_name,
        "member_id": member_id,
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


@require_POST
def auth_signup(request):
    """
    AJAX endpoint: /auth/signup/
    Creates a Django user + Supabase member record with generated member_id,
    then returns JSON.
    """
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

    errors: list[str] = []

    if not full_name:
        errors.append("Full name is required.")
    if not email:
        errors.append("Email is required.")
    if not phone_number:
        errors.append("Phone number is required.")
    if not password:
        errors.append("Password is required.")

    if based_in_nigeria:
        if not state:
            errors.append("State is required for members based in Nigeria.")
    else:
        if not country:
            errors.append("Country of residence is required for foreign members.")

    if errors:
        return JsonResponse({"success": False, "errors": errors}, status=400)

    from django.contrib.auth.hashers import make_password

    password_hash = make_password(password)

    region_key = _get_region_key(based_in_nigeria, state, country)
    member_id = _generate_member_id(region_key)

    # Optional: upload profile image to Supabase "profiles" bucket
    profile_image_url = None
    if profile_image_file:
        profile_image_url = _upload_profile_image_to_supabase(member_id, profile_image_file)

    try:
        with transaction.atomic():
            # Create or update Django user for authentication
            user, created = User.objects.get_or_create(
                username=email,
                defaults={"email": email, "first_name": full_name},
            )
            user.email = email
            user.first_name = full_name
            user.set_password(password)
            user.save()

            # Save to Supabase
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

        # Send welcome email (non‑blocking for user experience)
        _send_welcome_email(email, full_name, member_id)

        return JsonResponse(
            {
                "success": True,
                "message": "Registration successful! Welcome to the RATEL Movement.",
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
    Authenticates against Django's auth system.
    """
    email = request.POST.get("email", "").strip().lower()
    password = request.POST.get("password", "")

    if not email or not password:
        return JsonResponse(
            {"success": False, "errors": ["Email and password are required."]},
            status=400,
        )

    user = authenticate(request, username=email, password=password)
    if user is None:
        return JsonResponse(
            {"success": False, "errors": ["Invalid email or password."]},
            status=400,
        )

    login(request, user)

    welcome_message = f"Welcome back, {user.first_name or 'member'}!"

    redirect_url = request.POST.get("next") or "/dashboard/"

    return JsonResponse(
        {
            "success": True,
            "message": "Login successful.",
            "welcome_message": welcome_message,
            "redirect_url": redirect_url,
        }
    )


@require_POST
def auth_forgot_password(request):
    """
    AJAX endpoint: /auth/forgot-password/
    Uses Django's PasswordResetForm to send a reset link.
    """
    email = request.POST.get("email", "").strip().lower()
    if not email:
        return JsonResponse(
            {"success": False, "errors": ["Email address is required."]},
            status=400,
        )

    form = PasswordResetForm({"email": email})
    if form.is_valid():
        form.save(
            request=request,
            use_https=request.is_secure(),
            email_template_name="emails/password_reset_email.txt",
            subject_template_name="emails/password_reset_subject.txt",
            from_email=settings.DEFAULT_FROM_EMAIL,
        )
        return JsonResponse(
            {
                "success": True,
                "message": "If an account exists with that email, a password reset link has been sent.",
            }
        )

    return JsonResponse(
        {
            "success": False,
            "errors": ["If an account exists with that email, a password reset link has been sent."],
        }
    )


# --- Dashboard Views ---


def dashboard_home(request):
    return render(request, "dashboard/dashboard.html", {"active_page": "dashboard"})


def dashboard_contacts(request):
    """
    Membership view: show all registered members from Supabase.
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
        # First try with extended fields (membership_type, status)
        params_full = {
            "select": "member_id,full_name,email,phone_number,based_in_nigeria,state,lga,country,city,engagement_preferences,created_at,membership_type,status,profile_image_url",
            "order": "created_at.desc",
        }
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

    # Keep Django user in sync for suspend/unsuspend
    if email and action == "suspend":
        try:
            user = User.objects.filter(username=email).first()
            if user:
                user.is_active = payload.get("status") != "suspended"
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

    return redirect("dashboard_membership")


def dashboard_companies(request):
    return render(request, "dashboard/companies.html", {"active_page": "companies"})


def dashboard_deals(request):
    return render(request, "dashboard/deals.html", {"active_page": "deals"})


def dashboard_tasks(request):
    return render(request, "dashboard/tasks.html", {"active_page": "tasks"})


def dashboard_about(request):
    """Dashboard page for managing About/Manifesto content."""
    base_url = settings.SUPABASE_URL.rstrip("/")
    headers = _get_supabase_headers()

    manifesto = None
    faqs = []

    try:
        # Fetch manifesto content
        url = f"{base_url}/rest/v1/site_content?content_key=eq.manifesto&select=*"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                manifesto = data[0]

        # Fetch FAQs
        faq_url = f"{base_url}/rest/v1/faqs?select=*&order=display_order.asc"
        faq_resp = requests.get(faq_url, headers=headers, timeout=10)
        if faq_resp.status_code == 200:
            faqs = faq_resp.json()
    except Exception as e:
        print(f"[Dashboard About] Error fetching data: {e}")

    return render(request, "dashboard/about.html", {
        "active_page": "about",
        "manifesto": manifesto,
        "faqs": faqs,
    })


@require_POST
def dashboard_about_save(request):
    """Save manifesto content to Supabase with optional image upload."""
    title = request.POST.get("title", "").strip()
    content = request.POST.get("content", "").strip()
    subtitle = request.POST.get("subtitle", "").strip()
    manifesto_id = request.POST.get("manifesto_id", "").strip()
    image_file = request.FILES.get("image")
    existing_image_url = request.POST.get("existing_image_url", "").strip()

    if not content:
        messages.error(request, "Manifesto content is required.")
        return redirect("dashboard_about")

    base_url = settings.SUPABASE_URL.rstrip("/")
    headers = _get_supabase_headers()
    headers["Content-Type"] = "application/json"
    headers["Prefer"] = "return=representation"

    # Handle image upload
    image_url = existing_image_url
    if image_file:
        uploaded_url = _upload_to_supabase_storage(image_file, "site-content", "manifesto")
        if uploaded_url:
            image_url = uploaded_url
        else:
            messages.warning(request, "Image upload failed, but manifesto will be saved.")

    payload = {
        "content_key": "manifesto",
        "title": title or "Our Manifesto",
        "content": content,
        "subtitle": subtitle or "The Ratel Movement",
        "image_url": image_url or None,
        "is_active": True,
    }

    try:
        if manifesto_id:
            # Update existing
            url = f"{base_url}/rest/v1/site_content?id=eq.{manifesto_id}"
            resp = requests.patch(url, headers=headers, json=payload, timeout=10)
            if resp.status_code in [200, 201, 204]:
                messages.success(request, "Manifesto updated successfully!")
            else:
                messages.error(request, f"Failed to update manifesto: {resp.text}")
        else:
            # Insert new (upsert)
            headers["Prefer"] = "return=representation,resolution=merge-duplicates"
            url = f"{base_url}/rest/v1/site_content"
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            if resp.status_code in [200, 201]:
                messages.success(request, "Manifesto created successfully!")
            else:
                messages.error(request, f"Failed to create manifesto: {resp.text}")
    except Exception as e:
        print(f"[Dashboard About Save] Exception: {e}")
        messages.error(request, f"Error saving manifesto: {str(e)}")

    return redirect("dashboard_about")


def dashboard_billing(request):
    return render(request, "dashboard/billing.html", {"active_page": "billing"})


def dashboard_settings(request):
    return render(request, "dashboard/settings.html", {"active_page": "settings"})


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


def _upload_to_supabase_storage(file, bucket="media-vault", folder=""):
    """Upload file to Supabase Storage and return public URL."""
    try:
        supabase = get_supabase()

        # Generate unique filename
        import uuid
        ext = file.name.split('.')[-1] if '.' in file.name else ''
        unique_name = f"{folder}/{uuid.uuid4().hex}.{ext}" if folder else f"{uuid.uuid4().hex}.{ext}"

        # Read file content
        file_content = file.read()

        # Upload to Supabase Storage
        result = supabase.storage.from_(bucket).upload(
            unique_name,
            file_content,
            {"content-type": file.content_type}
        )

        # Get public URL
        public_url = supabase.storage.from_(bucket).get_public_url(unique_name)
        return public_url
    except Exception as e:
        print(f"[Storage Upload] Error: {e}")
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
    Save a new video to the database and upload file to storage.
    """
    title = request.POST.get("title", "").strip()
    category = request.POST.get("category", "").strip()
    description = request.POST.get("description", "").strip()
    source = request.POST.get("source", "").strip()
    location = request.POST.get("location", "").strip()
    recorded_date = request.POST.get("recorded_date", "").strip() or None
    tags = request.POST.get("tags", "").strip()

    video_file = request.FILES.get("video_file")
    thumbnail_file = request.FILES.get("thumbnail")

    if not title or not category or not video_file:
        messages.error(request, "Title, category, and video file are required.")
        return redirect("dashboard_media_videos")

    try:
        # Upload video file
        file_url = _upload_to_supabase_storage(video_file, "media-vault", "videos")
        if not file_url:
            messages.error(request, "Failed to upload video file.")
            return redirect("dashboard_media_videos")

        # Upload thumbnail if provided
        thumbnail_url = None
        if thumbnail_file:
            thumbnail_url = _upload_to_supabase_storage(thumbnail_file, "media-vault", "thumbnails")

        # Parse tags
        tags_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

        # Save to database
        base_url = settings.SUPABASE_URL.rstrip("/")
        headers = _get_supabase_headers()

        payload = {
            "title": title,
            "category": category,
            "description": description,
            "file_url": file_url,
            "thumbnail_url": thumbnail_url,
            "source": source,
            "location": location,
            "recorded_date": recorded_date,
            "tags": tags_list,
            "file_size_bytes": video_file.size,
            "mime_type": video_file.content_type,
        }

        resp = requests.post(
            f"{base_url}/rest/v1/media_videos",
            headers=headers,
            json=payload,
            timeout=30
        )
        resp.raise_for_status()

        messages.success(request, "Video uploaded successfully!")
    except Exception as e:
        print(f"[Video Save] Error: {e}")
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

