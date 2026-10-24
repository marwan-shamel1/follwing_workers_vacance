import json
from datetime import date, datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.utils import timezone
from django.contrib import messages
from django.db.models import Q, Sum, Count

from .models import (
    UserProfile, 
    CivilianWorker, 
    LeaveRequest, 
    get_current_leave_year_info
)
from .forms import (
    LeaveRequestForm, 
    ManagerLeaveRequestForm, 
    CivilianWorkerForm, 
    UserProfileUpdateForm
)
from .auth_backend import normalize_arabic

# -------------------------------------------------------------
# Authentication Views
# -------------------------------------------------------------

def login_view(request):
    if request.user.is_authenticated:
        return redirect_by_role(request.user)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect_by_role(user)
        else:
            messages.error(request, 'بيانات الدخول غير صحيحة، يرجى التأكد من اسم المستخدم وكلمة المرور.')

    return render(request, 'auth/login.html')


def logout_view(request):
    logout(request)
    messages.info(request, 'تم تسجيل الخروج بنجاح.')
    return redirect('login')


def redirect_by_role(user):
    try:
        role = user.profile.role
    except Exception:
        role = 'worker'
    
    if role == 'commander':
        return redirect('commander_dashboard')
    elif role == 'hr_manager':
        return redirect('hr_dashboard')
    else:
        return redirect('worker_dashboard')


def role_required(*allowed_roles):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            try:
                role = request.user.profile.role
            except Exception:
                role = 'worker'
            if role not in allowed_roles:
                messages.warning(request, 'عفواً، لا تملك الصلاحية للوصول إلى هذه الصفحة.')
                return redirect_by_role(request.user)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# -------------------------------------------------------------
# Worker Portal Views
# -------------------------------------------------------------

@login_required
def worker_dashboard(request):
    workers = CivilianWorker.objects.filter(is_active=True).order_by('name')
    current_year, _, _ = get_current_leave_year_info()

    if request.method == 'POST':
        form = LeaveRequestForm(request.POST)
        worker_id = request.POST.get('worker_id')
        worker = get_object_or_404(CivilianWorker, id=worker_id)
        
        leave_type = request.POST.get('leave_type')
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        days_count = int(request.POST.get('days_count', 1) or 1)
        permission_hours = request.POST.get('permission_hours', '').strip()
        reason = request.POST.get('reason', '').strip()
        address = request.POST.get('address_during_leave', '').strip()
        substitute = request.POST.get('substitute_worker', '').strip()
        phone = request.POST.get('applicant_phone', '').strip() or worker.phone

        if not start_date_str or not end_date_str:
            messages.error(request, 'يرجى تحديد تاريخ البداية والنهاية للإجازة.')
            return redirect('worker_dashboard')

        start_d = date.fromisoformat(start_date_str)
        end_d = date.fromisoformat(end_date_str)

        if end_d < start_d:
            messages.error(request, 'تاريخ انتهاء الإجازة لا يمكن أن يكون قبل تاريخ البدء.')
            return redirect('worker_dashboard')

        # Balance verification warnings
        summary = worker.get_leaves_summary(current_year)
        if leave_type == 'regular' and days_count > summary['regular']['remaining']:
            messages.warning(request, f"تنبيه: الرصيد الاعتيادي المتبقي ({summary['regular']['remaining']} يوم) أقل من المدة المطلوبة ({days_count} يوم). تم إرسال الطلب للنظر بمعرفة شؤون العاملين والقيادة.")
        elif leave_type == 'casual' and days_count > summary['casual']['remaining']:
            messages.warning(request, f"تنبيه: رصيد الإجازات العارضة المتبقي ({summary['casual']['remaining']} يوم) أقل من المدة المطلوبة ({days_count} يوم).")
        elif leave_type == 'permission' and summary['permission']['remaining'] <= 0:
            messages.warning(request, "تنبيه: استنفذت الحد الأقصى للأذونات السنوية (إذنان). تم إرسال الطلب لتقدير القيادة.")

        # Create leave request
        new_request = LeaveRequest.objects.create(
            worker=worker,
            is_manager_request=False,
            applicant_name=worker.name,
            applicant_job=worker.job_title,
            applicant_department=worker.department,
            applicant_phone=phone,
            leave_type=leave_type,
            start_date=start_d,
            end_date=end_d,
            days_count=days_count,
            permission_hours=permission_hours,
            leave_year=current_year,
            reason=reason,
            address_during_leave=address,
            substitute_worker=substitute,
            hr_status='pending',
            commander_status='pending',
        )

        messages.success(request, f'تم إرسال طلب إجازة ({new_request.get_leave_type_display()}) بنجاح، وهو الآن قيد المراجعة والتصديق لدى مدير شؤون العاملين.')
        return redirect(f"/worker/?worker_id={worker.id}")

    selected_worker_id = request.GET.get('worker_id')
    initial_worker = None
    if selected_worker_id:
        try:
            initial_worker = CivilianWorker.objects.get(id=selected_worker_id)
        except CivilianWorker.DoesNotExist:
            pass

    context = {
        'workers': workers,
        'initial_worker': initial_worker,
        'current_leave_year': current_year,
    }
    return render(request, 'worker/dashboard.html', context)


