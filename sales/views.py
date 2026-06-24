from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Sale, Invoice
from orders.models import Order, OrderItem
from stock.models import Stock
from customers.models import Customer
from decimal import Decimal


def get_distributor(request):
    if request.user.role == 'distributor':
        return request.user.distributor
    elif request.user.role == 'employee':
        return request.user.employee.distributor
    return None


@login_required
def sale_list(request):
    distributor = get_distributor(request)
    sales = Sale.objects.filter(
        distributor=distributor
    ).order_by('-sale_date')

    return render(request, 'sales/list.html', {'sales': sales})


@login_required
def add_sale(request):
    distributor = get_distributor(request)
    customers = Customer.objects.filter(distributor=distributor)
    stocks = Stock.objects.filter(
        distributor=distributor,
        quantity__gt=0
    )

    if request.method == 'POST':
        customer_id = request.POST['customer']
        stock_id = request.POST['stock']
        quantity = int(request.POST['quantity'])
        payment_method = request.POST['payment_method']

        customer = Customer.objects.get(id=customer_id)
        stock = Stock.objects.get(id=stock_id)

        if stock.quantity < quantity:
            messages.error(
                request,
                f'Insufficient stock! Available: {stock.quantity}'
            )
            return redirect('add_sale')

        total_price = stock.unit_price * Decimal(quantity)

        order = Order.objects.create(
            customer=customer,
            distributor=distributor,
            status='confirmed',
            order_type='manual'
        )

        OrderItem.objects.create(
            order=order,
            stock=stock,
            quantity=quantity,
            unit_price=stock.unit_price
        )

        stock.quantity -= quantity
        stock.save()

        sale = Sale.objects.create(
            order=order,
            customer=customer,
            distributor=distributor,
            total_price=total_price,
            payment_method=payment_method
        )

        Invoice.objects.create(
            sale=sale,
            customer=customer,
            total_amount=total_price,
            contact=customer.contact
        )

        messages.success(
            request,
            f'Sale recorded! Invoice generated.'
        )
        return redirect('sale_list')

    return render(request, 'sales/add.html', {
        'customers': customers,
        'stocks': stocks,
    })


@login_required
def view_invoice(request, sale_id):
    sale = Sale.objects.get(id=sale_id)
    invoice = sale.invoice
    items = sale.order.items.all()

    return render(request, 'sales/invoice.html', {
        'sale': sale,
        'invoice': invoice,
        'items': items,
    })