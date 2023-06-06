from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.urls import reverse
from django.views import generic
import logging

from .models import Course, Enrollment, Question, Choice, Submission

logger = logging.getLogger(__name__)

def registration_request(request):
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html')
    
    elif request.method == 'POST':
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        
        user_exist = User.objects.filter(username=username).exists()
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context = {'message': "User already exists."}
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)

def login_request(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context = {'message': "Invalid username or password."}
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html')

def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')

def check_if_enrolled(user, course):
    return Enrollment.objects.filter(user=user, course=course).exists()

class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses

class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'

def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))

def extract_answers(request):
    submitted_answers = []
    for key in request.POST:
        if key.startswith('choice'):
            choice_id = int(request.POST[key])
            submitted_answers.append(choice_id)
    return submitted_answers

def submit(request, course_id):
    user = request.user
    course = get_object_or_404(Course, id=course_id)
    enrollment = get_object_or_404(Enrollment, user=user, course=course)
    submission = Submission.objects.create(enrollment=enrollment)
    submitted_answers = extract_answers(request)

    for choice_id in submitted_answers:
        choice_obj = get_object_or_404(Choice, id=choice_id)
        submission.choices.add(choice_obj)
    submission.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:show_exam_result', args=(course_id, submission.id)))

def show_exam_result(request, course_id, submission_id):
    course = get_object_or_404(Course, id=course_id)
    submission = get_object_or_404(Submission, id=submission_id)

    context = {}
    context['course'] = course
    context['choices'] = submission.choices.all()
    context['questions'] = Question.objects.filter(courses=course_id)

    submission_score = 0
    max_score = 0
    for question in context['questions']:
        max_score += question.marks
        if question.answered_correctly(submission.choices.all()):
            submission_score += question.marks

    context['grade'] = round(submission_score / max_score * 100)
    return render(request, 'onlinecourse/exam_result_bootstrap.html', context)
