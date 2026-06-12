import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'annotation_platform.settings')
django.setup()

from annotation.models import Task, Annotator, User

# Create annotators
for i in range(1, 4):
    user, created = User.objects.get_or_create(username=f"annotator{i}", defaults={'password': 'pass'})
    Annotator.objects.get_or_create(user=user)

# Create a sample task
Task.objects.create(
    task_type='preference_ranking',
    data={
        "prompt": "Explain the benefits of renewable energy.",
        "response_a": "Renewable energy reduces carbon emissions and is sustainable.",
        "response_b": "Renewable energy is good for the environment."
    },
    status='pending'
)

print("Sample data created.")