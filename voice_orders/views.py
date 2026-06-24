from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.conf import settings
from .models import VoiceOrder
from orders.models import Order, OrderItem
from customers.models import Customer
from stock.models import Stock
from sales.models import Sale, Invoice
import json
import re
import requests as http_requests


def get_distributor(request):
    if request.user.role == 'distributor':
        return request.user.distributor
    elif request.user.role == 'employee':
        return request.user.employee.distributor
    return None


# ── Meta WhatsApp Webhook ────────────────────
@csrf_exempt
def whatsapp_webhook(request):

    # Meta verification (GET request)
    if request.method == 'GET':
        mode = request.GET.get('hub.mode', '')
        verify_token = request.GET.get('hub.verify_token', '')
        challenge = request.GET.get('hub.challenge', '')

        if mode == 'subscribe' and verify_token == 'pharmaflux123':
            return HttpResponse(challenge, status=200)
        return HttpResponse('Forbidden', status=403)

    # Message receive karo (POST request)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print("=== WEBHOOK HIT ===")
            print(data)

            entry = data['entry'][0]
            changes = entry['changes'][0]
            value = changes['value']

            if 'messages' in value:
                message_data = value['messages'][0]
                from_number = message_data['from']
                incoming_msg = None

                # ── TEXT MESSAGE ──
                if message_data['type'] == 'text':
                    incoming_msg = message_data['text']['body']
                    print(f"TEXT RECEIVED: {incoming_msg}")

                # ── VOICE / AUDIO MESSAGE ──
                elif message_data['type'] == 'audio':
                    audio_id = message_data['audio']['id']
                    print(f"AUDIO RECEIVED, id: {audio_id}")
                    incoming_msg = process_voice_audio(audio_id)
                    print(f"TRANSCRIBED TEXT: {incoming_msg}")

                if incoming_msg:
                    medicines = extract_medicines(incoming_msg, 1)
                    if medicines:
                        create_draft_order(
                            incoming_msg, medicines, from_number, 1
                        )
                        print("DRAFT ORDER CREATED")
                    else:
                        print("NO MEDICINES FOUND IN MESSAGE")
                else:
                    print("NO MESSAGE TEXT EXTRACTED")

        except Exception as e:
            print(f"Webhook Error: {e}")

        return HttpResponse('OK', status=200)

    return HttpResponse('Method not allowed', status=405)


# ── Voice Audio Ko Text Mein Convert Karo ────
def process_voice_audio(audio_id):
    """
    Meta se audio file download karke
    Whisper se text mein convert karta hai
    """
    try:
        access_token = settings.META_ACCESS_TOKEN

        # Step 1: Media URL nikalo Meta se
        url_response = http_requests.get(
            f"https://graph.facebook.com/v19.0/{audio_id}",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        media_url = url_response.json().get('url')

        if not media_url:
            print("Could not get media URL")
            print(url_response.json())
            return None

        # Step 2: Actual audio file download karo
        audio_response = http_requests.get(
            media_url,
            headers={"Authorization": f"Bearer {access_token}"}
        )

        audio_path = 'temp_voice.ogg'
        with open(audio_path, 'wb') as f:
            f.write(audio_response.content)

        # Step 3: Whisper se speech to text karo
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(audio_path)
        text = result["text"]

        print(f"Whisper transcription: {text}")
        return text

    except Exception as e:
        print(f"Voice processing error: {e}")
        return None


# ── Zapier Webhook (Backup Option) ───────────
@csrf_exempt
def zapier_webhook(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message = data.get('message', '')
            phone = data.get('phone', '')
            distributor_id = data.get('distributor_id', 1)

            medicines = extract_medicines(message, distributor_id)

            if medicines:
                order = create_draft_order(
                    message, medicines, phone, distributor_id
                )
                return JsonResponse({
                    'status': 'success',
                    'order_id': order.id
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No medicines found'
                })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })

    return JsonResponse({'status': 'ok'})


# ── NLP Medicine Extract ─────────────────────
def extract_medicines(text, distributor_id):
    found = []
    all_medicines = Stock.objects.filter(
        distributor_id=distributor_id
    )
    text_lower = text.lower()

    for medicine in all_medicines:
        name = medicine.medicine_name.lower()
        if name in text_lower:
            quantity = extract_quantity(text_lower, name)
            found.append({
                'stock': medicine,
                'quantity': quantity
            })
    return found


