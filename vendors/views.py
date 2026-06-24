from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Vendor


def get_distributor(request):
    if request.user.role == 'distributor':
        return request.user.distributor
    elif request.user.role == 'employee':
        return request.user.employee.distributor
    return None


@login_required
def vendor_list(request):
    distributor = get_distributor(request)
    vendors = Vendor.objects.filter(
        distributor=distributor
    ).order_by('company_name')

    return render(request, 'vendors/list.html', {'vendors': vendors})


@login_required
def add_vendor(request):
    distributor = get_distributor(request)

    if request.method == 'POST':
        Vendor.objects.create(
            distributor=distributor,
            company_name=request.POST['company_name'],
            contact=request.POST['contact'],
            email=request.POST.get('email', ''),
            address=request.POST.get('address', '')
        )
        messages.success(request, 'Vendor added successfully!')
        return redirect('vendor_list')

    return render(request, 'vendors/add.html')


@login_required
def edit_vendor(request, vendor_id):
    vendor = Vendor.objects.get(id=vendor_id)

    if request.method == 'POST':
        vendor.company_name = request.POST['company_name']
        vendor.contact = request.POST['contact']
        vendor.email = request.POST.get('email', '')
        vendor.address = request.POST.get('address', '')
        vendor.save()
        messages.success(request, 'Vendor updated!')
        return redirect('vendor_list')

    return render(request, 'vendors/edit.html', {'vendor': vendor})


@login_required
def delete_vendor(request, vendor_id):
    vendor = Vendor.objects.get(id=vendor_id)
    vendor.delete()
    messages.success(request, 'Vendor deleted!')
    return redirect('vendor_list')