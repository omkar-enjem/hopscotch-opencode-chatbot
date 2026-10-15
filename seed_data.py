"""Generate mock kids-fashion catalog, orders, FAQs and size chart into SQLite.

Run:  python seed_data.py
"""

from __future__ import annotations

from datetime import timedelta

from app.db import get_session, init_db
from app.models import (  # noqa: F401
    ChildProfile,
    Conversation,
    Faq,
    Message,
    Order,
    Product,
    SizeChart,
    utcnow,
)

PRODUCTS = [
    # (sku, name, category, gender, occasion, style_tags, age_min, age_max, sizes, color, fabric, price, rating, stock, emoji, description)
    ("KF-DR-001", "Rainbow Twirl Party Dress", "Dress", "girl", "party", "twirl,party,birthday,sparkle", 2, 8, "2T,3T,4T,5,6,7", "Multicolor", "Cotton blend", 2490, 4.8, 25, "\U0001F457", "A layered twirl dress with a rainbow tulle underskirt - every little one's birthday favourite."),
    ("KF-DR-002", "Unicorn Dream Layered Dress", "Dress", "girl", "party", "unicorn,twirl,fairy,sparkle", 2, 9, "3T,4T,5,6,7,8", "Lilac", "Chiffon", 2790, 4.7, 18, "\U0001F984", "Soft chiffon layers with an embroidered unicorn and glitter hem."),
    ("KF-DR-003", "Cotton Casual A-Line Frock", "Dress", "girl", "casual", "everyday,breathable,summer", 1, 7, "12-18M,2T,3T,4T,5,6", "Mint", "Pure cotton", 1290, 4.5, 40, "\U0001F338", "Lightweight everyday A-line frock with side pockets and a button back."),
    ("KF-DR-004", "Festive Velvet Gown", "Dress", "girl", "festive", "festive,elegant,velvet,wedding", 3, 10, "4T,5,6,7,8,9,10", "Maroon", "Velvet", 3990, 4.9, 12, "\U0001F380", "A rich velvet gown with gold trim for weddings and festivals."),
    ("KF-SH-001", "Denim Dungaree Set", "Set", "unisex", "casual", "dungaree,denim,everyday,play", 2, 8, "2T,3T,4T,5,6,7", "Blue", "Cotton denim", 2190, 4.6, 30, "\U0001F455", "Classic dungaree with an inner tee - built for playground adventures."),
    ("KF-SH-002", "Striped Cotton T-Shirt Pack (3)", "T-Shirt", "unisex", "casual", "basics,everyday,combo,striped", 1, 10, "12-18M,2T,3T,4T,5,6,7,8", "Assorted", "Pure cotton", 1490, 4.4, 60, "\U0001F454", "Pack of 3 breathable striped tees in soft combed cotton."),
    ("KF-SH-003", "Dinosaur Print Half Sleeve Tee", "T-Shirt", "boy", "casual", "dinosaur,print,play,everyday", 2, 8, "2T,3T,4T,5,6,7", "Green", "Cotton", 890, 4.5, 55, "\U0001F996", "Bold dinosaur print tee that survives endless washes."),
    ("KF-SH-004", "Space Explorer Graphic Tee", "T-Shirt", "boy", "casual", "space,rocket,print,play", 3, 10, "4T,5,6,7,8,9,10", "Navy", "Cotton", 990, 4.3, 42, "\U0001F680", "Glow-in-the-dark rocket graphic for curious little astronauts."),
    ("KF-BT-001", "Cargo Jogger Pants", "Bottom", "boy", "casual", "jogger,cargo,play,stretch", 2, 10, "2T,3T,4T,5,6,7,8,9,10", "Khaki", "Cotton twill", 1390, 4.6, 38, "\U0001F456", "Stretchy cargo joggers with deep pockets and a drawcord waist."),
    ("KF-BT-002", "Ruffled Denim Skirt", "Bottom", "girl", "casual", "denim,skirt,summer,everyday", 2, 8, "2T,3T,4T,5,6,7", "Light blue", "Cotton denim", 1190, 4.4, 26, "\U0001F45A", "A cute ruffle-hem denim skirt with an adjustable waist."),
    ("KF-BT-003", "Pleated School Skirt", "Bottom", "girl", "school", "school,uniform,pleated", 4, 12, "5,6,7,8,9,10,11,12", "Grey", "Poly-cotton", 990, 4.2, 50, "\U0001F392", "Wrinkle-resistant pleated school skirt built for the daily routine."),
    ("KF-BT-004", "School Trousers (Elastic Waist)", "Bottom", "unisex", "school", "school,uniform,trousers", 4, 12, "5,6,7,8,9,10,11,12", "Navy", "Poly-cotton", 1090, 4.3, 48, "\U0001F45E", "Comfortable uniform trousers with an easy elastic waist."),
    ("KF-OW-001", "Hooded Sweatshirt", "Outerwear", "unisex", "casual", "hoodie,warm,winter,everyday", 2, 12, "2T,3T,4T,5,6,7,8,9,10", "Grey melange", "Fleece", 1690, 4.7, 35, "\U0001F9E5", "Cosy fleece-lined hoodie with a kangaroo pocket for winter days."),
    ("KF-OW-002", "Puffer Jacket", "Outerwear", "unisex", "casual", "winter,jacket,warm,puffer", 3, 12, "4T,5,6,7,8,9,10", "Teal", "Polyester fill", 3290, 4.8, 20, "\U0001F9CA", "Lightweight-yet-toasty puffer with a water-resistant shell."),
    ("KF-OW-003", "Knit Cardigan", "Outerwear", "girl", "festive", "knit,cardigan,festive,warm", 2, 9, "2T,3T,4T,5,6,7,8", "Cream", "Acrylic knit", 1590, 4.5, 24, "\U0001F9F6", "Soft knit cardigan with pearl buttons for festive layering."),
    ("KF-ET-001", "Tutu & Leggings Party Set", "Set", "girl", "party", "tutu,party,leggings,birthday,twirl", 1, 6, "12-18M,2T,3T,4T,5", "Blush pink", "Tulle + cotton", 2290, 4.7, 22, "\U0001F388", "A fluffy tutu paired with soft leggings - ready to party."),
    ("KF-ET-002", "Kurta Pyjama Festive Set", "Set", "boy", "festive", "kurta,festive,ethnic,wedding", 2, 10, "2T,3T,4T,5,6,7,8,9,10", "Mustard", "Cotton silk", 2590, 4.6, 28, "\U0001FA94", "A smart kurta-pyjama set with mandarin collar and tonal embroidery."),
    ("KF-ET-003", "Lehenga Choli Set", "Set", "girl", "festive", "lehenga,festive,ethnic,wedding,sparkle", 3, 10, "4T,5,6,7,8,9,10", "Magenta", "Silk blend", 4590, 4.9, 10, "\U0001F483", "A festive lehenga-choli with mirror-work detailing."),
    ("KF-AC-001", "Sunny Day Cotton Cap", "Accessory", "unisex", "casual", "cap,summer,hat,sun", 1, 12, "One size", "Yellow", "Cotton", 490, 4.4, 70, "\U0001F9E2", "A wide-brim cotton cap with UPF-friendly fabric for sunny outings."),
    ("KF-AC-002", "Bunny Socks Pack (5 pairs)", "Accessory", "unisex", "casual", "socks,combo,everyday", 1, 8, "1-2Y,3-4Y,5-6Y,7-8Y", "Assorted", "Cotton", 690, 4.3, 90, "\U0001F9E6", "Five pairs of soft bunny-motif socks with anti-slip soles."),
    ("KF-AC-003", "Birthday Party Hairband Set", "Accessory", "girl", "party", "hairband,party,birthday,sparkle", 1, 9, "One size", "Rose gold", "Satin", 390, 4.5, 65, "\U0001F380", "A sparkly bow hairband set to complete the party look."),
    ("KF-PL-001", "Everyday Cotton Shorts", "Bottom", "unisex", "casual", "shorts,summer,everyday,play", 1, 9, "12-18M,2T,3T,4T,5,6,7,8", "Grey", "Cotton", 790, 4.4, 58, "\U0001FA72", "Easy pull-on shorts with an elastic waist for fuss-free dressing."),
    ("KF-PL-002", "Fleece Pyjama Set", "Set", "unisex", "casual", "pyjama,nightwear,warm,fleece", 2, 10, "2T,3T,4T,5,6,7,8,9,10", "Red", "Fleece", 1490, 4.6, 33, "\U0001F634", "Snug fleece pyjama set for warm, happy bedtimes."),
    ("KF-SW-001", "Bow Party Frock", "Dress", "girl", "party", "bow,party,birthday,sparkle", 1, 6, "12-18M,2T,3T,4T,5", "Coral", "Satin + tulle", 2190, 4.7, 27, "\U0001F380", "A satin bodice with an oversized bow and a flared tulle skirt."),
    ("KF-SW-002", "Smart Waistcoat Set", "Set", "boy", "party", "waistcoat,party,formal,birthday", 2, 9, "2T,3T,4T,5,6,7,8", "Charcoal", "Cotton blend", 2790, 4.8, 19, "\U0001F454", "A dapper waistcoat, shirt and trouser set for little gentlemen."),
    ("KF-SW-003", "Bandhani Print Ethnic Set", "Set", "girl", "festive", "bandhani,ethnic,festive,cotton", 2, 9, "2T,3T,4T,5,6,7,8", "Pink", "Cotton", 1990, 4.5, 25, "\U0001F9E3", "Traditional bandhani print set that keeps little ones cool and festive."),
    ("KF-SW-004", "Sunshine Yellow Romper", "Set", "unisex", "casual", "romper,baby,summer,everyday", 0, 2, "0-6M,6-12M,12-18M,18-24M", "Yellow", "Organic cotton", 1190, 4.6, 44, "\U0001F31E", "A snap-button romper in GOTS-certified organic cotton."),
    ("KF-SW-005", "Kitten Print Nighty", "Dress", "girl", "casual", "nightwear,nighty,print,summer", 2, 8, "2T,3T,4T,5,6,7", "Peach", "Cotton", 890, 4.3, 37, "\U0001F431", "A breezy kitten-print nighty for easy summer nights."),
    ("KF-SW-006", "Truck Print Dungaree", "Set", "boy", "casual", "dungaree,truck,print,play", 1, 6, "12-18M,2T,3T,4T,5", "Blue", "Cotton", 1790, 4.5, 29, "\U0001F69B", "Truck-print dungaree with adjustable straps and snap bottoms."),
    ("KF-SW-007", "Pastel Ruffle Frock", "Dress", "girl", "casual", "ruffle,pastel,summer,everyday", 1, 7, "12-18M,2T,3T,4T,5,6", "Lavender", "Cotton", 1290, 4.4, 34, "\U0001F380", "A soft pastel frock with tiered ruffles for everyday twirling."),
]

