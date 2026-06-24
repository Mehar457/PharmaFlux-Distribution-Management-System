from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from sales.models import Sale
from purchases.models import Purchase
from datetime import date


def get_distributor(request):
    if request.user.role == 'distributor':
        return request.user.distributor
    elif request.user.role == 'employee':
        return request.user.employee.distributor
    return None


@login_required
def sale_report(request):
    distributor = get_distributor(request)
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    sales = Sale.objects.filter(distributor=distributor)

    if start_date and end_date:
        sales = sales.filter(
            sale_date__range=[start_date, end_date]
        )

    total = sales.aggregate(
        total=Sum('total_price')
    )['total'] or 0

    return render(request, 'reports/sale_report.html', {
        'sales': sales,
        'total': total,
        'start_date': start_date,
        'end_date': end_date,
    })


@login_required
def purchase_report(request):
    distributor = get_distributor(request)
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    purchases = Purchase.objects.filter(distributor=distributor)

    if start_date and end_date:
        purchases = purchases.filter(
            purchase_date__range=[start_date, end_date]
        )

    total = purchases.aggregate(
        total=Sum('purchase_price')
    )['total'] or 0

    return render(request, 'reports/purchase_report.html', {
        'purchases': purchases,
        'total': total,
        'start_date': start_date,
        'end_date': end_date,
    })


@login_required
def profit_loss_report(request):
    distributor = get_distributor(request)
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    sales = Sale.objects.filter(distributor=distributor)
    purchases = Purchase.objects.filter(distributor=distributor)

    if start_date and end_date:
        sales = sales.filter(
            sale_date__range=[start_date, end_date]
        )
        purchases = purchases.filter(
            purchase_date__range=[start_date, end_date]
        )

    total_sales = sales.aggregate(
        total=Sum('total_price')
    )['total'] or 0

    total_purchases = purchases.aggregate(
        total=Sum('purchase_price')
    )['total'] or 0

    profit_loss = total_sales - total_purchases

    if total_sales > 0:
        margin = round((profit_loss / total_sales) * 100, 2)
    else:
        margin = 0

    return render(request, 'reports/profit_loss.html', {
        'total_sales': total_sales,
        'total_purchases': total_purchases,
        'profit_loss': profit_loss,
        'margin': margin,
        'status': 'Profit' if profit_loss >= 0 else 'Loss',
        'start_date': start_date,
        'end_date': end_date,
    })