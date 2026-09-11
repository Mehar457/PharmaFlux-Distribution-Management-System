from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.conf import settings
from django.utils import timezone as dj_timezone
from django.utils.dateparse import parse_datetime
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

    if request.method == 'GET':
        mode = request.GET.get('hub.mode', '')
        verify_token = request.GET.get('hub.verify_token', '')
        challenge = request.GET.get('hub.challenge', '')
        if mode == 'subscribe' and verify_token == 'pharmaflux123':
            return HttpResponse(challenge, status=200)
        return HttpResponse('Forbidden', status=403)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print("=== WEBHOOK HIT ===")

            entry = data['entry'][0]
            changes = entry['changes'][0]
            value = changes['value']

            if 'messages' in value:
                message_data = value['messages'][0]
                from_number = message_data['from']
                print(f"FROM NUMBER: {from_number}")
                incoming_msg = None

                if message_data['type'] == 'text':
                    incoming_msg = message_data['text']['body']
                    print(f"TEXT: {incoming_msg}")

                elif message_data['type'] == 'audio':
                    audio_id = message_data['audio']['id']
                    print(f"AUDIO RECEIVED, id: {audio_id}")
                    incoming_msg = process_voice_audio(audio_id)
                    print(f"TRANSCRIBED: {incoming_msg}")

                if incoming_msg:
                    medicines, hints = extract_medicines(incoming_msg, 1)
                    # Order ab HAMESHA banega — chahe kuch match ho ya
                    # na ho — taake koi bhi customer message chup-chap
                    # gayab na ho. Agar kuch match nahi hua ya kuch
                    # hissa samajh nahi aaya, VoiceOrder mein warning
                    # note save ho jaata hai (neeche create_draft_order
                    # mein).
                    create_draft_order(
                        incoming_msg, medicines, from_number, 1,
                        unmatched_hints=hints
                    )
                    print(f"DRAFT ORDER CREATED (matched: {len(medicines)}, unmatched hints: {hints})")
                else:
                    print("NO MESSAGE TEXT EXTRACTED")

        except Exception as e:
            print(f"Webhook Error: {e}")

        return HttpResponse('OK', status=200)

    return HttpResponse('Method not allowed', status=405)


# ── Voice Audio Process ──────────────────────
def process_voice_audio(audio_id):
    try:
        import speech_recognition as sr
        from pydub import AudioSegment
        import os

        access_token = settings.META_ACCESS_TOKEN

        url_response = http_requests.get(
            f"https://graph.facebook.com/v19.0/{audio_id}",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        print(f"URL Response: {url_response.json()}")
        media_url = url_response.json().get('url')

        if not media_url:
            print("Could not get media URL")
            return None

        audio_response = http_requests.get(
            media_url,
            headers={"Authorization": f"Bearer {access_token}"}
        )

        ogg_path = 'temp_voice.ogg'
        wav_path = 'temp_voice.wav'

        with open(ogg_path, 'wb') as f:
            f.write(audio_response.content)

        print(f"Audio downloaded: {len(audio_response.content)} bytes")

        audio_segment = AudioSegment.from_ogg(ogg_path)
        audio_segment.export(wav_path, format='wav')
        print("Converted to WAV")

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)

        text = recognizer.recognize_google(audio_data, language='en-US')
        print(f"Recognized text: {text}")

        if os.path.exists(ogg_path):
            os.remove(ogg_path)
        if os.path.exists(wav_path):
            os.remove(wav_path)

        return text

    except Exception as e:
        print(f"Voice processing error: {e}")
        return None


# ── Quantity Helpers (word-numbers + filler-word-aware search) ──
NUMBER_WORDS = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
    'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18,
    'nineteen': 19, 'twenty': 20, 'thirty': 30, 'forty': 40,
    'fifty': 50, 'sixty': 60, 'seventy': 70, 'eighty': 80,
    'ninety': 90, 'hundred': 100
}
FILLER = {'of', 'the', 'a', 'an', 'packets', 'packet', 'tablets', 'tablet',
          'strips', 'strip', 'boxes', 'box', 'pcs'}

