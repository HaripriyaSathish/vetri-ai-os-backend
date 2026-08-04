from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from ai_service.client import ask_claude


class GenerateLessonPlanView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        topic = request.data.get('topic')
        level = request.data.get('level', 'beginner')
        batch_id = request.data.get('batch_id')

        if not topic or not batch_id:
            return Response({"detail": "topic and batch_id are required."}, status=400)

        prompt = f"""Create a structured lesson plan for teaching "{topic}" to {level}-level trainees.
Include: learning objectives, key concepts to cover, a short hands-on exercise, and estimated time per section.
Format it clearly with headings."""

        generated_content = ask_claude(prompt, max_tokens=3000)

        return Response({
            "topic": topic,
            "generated_content": generated_content,
        })

class GenerateAssignmentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        topic = request.data.get('topic')
        level = request.data.get('level', 'beginner')
        category = request.data.get('category', 'task')
        batch_id = request.data.get('batch_id')

        if not topic or not batch_id:
            return Response({"detail": "topic and batch_id are required."}, status=400)

        category_prompts = {
            'task': f"""Create a short daily practice task for {level}-level trainees on the topic "{topic}".
It should take 30-60 minutes to complete. Include: a clear task description, 2-3 specific requirements,
and a one-line submission format suggestion. Keep it concise.""",

            'mini_project': f"""Create a mini project for {level}-level trainees on the topic "{topic}".
It should take 2-4 days to complete. Include: a project overview, 4-6 functional requirements,
suggested tech stack (if relevant), and a submission format (e.g. GitHub repo link + README).
Keep it practical and scoped for a short project.""",

            'main_project': f"""Create a comprehensive main/capstone project for {level}-level trainees on the topic "{topic}".
It should take 1-2 weeks to complete. Include: a detailed project overview, 8-10 functional requirements,
suggested architecture/tech stack, evaluation criteria, and a submission format (e.g. GitHub repo + deployed link + README + demo video).
Make it substantial enough to serve as a portfolio piece.""",
        }

        prompt = category_prompts.get(category, category_prompts['task'])
        generated_content = ask_claude(prompt, max_tokens=2000 if category == 'main_project' else 1500)

        return Response({
            "topic": topic,
            "category": category,
            "generated_content": generated_content,
        })

class GenerateMockQuestionsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        topic = request.data.get('topic')
        difficulty = request.data.get('difficulty', 'beginner')
        count = request.data.get('count', 5)
        batch_id = request.data.get('batch_id')

        if not topic or not batch_id:
            return Response({"detail": "topic and batch_id are required."}, status=400)

        prompt = f"""Generate {count} mock interview questions on the topic "{topic}" at {difficulty} level.
Number each question. Keep them realistic, as if asked in an actual technical interview.
Do not include answers, only the questions."""

        generated_content = ask_claude(prompt, max_tokens=1500)

        return Response({
            "topic": topic,
            "generated_content": generated_content,
        })    


from django.db.models import Avg
from .models import Attendance, AssignmentSubmission


class GenerateStudentProgressView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        student_id = request.data.get('student_id')
        batch_id = request.data.get('batch_id')

        if not student_id or not batch_id:
            return Response({"detail": "student_id and batch_id are required."}, status=400)

        # Attendance stats
        attendance_records = Attendance.objects.filter(student_id=student_id, batch_id=batch_id)
        total_days = attendance_records.count()
        present_days = attendance_records.filter(status='present').count()
        attendance_pct = round((present_days / total_days) * 100, 1) if total_days > 0 else None

        # Submission stats
        submissions = AssignmentSubmission.objects.filter(
            student_id=student_id,
            assignment__batch_id=batch_id
        )
        avg_score = submissions.aggregate(avg=Avg('score'))['avg']
        submission_details = "\n".join([
            f"- {s.assignment.title}: {s.score if s.score is not None else 'not scored'}/100. Remarks: {s.remarks or 'none'}"
            for s in submissions
        ]) or "No assignments submitted yet."

        prompt = f"""You are writing a short, encouraging but honest progress summary for a trainee.

Attendance: {present_days}/{total_days} days present ({attendance_pct if attendance_pct is not None else 'N/A'}%)
Average assignment score: {round(avg_score, 1) if avg_score is not None else 'N/A'}/100

Assignment details:
{submission_details}

Write a 3-4 sentence personalized progress summary for this trainee, mentioning strengths, areas to improve, and one concrete recommendation. Keep the tone supportive and professional."""

        generated_content = ask_claude(prompt, max_tokens=500)

        return Response({
            "student_id": student_id,
            "batch_id": batch_id,
            "attendance_percentage": attendance_pct,
            "average_score": round(avg_score, 1) if avg_score is not None else None,
            "generated_summary": generated_content,
        })    


from django.contrib.auth import get_user_model
from .models import Batch, Attendance, AssignmentSubmission

User = get_user_model()


class GenerateBatchPerformanceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        batch_id = request.data.get('batch_id')

        if not batch_id:
            return Response({"detail": "batch_id is required."}, status=400)

        student_ids = set(
            Attendance.objects.filter(batch_id=batch_id).values_list('student_id', flat=True)
        ) | set(
            AssignmentSubmission.objects.filter(assignment__batch_id=batch_id).values_list('student_id', flat=True)
        )

        if not student_ids:
            return Response({"detail": "No attendance or submission data found for this batch."}, status=404)

        student_summaries = []
        student_rows = []  # NEW: structured data for the table

        for sid in student_ids:
            student = User.objects.get(id=sid)
            attendance_records = Attendance.objects.filter(student_id=sid, batch_id=batch_id)
            total_days = attendance_records.count()
            present_days = attendance_records.filter(status='present').count()
            attendance_pct = round((present_days / total_days) * 100, 1) if total_days > 0 else None

            submissions = AssignmentSubmission.objects.filter(student_id=sid, assignment__batch_id=batch_id)
            avg_score = submissions.aggregate(avg=Avg('score'))['avg']

            student_summaries.append(
                f"- {student.username}: attendance {attendance_pct if attendance_pct is not None else 'N/A'}%, "
                f"avg score {round(avg_score, 1) if avg_score is not None else 'N/A'}/100"
            )

            # NEW: determine status label for the table
            if avg_score is not None and avg_score >= 75 and (attendance_pct or 0) >= 75:
                status_label = "Excelling"
            elif avg_score is not None and avg_score < 50:
                status_label = "Needs Attention"
            else:
                status_label = "On Track"

            student_rows.append({
                "student": student.username,
                "attendance_percentage": attendance_pct,
                "average_score": round(avg_score, 1) if avg_score is not None else None,
                "assignments_submitted": submissions.count(),
                "status": status_label,
            })

        batch = Batch.objects.get(id=batch_id)
        summary_text = "\n".join(student_summaries)

        prompt = f"""You are writing a batch performance report for a trainer, for batch "{batch.name}".

Per-student data:
{summary_text}

Write a concise batch performance report (4-6 sentences) covering:
1. Overall batch performance level
2. Which students are excelling
3. Which students may need extra attention
4. One concrete recommendation for the trainer

Keep it professional and actionable."""

        generated_content = ask_claude(prompt, max_tokens=800)

        return Response({
            "batch_id": batch_id,
            "batch_name": batch.name,
            "student_count": len(student_ids),
            "generated_report": generated_content,
            "students": student_rows,  # NEW
        })


from .models import Report
from .serializers import ReportSerializer


class GenerateReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        batch_id = request.data.get('batch_id')

        if not batch_id:
            return Response({"detail": "batch_id is required."}, status=400)

        student_ids = set(
            Attendance.objects.filter(batch_id=batch_id).values_list('student_id', flat=True)
        ) | set(
            AssignmentSubmission.objects.filter(assignment__batch_id=batch_id).values_list('student_id', flat=True)
        )

        if not student_ids:
            return Response({"detail": "No data found for this batch."}, status=404)

        batch = Batch.objects.get(id=batch_id)
        student_details = []

        for sid in student_ids:
            student = User.objects.get(id=sid)
            attendance_records = Attendance.objects.filter(student_id=sid, batch_id=batch_id)
            total_days = attendance_records.count()
            present_days = attendance_records.filter(status='present').count()
            attendance_pct = round((present_days / total_days) * 100, 1) if total_days > 0 else None

            submissions = AssignmentSubmission.objects.filter(student_id=sid, assignment__batch_id=batch_id)
            avg_score = submissions.aggregate(avg=Avg('score'))['avg']

            student_details.append(
                f"Student: {student.username}, Attendance: {attendance_pct}%, Average Score: {round(avg_score, 1) if avg_score is not None else 'N/A'}/100, "
                f"Assignments submitted: {submissions.count()}"
            )

        full_data = "\n".join(student_details)

        prompt = f"""You are writing a batch training report for "{batch.name}".

Data:
{full_data}

Respond ONLY with a JSON object in this exact structure, no markdown, no extra text before or after:

{{
  "executive_summary": "2-3 sentence overall summary",
  "recommendations": ["recommendation 1", "recommendation 2", "recommendation 3"],
  "student_notes": [
    {{"student": "username", "note": "1-2 sentence individual note"}}
  ]
}}

Keep each field concise. Do not include markdown formatting, asterisks, or pound signs anywhere in the text."""

        raw_content = ask_claude(prompt, max_tokens=2000)

        # Strip potential markdown code fences if the model wraps the JSON
        cleaned = raw_content.strip()
        if cleaned.startswith('```'):
            cleaned = cleaned.split('```')[1]
            if cleaned.startswith('json'):
                cleaned = cleaned[4:]
        cleaned = cleaned.strip()

        report = Report.objects.create(
            batch=batch,
            title=f"{batch.name} - Performance Report",
            content=cleaned,
            generated_by=request.user,
        )

        return Response(ReportSerializer(report).data, status=201)
    