"""
Email Templates — personalized outreach messages for business development.
Generates email and WhatsApp content for approaching potential clients.
"""

from datetime import datetime


def generate_outreach_email(
    business_name: str,
    demo_url: str = "",
    business_type: str = "general",
    sender_name: str = "Kaihara",
    sender_phone: str = "",
) -> dict:
    """Generate a personalized outreach email.

    Returns dict with 'subject' and 'body' keys.
    """
    subject = f"Laman Web Percuma untuk {business_name}"

    body = f"""Bismillahirrahmanirrahim,

Assalamualaikum dan salam sejahtera,

Saya {sender_name} dari KAIHARA Digital.

Saya terjumpa {business_name} semasa saya membuat carian dalam talian. Saya perasan bahawa{business_name} belum mempunyai laman web sendiri.

Oleh itu, saya telah buatkan DEMO laman web percuma untuk {business_name}:

🔗 Demo: {demo_url}

Laman web ini termasuk:
✅ Reka bentuk profesional dan moden
✅ Responsive (sesuai untuk mobile & desktop)
✅ Maklumat hubungan & lokasi
✅ Senarai servis/menu
✅联系 form untuk pelanggan

Saya boleh sesuaikan laman web ini mengikut keperluan {business_name}. Jika berminat, boleh hubungi saya:

📞 {sender_phone or "Hubungi saya untuk maklumat lanjut"}

Sekian, terima kasih.

Salam hormat,
{sender_name}
KAIHARA Digital"""

    return {"subject": subject, "body": body}


def generate_whatsapp_message(
    business_name: str,
    demo_url: str = "",
    business_type: str = "general",
    sender_name: str = "Kaihara",
) -> dict:
    """Generate a WhatsApp outreach message.

    Returns dict with 'message' key.
    """
    message = f"""Hai {business_name}! 👋

Saya {sender_name} dari KAIHARA Digital.

Saya nampak {business_name} belum ada website lagi. Jadi saya buatkan demo website percuma untuk you!

🔗 {demo_url}

Website ni:
✅ Design profesional
✅ Boleh buka kat phone & laptop
✅ Ada contact form
✅Senarai servis/menu

Nak tukar-tukar sikit? Boleh je. Nak full website? Boleh discuss.

Boleh reply mesej ni kalau berminat ya! 😊"""

    return {"message": message}


def generate_followup_email(
    business_name: str,
    sender_name: str = "Kaihara",
) -> dict:
    """Generate a follow-up email after no response."""
    subject = f"Follow-up: Laman Web untuk {business_name}"

    body = f"""Bismillahirrahmanirrahim,

Assalamualaikum,

Saya {sender_name} dari KAIHARA Digital.

Saya telah menghantar e-mel sebelum ini berkenaan laman web percuma untuk {business_name}. 

Saya pasti anda sibuk, jadi saya follow up sekali lagi.

Jika anda berminat, saya boleh:
1. Tunjuk demo laman web yang telah saya buat
2. Sesuaikan mengikut keperluan {business_name}
3. Setup domain & hosting untuk anda

Boleh hubungi saya bila-bila masa.

Salam hormat,
{sender_name}
KAIHARA Digital"""

    return {"subject": subject, "body": body}


def generate_proposal_email(
    business_name: str,
    features: list[str] = None,
    price: str = "RM 2,500",
    sender_name: str = "Kaihara",
) -> dict:
    """Generate a pricing proposal email."""
    features = features or ["Laman web 5 muka surat", "Responsive design", "Contact form", "SEO basics", "1 tahun hosting"]

    features_text = "\n".join(f"✅ {f}" for f in features)

    subject = f"Tawaran Harga: Laman Web {business_name}"

    body = f"""Bismillahirrahmanirrahim,

Assalamualaikum,

Saya {sender_name} dari KAIHARA Digital.

Terima kasih kerana berminat dengan laman web untuk {business_name}.

Berikut adalah tawaran harga:

📋 Pakej Laman Web:
{features_text}

💰 Harga: {price}
📊 Termasuk 1 tahun percuma hosting & domain

🔧 Apa yang saya buat:
1. Reka bentuk profesional mengikut brand {business_name}
2. Responsive design (mobile & desktop)
3. Contact form & location map
4. SEO optimization asas
5. Setup domain & hosting

Jika berminat, boleh reply e-mel ini atau hubungi saya.

Salam hormat,
{sender_name}
KAIHARA Digital"""

    return {"subject": subject, "body": body}