# Common command/filler words jo medicine name nahi ho saktay — inko
# "unmatched hint" mein ignore kiya jaata hai taake sirf asal ajeeb
# (samajh na aane waale) words hi flag hon, "give me order" jaisay
# aam alfaaz nahi.
STOPWORDS = {
    'give', 'me', 'my', 'order', 'and', 'please', 'track', 'want',
    'need', 'buy', 'send', 'for', 'to', 'on', 'in', 'is', 'are',
    'i', 'would', 'like', 'kindly', 'plz', 'get', 'mujhe', 'chahiye'
}


def word_to_qty(word):
    """Digit string ('10') ya number-word ('ten') ko int mein convert
    karta hai. Match na ho to None."""
    word = word.lower().strip()
    if word.isdigit():
        return int(word)
    return NUMBER_WORDS.get(word)


def find_qty_nearby(words, start, end, window=3):
    """Medicine ke word-span (start..end) ke ird-gird quantity dhoondhta
    hai — filler words ('of', 'packets', 'tablets' etc.) ko skip karte
    hue. Pehle peeche dekhta hai, phir aage. Kuch na mile to 1."""
    for i in range(start - 1, max(start - 1 - window, -1), -1):
        if words[i] in FILLER:
            continue
        q = word_to_qty(words[i])
        if q is not None:
            return q
        break  # non-filler, non-number word aaya -> ruk jao
    for i in range(end, min(end + window, len(words))):
        if words[i] in FILLER:
            continue
        q = word_to_qty(words[i])
        if q is not None:
            return q
        break
    return 1


def find_unmatched_hints(words, used_word_indices):
    """Jo words kisi bhi Stock medicine se match nahi huye AUR filler/
    stopword/number bhi nahi hain, unko group kar ke wapas karta hai —
    taake distributor ko dikh sake 'ye hissa samajh nahi aaya', chup-
    chap gayab hone ke bajaye."""
    leftover_idx = [
        i for i in range(len(words))
        if i not in used_word_indices
        and words[i] not in STOPWORDS
        and words[i] not in FILLER
        and word_to_qty(words[i]) is None
    ]
    if not leftover_idx:
        return []

    groups = []
    current = [leftover_idx[0]]
    for idx in leftover_idx[1:]:
        if idx == current[-1] + 1:
            current.append(idx)
        else:
            groups.append(current)
            current = [idx]
    groups.append(current)

    return [' '.join(words[i] for i in g) for g in groups]


# ── Simple Similarity Check ──────────────────
def similarity_score(word1, word2):
    """
    Simple similarity — kitne characters same hain
    No external library needed
    """
    w1 = word1.lower().strip()
    w2 = word2.lower().strip()

    if w1 == w2:
        return 100

    # Common prefix length
    prefix = 0
    for a, b in zip(w1, w2):
        if a == b:
            prefix += 1
        else:
            break

    # Score based on prefix and length
    max_len = max(len(w1), len(w2))
    if max_len == 0:
        return 0

    score = (prefix / max_len) * 100

    # Bonus if one contains the other — SIRF tab jab dono words kaafi
    # lambe hon, warna chhote words ('me', 'of', 'to') kisi bhi lambe
    # medicine-name ke andar false-match ho jaate hain (e.g. 'me' is
    # a substring of 'augmentin').
    shorter = min(len(w1), len(w2))
    if shorter >= 4 and (w1 in w2 or w2 in w1):
        score = max(score, 75)

    return score


