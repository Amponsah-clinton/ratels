from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),

    # About Us
    path("about/", views.about, name="about"),
    path("about/ratel/", views.about_ratel, name="about_ratel"),
    path("about/mission-vision/", views.mission_vision, name="mission_vision"),
    path("about/ideology/", views.ideology, name="ideology"),
    path("about/faqs/", views.faqs, name="faqs"),

    # Media Vault
    path("media-vault/", views.media_vault, name="media_vault"),
    path("media-vault/videos/", views.media_videos, name="media_videos"),
    path("media-vault/audios/", views.media_audios, name="media_audios"),
    path("media-vault/images/", views.media_images, name="media_images"),
    path("media-vault/documents/", views.media_documents, name="media_documents"),

    # Other pages
    path("resources/", views.resources, name="resources"),
    path("membership/", views.membership, name="membership"),
    path("leadership/", views.leadership, name="leadership"),
    path("contact/", views.contact, name="contact"),
    path("contact/submit/", views.contact_submit, name="contact_submit"),
    path("auth/", views.auth_page, name="auth"),
    path("auth/login/", views.auth_login, name="auth_login"),
    path("auth/signup/", views.auth_signup, name="auth_signup"),
    path("auth/forgot-password/", views.auth_forgot_password, name="auth_forgot_password"),
    path("blog/", views.blog, name="blog"),
    path("features/", views.features, name="features"),
    # Dashboard
    path("dashboard/", views.dashboard_home, name="dashboard_home"),
    # Dashboard membership (previously dashboard/contacts/)
    path("dashboard/membership/", views.dashboard_contacts, name="dashboard_membership"),
    path("dashboard/membership/actions/", views.membership_manage, name="dashboard_membership_actions"),
    # Dashboard leadership management
    path("dashboard/leadership/", views.dashboard_leadership, name="dashboard_leadership"),
    path("dashboard/leadership/save/", views.dashboard_leadership_save, name="dashboard_leadership_save"),
    path("dashboard/leadership/get/", views.dashboard_leadership_get, name="dashboard_leadership_get"),
    path("dashboard/leadership/delete/", views.dashboard_leadership_delete, name="dashboard_leadership_delete"),
    path("dashboard/companies/", views.dashboard_companies, name="dashboard_companies"),
    # Contact Inquiries (replaces deals)
    path("dashboard/inquiries/", views.dashboard_inquiries, name="dashboard_inquiries"),
    path("dashboard/inquiries/get/", views.dashboard_inquiry_get, name="dashboard_inquiry_get"),
    path("dashboard/inquiries/status/", views.dashboard_inquiry_status, name="dashboard_inquiry_status"),
    path("dashboard/inquiries/reply/", views.dashboard_inquiry_reply, name="dashboard_inquiry_reply"),
    path("dashboard/deals/", views.dashboard_deals, name="dashboard_deals"),  # Keep for backwards compat
    # Media Vault Dashboard Routes
    path("dashboard/media-vault/", views.dashboard_media_vault, name="dashboard_media_vault"),
    path("dashboard/media-vault/videos/", views.dashboard_media_videos, name="dashboard_media_videos"),
    path("dashboard/media-vault/videos/save/", views.dashboard_media_videos_save, name="dashboard_media_videos_save"),
    path("dashboard/media-vault/videos/delete/", views.dashboard_media_videos_delete, name="dashboard_media_videos_delete"),
    path("dashboard/media-vault/audio/", views.dashboard_media_audio, name="dashboard_media_audio"),
    path("dashboard/media-vault/audio/save/", views.dashboard_media_audio_save, name="dashboard_media_audio_save"),
    path("dashboard/media-vault/audio/delete/", views.dashboard_media_audio_delete, name="dashboard_media_audio_delete"),
    path("dashboard/media-vault/images/", views.dashboard_media_images, name="dashboard_media_images"),
    path("dashboard/media-vault/images/save/", views.dashboard_media_images_save, name="dashboard_media_images_save"),
    path("dashboard/media-vault/images/delete/", views.dashboard_media_images_delete, name="dashboard_media_images_delete"),
    path("dashboard/media-vault/documents/", views.dashboard_media_documents, name="dashboard_media_documents"),
    path("dashboard/media-vault/documents/save/", views.dashboard_media_documents_save, name="dashboard_media_documents_save"),
    path("dashboard/media-vault/documents/delete/", views.dashboard_media_documents_delete, name="dashboard_media_documents_delete"),
    # Legacy tasks route redirects to media vault
    path("dashboard/tasks/", views.dashboard_media_vault, name="dashboard_tasks"),
    path("dashboard/about/", views.dashboard_about, name="dashboard_about"),
    path("dashboard/about/save/", views.dashboard_about_save, name="dashboard_about_save"),
    path("dashboard/billing/", views.dashboard_billing, name="dashboard_billing"),
    path("dashboard/settings/", views.dashboard_settings, name="dashboard_settings"),
]

