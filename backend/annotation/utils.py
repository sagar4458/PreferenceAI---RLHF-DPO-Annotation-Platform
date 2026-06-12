from itertools import combinations
from sklearn.metrics import cohen_kappa_score
from collections import Counter
from .models import Annotation
import numpy as np
import json
import os
from django.conf import settings

def compute_agreement(task_id):
    """Percent agreement for a single task (simple majority)."""
    annotations = Annotation.objects.filter(assignment__task_id=task_id)
    if annotations.count() < 2:
        return None
    choices = [ann.result.get('chosen') for ann in annotations]
    counter = Counter(choices)
    most_common_count = counter.most_common(1)[0][1]
    return most_common_count / len(choices)

def get_task_avg_time(task_id):
    annotations = Annotation.objects.filter(assignment__task_id=task_id)
    if not annotations:
        return None
    total_time = sum(a.time_spent or 0 for a in annotations)
    return total_time / len(annotations)

def pairwise_kappa_across_tasks():
    """Compute Cohen's kappa for every pair of annotators across all tasks they both annotated."""
    annotations = Annotation.objects.select_related('assignment__annotator', 'assignment__task')
    data = {}  # annotator_id -> {task_id: label}
    for ann in annotations:
        ann_id = ann.assignment.annotator.id
        task_id = ann.assignment.task.id
        label = 0 if ann.result.get('chosen') == 'response_a' else 1
        data.setdefault(ann_id, {})[task_id] = label

    kappas = []
    for a1, a2 in combinations(data.keys(), 2):
        common_tasks = set(data[a1].keys()) & set(data[a2].keys())
        if len(common_tasks) >= 2:
            labels1 = [data[a1][t] for t in common_tasks]
            labels2 = [data[a2][t] for t in common_tasks]
            try:
                k = cohen_kappa_score(labels1, labels2)
                if np.isfinite(k):   # filter out NaN or inf
                    kappas.append({'annotator1': a1, 'annotator2': a2, 'kappa': round(k, 3)})
            except:
                pass
    return kappas

def export_rlhf_pairs():
    from .models import Task
    tasks = Task.objects.filter(task_type='preference_ranking', status='pending')
    pairs = []
    for task in tasks:
        annotations = Annotation.objects.filter(assignment__task_id=task.id)
        if not annotations:
            continue
        votes = {'response_a': 0, 'response_b': 0}
        for ann in annotations:
            chosen = ann.result.get('chosen')
            if chosen == 'response_a':
                votes['response_a'] += 1
            elif chosen == 'response_b':
                votes['response_b'] += 1
        if votes['response_a'] == votes['response_b']:
            continue
        chosen_key = 'response_a' if votes['response_a'] > votes['response_b'] else 'response_b'
        rejected_key = 'response_b' if chosen_key == 'response_a' else 'response_a'
        pairs.append({
            "prompt": task.data.get('prompt', ''),
            "chosen": task.data.get(chosen_key, ''),
            "rejected": task.data.get(rejected_key, '')
        })
    export_dir = os.path.join(settings.BASE_DIR, '..', 'data', 'exports')
    os.makedirs(export_dir, exist_ok=True)
    filepath = os.path.join(export_dir, 'dpo_train.jsonl')
    with open(filepath, 'w') as f:
        for pair in pairs:
            f.write(json.dumps(pair) + '\n')
    return filepath