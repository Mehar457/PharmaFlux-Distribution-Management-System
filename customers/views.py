from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Customer


def get_distributor(request):
    if request.user.role == 'distributor':
        return request.user.distributor
    elif request.user.role == 'employee':
        return request.user.employee.distributor
    return None


@login_required
def customer_list(request):
    distributor = get_distributor(request)
    customers = Customer.objects.filter(
        distributor=distributor
    ).order_by('name')

    search = request.GET.get('search', '')
    if search:
        customers = customers.filter(
            name__icontains=search
        )

    return render(request, 'customers/list.html', {
        'customers': customers,
        'search': search,
    })


@login_required
def add_customer(request):
    distributor = get_distributor(request)

    if request.method == 'POST':
        Customer.objects.create(
            distributor=distributor,
            name=request.POST['name'],
            type=request.POST['type'],
            contact=request.POST['contact'],
            email=request.POST.get('email', ''),
            address=request.POST.get('address', ''),
            whatsapp_number=request.POST.get('whatsapp_number', '')
        )
        messages.success(request, 'Customer added successfully!')
        return redirect('customer_list')

    return render(request, 'customers/add.html')


@login_required
def edit_customer(request, customer_id):
    customer = Customer.objects.get(id=customer_id)

    if request.method == 'POST':
        customer.name = request.POST['name']
        customer.type = request.POST['type']
        customer.contact = request.POST['contact']
        customer.email = request.POST.get('email', '')
        customer.address = request.POST.get('address', '')
        customer.whatsapp_number = request.POST.get('whatsapp_number', '')
        customer.save()
        messages.success(request, 'Customer updated!')
        return redirect('customer_list')

    return render(request, 'customers/edit.html', {'customer': customer})


@login_required
def delete_customer(request, customer_id):
    customer = Customer.objects.get(id=customer_id)
    customer.delete()
    messages.success(request, 'Customer deleted!')
    return redirect('customer_list')