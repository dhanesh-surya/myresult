from django.urls import path
from .views import (
    index,
    start_download,
    get_progress,
    stop_download,
    get_files,
    get_status,
    get_jobs,
    delete_job,
)

urlpatterns = [
    path("", index, name="index"),
    path("start-download/", start_download, name="start_download"),
    path("progress/", get_progress, name="get_progress"),
    path("stop/", stop_download, name="stop_download"),
    path("files/", get_files, name="get_files"),
    path("status/", get_status, name="get_status"),
    path("jobs/", get_jobs, name="get_jobs"),
    path("delete-job/<int:job_id>/", delete_job, name="delete_job"),
]