def api_worker_summary(request, worker_id):
    worker = get_object_or_404(CivilianWorker, id=worker_id)
    current_year, _, _ = get_current_leave_year_info()
    summary = worker.get_leaves_summary(current_year)

    # Get recent leaves for this worker
    leaves = worker.leave_requests.all().order_by('-created_at')[:20]
    leaves_data = []
    for l in leaves:
        leaves_data.append({
            'id': l.id,
            'leave_type_display': l.get_leave_type_display(),
            'leave_type': l.leave_type,
            'start_date': l.start_date.strftime('%Y-%m-%d'),
            'end_date': l.end_date.strftime('%Y-%m-%d'),
            'days_count': l.days_count,
            'permission_hours': l.permission_hours,
            'created_at': l.created_at.strftime('%Y-%m-%d %H:%M'),
            'hr_status': l.hr_status,
            'hr_status_display': l.get_hr_status_display(),
            'commander_status': l.commander_status,
            'commander_status_display': l.get_commander_status_display(),
            'composite_status': l.composite_status,
            'reason': l.reason,
            'substitute_worker': l.substitute_worker,
            'can_print': l.commander_status == 'approved',
        })

    return JsonResponse({
        'status': 'success',
        'worker': {
            'id': worker.id,
            'name': worker.name,
            'job_title': worker.job_title,
            'department': worker.department,
            'national_id': worker.national_id,
            'employee_code': worker.employee_code,
            'phone': worker.phone,
            'address': worker.address,
        },
        'summary': summary,
        'leaves': leaves_data,
    })


# -------------------------------------------------------------
# HR Manager Portal Views
# -------------------------------------------------------------

@login_required
@role_required('hr_manager', 'commander')
def hr_dashboard(request):
    """
    Incoming leave requests feed (مستجدات طلبات الإجازة)
    Displays frame with worker details, leave info, and leaves tally
    """
    pending_requests = LeaveRequest.objects.filter(hr_status='pending').order_by('-created_at')
    
    # Pre-attach summary for each pending request
    requests_with_summary = []
    for req in pending_requests:
        summary = None
        if req.worker:
            summary = req.worker.get_leaves_summary(req.leave_year)
        requests_with_summary.append({
            'request': req,
            'summary': summary
        })

    today = timezone.localdate()
    today_endorsed_count = LeaveRequest.objects.filter(hr_status='endorsed', hr_endorsed_at__date=today).count()
    total_workers_count = CivilianWorker.objects.filter(is_active=True).count()
    approved_commander_count = LeaveRequest.objects.filter(commander_status='approved').count()

    context = {
        'requests_with_summary': requests_with_summary,
        'pending_count': pending_requests.count(),
        'today_endorsed_count': today_endorsed_count,
        'total_workers_count': total_workers_count,
        'approved_commander_count': approved_commander_count,
    }
    return render(request, 'hr/dashboard.html', context)