def extract_quantity(text, medicine_name):
    pattern1 = r'(\d+)\s*' + re.escape(medicine_name)
    match1 = re.search(pattern1, text)
    if match1:
        return int(match1.group(1))

    pattern2 = re.escape(medicine_name) + r'\s*(\d+)'
    match2 = re.search(pattern2, text)
    if match2:
        return int(match2.group(1))

    return 1


# ── Create Draft Order ───────────────────────
def create_draft_order(text, medicines, phone, distributor_id):
    from users.models import Distributor
    distributor = Distributor.objects.get(id=distributor_id)

    customer = Customer.objects.filter(
        distributor=distributor,
        whatsapp_number=phone
    ).first()

    if not customer:
        customer = Customer.objects.filter(
            distributor=distributor
        ).first()

    order = Order.objects.create(
        customer=customer,
        distributor=distributor,
        status='draft',
        order_type='voice'
    )

    for item in medicines:
        OrderItem.objects.create(
            order=order,
            stock=item['stock'],
            quantity=item['quantity'],
            unit_price=item['stock'].unit_price
        )

    VoiceOrder.objects.create(
        order=order,
        distributor=distributor,
        voice_input=text,
        converted_text=text,
        status='draft'
    )

    return order


# ── Voice Orders List ────────────────────────
@login_required
def voice_orders_list(request):
    distributor = get_distributor(request)
    voice_orders = VoiceOrder.objects.filter(
        distributor=distributor
    ).order_by('-created_at')

    return render(
        request,
        'voice_orders/list.html',
        {'voice_orders': voice_orders}
    )


# ── Manual Voice Order Create ────────────────
@login_required
def create_manual_voice_order(request):
    distributor = get_distributor(request)
    customers = Customer.objects.filter(distributor=distributor)

    if request.method == 'POST':
        message = request.POST['message']
        customer_id = request.POST['customer']
        customer = Customer.objects.get(id=customer_id)

        medicines = extract_medicines(message, distributor.id)

        if not medicines:
            messages.error(
                request,
                'No medicines found! Check medicine names.'
            )
            return redirect('create_manual_voice_order')

        order = Order.objects.create(
            customer=customer,
            distributor=distributor,
            status='draft',
            order_type='voice'
        )

        for item in medicines:
            OrderItem.objects.create(
                order=order,
                stock=item['stock'],
                quantity=item['quantity'],
                unit_price=item['stock'].unit_price
            )

        VoiceOrder.objects.create(
            order=order,
            distributor=distributor,
            voice_input=message,
            converted_text=message,
            status='draft'
        )

        messages.success(request, 'Draft order created!')
        return redirect('voice_orders_list')

    return render(
        request,
        'voice_orders/create.html',
        {'customers': customers}
    )


# ── Confirm Order ────────────────────────────
@login_required
def confirm_order(request, voice_order_id):
    voice_order = VoiceOrder.objects.get(id=voice_order_id)
    order = voice_order.order

    for item in order.items.all():
        if item.stock.quantity < item.quantity:
            messages.error(
                request,
                f'Insufficient stock for {item.stock.medicine_name}!'
            )
            return redirect('voice_orders_list')

    total_price = sum(
        item.unit_price * item.quantity
        for item in order.items.all()
    )

    for item in order.items.all():
        item.stock.quantity -= item.quantity
        item.stock.save()

    sale = Sale.objects.create(
        order=order,
        customer=order.customer,
        distributor=order.distributor,
        total_price=total_price,
        payment_method='cash'
    )

    Invoice.objects.create(
        sale=sale,
        customer=order.customer,
        total_amount=total_price,
        contact=order.customer.contact
    )

    order.status = 'confirmed'
    order.save()
    voice_order.status = 'confirmed'
    voice_order.save()

    messages.success(request, 'Order confirmed! Invoice generated.')
    return redirect('voice_orders_list')


# ── Cancel Order ─────────────────────────────
@login_required
def cancel_order(request, voice_order_id):
    voice_order = VoiceOrder.objects.get(id=voice_order_id)
    voice_order.order.status = 'cancelled'
    voice_order.order.save()
    voice_order.status = 'cancelled'
    voice_order.save()

    messages.success(request, 'Order cancelled!')
    return redirect('voice_orders_list')