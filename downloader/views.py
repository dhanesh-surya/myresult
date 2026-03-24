import pandas as pd
import os
import zipfile
import json
from django.shortcuts import render
from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.core.files import File
from django.utils import timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from .forms import UploadForm
from .models import ResultFile, Job
from .utils import download_result, STOP_FLAG_FILE

MAX_WORKERS = 3


def index(request):
    form = UploadForm()
    jobs = Job.objects.all().order_by("-created_at")[:10]
    return render(request, "index.html", {"form": form, "jobs": jobs})


def start_download(request):
    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                job_name = request.POST.get("job_name", "").strip()
                download_url = request.POST.get("download_url", "").strip()
                username_field = request.POST.get("username_field", "userid").strip()
                password_field = request.POST.get("password_field", "pass").strip()
                download_button_id = request.POST.get(
                    "download_button_id", "download"
                ).strip()

                if not job_name:
                    job_name = f"Job_{timezone.now().strftime('%Y%m%d_%H%M%S')}"

                if not download_url:
                    return JsonResponse(
                        {"success": False, "error": "Download URL is required"}
                    )

                if os.path.exists(STOP_FLAG_FILE):
                    os.remove(STOP_FLAG_FILE)

                obj = form.save()
                file_path = obj.file.path
                download_dir = os.path.join(settings.MEDIA_ROOT, "results")
                os.makedirs(download_dir, exist_ok=True)

                if file_path.endswith(".xlsx"):
                    df = pd.read_excel(file_path)
                    user_col = "user_id" if "user_id" in df.columns else "username"
                else:
                    df = pd.read_csv(file_path, names=["username", "password"])
                    user_col = "username"

                total = len(df)

                job = Job.objects.create(
                    name=job_name,
                    file_name=obj.file.name,
                    download_url=download_url,
                    username_field=username_field,
                    password_field=password_field,
                    download_button_id=download_button_id,
                    total_count=total,
                    status="processing",
                )

                progress = {
                    "current": 0,
                    "total": total,
                    "status": "processing",
                    "job_id": job.id,
                }
                with open("progress.json", "w") as f:
                    json.dump(progress, f)

                result_ids = []
                for _, row in df.iterrows():
                    user_id = str(row[user_col])
                    password = str(row["password"])
                    result = ResultFile.objects.create(
                        job=job, user_id=user_id, password=password, status="pending"
                    )
                    result_ids.append(result.id)

                def process_result(result_id):
                    result = ResultFile.objects.get(id=result_id)
                    if os.path.exists(STOP_FLAG_FILE):
                        result.status = "failed"
                        result.error_message = "Stopped by user"
                        result.save()
                        return False

                    result.status = "processing"
                    result.save()

                    try:
                        file_path = download_result(
                            result.user_id,
                            result.password,
                            download_dir,
                            job.download_url,
                            job.username_field,
                            job.password_field,
                            job.download_button_id,
                        )
                        if file_path and os.path.exists(file_path):
                            with open(file_path, "rb") as f:
                                result.file.save(os.path.basename(file_path), File(f))
                            result.status = "completed"
                        else:
                            result.status = "failed"
                            result.error_message = "No file downloaded"
                    except Exception as e:
                        result.status = "failed"
                        result.error_message = str(e)

                    result.save()
                    return True

                processed = 0
                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    futures = {
                        executor.submit(process_result, rid): rid for rid in result_ids
                    }
                    for future in as_completed(futures):
                        if os.path.exists(STOP_FLAG_FILE):
                            break
                        processed += 1
                        progress["current"] = processed
                        with open("progress.json", "w") as f:
                            json.dump(progress, f)

                if os.path.exists(STOP_FLAG_FILE):
                    job.status = "stopped"
                else:
                    job.status = "completed"

                job.processed_count = processed
                job.completed_count = job.results.filter(status="completed").count()
                job.failed_count = job.results.filter(status="failed").count()
                job.save()

                progress["status"] = job.status
                with open("progress.json", "w") as f:
                    json.dump(progress, f)

                completed_results = job.results.filter(
                    status="completed", file__isnull=False
                )
                file_list = []
                for r in completed_results:
                    if r.file:
                        file_list.append(
                            {
                                "name": f"{r.user_id}_result.pdf",
                                "url": r.file.url,
                                "user_id": r.user_id,
                            }
                        )

                if completed_results.exists():
                    zip_path = os.path.join(
                        settings.MEDIA_ROOT, f"results_{job.id}.zip"
                    )
                    if os.path.exists(zip_path):
                        os.remove(zip_path)
                    with zipfile.ZipFile(zip_path, "w") as zipf:
                        for r in completed_results:
                            if r.file:
                                zipf.write(r.file.path, os.path.basename(r.file.name))

                    return JsonResponse(
                        {
                            "success": True,
                            "job_id": job.id,
                            "files": len(file_list),
                            "file_list": file_list,
                            "zip_url": f"/media/results_{job.id}.zip",
                        }
                    )

                return JsonResponse(
                    {
                        "success": True,
                        "job_id": job.id,
                        "files": 0,
                        "file_list": [],
                        "zip_url": None,
                    }
                )

            except Exception as e:
                return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request"})