@login_required
@role_required('hr_manager', 'commander')
def hr_endorse_request(request, request_id):
    if request.method == 'POST':
        req = get_object_or_404(LeaveRequest, id=request_id)
        notes = request.POST.get('hr_notes', '').strip()
        manager_profile = request.user.profile

        req.hr_status = 'endorsed'
        req.hr_endorsed_at = timezone.now()
        req.hr_endorsed_by = f"{manager_profile.full_name} ({manager_profile.job_title})"
        req.hr_notes = notes
        req.save()

        messages.success(request, f'تم تصديق طلب الإجازة للموظف ({req.applicant_name}) وإحالته إلى سيادة العميد أ ح / عبدالحميد محمد سلامة.')
    return redirect('hr_dashboard')


@login_required
@role_required('hr_manager', 'commander')
def hr_reject_request(request, request_id):
    if request.method == 'POST':
        req = get_object_or_404(LeaveRequest, id=request_id)
        notes = request.POST.get('hr_notes', '').strip()
        manager_profile = request.user.profile

        req.hr_status = 'rejected'
        req.hr_endorsed_at = timezone.now()
        req.hr_endorsed_by = f"{manager_profile.full_name} ({manager_profile.job_title})"
        req.hr_notes = notes
        req.save()

        messages.warning(request, f'تم عدم التصديق (رفض) على طلب الإجازة للموظف ({req.applicant_name}).')
    return redirect('hr_dashboard')


@login_required
@role_required('hr_manager', 'commander')
def hr_today_endorsed(request):
    """
    Requests endorsed today by HR manager
    """
    today = timezone.localdate()
    requests = LeaveRequest.objects.filter(
        hr_status='endorsed',
        hr_endorsed_at__date=today
    ).order_by('-hr_endorsed_at')

    context = {
        'requests': requests,
        'today': today,
        'count': requests.count(),
    }
    return render(request, 'hr/today_endorsed.html', context)


@login_required
@role_required('hr_manager', 'commander')
def hr_all_approved(request):
    """
    Archive of all endorsed / approved leave requests
    """
    requests = LeaveRequest.objects.filter(hr_status='endorsed').order_by('-created_at')

    # Optional search / filter
    query = request.GET.get('q', '').strip()
    if query:
        requests = requests.filter(
            Q(applicant_name__icontains=query) |
            Q(applicant_job__icontains=query) |
            Q(applicant_department__icontains=query) |
            Q(worker__national_id__icontains=query)
        )

    leave_type_filter = request.GET.get('leave_type', '')
    if leave_type_filter:
        requests = requests.filter(leave_type=leave_type_filter)

    commander_status_filter = request.GET.get('commander_status', '')
    if commander_status_filter:
        requests = requests.filter(commander_status=commander_status_filter)

    context = {
        'requests': requests,
        'query': query,
        'leave_type_filter': leave_type_filter,
        'commander_status_filter': commander_status_filter,
        'count': requests.count(),
    }
    return render(request, 'hr/all_approved.html', context)


@login_required
@role_required('hr_manager', 'commander')
def hr_manage_workers(request):
    """
    Civilian Workers management: Add / Edit / List
    """
    workers = CivilianWorker.objects.all().order_by('name')
    current_year, _, _ = get_current_leave_year_info()

    if request.method == 'POST':
        form = CivilianWorkerForm(request.POST)
        if form.is_valid():
            worker = form.save()
            messages.success(request, f'تمت إضافة العامل المدني ({worker.name}) بنجاح، وسيظهر فوراً في قائمة اختيار العمال.')
            return redirect('hr_manage_workers')
        else:
            messages.error(request, 'يرجى مراجعة البيانات المدخلة، تأكد من عدم تكرار الرقم القومي.')
    else:
        form = CivilianWorkerForm()

    # Precalculate summary for each worker
    workers_with_stats = []
    for w in workers:
        summary = w.get_leaves_summary(current_year)
        workers_with_stats.append({
            'worker': w,
            'summary': summary
        })

    context = {
        'workers_with_stats': workers_with_stats,
        'form': form,
        'total_count': workers.count(),
    }
    return render(request, 'hr/workers.html', context)


