"""
HTML Generator — LLM-powered website HTML generation.
Generates complete, responsive websites from business data.
"""

import json
import logging

logger = logging.getLogger("kaihara.html_generator")


# ============================================================
# Website Templates
# ============================================================

RESTAURANT_TEMPLATE = """
<!DOCTYPE html>
<html lang="ms">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{business_name}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Inter', sans-serif; }}
        h1, h2, h3 {{ font-family: 'Playfair Display', serif; }}
        .hero {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); }}
        .gold {{ color: #d4af37; }}
    </style>
</head>
<body class="bg-gray-50">
    <nav class="bg-white shadow-md fixed w-full z-50">
        <div class="max-w-6xl mx-auto px-4 py-4 flex justify-between items-center">
            <h1 class="text-2xl font-bold gold">{business_name}</h1>
            <div class="space-x-6">
                <a href="#about" class="hover:text-amber-600">Tentang</a>
                <a href="#menu" class="hover:text-amber-600">Menu</a>
                <a href="#contact" class="hover:text-amber-600">Hubungi</a>
            </div>
        </div>
    </nav>

    <section class="hero text-white py-32 mt-16">
        <div class="max-w-6xl mx-auto px-4 text-center">
            <h2 class="text-5xl font-bold mb-4">{business_name}</h2>
            <p class="text-xl text-gray-300 mb-8">Selamat datang ke {business_name}</p>
            <a href="#contact" class="bg-amber-600 hover:bg-amber-700 px-8 py-3 rounded-full text-white font-semibold transition">Buat Tempahan</a>
        </div>
    </section>

    <section id="about" class="py-20">
        <div class="max-w-4xl mx-auto px-4 text-center">
            <h2 class="text-3xl font-bold mb-6">Tentang Kami</h2>
            <p class="text-gray-600 text-lg">{business_name} menyajikan makanan yang lazat dan segar. Kami berkomitmen untuk memberikan pengalaman dining yang terbaik kepada pelanggan kami.</p>
        </div>
    </section>

    <section id="menu" class="py-20 bg-white">
        <div class="max-w-6xl mx-auto px-4">
            <h2 class="text-3xl font-bold text-center mb-12">Menu Pilihan</h2>
            <div class="grid md:grid-cols-3 gap-8">
                <div class="bg-gray-50 rounded-xl p-6 shadow">
                    <h3 class="text-xl font-bold mb-2">Nasi Lemak Spesial</h3>
                    <p class="text-gray-600 mb-4">Nasi lemak dengan ayam rendang, sambal, dan telur.</p>
                    <span class="text-amber-600 font-bold">RM 12.90</span>
                </div>
                <div class="bg-gray-50 rounded-xl p-6 shadow">
                    <h3 class="text-xl font-bold mb-2">Mee Goreng Mamak</h3>
                    <p class="text-gray-600 mb-4">Mee goreng dengan udang, sayur, dan telur.</p>
                    <span class="text-amber-600 font-bold">RM 10.90</span>
                </div>
                <div class="bg-gray-50 rounded-xl p-6 shadow">
                    <h3 class="text-xl font-bold mb-2">Teh Tarik Panas</h3>
                    <p class="text-gray-600 mb-4">Teh tarik yang lembut dan manis.</p>
                    <span class="text-amber-600 font-bold">RM 3.50</span>
                </div>
            </div>
        </div>
    </section>

    <section id="contact" class="py-20 bg-gray-100">
        <div class="max-w-4xl mx-auto px-4">
            <h2 class="text-3xl font-bold text-center mb-12">Hubungi Kami</h2>
            <div class="grid md:grid-cols-2 gap-8">
                <div>
                    <h3 class="text-xl font-bold mb-4">Lokasi</h3>
                    <p class="text-gray-600 mb-2">{address}</p>
                    <p class="text-gray-600 mb-2">{phone}</p>
                </div>
                <div>
                    <h3 class="text-xl font-bold mb-4">Waktu Operasi</h3>
                    <p class="text-gray-600 mb-2">Isnin - Jumaat: 10:00 AM - 10:00 PM</p>
                    <p class="text-gray-600 mb-2">Sabtu - Ahad: 9:00 AM - 11:00 PM</p>
                </div>
            </div>
        </div>
    </section>

    <footer class="bg-gray-900 text-white py-8 text-center">
        <p>&copy; 2026 {business_name}. Hak cipta terpelihara.</p>
    </footer>
</body>
</html>
"""

