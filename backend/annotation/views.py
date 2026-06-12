from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Task, Annotator, Assignment, Annotation
from .serializers import TaskSerializer
from .utils import compute_agreement, get_task_avg_time, export_rlhf_pairs, pairwise_kappa_across_tasks
import random
from django.utils import timezone
import csv
import io

def login_page(request):
    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            error = "Invalid username or password"
    return render(request, 'login.html', {'error': error})

def home(request):
    return render(request, 'index.html')

@api_view(['POST'])
@ensure_csrf_cookie
def api_login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(request, username=username, password=password)
    if user:
        login(request, user)
        return Response({"message": "Logged in"})
    return Response({"error": "Invalid credentials"}, status=401)

@api_view(['POST'])
@login_required
def api_logout(request):
    logout(request)
    return Response({"message": "Logged out"})

@api_view(['GET'])
@login_required
def me(request):
    # Ensure an Annotator record exists for this user
    annotator, _ = Annotator.objects.get_or_create(user=request.user)
    is_admin = request.user.is_superuser
    return Response({
        'id': annotator.id,
        'username': request.user.username,
        'is_admin': is_admin
    })

@api_view(['GET'])
@login_required
def next_task(request):
    # Ensure an Annotator record exists
    annotator, _ = Annotator.objects.get_or_create(user=request.user)

    annotated_task_ids = Annotation.objects.filter(
        assignment__annotator=annotator
    ).values_list('assignment__task_id', flat=True)

    available_tasks = Task.objects.filter(status='pending').exclude(id__in=annotated_task_ids)
    if not available_tasks.exists():
        return Response({"message": "No tasks available"}, status=200)

    tasks_with_counts = []
    for task in available_tasks:
        count = Annotation.objects.filter(assignment__task_id=task.id).count()
        tasks_with_counts.append((count, task))
    tasks_with_counts.sort(key=lambda x: x[0])
    task = tasks_with_counts[0][1]

    assignment = Assignment.objects.create(task=task, annotator=annotator)
    serializer = TaskSerializer(task)
    return Response({"assignment_id": assignment.id, "task": serializer.data})

@api_view(['POST'])
@login_required
def submit_annotation(request):
    # Ensure an Annotator record exists
    annotator, _ = Annotator.objects.get_or_create(user=request.user)

    assignment_id = request.data.get('assignment_id')
    result = request.data.get('result')
    time_spent = request.data.get('time_spent', 0)
    try:
        assignment = Assignment.objects.get(id=assignment_id, annotator=annotator)
    except Assignment.DoesNotExist:
        return Response({"error": "Assignment not found"}, status=404)
    Annotation.objects.create(assignment=assignment, result=result, time_spent=time_spent)
    assignment.is_completed = True
    assignment.completed_at = timezone.now()
    assignment.save()
    annotator.total_annotations += 1
    annotator.save()
    return Response({"message": "Annotation saved"})

@api_view(['GET'])
@login_required
def agreement_view(request, task_id):
    kappa = compute_agreement(task_id)
    return Response({"task_id": task_id, "percent_agreement": kappa})

@api_view(['GET'])
@login_required
def export_view(request):
    filepath = export_rlhf_pairs()
    return Response({"message": f"Export saved to {filepath}"})

@api_view(['POST'])
@login_required
def create_task(request):
    if not request.user.is_superuser:
        return Response({"error": "Admin only"}, status=403)
    data = request.data
    task = Task.objects.create(
        task_type=data.get('task_type', 'preference_ranking'),
        data=data.get('data', {}),
        status=data.get('status', 'pending')
    )
    return Response({"message": "Task created", "task_id": task.id})

@api_view(['POST'])
@login_required
def import_csv(request):
    if not request.user.is_superuser:
        return Response({"error": "Admin only"}, status=403)
    if 'file' not in request.FILES:
        return Response({"error": "No file provided"}, status=400)
    csv_file = request.FILES['file']
    decoded = io.TextIOWrapper(csv_file.file, encoding='utf-8')
    reader = csv.DictReader(decoded)
    created = 0
    for row in reader:
        prompt = row.get('prompt')
        response_a = row.get('response_a')
        response_b = row.get('response_b')
        if prompt and response_a and response_b:
            Task.objects.create(
                task_type='preference_ranking',
                data={'prompt': prompt, 'response_a': response_a, 'response_b': response_b},
                status='pending'
            )
            created += 1
    return Response({"message": f"Imported {created} tasks"})

@api_view(['GET'])
@login_required
def stats(request):
    # Ensure Annotator exists (though not strictly needed for stats, but safe)
    Annotator.objects.get_or_create(user=request.user)

    total_tasks = Task.objects.filter(task_type='preference_ranking').count()
    annotator_stats = []
    for ann in Annotator.objects.all():
        done = Assignment.objects.filter(annotator=ann, is_completed=True).count()
        annotator_stats.append({
            'id': ann.id,
            'name': ann.user.username,
            'completed': done
        })
    task_details = []
    for task in Task.objects.filter(task_type='preference_ranking'):
        agreement = compute_agreement(task.id)
        avg_time = get_task_avg_time(task.id)
        num_annotations = Annotation.objects.filter(assignment__task_id=task.id).count()
        task_details.append({
            'task_id': task.id,
            'agreement': round(agreement, 2) if agreement is not None else None,
            'avg_time': round(avg_time, 1) if avg_time else None,
            'annotation_count': num_annotations
        })
    pairwise_kappa = pairwise_kappa_across_tasks()
    return Response({
        'total_tasks': total_tasks,
        'annotators': annotator_stats,
        'task_details': task_details,
        'pairwise_kappa': pairwise_kappa
    })
    
@ensure_csrf_cookie
def csrf_token(request):
    return JsonResponse({'csrfToken': 'set'})