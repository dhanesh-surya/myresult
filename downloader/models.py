from django.db import models


class UploadFile(models.Model):
    file = models.FileField(upload_to="uploads/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.file.name} - {self.uploaded_at}"


class Job(models.Model):
    name = models.CharField(max_length=200)
    file_name = models.CharField(max_length=200)
    download_url = models.URLField(max_length=500, blank=True, null=True)
    username_field = models.CharField(max_length=50, default="userid", blank=True)
    password_field = models.CharField(max_length=50, default="pass", blank=True)
    download_button_id = models.CharField(
        max_length=100, default="download", blank=True
    )
    total_count = models.IntegerField(default=0)
    processed_count = models.IntegerField(default=0)
    completed_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("completed", "Completed"),
            ("stopped", "Stopped"),
        ],
        default="pending",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ResultFile(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    job = models.ForeignKey(
        Job, on_delete=models.CASCADE, related_name="results", null=True, blank=True
    )
    user_id = models.CharField(max_length=100)
    password = models.CharField(max_length=100, blank=True)
    file = models.FileField(upload_to="results/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.job.name if self.job else 'N/A'} - {self.user_id}"