SALON_TEMPLATE = """
<!DOCTYPE html>
<html lang="ms">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{business_name}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Inter', sans-serif; }}
        h1, h2, h3 {{ font-family: 'Cormorant Garamond', serif; }}
        .hero {{ background: linear-gradient(135deg, #2d1b69 0%, #11998e 100%); }}
    </style>
</head>
<body class="bg-gray-50">
    <nav class="bg-white shadow-md fixed w-full z-50">
        <div class="max-w-6xl mx-auto px-4 py-4 flex justify-between items-center">
            <h1 class="text-2xl font-bold">{business_name}</h1>
            <div class="space-x-6">
                <a href="#services" class="hover:text-purple-600">Servis</a>
                <a href="#gallery" class="hover:text-purple-600">Galeri</a>
                <a href="#contact" class="hover:text-purple-600">Hubungi</a>
            </div>
        </div>
    </nav>

    <section class="hero text-white py-32 mt-16">
        <div class="max-w-6xl mx-auto px-4 text-center">
            <h2 class="text-5xl font-bold mb-4">{business_name}</h2>
            <p class="text-xl text-gray-300 mb-8">Kecantikan anda, keutamaan kami</p>
            <a href="#contact" class="bg-white text-purple-900 px-8 py-3 rounded-full font-semibold hover:bg-gray-100 transition">Buat Janji Temu</a>
        </div>
    </section>

    <section id="services" class="py-20">
        <div class="max-w-6xl mx-auto px-4">
            <h2 class="text-3xl font-bold text-center mb-12">Servis Kami</h2>
            <div class="grid md:grid-cols-3 gap-8">
                <div class="bg-white rounded-xl p-6 shadow-lg text-center">
                    <div class="text-4xl mb-4">✂️</div>
                    <h3 class="text-xl font-bold mb-2">Potong Rambut</h3>
                    <p class="text-gray-600">RM 25 - RM 50</p>
                </div>
                <div class="bg-white rounded-xl p-6 shadow-lg text-center">
                    <div class="text-4xl mb-4">💇</div>
                    <h3 class="text-xl font-bold mb-2">Coloring</h3>
                    <p class="text-gray-600">RM 80 - RM 200</p>
                </div>
                <div class="bg-white rounded-xl p-6 shadow-lg text-center">
                    <div class="text-4xl mb-4">💆</div>
                    <h3 class="text-xl font-bold mb-2">Hair Treatment</h3>
                    <p class="text-gray-600">RM 50 - RM 150</p>
                </div>
            </div>
        </div>
    </section>

    <section id="contact" class="py-20 bg-gray-100">
        <div class="max-w-4xl mx-auto px-4 text-center">
            <h2 class="text-3xl font-bold mb-8">Hubungi Kami</h2>
            <p class="text-gray-600 mb-2">{address}</p>
            <p class="text-gray-600 mb-2">{phone}</p>
            <p class="text-gray-600">Isnin - Ahad: 10:00 AM - 9:00 PM</p>
        </div>
    </section>

    <footer class="bg-gray-900 text-white py-8 text-center">
        <p>&copy; 2026 {business_name}. Hak cipta terpelihara.</p>
    </footer>
</body>
</html>
"""

