from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Stock
from datetime import date, timedelta
from django.db.models import F


def get_distributor(request):
    if request.user.role == 'distributor':
        return request.user.distributor
    elif request.user.role == 'employee':
        return request.user.employee.distributor
    return None


@login_required
def stock_list(request):
    distributor = get_distributor(request)
    if not distributor:
        return redirect('dashboard')

    stocks = Stock.objects.filter(
        distributor=distributor
    ).order_by('medicine_name')

    search = request.GET.get('search', '')
    if search:
        stocks = stocks.filter(
            medicine_name__icontains=search
        )

    low_stock = Stock.objects.filter(
        distributor=distributor,
        quantity__lte=F('reorder_level')
    )

    expiry_alert = Stock.objects.filter(
        distributor=distributor,
        expiry_date__lte=date.today() + timedelta(days=30)
    )

    return render(request, 'stock/list.html', {
        'stocks': stocks,
        'low_stock': low_stock,
        'expiry_alert': expiry_alert,
        'search': search,
        'today': date.today(),
    })


@login_required
def add_stock(request):
    if request.user.role == 'employee':
        emp = request.user.employee
        if emp.privileges not in [
            'manage_stock', 'full_access'
        ]:
            messages.error(
                request,
                'You do not have permission!'
            )
            return redirect('stock_list')

    distributor = get_distributor(request)

    if request.method == 'POST':
        batch_no = request.POST['batch_no']

        if Stock.objects.filter(
            batch_no=batch_no
        ).exists():
            messages.error(
                request,
                'Batch number already exists!'
            )
            return redirect('add_stock')

        Stock.objects.create(
            distributor=distributor,
            medicine_name=request.POST['medicine_name'],
            batch_no=batch_no,
            quantity=request.POST['quantity'],
            expiry_date=request.POST['expiry_date'],
            unit_price=request.POST['unit_price'],
            reorder_level=request.POST['reorder_level']
        )
        messages.success(
            request,
            'Medicine added successfully!'
        )
        return redirect('stock_list')

    return render(request, 'stock/add.html')


@login_required
def edit_stock(request, stock_id):
    stock = Stock.objects.get(id=stock_id)

    if request.method == 'POST':
        stock.medicine_name = request.POST['medicine_name']
        stock.quantity = request.POST['quantity']
        stock.unit_price = request.POST['unit_price']
        stock.expiry_date = request.POST['expiry_date']
        stock.reorder_level = request.POST['reorder_level']
        stock.save()
        messages.success(
            request,
            'Medicine updated successfully!'
        )
        return redirect('stock_list')

    return render(
        request,
        'stock/edit.html',
        {'stock': stock}
    )


@login_required
def delete_stock(request, stock_id):
    stock = Stock.objects.get(id=stock_id)
    stock.delete()
    messages.success(
        request,
        'Medicine deleted!'
    )
    return redirect('stock_list')