# ── NLP Medicine Extract ─────────────────────
def extract_medicines(text, distributor_id):
    found = []

    # Longest name pehle (Dicloran SR before Dicloran)
    all_medicines = sorted(
        Stock.objects.filter(distributor_id=distributor_id),
        key=lambda m: len(m.medicine_name),
        reverse=True
    )

    text_lower = text.lower()
    words = text_lower.split()
    used_word_indices = set()

    print(f"Checking text: {text_lower}")
    print(f"Words: {words}")

    for medicine in all_medicines:
        med_name = medicine.medicine_name.lower()
        med_words = med_name.split()
        n = len(med_words)

        best_score = 0
        best_start = -1

        for i in range(len(words) - n + 1):
            # Skip already used words
            if any(j in used_word_indices for j in range(i, i + n)):
                continue

            # Comparing word
            phrase_words = words[i:i + n]
            scores = []
            for mw, pw in zip(med_words, phrase_words):
                scores.append(similarity_score(mw, pw))

            avg_score = sum(scores) / len(scores)

            if avg_score > best_score:
                best_score = avg_score
                best_start = i

        print(f"Medicine: {medicine.medicine_name}, Best score: {best_score:.1f}%")
        if best_score >= 65 and best_start >= 0:
            quantity = find_qty_nearby(words, best_start, best_start + n)

            # Pattern matching (digit-adjacent-to-name — extra fallback,
            # e.g. "Augmentin 100" where the digit sits right after the
            # name with no filler word in between)
            q = extract_quantity(text_lower, med_name)
            if q > 1:
                quantity = q

            print(f"  → MATCHED! Qty: {quantity}")

            found.append({
                'stock': medicine,
                'quantity': quantity
            })

            # Mark words as used
            for j in range(best_start, best_start + n):
                used_word_indices.add(j)

    hints = find_unmatched_hints(words, used_word_indices)
    return found, hints


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
def create_draft_order(text, medicines, phone, distributor_id, unmatched_hints=None):
    from users.models import Distributor
    distributor = Distributor.objects.get(id=distributor_id)

    clean_phone = phone.replace('+', '').strip()
    print(f"Looking for customer: {clean_phone}")

    # Exact match
    customer = Customer.objects.filter(
        distributor=distributor,
        whatsapp_number=clean_phone
    ).first()

    # Last 10 digits match
    if not customer:
        last_10 = clean_phone[-10:]
        for c in Customer.objects.filter(distributor=distributor):
            saved = c.whatsapp_number.replace(
                '+', ''
            ).replace('-', '').replace(' ', '')
            if saved.endswith(last_10):
                customer = c
                print(f"Matched customer: {c.name}")
                break

    # Auto create if not found
    if not customer:
        customer = Customer.objects.create(
            distributor=distributor,
            name=f"WhatsApp ({clean_phone})",
            contact=clean_phone,
            whatsapp_number=clean_phone,
            type='Unknown',
            address='',
            email=''
        )
        print(f"New customer created: {customer.name}")

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

    # ── Warning note banayein agar kuch match nahi hua, kuch hissa
    # samajh nahi aaya, YA kisi medicine ka stock kam/khatam hai —
    # taake distributor ko confirm karne se PEHLE hi pata chal jaye,
    # confirm button dabane ke baad achanak block na ho ──
    note_parts = []
    if not medicines:
        note_parts.append("⚠ Koi bhi medicine Stock se match nahi hui — manual review zaroori hai")
    if unmatched_hints:
        note_parts.append("⚠ Samajh nahi aaya: " + ', '.join(unmatched_hints))

    stock_warnings = []
    for item in medicines:
        available = item['stock'].quantity
        requested = item['quantity']
        if available <= 0:
            stock_warnings.append(f"{item['stock'].medicine_name} OUT OF STOCK (0 available)")
        elif requested > available:
            stock_warnings.append(
                f"{item['stock'].medicine_name}: sirf {available} available, {requested} manga gaya"
            )
    if stock_warnings:
        note_parts.append("⚠ Stock kam hai: " + '; '.join(stock_warnings))

    # converted_text mein sirf warnings rakhte hain (raw text dobara
    # nahi likhते — wo pehle se hi voice_input field mein hai aur
    # "WhatsApp Message" column mein dikhta hai). Agar koi warning
    # nahi hai, converted_text khali rehta hai.
    converted_text = " | ".join(note_parts) if note_parts else ""

    VoiceOrder.objects.create(
        order=order,
        distributor=distributor,
        voice_input=text,
        converted_text=converted_text,
        status='draft'
    )

    return order