FAQ_ITEMS = [
    ("shipping", "Which cities do you deliver to?", "We deliver across Nepal including Kathmandu, Pokhara, Biratnagar, Birgunj, Lalitpur and Bhaktapur. Remote areas may take 1-2 extra days."),
    ("shipping", "How long does delivery take?", "Inside Kathmandu Valley delivery takes 1-3 business days. Elsewhere in Nepal it takes 3-7 business days depending on location."),
    ("shipping", "Do you offer free shipping?", "Orders above NPR 3,000 enjoy free standard shipping. Below that, a flat NPR 150 delivery fee applies."),
    ("shipping", "Do you ship internationally?", "Not yet - we currently ship within Nepal only. International shipping is planned for next year."),
    ("returns", "What is your return policy?", "You can return unused items with tags intact within 7 days of delivery. We offer a full refund or exchange for eligible items."),
    ("returns", "How do I start a return or exchange?", "Just tell me your order number and I'll register the return for you. You can also use the Returns page and pick a pickup window."),
    ("returns", "Are sale items returnable?", "Sale and clearance items are final sale and cannot be returned, but they can still be exchanged for a different size if available."),
    ("sizing", "How do I know which size to pick?", "Tell me your child's age and height in cm and I'll suggest a size. Kids' sizing runs roughly 92cm=2T, 104cm=4T, 110cm=5, 116cm=6."),
    ("sizing", "Do your clothes run small or large?", "Our garments fit true to the size chart. If your child is between sizes, we recommend sizing up for cotton items that may shrink slightly."),
    ("sizing", "Can I exchange for a different size?", "Yes - size exchanges are free within 7 days, subject to stock availability."),
    ("payment", "What payment methods do you accept?", "We accept eSewa, Khalti, fonepay, major debit/credit cards, and cash on delivery inside Nepal."),
    ("payment", "Is cash on delivery available?", "Yes, cash on delivery is available across most of Nepal for orders under NPR 15,000."),
    ("product", "What fabrics do you use?", "We mostly use soft combed cotton, organic cotton for baby items, and skin-friendly blends. Fabric details appear on each product page."),
    ("product", "Are the clothes safe for sensitive skin?", "Yes. Our baby and toddler ranges use GOTS-certified organic cotton with azo-free dyes, ideal for sensitive skin."),
    ("product", "How should I care for the clothes?", "Wash in cold water with mild detergent, tumble dry low or line dry in shade. Avoid bleach to keep prints and colours fresh."),
    ("orders", "Can I change or cancel my order?", "Orders can be changed or cancelled within 2 hours of placing them, before dispatch. Share your order number and I'll help."),
    ("orders", "Will I get an invoice?", "Yes, a digital invoice is emailed and attached to your order confirmation. GST invoices are available on request."),
    ("loyalty", "Do you have a loyalty or rewards program?", "Yes - our 'Little Steps' program gives you points on every purchase that you can redeem for discounts on future orders."),
]