def get_progress(request):
    try:
        with open("progress.json", "r") as f:
            progress = json.load(f)
        return JsonResponse(progress)
    except:
        return JsonResponse({"current": 0, "total": 0, "status": "idle"})


def stop_download(request):
    try:
        with open(STOP_FLAG_FILE, "w") as f:
            f.write("stop")
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


def get_files(request):
    job_id = request.GET.get("job_id")
    if not job_id:
        return JsonResponse({"success": False, "error": "Job ID is required"})

    try:
        job = Job.objects.get(id=job_id)
        results = job.results.filter(status="completed", file__isnull=False)

        files = []
        for r in results:
            if r.file:
                files.append(
                    {
                        "id": r.id,
                        "user_id": r.user_id,
                        "file_name": os.path.basename(r.file.name),
                        "file_url": r.file.url,
                        "created_at": r.created_at.isoformat()
                        if r.created_at
                        else None,
                    }
                )

        return JsonResponse({"success": True, "files": files, "total": len(files)})
    except Job.DoesNotExist:
        return JsonResponse({"success": False, "error": "Job not found"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


def get_status(request):
    job_id = request.GET.get("job_id")
    if not job_id:
        return JsonResponse({"success": False, "error": "Job ID is required"})

    try:
        job = Job.objects.get(id=job_id)

        status_data = {
            "success": True,
            "job_id": job.id,
            "name": job.name,
            "status": job.status,
            "total_count": job.total_count,
            "processed_count": job.processed_count,
            "completed_count": job.completed_count,
            "failed_count": job.failed_count,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "download_url": job.download_url,
            "username_field": job.username_field,
            "password_field": job.password_field,
            "download_button_id": job.download_button_id,
        }

        try:
            with open("progress.json", "r") as f:
                progress = json.load(f)
                status_data["progress"] = progress
        except:
            pass

        return JsonResponse(status_data)
    except Job.DoesNotExist:
        return JsonResponse({"success": False, "error": "Job not found"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


def get_jobs(request):
    try:
        jobs = Job.objects.all().order_by("-created_at")

        job_list = []
        for job in jobs:
            job_data = {
                "id": job.id,
                "name": job.name,
                "status": job.status,
                "total_count": job.total_count,
                "processed_count": job.processed_count,
                "completed_count": job.completed_count,
                "failed_count": job.failed_count,
                "download_url": job.download_url,
                "created_at": job.created_at.isoformat() if job.created_at else None,
            }

            if (
                job.status == "completed"
                and job.results.filter(status="completed").exists()
            ):
                zip_path = os.path.join(settings.MEDIA_ROOT, f"results_{job.id}.zip")
                job_data["zip_url"] = (
                    f"/media/results_{job.id}.zip" if os.path.exists(zip_path) else None
                )
            else:
                job_data["zip_url"] = None

            job_list.append(job_data)

        return JsonResponse({"success": True, "jobs": job_list, "total": len(job_list)})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


def delete_job(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request method"})

    job_id = request.POST.get("job_id")
    if not job_id:
        return JsonResponse({"success": False, "error": "Job ID is required"})

    try:
        job = Job.objects.get(id=job_id)

        for result in job.results.all():
            if result.file:
                try:
                    if os.path.exists(result.file.path):
                        os.remove(result.file.path)
                except:
                    pass

            zip_path = os.path.join(settings.MEDIA_ROOT, f"results_{job.id}.zip")
            if os.path.exists(zip_path):
                try:
                    os.remove(zip_path)
                except:
                    pass

        job.delete()

        return JsonResponse(
            {"success": True, "message": f"Job {job_id} deleted successfully"}
        )
    except Job.DoesNotExist:
        return JsonResponse({"success": False, "error": "Job not found"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})