@login_required
@role_required('hr_manager', 'commander')
def hr_edit_worker(request, worker_id):
    worker = get_object_or_404(CivilianWorker, id=worker_id)
    if request.method == 'POST':
        form = CivilianWorkerForm(request.POST, instance=worker)
        if form.is_valid():
            form.save()
            messages.success(request, f'تم تحديث بيانات العامل المدني ({worker.name}) بنجاح.')
            return redirect('hr_manage_workers')
    else:
        form = CivilianWorkerForm(instance=worker)

    return render(request, 'hr/edit_worker.html', {'form': form, 'worker': worker})


@login_required
@role_required('hr_manager', 'commander')
def hr_delete_worker(request, worker_id):
    worker = get_object_or_404(CivilianWorker, id=worker_id)
    name = worker.name
    worker.delete()
    messages.success(request, f'تم حذف العامل ({name}) من سجلات المنظومة.')
    return redirect('hr_manage_workers')


@login_required
@role_required('hr_manager', 'commander')
def hr_manager_leave(request):
    """
    Dedicated leave application form for the HR Manager.
    Name and job title are fixed to the HR Manager.
    Directly endorsed by HR and goes to Commander!
    """
    manager_profile = request.user.profile
    current_year, _, _ = get_current_leave_year_info()

    if request.method == 'POST':
        leave_type = request.POST.get('leave_type')
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        days_count = int(request.POST.get('days_count', 1) or 1)
        permission_hours = request.POST.get('permission_hours', '').strip()
        reason = request.POST.get('reason', '').strip()
        address = request.POST.get('address_during_leave', '').strip()
        substitute = request.POST.get('substitute_worker', '').strip()
        phone = request.POST.get('applicant_phone', '').strip() or manager_profile.phone

        if not start_date_str or not end_date_str:
            messages.error(request, 'يرجى تحديد تاريخ البداية والنهاية للإجازة.')
            return redirect('hr_manager_leave')

        start_d = date.fromisoformat(start_date_str)
        end_d = date.fromisoformat(end_date_str)

        req = LeaveRequest.objects.create(
            worker=None,
            is_manager_request=True,
            applicant_name=manager_profile.full_name,
            applicant_job=manager_profile.job_title,
            applicant_department=manager_profile.department,
            applicant_phone=phone,
            leave_type=leave_type,
            start_date=start_d,
            end_date=end_d,
            days_count=days_count,
            permission_hours=permission_hours,
            leave_year=current_year,
            reason=reason,
            address_during_leave=address,
            substitute_worker=substitute,
            hr_status='endorsed',
            hr_endorsed_at=timezone.now(),
            hr_endorsed_by=manager_profile.full_name,
            hr_notes='طلب إجازة خاص بالسيد مدير شؤون العاملين',
            commander_status='pending',
        )

        messages.success(request, f'تم إرسال طلب إجازتك إلى سيادة العميد أ ح / عبدالحميد محمد سلامة للتصديق والاعتماد.')
        return redirect('hr_manager_leave')

    manager_requests = LeaveRequest.objects.filter(is_manager_request=True).order_by('-created_at')

    context = {
        'manager_profile': manager_profile,
        'manager_requests': manager_requests,
        'current_leave_year': current_year,
    }
    return render(request, 'hr/manager_leave.html', context)