SIZE_CHART = [
    ("0-6M", 0, 0, 50, 61, 43, 42),
    ("6-12M", 1, 1, 62, 73, 47, 45),
    ("12-18M", 1, 1, 74, 81, 49, 47),
    ("18-24M", 2, 2, 82, 91, 51, 49),
    ("2T", 2, 2, 92, 97, 53, 50),
    ("3T", 3, 3, 98, 103, 55, 51),
    ("4T", 4, 4, 104, 110, 57, 52),
    ("5", 5, 5, 111, 116, 59, 54),
    ("6", 6, 6, 117, 122, 61, 55),
    ("7", 7, 7, 123, 128, 63, 57),
    ("8", 8, 8, 129, 134, 65, 58),
    ("10", 9, 10, 135, 146, 69, 61),
    ("12", 11, 12, 147, 158, 73, 64),
]

ORDERS = [
    ("KF10001", "Sita Rai", "delivered", 6, "Delivered on", "Pathao", "PT88421095", 2490, "1x Rainbow Twirl Party Dress (4T)"),
    ("KF10002", "Ramesh Thapa", "in_transit", 2, "Arriving in 1-2 days", "Aramex", "AR3391120", 3280, "1x Puffer Jacket (6) + 1x Bunny Socks Pack"),
    ("KF10003", "Anita Gurung", "processing", 0, "Dispatches within 24 hours", "", "", 1490, "1x Striped Cotton T-Shirt Pack (6)"),
    ("KF10004", "Bikash Shrestha", "out_for_delivery", 1, "Arriving today", "Pathao", "PT88421233", 4590, "1x Lehenga Choli Set (6)"),
    ("KF10005", "Pooja Karki", "delivered", 12, "Delivered on", "NCM", "NCM77201", 2190, "1x Denim Dungaree Set (3T)"),
    ("KF10006", "Sujan Maharjan", "returned", 20, "Refund processed", "Pathao", "PT88420011", 2790, "1x Unicorn Dream Layered Dress (5)"),
    ("KF10007", "Nisha Adhikari", "cancelled", 9, "Cancelled - refunded", "", "", 1690, "1x Hooded Sweatshirt (4T)"),
    ("KF10008", "Deepak Basnet", "in_transit", 3, "Arriving in 2-3 days", "Aramex", "AR3391244", 5380, "1x Kurta Pyjama Set (8) + 1x School Trousers (8)"),
    ("KF10009", "Sunita Limbu", "processing", 0, "Dispatches within 24 hours", "", "", 1290, "1x Cotton Casual A-Line Frock (2T)"),
    ("KF10010", "Hari Bahadur", "out_for_delivery", 1, "Arriving today", "NCM", "NCM77290", 2590, "1x Bandhani Print Ethnic Set (3T)"),
]