GENERAL_TEMPLATE = """
<!DOCTYPE html>
<html lang="ms">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{business_name}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Inter', sans-serif; }}
        .hero {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
    </style>
</head>
<body class="bg-gray-50">
    <nav class="bg-white shadow-md fixed w-full z-50">
        <div class="max-w-6xl mx-auto px-4 py-4 flex justify-between items-center">
            <h1 class="text-2xl font-bold">{business_name}</h1>
            <div class="space-x-6">
                <a href="#about" class="hover:text-purple-600">Tentang</a>
                <a href="#services" class="hover:text-purple-600">Servis</a>
                <a href="#contact" class="hover:text-purple-600">Hubungi</a>
            </div>
        </div>
    </nav>

    <section class="hero text-white py-32 mt-16">
        <div class="max-w-6xl mx-auto px-4 text-center">
            <h2 class="text-5xl font-bold mb-4">{business_name}</h2>
            <p class="text-xl text-gray-300 mb-8">Perkhidmatan berkualiti untuk anda</p>
            <a href="#contact" class="bg-white text-purple-900 px-8 py-3 rounded-full font-semibold hover:bg-gray-100 transition">Hubungi Kami</a>
        </div>
    </section>

    <section id="about" class="py-20">
        <div class="max-w-4xl mx-auto px-4 text-center">
            <h2 class="text-3xl font-bold mb-6">Tentang Kami</h2>
            <p class="text-gray-600 text-lg">{business_name} menyediakan perkhidmatan terbaik untuk pelanggan kami. Dengan pengalaman bertahun-tahun, kami komited untuk memberikan kepuasan kepada setiap pelanggan.</p>
        </div>
    </section>

    <section id="services" class="py-20 bg-white">
        <div class="max-w-6xl mx-auto px-4">
            <h2 class="text-3xl font-bold text-center mb-12">Perkhidmatan Kami</h2>
            <div class="grid md:grid-cols-3 gap-8">
                {feature_cards}
            </div>
        </div>
    </section>

    <section id="contact" class="py-20 bg-gray-100">
        <div class="max-w-4xl mx-auto px-4">
            <h2 class="text-3xl font-bold text-center mb-12">Hubungi Kami</h2>
            <div class="grid md:grid-cols-2 gap-8">
                <div>
                    <h3 class="text-xl font-bold mb-4">Lokasi</h3>
                    <p class="text-gray-600 mb-2">{address}</p>
                    <p class="text-gray-600 mb-2">{phone}</p>
                </div>
                <div>
                    <h3 class="text-xl font-bold mb-4">Waktu Operasi</h3>
                    <p class="text-gray-600 mb-2">Isnin - Jumaat: 9:00 AM - 6:00 PM</p>
                    <p class="text-gray-600 mb-2">Sabtu: 9:00 AM - 1:00 PM</p>
                </div>
            </div>
        </div>
    </section>

    <footer class="bg-gray-900 text-white py-8 text-center">
        <p>&copy; 2026 {business_name}. Hak cipta terpelihara.</p>
    </footer>
</body>
</html>
"""


# ============================================================
# Generator Functions
# ============================================================

def generate_website_html(
    business_name: str,
    business_type: str = "general",
    features: list[str] = None,
    phone: str = "",
    email: str = "",
    address: str = "",
    social_media: list[dict] = None,
    is_full_website: bool = False,
) -> str:
    """Generate a complete HTML website for a business.

    Args:
        business_name: Name of the business
        business_type: Type (restaurant, salon, general, etc.)
        features: List of features to include
        phone: Phone number
        email: Email address
        address: Physical address
        social_media: List of social media links
        is_full_website: If True, generates a more complete website

    Returns:
        Complete HTML string
    """
    features = features or []
    social_media = social_media or []

    # Build feature cards for general template
    feature_cards = ""
    for feature in features[:6]:
        feature_cards += f"""
                <div class="bg-gray-50 rounded-xl p-6 shadow">
                    <h3 class="text-xl font-bold mb-2">{feature}</h3>
                    <p class="text-gray-600">Tersedia untuk anda</p>
                </div>"""

    # Choose template based on business type
    template_map = {
        "restaurant": RESTAURANT_TEMPLATE,
        "salon": SALON_TEMPLATE,
    }
    template = template_map.get(business_type, GENERAL_TEMPLATE)

    # Fill template
    html = template.format(
        business_name=business_name,
        address=address or "Alamat belum dikemas kini",
        phone=phone or "Telefon belum dikemas kini",
        feature_cards=feature_cards,
    )

    return html


def generate_quick_landing(
    business_name: str,
    tagline: str = "Perkhidmatan berkualiti",
    cta_text: str = "Hubungi Kami",
    phone: str = "",
) -> str:
    """Generate a quick one-page landing site."""
    return f"""<!DOCTYPE html>
<html lang="ms">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{business_name}</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gradient-to-br from-indigo-600 to-purple-700 min-h-screen flex items-center justify-center">
    <div class="text-center text-white px-4">
        <h1 class="text-5xl font-bold mb-4">{business_name}</h1>
        <p class="text-xl text-gray-200 mb-8">{tagline}</p>
        {"<a href='tel:" + phone + "' class='bg-white text-indigo-700 px-8 py-3 rounded-full font-semibold hover:bg-gray-100 transition inline-block'>" + cta_text + "</a>" if phone else ""}
    </div>
</body>
</html>"""
