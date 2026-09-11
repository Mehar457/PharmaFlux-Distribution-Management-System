from django.shortcuts import render, redirect
from django.contrib.auth import authenticate
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages


def login_view(request):
    if request.user.is_authenticated:
        if request.user.role == 'superadmin':
            return redirect('superadmin_dashboard')
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(
            request,
            username=username,
            password=password
        )
        if user:
            login(request, user)
            if user.role == 'superadmin':
                return redirect('superadmin_dashboard')
            else:
                return redirect('dashboard')
        else:
            messages.error(
                request,
                'Invalid username or password'
            )
    return render(request, 'users/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    if request.user.role == 'superadmin':
        return redirect('superadmin_dashboard')

    context = {
        'total_stock': 0,
        'low_stock': 0,
        'expiry_soon': 0,
        'total_sales': 0,
        'total_purchases': 0,
        'profit': 0,
        # Chart data — sirf distributor ke liye populate hoga (neeche
        # dekhein). Employee ke liye ye khali rehta hai, aur template
        # mein bhi role check ki wajah se graphs render hi nahi honge.
        'chart_labels': '[]',
        'chart_sales': '[]',
        'chart_purchases': '[]',
        'chart_profit': '[]',
    }

    try:
        from stock.models import Stock
        from sales.models import Sale
        from purchases.models import Purchase
        from django.db.models import Sum
        from datetime import date, timedelta
        import json

        if request.user.role == 'distributor':
            distributor = request.user.distributor
        elif request.user.role == 'employee':
            distributor = request.user.employee.distributor

        context['total_stock'] = Stock.objects.filter(
            distributor=distributor
        ).count()

        context['low_stock'] = Stock.objects.filter(
            distributor=distributor,
            quantity__lte=10
        ).count()

        context['expiry_soon'] = Stock.objects.filter(
            distributor=distributor,
            expiry_date__lte=date.today() + timedelta(days=30)
        ).count()

        context['total_sales'] = Sale.objects.filter(
            distributor=distributor
        ).aggregate(total=Sum('total_price'))['total'] or 0

        context['total_purchases'] = Purchase.objects.filter(
            distributor=distributor
        ).aggregate(total=Sum('purchase_price'))['total'] or 0

        context['profit'] = (
            context['total_sales'] - context['total_purchases']
        )

        # ── Dashboard graphs — SIRF distributor ke liye ──
        # Employee is block mein bilkul nahi ghusta, is liye uske
        # liye koi extra query bhi nahi chalti aur data bhi nahi
        # banta (safe by default — kisi galti se bhi employee ko
        # ye data nahi mil sakta).
        if request.user.role == 'distributor':
            today = date.today()
            start_date = today - timedelta(days=29)  # pichle 30 din (aaj samet)

            sales_by_date = {
                row['sale_date']: float(row['total'] or 0)
                for row in (
                    Sale.objects.filter(
                        distributor=distributor,
                        sale_date__gte=start_date
                    )
                    .values('sale_date')
                    .annotate(total=Sum('total_price'))
                )
            }
            purchases_by_date = {
                row['purchase_date']: float(row['total'] or 0)
                for row in (
                    Purchase.objects.filter(
                        distributor=distributor,
                        purchase_date__gte=start_date
                    )
                    .values('purchase_date')
                    .annotate(total=Sum('purchase_price'))
                )
            }

            labels = []
            sales_series = []
            purchases_series = []
            profit_series = []

            for i in range(30):
                d = start_date + timedelta(days=i)
                labels.append(d.strftime('%d %b'))
                s = sales_by_date.get(d, 0)
                p = purchases_by_date.get(d, 0)
                sales_series.append(s)
                purchases_series.append(p)
                profit_series.append(round(s - p, 2))

            context['chart_labels'] = json.dumps(labels)
            context['chart_sales'] = json.dumps(sales_series)
            context['chart_purchases'] = json.dumps(purchases_series)
            context['chart_profit'] = json.dumps(profit_series)

    except Exception:
        pass

    return render(request, 'users/dashboard.html', context)


@login_required
def superadmin_dashboard(request):

    if request.user.role != 'superadmin':
        return redirect('dashboard')

    from .models import Distributor

    distributors = Distributor.objects.all()

    return render(
        request,
        'users/superadmin_dashboard.html',
        {'distributors': distributors}
    )
   
@login_required
def add_distributor(request):
    if request.method == 'POST':
        from .models import User, Distributor
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        name = request.POST['name']
        phone = request.POST['phone']

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists!')
            return redirect('add_distributor')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role='distributor'
        )
        Distributor.objects.create(
            user=user,
            name=name,
            phone=phone,
            status='active'
        )
        messages.success(request, f'Distributor {name} created!')
        return redirect('superadmin_dashboard')

    return render(request, 'users/add_distributor.html')


@login_required
def suspend_distributor(request, dist_id):
    from .models import Distributor
    dist = Distributor.objects.get(id=dist_id)
    dist.status = 'suspended'
    dist.save()
    dist.user.is_active = False
    dist.user.save()
    messages.success(request, f'{dist.name} suspended!')
    return redirect('superadmin_dashboard')


@login_required
def activate_distributor(request, dist_id):
    from .models import Distributor
    dist = Distributor.objects.get(id=dist_id)
    dist.status = 'active'
    dist.save()
    dist.user.is_active = True
    dist.user.save()
    messages.success(request, f'{dist.name} activated!')
    return redirect('superadmin_dashboard')


@login_required
def manage_employees(request):
    if request.user.role != 'distributor':
        return redirect('dashboard')
    from .models import Employee
    employees = Employee.objects.filter(
        distributor=request.user.distributor
    )
    return render(
        request,
        'users/employees.html',
        {'employees': employees}
    )


@login_required
def add_employee(request):
    if request.user.role != 'distributor':
        return redirect('dashboard')

    if request.method == 'POST':
        from .models import User, Employee
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        name = request.POST['name']
        privileges = request.POST.get('privileges', '')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists!')
            return redirect('add_employee')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role='employee'
        )
        Employee.objects.create(
            user=user,
            distributor=request.user.distributor,
            name=name,
            privileges=privileges,
            is_active=True
        )
        messages.success(request, f'Employee {name} created!')
        return redirect('manage_employees')

    return render(request, 'users/add_employee.html')