@login_required
@role_required('hr_manager', 'commander')
def hr_profile(request):
    """
    Profile settings: change username, password, manager's name and title
    """
    profile = request.user.profile
    if request.method == 'POST':
        form = UserProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            profile = form.save()
            new_username = form.cleaned_data.get('new_username')
            new_password = form.cleaned_data.get('new_password')

            user = request.user
            if new_username and new_username != user.username:
                user.username = new_username
            if new_password:
                user.set_password(new_password)
            user.save()

            if new_password:
                # Re-login so session remains valid
                login(request, user)

            messages.success(request, 'تم تحديث بيانات مدير شؤون العاملين وإعدادات الدخول بنجاح.')
            return redirect('hr_profile')
    else:
        form = UserProfileUpdateForm(instance=profile, initial={'new_username': request.user.username})

    return render(request, 'hr/profile.html', {'form': form, 'profile': profile})


# -------------------------------------------------------------
# Area Commander Portal Views
# -------------------------------------------------------------

@login_required
@role_required('commander')
def commander_dashboard(request):
    """
    Commander dashboard summary
    """
    pending_commander_requests = LeaveRequest.objects.filter(
        hr_status='endorsed',
        commander_status='pending'
    ).order_by('-created_at')

    recent_decisions = LeaveRequest.objects.filter(
        commander_status__in=['approved', 'rejected']
    ).order_by('-commander_decided_at')[:8]

    today = timezone.localdate()
    today_approved = LeaveRequest.objects.filter(
        commander_status='approved',
        commander_decided_at__date=today
    ).count()

    total_active_workers = CivilianWorker.objects.filter(is_active=True).count()

    context = {
        'pending_requests': pending_commander_requests,
        'pending_count': pending_commander_requests.count(),
        'recent_decisions': recent_decisions,
        'today_approved': today_approved,
        'total_workers': total_active_workers,
    }
    return render(request, 'commander/dashboard.html', context)


@login_required
@role_required('commander')
def commander_requests(request):
    """
    All requests for Commander review and decision
    Shows endorsement details, leaves tally, and allows Approve / Reject
    """
    status_filter = request.GET.get('status', 'pending')
    
    if status_filter == 'pending':
        requests = LeaveRequest.objects.filter(hr_status='endorsed', commander_status='pending').order_by('-created_at')
    elif status_filter == 'approved':
        requests = LeaveRequest.objects.filter(commander_status='approved').order_by('-commander_decided_at')
    elif status_filter == 'rejected':
        requests = LeaveRequest.objects.filter(commander_status='rejected').order_by('-commander_decided_at')
    elif status_filter == 'all':
        requests = LeaveRequest.objects.all().order_by('-created_at')
    else:
        requests = LeaveRequest.objects.filter(hr_status='endorsed', commander_status='pending').order_by('-created_at')

    # Pre-attach summary for each request
    requests_with_summary = []
    for req in requests:
        summary = None
        if req.worker:
            summary = req.worker.get_leaves_summary(req.leave_year)
        requests_with_summary.append({
            'request': req,
            'summary': summary
        })

    context = {
        'requests_with_summary': requests_with_summary,
        'status_filter': status_filter,
        'pending_count': LeaveRequest.objects.filter(hr_status='endorsed', commander_status='pending').count(),
    }
    return render(request, 'commander/requests.html', context)


@login_required
@role_required('commander')
def commander_decide(request, request_id):
    if request.method == 'POST':
        req = get_object_or_404(LeaveRequest, id=request_id)
        decision = request.POST.get('decision')  # 'approve' or 'reject'
        notes = request.POST.get('commander_notes', '').strip()
        commander_profile = request.user.profile

        if decision == 'approve':
            req.commander_status = 'approved'
            req.commander_decided_at = timezone.now()
            req.commander_decided_by = commander_profile.full_name
            req.commander_notes = notes
            req.save()
            messages.success(request, f'تم تصديق واعتماد إجازة ({req.applicant_name}) نهائياً من سيادة العميد.')
        elif decision == 'reject':
            req.commander_status = 'rejected'
            req.commander_decided_at = timezone.now()
            req.commander_decided_by = commander_profile.full_name
            req.commander_notes = notes
            req.save()
            messages.warning(request, f'تم رفض طلب إجازة ({req.applicant_name}) من سيادة العميد.')

    return redirect('commander_requests')