def seed() -> None:
    init_db()
    with get_session() as db:
        # wipe (idempotent seed)
        for model in (Message, ChildProfile, Conversation, Order, Faq, SizeChart, Product):
            db.query(model).delete()

        for row in PRODUCTS:
            db.add(Product(
                sku=row[0], name=row[1], category=row[2], gender=row[3], occasion=row[4],
                style_tags=row[5], age_min=row[6], age_max=row[7], sizes=row[8], color=row[9],
                fabric=row[10], price=row[11], rating=row[12], stock=row[13],
                image_emoji=row[14], description=row[15],
            ))

        for topic, question, answer in FAQ_ITEMS:
            db.add(Faq(topic=topic, question=question, answer=answer))

        for row in SIZE_CHART:
            db.add(SizeChart(
                label=row[0], age_min=row[1], age_max=row[2],
                height_min_cm=row[3], height_max_cm=row[4], chest_cm=row[5], waist_cm=row[6],
            ))

        for code, name, status, days_ago, eta, carrier, tracking, total, items in ORDERS:
            db.add(Order(
                order_code=code, customer_name=name, status=status,
                placed_at=utcnow() - timedelta(days=days_ago),
                eta=eta, carrier=carrier, tracking_no=tracking,
                total=total, items_summary=items,
            ))

    print(f"Seeded {len(PRODUCTS)} products, {len(FAQ_ITEMS)} FAQs, "
          f"{len(SIZE_CHART)} size rows, {len(ORDERS)} orders.")


if __name__ == "__main__":
    seed()