# ── Zapier Webhook ───────────────────────────
@csrf_exempt
def zapier_webhook(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message = data.get('message', '')
            phone = data.get('phone', '')
            distributor_id = data.get('distributor_id', 1)

            medicines, hints = extract_medicines(message, distributor_id)

            order = create_draft_order(
                message, medicines, phone, distributor_id,
                unmatched_hints=hints
            )
            status = 'success' if medicines else 'needs_review'
            return JsonResponse({
                'status': status,
                'order_id': order.id,
                'matched_count': len(medicines),
                'unmatched_hints': hints
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'ok'})


# ── Voice Orders List ────────────────────────
@login_required
def voice_orders_list(request):
    distributor = get_distributor(request)
    voice_orders = VoiceOrder.objects.filter(
        distributor=distributor
    ).order_by('-created_at')

    return render(request, 'voice_orders/list.html', {'voice_orders': voice_orders})


# ── Manual Voice Order (REDESIGNED: proper stock fields + order date + discount) ──
@login_required
def create_manual_voice_order(request):
    distributor = get_distributor(request)
    customers = Customer.objects.filter(distributor=distributor)
    stock_items = Stock.objects.filter(distributor=distributor).order_by('medicine_name')

    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        medicine_ids = request.POST.getlist('medicine_id[]')
        quantities = request.POST.getlist('quantity[]')
        order_date_raw = request.POST.get('order_date')  # optional, from datetime-local input
        discount_raw = request.POST.get('discount', '0')  # optional, defaults to 0 (no discount)

        if not customer_id:
            messages.error(request, 'Please select a customer.')
            return redirect('create_manual_voice_order')

        if not medicine_ids:
            messages.error(request, 'Please add at least one medicine.')
            return redirect('create_manual_voice_order')

        customer = Customer.objects.get(id=customer_id)

        # ── Order date: agar distributor ne nahi diya, "abhi" use hoga ──
        order_date = dj_timezone.now()
        if order_date_raw:
            parsed = parse_datetime(order_date_raw)
            if parsed:
                if dj_timezone.is_naive(parsed):
                    parsed = dj_timezone.make_aware(parsed)
                order_date = parsed
            else:
                messages.error(request, 'Invalid order date format.')
                return redirect('create_manual_voice_order')

        # ── Discount: optional — har order ke liye distributor ki apni choice ──
        try:
            discount = float(discount_raw) if discount_raw else 0
            if discount < 0:
                raise ValueError
        except ValueError:
            messages.error(request, 'Discount must be a valid non-negative number.')
            return redirect('create_manual_voice_order')

        # ── Validate every medicine row first (no partial orders) ──
        cleaned_items = []
        errors = []

        for med_id, qty_raw in zip(medicine_ids, quantities):
            if not med_id or not qty_raw:
                continue

            try:
                stock = Stock.objects.get(id=med_id, distributor=distributor)
            except Stock.DoesNotExist:
                errors.append('Selected medicine not found in stock.')
                continue

            try:
                qty = int(qty_raw)
            except ValueError:
                errors.append(f'Invalid quantity for {stock.medicine_name}.')
                continue

            if qty <= 0:
                errors.append(f'Quantity for {stock.medicine_name} must be greater than 0.')
                continue

            if stock.quantity <= 0:
                errors.append(f'{stock.medicine_name} is OUT OF STOCK.')
                continue

            if qty > stock.quantity:
                errors.append(
                    f'{stock.medicine_name}: only {stock.quantity} available, '
                    f'you requested {qty}.'
                )
                continue

            cleaned_items.append({'stock': stock, 'quantity': qty})

        if errors:
            for e in errors:
                messages.error(request, e)
            return redirect('create_manual_voice_order')

        if not cleaned_items:
            messages.error(request, 'No valid medicines to order.')
            return redirect('create_manual_voice_order')

        subtotal = sum(item['stock'].unit_price * item['quantity'] for item in cleaned_items)
        if discount > subtotal:
            messages.error(request, f'Discount ({discount}) cannot exceed order subtotal ({subtotal}).')
            return redirect('create_manual_voice_order')

        # ── All good → create order ──
        order = Order.objects.create(
            customer=customer,
            distributor=distributor,
            status='draft',
            order_type='voice',
            order_date=order_date,
            discount=discount
        )

        summary_lines = []
        for item in cleaned_items:
            OrderItem.objects.create(
                order=order,
                stock=item['stock'],
                quantity=item['quantity'],
                unit_price=item['stock'].unit_price
            )
            summary_lines.append(f"{item['stock'].medicine_name} x{item['quantity']}")

        VoiceOrder.objects.create(
            order=order,
            distributor=distributor,
            voice_input='Manual entry (form)',
            converted_text=', '.join(summary_lines),
            status='draft'
        )

        messages.success(request, 'Draft order created!')
        return redirect('voice_orders_list')

    return render(request, 'voice_orders/create.html', {
        'customers': customers,
        'stock_items': stock_items,
    })


# ── Confirm Order (UPDATED: discount ab final invoice total mein apply hoti hai) ──
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

    # order.get_total() = sum(item subtotals) - order.discount
    # Agar order par discount nahi di gayi thi (default 0), to ye
    # automatically pura subtotal hi return karta hai — koi extra check
    # nahi lagani padi, har order apni discount value khud carry karta hai.
    total_price = order.get_total()

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