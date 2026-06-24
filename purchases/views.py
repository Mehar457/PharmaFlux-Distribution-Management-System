from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Purchase
from stock.models import Stock
from vendors.models import Vendor


def get_distributor(request):
    if request.user.role == 'distributor':
        return request.user.distributor
    elif request.user.role == 'employee':
        return request.user.employee.distributor
    return None


@login_required
def purchase_list(request):
    distributor = get_distributor(request)
    purchases = Purchase.objects.filter(
        distributor=distributor
    ).order_by('-purchase_date')

    return render(request, 'purchases/list.html', {'purchases': purchases})


@login_required
def add_purchase(request):
    distributor = get_distributor(request)
    vendors = Vendor.objects.filter(distributor=distributor)
    stocks = Stock.objects.filter(distributor=distributor)

    if request.method == 'POST':
        vendor_id = request.POST['vendor']
        stock_id = request.POST['stock']
        quantity = int(request.POST['quantity'])
        purchase_price = request.POST['purchase_price']

        vendor = Vendor.objects.get(id=vendor_id)
        stock = Stock.objects.get(id=stock_id)

        Purchase.objects.create(
            distributor=distributor,
            vendor=vendor,
            stock=stock,
            quantity=quantity,
            purchase_price=purchase_price
        )

        stock.quantity += quantity
        stock.save()

        messages.success(
            request,
            f'Purchase recorded! {stock.medicine_name} stock updated.'
        )
        return redirect('purchase_list')

    return render(request, 'purchases/add.html', {
        'vendors': vendors,
        'stocks': stocks,
    })