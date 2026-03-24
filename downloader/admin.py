from django.contrib import admin
from .models import UploadFile, ResultFile, Job


@admin.register(UploadFile)
class UploadFileAdmin(admin.ModelAdmin):
    list_display = ["id", "file", "uploaded_at"]
    list_filter = ["uploaded_at"]
    search_fields = ["file"]


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "name",
        "download_url",
        "username_field",
        "password_field",
        "download_button_id",
        "total_count",
        "completed_count",
        "failed_count",
        "status",
        "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = ["name"]
    readonly_fields = ["created_at"]

    fieldsets = (
        ("Basic Info", {"fields": ("name", "file_name")}),
        (
            "Download Settings",
            {
                "fields": (
                    "download_url",
                    "username_field",
                    "password_field",
                    "download_button_id",
                )
            },
        ),
        (
            "Progress",
            {
                "fields": (
                    "total_count",
                    "completed_count",
                    "failed_count",
                    "processed_count",
                )
            },
        ),
        ("Status", {"fields": ("status",)}),
        ("Timestamps", {"fields": ("created_at",), "classes": ("collapse",)}),
    )


@admin.register(ResultFile)
class ResultFileAdmin(admin.ModelAdmin):
    list_display = ["id", "job", "user_id", "status", "file", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["user_id", "job__name"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("Job", {"fields": ("job",)}),
        ("User Info", {"fields": ("user_id", "password")}),
        ("Status", {"fields": ("status", "error_message")}),
        ("File", {"fields": ("file",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