@login_required
@role_required('commander')
def commander_all_leaves(request):
    """
    Search engine for all civilian workers leaves + top unit leaves tally!
    (ويوجد سيرش انجين فى الصفحة يستطيع ان يبحث عن اسم العامل وبمجرد ان يبحث يظهر كل اجازته و بالاعلى يوجد حصر للاجازات وعددها بكل انواعها وتكون محددة نوعها اساسى)
    """
    current_year, _, _ = get_current_leave_year_info()

    # 1. Top Unit-Wide Leaves Tally (Approved Leaves in current leave year)
    approved_year_requests = LeaveRequest.objects.filter(
        leave_year=current_year, 
        commander_status='approved'
    )

    total_regular = approved_year_requests.filter(leave_type='regular').aggregate(s=Sum('days_count'))['s'] or 0
    total_casual = approved_year_requests.filter(leave_type='casual').aggregate(s=Sum('days_count'))['s'] or 0
    total_hospital = approved_year_requests.filter(leave_type='hospital').aggregate(s=Sum('days_count'))['s'] or 0
    total_sick = approved_year_requests.filter(leave_type='sick').aggregate(s=Sum('days_count'))['s'] or 0
    total_permission = approved_year_requests.filter(leave_type='permission').count()
    total_mission = approved_year_requests.filter(leave_type='mission').aggregate(s=Sum('days_count'))['s'] or 0
    total_days_all = total_regular + total_casual + total_hospital + total_sick + total_mission

    # 2. Search Engine
    search_query = request.GET.get('search', '').strip()
    workers = CivilianWorker.objects.filter(is_active=True).order_by('name')

    if search_query:
        workers = workers.filter(
            Q(name__icontains=search_query) |
            Q(job_title__icontains=search_query) |
            Q(national_id__icontains=search_query) |
            Q(department__icontains=search_query) |
            Q(employee_code__icontains=search_query)
        )

    # Attach summary and all leave records for each matching worker
    worker_results = []
    for w in workers:
        summary = w.get_leaves_summary(current_year)
        leaves = w.leave_requests.all().order_by('-start_date')
        worker_results.append({
            'worker': w,
            'summary': summary,
            'leaves': leaves,
            'leaves_count': leaves.count(),
        })

    context = {
        'total_regular': total_regular,
        'total_casual': total_casual,
        'total_hospital': total_hospital,
        'total_sick': total_sick,
        'total_permission': total_permission,
        'total_mission': total_mission,
        'total_days_all': total_days_all,
        'current_leave_year': current_year,
        'search_query': search_query,
        'worker_results': worker_results,
        'matching_count': workers.count(),
    }
    return render(request, 'commander/all_leaves.html', context)


@login_required
@role_required('commander')
def commander_profile(request):
    """
    Commander profile: change username, password, and upload photo
    """
    profile = request.user.profile
    if request.method == 'POST':
        form = UserProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            profile = form.save()
            new_username = form.cleaned_data.get('new_username')
            new_password = form.cleaned_data.get('new_password')

            user = request.user
            if new_username and new_username != user.username:
                user.username = new_username
            if new_password:
                user.set_password(new_password)
            user.save()

            if new_password:
                login(request, user)

            messages.success(request, 'تم تحديث بيانات سيادة العميد وإعدادات الحساب والصورة بنجاح.')
            return redirect('commander_profile')
    else:
        form = UserProfileUpdateForm(instance=profile, initial={'new_username': request.user.username})

    return render(request, 'commander/profile.html', {'form': form, 'profile': profile})


# -------------------------------------------------------------
# Printable Leave Permit Document
# -------------------------------------------------------------

@login_required
def print_leave_order(request, request_id):
    leave_req = get_object_or_404(LeaveRequest, id=request_id)
    summary = None
    if leave_req.worker:
        summary = leave_req.worker.get_leaves_summary(leave_req.leave_year)

    context = {
        'req': leave_req,
        'summary': summary,
        'print_date': timezone.localdate(),
    }
    return render(request, 'print/leave_order.html', context)
