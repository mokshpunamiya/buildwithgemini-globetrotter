import logging
from google.cloud import firestore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Hardcode project ID explicitly to prevent project number resolution issues on Agent Platform
PROJECT_ID = "qwiklabs-gcp-02-a6a16ea59f35"

SEED_DESTINATIONS = [
    {
        "id": "dest_kyoto",
        "name": "Kyoto Ancient Temples & Gardens",
        "city": "Kyoto",
        "country": "Japan",
        "category": "Culture & History",
        "description": "Explore thousand-year-old Buddhist temples, tranquil bamboo groves, and traditional tea houses.",
        "budget_tier": "$$$",
        "highlights": ["Fushimi Inari Shrine", "Arashiyama Bamboo Grove", "Kinkaku-ji (Golden Pavilion)"],
        "rating": 4.9,
    },
    {
        "id": "dest_paris",
        "name": "Paris Art & Culinary Discovery",
        "city": "Paris",
        "country": "France",
        "category": "Food & Dining",
        "description": "Immerse yourself in world-class art galleries, iconic cafes, and romantic river strolls.",
        "budget_tier": "$$$$",
        "highlights": ["Louvre Museum", "Eiffel Tower Sunset", "Montmartre Bakery Crawl"],
        "rating": 4.8,
    },
    {
        "id": "dest_banff",
        "name": "Banff Alpine Wilderness",
        "city": "Banff",
        "country": "Canada",
        "category": "Nature & Adventure",
        "description": "Turquoise glacial lakes, rugged mountain peaks, and abundant wildlife in the Canadian Rockies.",
        "budget_tier": "$$",
        "highlights": ["Lake Louise Kayaking", "Moraine Lake Sunrise", "Johnston Canyon Hike"],
        "rating": 4.9,
    },
    {
        "id": "dest_bali",
        "name": "Bali Coastal Wellness Retreat",
        "city": "Ubud",
        "country": "Indonesia",
        "category": "Beach & Relaxation",
        "description": "Lush rice terraces, serene wellness sanctuaries, and pristine tropical beaches.",
        "budget_tier": "$$",
        "highlights": ["Tegallalang Rice Terraces", "Uluwatu Temple Cliff", "Sacred Monkey Forest"],
        "rating": 4.7,
    },
    {
        "id": "dest_sf",
        "name": "San Francisco Bay & Tech Tour",
        "city": "San Francisco",
        "country": "USA",
        "category": "City & Architecture",
        "description": "Iconic Golden Gate views, historic cable cars, and vibrant neighborhood food scenes.",
        "budget_tier": "$$$",
        "highlights": ["Golden Gate Bridge", "Alcatraz Island", "Fisherman's Wharf"],
        "rating": 4.6,
    },
]

def seed_database():
    logger.info("Initializing Firestore client for project: %s", PROJECT_ID)
    db = firestore.Client(project=PROJECT_ID)
    
    collection_ref = db.collection("destinations")
    for dest in SEED_DESTINATIONS:
        doc_id = dest["id"]
        collection_ref.document(doc_id).set(dest)
        logger.info("Seeded destination document: %s (%s)", doc_id, dest["name"])
        
    logger.info("Successfully seeded %d destinations into Firestore!", len(SEED_DESTINATIONS))

if __name__ == "__main__":
    seed_database()
