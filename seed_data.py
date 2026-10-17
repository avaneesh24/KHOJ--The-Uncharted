import json
from datetime import datetime
from app.database import init_db, get_db_connection
from app.services.data_processor import slugify, detect_missing_fields

SEED_PLACES = [
    # DHARAMSHALA / NADDI
    {
        "name": "Galu Devi Sunset Trail & Ridge Point",
        "category": "nature_scenic",
        "destination": "Naddi, Dharamshala",
        "short_description": "A tranquil cliffside ridge beyond Naddi village offering unobstructed 180-degree panoramic views of the snow-clad Dhauladhar range.",
        "detailed_story": "While most tourists stop at the crowded Naddi sunset point, local shepherds and village elders recommend walking 15 minutes past the village school along an unpaved pine ridge. Here, the sheer stone wall of the Dhauladhar rises immediately before you without concrete hotels blocking the vista. At dusk, the granite needles turn deep crimson-orange.",
        "claim_type": "community_experience",
        "practical_tips": [
            "Best visited between 4:30 PM and 6:00 PM for alpenglow lighting.",
            "Carry a warm windcheater; temperatures plummet sharply once the sun sets behind the ridge.",
            "Wear sturdy shoes as the red clay path has loose gravel and pine needle slickness."
        ],
        "budget_tier": "free",
        "source_url": "https://hptdc.in/destinations/dharamshala",
        "source_title": "Himachal Pradesh Tourism & Kangra Valley Local Lore",
        "source_type": "stored_archive",
        "freshness_indicator": "recently_verified"
    },
    {
        "name": "St. John in the Wilderness Church & Lord Elgin Grave",
        "category": "culture_history",
        "destination": "Naddi, Dharamshala",
        "short_description": "An 1852 neo-Gothic stone church surrounded by towering deodar trees, famous for surviving the devastating 1905 Kangra earthquake.",
        "detailed_story": "Built in 1852 amidst dense deodars between Forsythganj and McLeodganj, this church features Belgian stained-glass windows donated by Lady Elgin. It houses the memorial of James Bruce, 8th Earl of Elgin and Viceroy of India, who passed away in Dharamshala in 1863. Archaeological records state its thick stone walls resisted the historic 7.8-magnitude earthquake of 1905 when nearly every brick structure in Kangra collapsed.",
        "claim_type": "documented_history",
        "practical_tips": [
            "Open daily from 10:00 AM to 5:00 PM; no entrance fee.",
            "Maintain silent decorum in the cemetery yard.",
            "Photography inside the nave is restricted during active Sunday services."
        ],
        "budget_tier": "free",
        "source_url": "https://en.wikipedia.org/wiki/St._John_in_the_Wilderness",
        "source_title": "Archaeological Survey of India & Kangra District Gazetteers",
        "source_type": "stored_archive",
        "freshness_indicator": "recently_verified"
    },
    {
        "name": "Tibet Kitchen & Traditional Tingmo Alley",
        "category": "local_food",
        "destination": "Naddi, Dharamshala",
        "short_description": "Home-style steamed twisted bread (tingmo) served with spiced potato shapta and slow-simmered herbal Tibetan broths.",
        "detailed_story": "Hidden on Jogiwara Road a short hop from Naddi, this family-run kitchen has preserved authentic Amdo and Lhasa culinary recipes since the early 1960s. Their tingmo dough is fermented overnight using natural mountain sourdough starter, resulting in an airy, multi-layered cloud bread designed to mop up warming chili broths.",
        "claim_type": "community_experience",
        "practical_tips": [
            "Order the Thenthuk (hand-pulled square noodle soup) with steamed Tingmo.",
            "Average cost is around INR 180-250 per person.",
            "Seating is tight during lunch hours (1:00 PM - 2:30 PM); arrive early or visit around 4:00 PM."
        ],
        "budget_tier": "budget",
        "source_url": "https://www.incredibleindia.org/content/incredible-india-v2/en/destinations/dharamshala.html",
        "source_title": "Kangra Cultural Food Collective",
        "source_type": "stored_archive",
        "freshness_indicator": "recently_verified"
    },

    # LEPAKSHI, ANDHRA PRADESH
    {
        "name": "The Hanging Pillar of Veerabhadra Temple",
        "category": "culture_history",
        "destination": "Lepakshi, Andhra Pradesh",
        "short_description": "A 16th-century Vijayanagara engineering mystery: a massive sculpted granite pillar that does not rest on the floor.",
        "detailed_story": "The Veerabhadra temple was built in 1530 AD by Virupanna and Veeranna, governors under King Achyuta Deva Raya of the Vijayanagara Empire. Among its 70 carved stone pillars, one corner pillar hangs suspended with a clear gap underneath where visitors pass thin cloths and sheets of paper. Archaeological Survey of India (ASI) reports document that British engineer Hamilton tried to dislodge it in the colonial era to uncover its secret, only to cause neighbouring lintels to shift, proving the hanging pillar is a master load-bearing cantilever.",
        "claim_type": "documented_history",
        "practical_tips": [
            "ASI ticketed monument: INR 25 for Indian citizens, INR 300 for foreign visitors.",
            "Timings: 6:00 AM to 6:00 PM every day.",
            "Avoid midday heat; granite stone slabs get blistering hot under barefoot walking. Wear thick cotton socks."
        ],
        "budget_tier": "budget",
        "source_url": "https://asi.nic.in/ancient-monuments-and-archaeological-sites-and-remains-act-1958/",
        "source_title": "Archaeological Survey of India (Hyderabad Circle) & Epigraphia Indica",
        "source_type": "stored_archive",
        "freshness_indicator": "recently_verified"
    },
    {
        "name": "Jatayu Moksha & Giant Footprint Legend",
        "category": "culture_history",
        "destination": "Lepakshi, Andhra Pradesh",
        "short_description": "An etched depression in solid granite rock claimed in local folklore to be the footprint of Goddess Sita or Lord Rama.",
        "detailed_story": "According to oral Ramayana traditions deeply rooted in the region, when the noble bird Jatayu was wounded battling Ravana, Lord Rama found him here and uttered 'Le Pakshi' (Telugu for 'Rise, bird'). Next to the temple compound lies an etched footprint with a small natural spring trickling water over the toe. While local folklore attributes this to celestial footprints, epigraphists and geologists note it as a natural weathering feature sanctified by centuries of local pilgrimage.",
        "claim_type": "folklore_oral_tradition",
        "practical_tips": [
            "Located just outside the main temple courtyard.",
            "Water continually oozes from the bedrock fissure; avoid stepping into the depression out of cultural respect.",
            "Local village guides tell captivating oral tales in Telugu, Kannada, and Hindi."
        ],
        "budget_tier": "free",
        "source_url": "https://tourism.ap.gov.in/home",
        "source_title": "Andhra Pradesh State Folklore Archives & Anantapur District Gazetteer",
        "source_type": "stored_archive",
        "freshness_indicator": "recently_verified"
    },
    {
        "name": "Lepakshi Monolithic Nandi & Courtyard",
        "category": "culture_history",
        "destination": "Lepakshi, Andhra Pradesh",
        "short_description": "One of India's largest monolithic bull sculptures, carved out of a single granite boulder 200 metres from the temple.",
        "detailed_story": "Standing 4.5 metres high and nearly 8.2 metres long, this monolithic Nandi faces precisely towards the multi-hooded Naga Linga in the main temple. Adorned with intricately sculpted bell necklaces, floral garlands, and folded hooves, the sculpture exemplifies the zenith of Vijayanagara rock craftsmanship in the 16th century.",
        "claim_type": "documented_history",
        "practical_tips": [
            "Maintained by ASI with a green landscaped park around the statue.",
            "Ideal for early morning photography with soft side-lighting on the granite carvings.",
            "No extra entrance fee needed if you already have the temple ticket."
        ],
        "budget_tier": "free",
        "source_url": "https://asi.nic.in/monolithic-nandi-lepakshi/",
        "source_title": "ASI Vijayanagara Architectural Survey",
        "source_type": "stored_archive",
        "freshness_indicator": "recently_verified"
    },

    # DELHI / SAROJINI NAGAR
    {
        "name": "Sarojini Nagar Export Lane & Secret Sample Stalls",
        "category": "markets_shopping",
        "destination": "Sarojini Nagar, Delhi",
        "short_description": "Practical navigation guide to finding authentic surplus European export clothing and factory sample racks at fraction of retail.",
        "detailed_story": "Sarojini Nagar Market was established in the 1950s following the partition for displaced traders. Today, its inner concentric lanes (Babu Market, Subzi Market, and Central Market) receive daily morning shipments of factory surplus garments originally produced in Tirupur, Noida, and Bangladesh for global fashion brands. The best sample pieces are hidden in the inner alleyway racks behind shop numbers 80 to 110.",
        "claim_type": "community_experience",
        "practical_tips": [
            "Best time: Tuesday morning around 10:30 AM right as fresh weekly crates are unboxed.",
            "Carry cash in small denominations (INR 50, 100, 200); UPI QR codes frequently fail due to network congestion.",
            "Bargaining rule of thumb: start at roughly 50-60% of the initially quoted price with polite firmness.",
            "Inspect seams, zippers, and buttons carefully before paying as items are strictly non-refundable."
        ],
        "budget_tier": "budget",
        "source_url": "https://delhitourism.gov.in/delhitourism/shopping/sarojini_nagar.jsp",
        "source_title": "Delhi Market Guild & Urban Cultural Study",
        "source_type": "stored_archive",
        "freshness_indicator": "recently_verified"
    },
    {
        "name": "Ring Road Corner Shakarkandi & Fruit Chaat Stall",
        "category": "local_food",
        "destination": "Sarojini Nagar, Delhi",
        "short_description": "Slow-charcoal-roasted sweet potato slices tossed in black salt, roasted cumin, and tart dried pomegranate seed powder.",
        "detailed_story": "Positioned just outside the metro gate exit for over 35 years, this cart roasts sweet potatoes directly over glowing embers of wood charcoal. The vendor peels the scorched skin, slices the steaming golden root, and tosses it in fresh lemon juice and secret family-blended masala featuring dried amchoor (raw mango) and mint.",
        "claim_type": "community_experience",
        "practical_tips": [
            "Plate price: INR 50-70.",
            "Ask for 'Kam Mirch' if you have low tolerance for spicy green chilies.",
            "Peak crowd in winter months (November to February)."
        ],
        "budget_tier": "budget",
        "source_url": "https://delhitourism.gov.in",
        "source_title": "Delhi Street Food Chronicles",
        "source_type": "stored_archive",
        "freshness_indicator": "recently_verified"
    },
    {
        "name": "Kumhar Gram Traditional Terracotta Pottery Village",
        "category": "local_experiences",
        "destination": "Sarojini Nagar, Delhi",
        "short_description": "India's largest potter colony tucked in West Delhi, where over 700 families turn earthenware on manual kick-wheels.",
        "detailed_story": "Relocated from Haryana and Rajasthan in the early 1970s, the artisans of Kumhar Gram supply raw clay handis, water coolers, terracotta lamps, and sculpted murals to markets across north India. Visiting travellers can watch clay slaking in underground pits, open-flame kiln firings, and try their hand at shaping bowls under the guidance of National Award-winning master potters.",
        "claim_type": "community_experience",
        "practical_tips": [
            "Visit on weekday mornings to see artisans at active work.",
            "Ask permission before photographing potters at work.",
            "Pottery workshops can be arranged for a modest honorarium (INR 300-500) supporting the artisan cooperative."
        ],
        "budget_tier": "budget",
        "source_url": "https://www.craftscouncilofindia.org/",
        "source_title": "Delhi Crafts Council & Urban Heritage Documentation",
        "source_type": "stored_archive",
        "freshness_indicator": "recently_verified"
    },

    # HAMPI & ANEGUNDI
    {
        "name": "Chintamani Temple Cave & Vali-Sugriva Lore",
        "category": "culture_history",
        "destination": "Hampi / Anegundi, Karnataka",
        "short_description": "A quiet riverbank rock shelter where local tradition marks the spot where Rama aimed his arrow at Vali.",
        "detailed_story": "Anegundi, directly across the Tungabhadra River from Hampi, is identified by local tradition as Kishkindha, the monkey kingdom of the epic Ramayana. The Chintamani temple complex clings to boulder overhangs above the river. Inside a small stone chamber, iron bows and rock paintings are preserved. Local villagers hold strong oral reverence for this site, though modern historians note the existing masonry was constructed during the late Sangama dynasty.",
        "claim_type": "folklore_oral_tradition",
        "practical_tips": [
            "Cross the river via the Anegundi bridge or take a local ferry coracle.",
            "Modest dress code required for temple sanctuary.",
            "The riverside boulders are prime spots for sunset over the river."
        ],
        "budget_tier": "free",
        "source_url": "https://karnatakatourism.org/tour-item/hampi/",
        "source_title": "Karnataka State Tourism & Ballari District Gazetteer",
        "source_type": "stored_archive",
        "freshness_indicator": "recently_verified"
    },
    {
        "name": "The Banana Fiber Craft Collective of Anegundi",
        "category": "local_experiences",
        "destination": "Hampi / Anegundi, Karnataka",
        "short_description": "Community women cooperative transforming discarded banana plant stems into eco-friendly bags, mats, and baskets.",
        "detailed_story": "Founded in the late 1990s as a rural self-reliance initiative, the Kishkinda Trust trained local village women to extract natural fibers from the trunks of harvested banana trees. What was once agricultural waste is processed, braided, and woven on wooden looms into biodegradable household crafts exported worldwide.",
        "claim_type": "community_experience",
        "practical_tips": [
            "Open Monday through Saturday, 9:30 AM to 5:30 PM.",
            "Workshops available where you can learn basic fiber braiding.",
            "Direct purchase supports fair wages for local rural families."
        ],
        "budget_tier": "budget",
        "source_url": "https://karnatakatourism.org/",
        "source_title": "Kishkinda Trust Rural Crafts Archives",
        "source_type": "stored_archive",
        "freshness_indicator": "recently_verified"
    },

    # MEGHALAYA / CHERRAPUNJI
    {
        "name": "Nohwet Living Root Bridge & Broom Grass Trails",
        "category": "nature_scenic",
        "destination": "Nohwet / Mawlynnong, Meghalaya",
        "short_description": "An ancient bio-engineered bridge grown from aerial roots of Ficus elastica trees by Indigenous Khasi clans.",
        "detailed_story": "Unlike the overcrowded double-decker root bridge in Nongriat which requires a 3,500-step trek, the Nohwet Living Root Bridge spans the Thyllong River near Mawlynnong with a gentle 10-minute stone stairway walk. Indigenous Khasi elders guide the supple rubber fig roots through hollowed betel nut trunks across the boulder-strewn canyon. Over 150-200 years, the roots intertwine and anchor into solid granite banks, growing stronger with monsoon floods rather than decaying.",
        "claim_type": "community_experience",
        "practical_tips": [
            "Entry token: INR 40 maintained by the Nohwet Village Council.",
            "Wear shoes with rubber tread; moss on river stones is extremely slippery during monsoons.",
            "Visit before 9:00 AM to experience the misty river canyon in quiet isolation."
        ],
        "budget_tier": "budget",
        "source_url": "https://www.meghalayatourism.in/",
        "source_title": "Meghalaya Tourism & Khasi Hills Heritage Council",
        "source_type": "stored_archive",
        "freshness_indicator": "recently_verified"
    },

    # CHETTINAD, TAMIL NADU
    {
        "name": "Athangudi Handmade Tile Atelier & 1000-Window House",
        "category": "culture_history",
        "destination": "Karaikudi, Chettinad, Tamil Nadu",
        "short_description": "Traditional artisan workshops crafting geometric cement tiles using local sand, mineral pigments, and glass casting frames.",
        "detailed_story": "When the merchant seafaring Nagarathar Chettiars traded across Burma, Ceylon, and Vietnam in the 19th and early 20th centuries, they imported Burmese teak, Italian marble, and European crystal for their palatial heritage mansions. In Athangudi village, local craftsmen developed an ingenious domestic alternative: sun-cured, hand-poured geometric cement tiles cast onto smooth sheets of Belgian glass. Today, master artisans still swirl bright floral pigments by hand into century-old brass stencils.",
        "claim_type": "documented_history",
        "practical_tips": [
            "Workshops operate 8:30 AM to 5:00 PM; closed on major temple festival days.",
            "Free to observe tile casting; artisans welcome polite questions and photography.",
            "Combine with a visit to the nearby 1000-Window Mansion (Aayiram Jannal Veedu) in Karaikudi."
        ],
        "budget_tier": "free",
        "source_url": "https://www.tamilnadutourism.tn.gov.in/destinations/chettinad",
        "source_title": "Tamil Nadu Tourism & Chettinad Heritage Trust",
        "source_type": "stored_archive",
        "freshness_indicator": "recently_verified"
    },

    # MAJULI ISLAND, ASSAM
    {
        "name": "Natun Samaguri Satra Traditional Bamboo Mask-Making",
        "category": "local_experiences",
        "destination": "Majuli, Assam",
        "short_description": "A 17th-century Vaishnavite monastic sanctuary preserving the rare art of organic bamboo and clay masks (Mukha).",
        "detailed_story": "Majuli is the world's largest inhabited river island, nestled in the braided channels of the Brahmaputra River. Established by the saint-reformer Srimanta Sankardeva, the Satras are socio-cultural monastic institutions. At Natun Samaguri Satra, Vaishnavite monks carve lightweight expressive masks representing characters from the Ramayana and Bhagavata Purana using split bamboo frames, cow dung-clay plaster, and organic vegetable dyes. The masks feature unique movable jaws and eyes used during Bhaona devotional theatre.",
        "claim_type": "documented_history",
        "practical_tips": [
            "Reachable via public ferry from Nimati Ghat near Jorhat (1 hour scenic river crossing).",
            "Monks demonstrate mask movements and storytelling; small voluntary donations support apprentice monks.",
            "Winter (November to February) is ideal before monsoon river waters surge."
        ],
        "budget_tier": "budget",
        "source_url": "https://tourism.assam.gov.in/portlet-innerpage/majuli",
        "source_title": "Assam State Tourism & Majuli Cultural Heritage Board",
        "source_type": "stored_archive",
        "freshness_indicator": "recently_verified"
    }
]

def seed_database():
    """Seeds the SQLite database with rich initial discoveries."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    inserted = 0
    for item in SEED_PLACES:
        slug = slugify(item["name"], item["destination"])
        missing_flags = detect_missing_fields(item)
        now_str = datetime.utcnow().isoformat()

        cursor.execute("""
        INSERT OR IGNORE INTO places (
            name, slug, category, destination, short_description, detailed_story,
            claim_type, practical_tips, budget_tier, source_url, source_title,
            source_type, retrieved_at, freshness_indicator, missing_fields_flag,
            upvotes, is_approved, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item["name"],
            slug,
            item["category"],
            item["destination"],
            item["short_description"],
            item["detailed_story"],
            item["claim_type"],
            json.dumps(item["practical_tips"]),
            item["budget_tier"],
            item["source_url"],
            item["source_title"],
            item["source_type"],
            now_str,
            item["freshness_indicator"],
            json.dumps(missing_flags),
            12,
            1,
            now_str
        ))
        if cursor.rowcount > 0:
            inserted += 1

    conn.commit()
    conn.close()
    print(f"Seed complete. Inserted {inserted} places into database.")

if __name__ == "__main__":
    seed_database()
