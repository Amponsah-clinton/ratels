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
    path("suspended-members/", views.suspended_members_page, name="suspended_members"),
    path("banned-accounts/", views.banned_accounts_page, name="banned_accounts"),
    path("leadership/", views.leadership, name="leadership"),
    path("contact/", views.contact, name="contact"),
    path("contact/submit/", views.contact_submit, name="contact_submit"),
    path("donation/verify/", views.donation_verify, name="donation_verify"),
    path("messages/", views.messages_page, name="messages"),
    path("auth/", views.auth_page, name="auth"),
    path("auth/login/", views.auth_login, name="auth_login"),
    path("auth/signup/", views.auth_signup, name="auth_signup"),
    path("auth/forgot-password/", views.auth_forgot_password, name="auth_forgot_password"),
    path("auth/reset/<str:token>/", views.auth_password_reset_confirm, name="password_reset_confirm"),
    path("auth/reset/done/", views.auth_password_reset_complete, name="password_reset_complete"),
    path("auth/logout/", views.auth_logout, name="auth_logout"),
    path("blog/", views.blog, name="blog"),
    path("blog/<str:slug>/", views.blog_detail, name="blog_detail"),
    path("api/blog/comments/", views.api_blog_comments_list, name="api_blog_comments_list"),
    path("api/blog/comments/create/", views.api_blog_comment_create, name="api_blog_comment_create"),
    path("api/blog/comments/like/", views.api_blog_comment_like, name="api_blog_comment_like"),
    path("api/blog/comments/likes-check/", views.api_blog_comment_likes_check, name="api_blog_comment_likes_check"),
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
    path("dashboard/landing/save/", views.dashboard_landing_save, name="dashboard_landing_save"),
    # About Pages Management (About Ratel & Mission/Vision)
    path("dashboard/about-pages/save/", views.dashboard_about_pages_save, name="dashboard_about_pages_save"),
    path("dashboard/about-pages/get/", views.dashboard_about_pages_get, name="dashboard_about_pages_get"),
    path("dashboard/about-pages/delete/", views.dashboard_about_pages_delete, name="dashboard_about_pages_delete"),
    path("dashboard/site-settings/", views.dashboard_site_settings, name="dashboard_site_settings"),
    path("dashboard/site-settings/save/", views.dashboard_site_settings_save, name="dashboard_site_settings_save"),
    path("dashboard/site-settings/save-single/", views.dashboard_site_settings_save_single, name="dashboard_site_settings_save_single"),
    path("dashboard/site-settings/paystack-save/", views.dashboard_paystack_settings_save, name="dashboard_paystack_settings_save"),
    # Dashboard Resources Management (replaces billing)
    path("dashboard/resources/", views.dashboard_resources, name="dashboard_resources"),
    path("dashboard/resources/save/", views.dashboard_resources_save, name="dashboard_resources_save"),
    path("dashboard/resources/delete/", views.dashboard_resources_delete, name="dashboard_resources_delete"),
    path("dashboard/resources/get/", views.dashboard_resources_get, name="dashboard_resources_get"),
    path("dashboard/settings/", views.dashboard_settings, name="dashboard_settings"),
    # Dashboard Ideology Management (within settings)
    path("dashboard/ideology/save/", views.dashboard_ideology_save, name="dashboard_ideology_save"),
    path("dashboard/ideology/delete/", views.dashboard_ideology_delete, name="dashboard_ideology_delete"),
    path("dashboard/ideology/get/", views.dashboard_ideology_get, name="dashboard_ideology_get"),
    # Dashboard Announcements Management
    path("dashboard/announcements/", views.dashboard_announcements, name="dashboard_announcements"),
    path("dashboard/announcements/save/", views.dashboard_announcements_save, name="dashboard_announcements_save"),
    path("dashboard/announcements/delete/", views.dashboard_announcements_delete, name="dashboard_announcements_delete"),
    path("dashboard/announcements/get/", views.dashboard_announcements_get, name="dashboard_announcements_get"),
    # Dashboard Communications Management
    path("dashboard/communications/", views.dashboard_communications, name="dashboard_communications"),
    path("dashboard/communications/save/", views.dashboard_communications_save, name="dashboard_communications_save"),
    path("dashboard/communications/delete/", views.dashboard_communications_delete, name="dashboard_communications_delete"),
    path("dashboard/communications/get/", views.dashboard_communications_get, name="dashboard_communications_get"),
    # Dashboard Membership Status (Renewal Management)
    path("dashboard/status/", views.dashboard_membership_status, name="dashboard_membership_status"),
    path("dashboard/payments/", views.dashboard_payments, name="dashboard_payments"),
    path("dashboard/status/settings/save/", views.dashboard_membership_settings_save, name="dashboard_membership_settings_save"),
    path("dashboard/status/send-reminder/", views.dashboard_membership_send_reminder, name="dashboard_membership_send_reminder"),
    # Dashboard Messages Management (Share the Message)
    path("dashboard/messages/", views.dashboard_messages, name="dashboard_messages"),
    path("dashboard/messages/save/", views.dashboard_messages_save, name="dashboard_messages_save"),
    path("dashboard/messages/delete/", views.dashboard_messages_delete, name="dashboard_messages_delete"),
    path("dashboard/messages/get/", views.dashboard_messages_get, name="dashboard_messages_get"),
    # Dashboard YouTube/IG (Landing page links)
    path("dashboard/youtube-ig/", views.dashboard_youtube_ig, name="dashboard_youtube_ig"),
    path("dashboard/youtube-ig/save/", views.dashboard_youtube_ig_save, name="dashboard_youtube_ig_save"),
    path("dashboard/youtube-ig/get/", views.dashboard_youtube_ig_get, name="dashboard_youtube_ig_get"),
    path("dashboard/youtube-ig/delete/", views.dashboard_youtube_ig_delete, name="dashboard_youtube_ig_delete"),
    # Messages tracking (for public page)
    path("messages/track/", views.messages_track, name="messages_track"),
    # Cases (public)
    path("cases/", views.cases_page, name="cases"),
    # Dashboard Cases Management
    path("dashboard/cases/", views.dashboard_cases, name="dashboard_cases"),
    path("dashboard/cases/save/", views.dashboard_cases_save, name="dashboard_cases_save"),
    path("dashboard/cases/delete/", views.dashboard_cases_delete, name="dashboard_cases_delete"),
    path("dashboard/cases/get/", views.dashboard_cases_get, name="dashboard_cases_get"),
    path("dashboard/cases/status/", views.dashboard_cases_status, name="dashboard_cases_status"),
    # Dashboard Blog Management
    path("dashboard/blogs/", views.dashboard_blogs, name="dashboard_blogs"),
    path("dashboard/blogs/save/", views.dashboard_blogs_save, name="dashboard_blogs_save"),
    path("dashboard/blogs/get/", views.dashboard_blogs_get, name="dashboard_blogs_get"),
    path("dashboard/blogs/delete/", views.dashboard_blogs_delete, name="dashboard_blogs_delete"),
    # Member Dashboard (User-facing)
    path("member/", views.member_dashboard, name="member_dashboard"),
    path("member/announcements/", views.member_announcements, name="member_announcements"),
    path("member/communications/", views.member_communications, name="member_communications"),
    path("member/resources/", views.member_resources, name="member_resources"),
    path("member/events/", views.member_events, name="member_events"),
    path("member/subscriptions/", views.member_subscriptions, name="member_subscriptions"),
    path("member/subscriptions/invoice/<str:subscription_id>/", views.member_subscription_invoice_pdf, name="member_subscription_invoice_pdf"),
    path("member/profile/", views.member_profile, name="member_profile"),
    path("member/profile/update/", views.member_profile_update, name="member_profile_update"),
    path("member/profile/password/", views.member_profile_password, name="member_profile_password"),
    path("member/profile/photo/", views.member_profile_photo, name="member_profile_photo"),
    path("member/renew/", views.member_renew, name="member_renew"),
    path("member/renew/verify/", views.member_renew_verify, name="member_renew_verify"),
    # Admin tools
    path("admin/fix-subscriptions/", views.admin_fix_missing_subscriptions, name="admin_fix_subscriptions"),
    # About Us redirect (new URL structure)
    path("about-us/", views.ideology, name="about_us"),
]

