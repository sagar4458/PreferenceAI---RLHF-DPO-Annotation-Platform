from django.db import models
from django.contrib.auth.models import User

class Task(models.Model):
    TASK_TYPES = [
        ('text_classification', 'Text Classification'),
        ('preference_ranking', 'Preference Ranking'),
    ]
    task_type = models.CharField(max_length=50, choices=TASK_TYPES)
    data = models.JSONField()
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

class Annotator(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    expertise = models.CharField(max_length=100, blank=True)
    total_annotations = models.IntegerField(default=0)

class Assignment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    annotator = models.ForeignKey(Annotator, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)

class Annotation(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    result = models.JSONField()
    time_spent = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)